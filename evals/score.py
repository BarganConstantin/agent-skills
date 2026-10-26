#!/usr/bin/env python3
"""Score independently reviewed Agent Skill evaluations.

No models or browsers run here. Matching judgments are human-supplied;
never present scorer output as independently verified agent performance.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ARMS = ("control", "skill")
STATUSES = ("completed", "stopped", "failed")
VERDICTS = ("matched", "false_positive", "unreviewed")


class EvalError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvalError(message)


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty string required")
    return value.strip()


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvalError(f"Cannot load {path}: {exc}") from exc


def validate_manifest(doc):
    require(isinstance(doc, dict) and doc.get("schema_version") == 1, "manifest schema_version must be 1")
    fixtures = doc.get("fixtures")
    require(isinstance(fixtures, list) and fixtures, "manifest.fixtures must be nonempty list")
    truths = {}
    for n, fixture in enumerate(fixtures):
        require(isinstance(fixture, dict), f"fixture[{n}] must be object")
        fid = string(fixture.get("fixture_id"), f"fixture[{n}].fixture_id")
        require(fid not in truths, f"duplicate fixture ID: {fid}")
        defects = fixture.get("truth_ids")
        require(isinstance(defects, list), f"{fid}: truth_ids must be a list (empty for clean fixtures)")
        require(all(isinstance(x, str) and bool(x.strip()) for x in defects), f"{fid}: truth_ids must be strings")
        require(len(defects) == len(set(defects)), f"{fid}: duplicate truth IDs")
        truths[fid] = set(defects)
    return truths


def score_run(run, truth, seen_run_ids):
    require(isinstance(run, dict), "run must be object")
    run_id = string(run.get("run_id"), "run_id")
    require(run_id not in seen_run_ids, f"duplicate run_id: {run_id}")
    seen_run_ids.add(run_id)
    fixture_id = string(run.get("fixture_id"), f"{run_id}.fixture_id")
    require(fixture_id in truth, f"{run_id}: unknown fixture_id {fixture_id}")
    arm = run.get("arm")
    require(arm in ARMS, f"{run_id}: arm must be control or skill")
    pair_id = string(run.get("pair_id"), f"{run_id}.pair_id")
    status = run.get("status")
    require(status in STATUSES, f"{run_id}: invalid status")
    findings = run.get("findings")
    require(isinstance(findings, list), f"{run_id}: findings must be a list (empty if none)")
    ids = set()
    matches, fp, unreviewed = set(), 0, 0
    redundant, evidence_complete = 0, 0
    for i, finding in enumerate(findings):
        require(isinstance(finding, dict), f"{run_id}.findings[{i}]: object required")
        name = string(finding.get("finding_id"), f"{run_id}.findings[{i}].finding_id")
        require(name not in ids, f"{run_id}: duplicate finding_id {name}")
        ids.add(name)
        review = finding.get("review")
        require(isinstance(review, dict), f"{run_id}.{name}: review object required")
        verdict = review.get("verdict")
        require(verdict in VERDICTS, f"{run_id}.{name}: invalid verdict")
        reviewer = review.get("reviewer")
        if verdict != "unreviewed":
            string(reviewer, f"{run_id}.{name}: reviewer")
            require(type(review.get("evidence_checked")) is bool, f"{run_id}.{name}: evidence_checked boolean required")
            require(type(review.get("reproduction_checked")) is bool, f"{run_id}.{name}: reproduction_checked boolean required")
            if review["evidence_checked"] and review["reproduction_checked"]:
                evidence_complete += 1
        truth_id = review.get("truth_id")
        if verdict == "matched":
            require(isinstance(truth_id, str) and truth_id in truth[fixture_id], f"{run_id}.{name}: unknown matching truth_id")
            if truth_id in matches:
                redundant += 1
            else:
                matches.add(truth_id)
        else:
            require(truth_id is None, f"{run_id}.{name}: truth_id only allowed on matched findings")
            if verdict == "false_positive":
                fp += 1
            else:
                unreviewed += 1
    # Failed attempts are always counted; their incomplete findings do not
    # become a convenient "0%" comparison or disappear from the dataset.
    valid = status == "completed" and unreviewed == 0
    recall = round(len(matches) / len(truth[fixture_id]), 4) if valid and truth[fixture_id] else None
    precision = round(len(matches) / (len(matches) + fp), 4) if valid and (matches or fp) else None
    return {
        "run_id": run_id, "fixture_id": fixture_id, "pair_id": pair_id,
        "arm": arm, "status": status, "judged": unreviewed == 0,
        "reported_findings": len(findings), "true_positive_defects": len(matches),
        "false_positive_findings": fp, "redundant_matches": redundant,
        "unreviewed_findings": unreviewed, "fully_evidenced_findings": evidence_complete,
        "recall": recall, "precision": precision,
    }


def evaluate(manifest, reviews):
    truth = validate_manifest(manifest)
    require(isinstance(reviews, dict) and reviews.get("schema_version") == 1, "reviews schema_version must be 1")
    require(reviews.get("data_kind") == "real_evaluation", "reviews.data_kind must be 'real_evaluation'; synthetic examples cannot be used as measured results")
    runs = reviews.get("runs")
    require(isinstance(runs, list) and bool(runs), "reviews.runs must be nonempty list")
    seen, scored = set(), []
    pairs = defaultdict(dict)
    for run in runs:
        result = score_run(run, truth, seen)
        key = (result["fixture_id"], result["pair_id"])
        require(result["arm"] not in pairs[key], f"duplicate arm {result['arm']} in pair {key}")
        pairs[key][result["arm"]] = result
        scored.append(result)

    incomplete = []
    comparable_pairs = []
    for (fixture_id, pair_id), arms in sorted(pairs.items()):
        if set(arms) != set(ARMS):
            incomplete.append(f"{fixture_id}/{pair_id}: missing comparison arm")
            continue
        if any(arms[arm]["status"] != "completed" or not arms[arm]["judged"] for arm in ARMS):
            incomplete.append(f"{fixture_id}/{pair_id}: stopped, failed, or unreviewed run")
            continue
        control_recall, skill_recall = arms["control"]["recall"], arms["skill"]["recall"]
        comparable_pairs.append({
            "fixture_id": fixture_id, "pair_id": pair_id,
            "control_recall": control_recall, "skill_recall": skill_recall,
            "delta_recall": (round(skill_recall - control_recall, 4)
                             if control_recall is not None and skill_recall is not None else None),
            "control_false_positives": arms["control"]["false_positive_findings"],
            "skill_false_positives": arms["skill"]["false_positive_findings"],
        })

    # No aggregate comparison when an arm or fixture is missing or failed.
    comparison_available = bool(comparable_pairs) and not incomplete and set(truth) == {x["fixture_id"] for x in scored}
    if set(truth) != {x["fixture_id"] for x in scored}:
        incomplete.append("Not every declared fixture has been attempted")
    recall_deltas = [p["delta_recall"] for p in comparable_pairs if p["delta_recall"] is not None]
    fp_deltas = [p["skill_false_positives"] - p["control_false_positives"] for p in comparable_pairs]
    return {
        "schema_version": 1, "status": "reviewed_inputs_not_independently_verified",
        "run_count": len(scored),
        "completed_run_count": sum(r["status"] == "completed" for r in scored),
        "comparable_pair_count": len(comparable_pairs),
        "comparison_available": comparison_available,
        "comparison_blockers": incomplete,
        "mean_recall_delta_skill_minus_control": (round(mean(recall_deltas), 4)
                                                 if comparison_available and recall_deltas else None),
        "mean_false_positive_delta_skill_minus_control": (round(mean(fp_deltas), 4)
                                                          if comparison_available else None),
        "paired_results": comparable_pairs if comparison_available else [],
        "runs": scored,
        "disclaimer": "Human-supplied adjudications are not verified by this script. This tool does not run agents or browser audits, validate screenshot authenticity, prove reviewer independence, or measure real-user conversion.",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Score reviewed agent skill evaluations without fabricating runs")
    p.add_argument("--manifest", type=Path, required=True, help="Frozen fixture truth IDs")
    p.add_argument("--reviews", type=Path, required=True, help="Human adjudications of agent attempts")
    p.add_argument("--output", type=Path, help="Optional JSON results path")
    args = p.parse_args(argv)
    try:
        result = evaluate(load_json(args.manifest), load_json(args.reviews))
        output = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(output, end="")
        return 0
    except (EvalError, OSError) as error:
        p.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
