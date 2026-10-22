#!/usr/bin/env python3
"""Validate and summarize independently collected, persona-level first-user reports.

Never fabricates data. Identical issue IDs are consolidated; semantic deduplication
and screenshot validity require human review.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

PERSONAS = ("impatient", "skeptic", "mobile", "breaker")
PHASES = ("baseline", "after")
SEVERITY = {"blocker": 3, "major": 2, "minor": 1}
CATEGORIES = {"technical", "pricing", "terms", "privacy"}


class ReportError(ValueError):
    pass


def _valid_record(record: dict, phase: str, persona: str, file: Path):
    def require(condition, text):
        if not condition:
            raise ReportError(f"{file}: {text}")

    require(isinstance(record, dict), "report must be an object")
    require(record.get("phase") == phase, f"phase must be {phase}")
    require(record.get("persona") == persona, f"persona must be {persona}")
    require(isinstance(record.get("environment"), str) and record["environment"].strip(), "environment required")
    require(isinstance(record.get("app_revision"), str) and record["app_revision"].strip(), "app_revision required")
    first = record.get("first_success")
    require(isinstance(first, dict), "first_success object required")
    require(isinstance(first.get("name"), str) and first["name"].strip(), "first_success.name required")
    reached = first.get("reached")
    require(type(reached) is bool, "first_success.reached must be boolean")
    clicks = record.get("clicks_to_success")
    if reached:
        require(type(clicks) is int and clicks >= 0, "successful run needs nonnegative click count")
        require(isinstance(first.get("evidence"), str) and first["evidence"].strip(), "successful run needs evidence")
    else:
        require(clicks is None, "unsuccessful run must have null clicks_to_success")
    require(isinstance(record.get("would_return"), str) and record["would_return"] in {"yes", "no", "uncertain"}, "invalid would_return")
    require(isinstance(record.get("would_return_reason"), str) and record["would_return_reason"].strip(), "would_return_reason required")
    require(isinstance(record.get("capabilities"), dict), "capabilities object required")
    require(isinstance(record.get("limitations"), list), "limitations array required")
    issues = record.get("issues")
    require(isinstance(issues, list), "issues array required")
    seen = set()
    for i, issue in enumerate(issues):
        require(isinstance(issue, dict), f"issues[{i}] must be an object")
        iid = issue.get("id")
        require(isinstance(iid, str) and re.fullmatch(r"FUA-\d{3,}", iid) is not None, f"issues[{i}] invalid id")
        require(iid not in seen, f"duplicate issue {iid} within one report")
        seen.add(iid)
        require(isinstance(issue.get("category"), str) and issue["category"] in CATEGORIES, f"{iid} invalid category")
        require(isinstance(issue.get("severity"), str) and issue["severity"] in SEVERITY, f"{iid} invalid severity")
        for field in ("stage", "location", "summary", "reproduction", "expected", "actual"):
            require(isinstance(issue.get(field), str) and issue[field].strip(), f"{iid} missing {field}")
        require(isinstance(issue.get("evidence"), list), f"{iid} evidence must be an array")
    return record


def load_reports(root: Path, phases=PHASES):
    result = {}
    missing = {}
    for phase in PHASES:
        if phase not in phases:
            result[phase], missing[phase] = {}, list(PERSONAS)
            continue
        reports, absent = {}, []
        for persona in PERSONAS:
            path = root / phase / f"{persona}.json"
            if not path.is_file():
                absent.append(persona)
                continue
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise ReportError(f"{path}: invalid JSON: {exc}") from exc
            reports[persona] = _valid_record(report, phase, persona, path)
        result[phase] = reports
        missing[phase] = absent
    return result, missing


def aggregate(reports):
    issues = {}
    conflicts = []
    for persona, record in reports.items():
        for entry in record["issues"]:
            iid = entry["id"]
            if iid not in issues:
                issues[iid] = {**entry, "personas": set()}
            else:
                prior = issues[iid]
                if entry["category"] != prior["category"] or entry["location"] != prior["location"]:
                    conflicts.append(f"{iid}: conflicting location/category; review manual deduplication")
                if SEVERITY[entry["severity"]] > SEVERITY[prior["severity"]]:
                    prior["severity"] = entry["severity"]
            issues[iid]["personas"].add(persona)
    return sorted(issues.values(), key=lambda row: (-len(row["personas"]), -SEVERITY[row["severity"]], row["id"])), conflicts


def comparability_warnings(reports):
    """Find mismatched success criteria or versions within a supposed fixed phase."""
    warnings = []
    criteria = {record["first_success"]["name"].strip() for phase in PHASES for record in reports[phase].values()}
    if len(criteria) > 1:
        warnings.append("first-success definition differs between persona reports")
    for phase in PHASES:
        revisions = {record["app_revision"] for record in reports[phase].values()}
        if len(revisions) > 1:
            warnings.append(f"{phase} uses more than one app revision")
        environments = {record["environment"] for record in reports[phase].values()}
        if len(environments) > 1:
            warnings.append(f"{phase} uses more than one environment URL")
    return warnings


def _escape_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def render(root: Path, reports: dict, missing: dict, baseline_only=False):
    lines = ["# First User Audit — generated summary", "", "**Scope:** simulated QA journeys, not human conversion data.",
             "**Method:** issue IDs are manually assigned and reused; aggregation counts distinct affected personas.", ""]
    phases = PHASES[:1] if baseline_only else PHASES
    aggregates = {}
    for phase in phases:
        data = reports[phase]
        issue_rows, conflicts = aggregate(data)
        aggregates[phase] = issue_rows
        lines += [f"## {phase.title()}", "", f"Completed reports: **{len(data)}/4**. Missing: {', '.join(missing[phase]) or 'none'}.", ""]
        if conflicts:
            lines += ["**Review duplicate ID conflicts:** " + "; ".join(sorted(set(conflicts))), ""]
        lines += ["| Persona | First success | Clicks to success | Would return (simulated) |",
                  "| --- | --- | --- | --- |"]
        for persona in PERSONAS:
            if persona in data:
                r = data[persona]
                lines.append(f"| {persona} | {'yes' if r['first_success']['reached'] else 'no'} | {r['clicks_to_success'] if r['clicks_to_success'] is not None else '—'} | {r['would_return']} |")
            else:
                lines.append(f"| {persona} | not run | — | — |")
        lines += ["", "| Issue ID | Affected personas | Severity | Category | Stage | Summary |",
                  "| --- | ---: | --- | --- | --- | --- |"]
        for r in issue_rows:
            lines.append(f"| {r['id']} | {len(r['personas'])}/4 ({', '.join(sorted(r['personas']))}) | {r['severity']} | {r['category']} | {_escape_cell(r['stage'])} | {_escape_cell(r['summary'])} |")
        if not issue_rows:
            lines.append("| — | 0 | — | — | — | No reported issues in available reports |")
        lines += [""]

    if not baseline_only:
        lines += ["## Before / after", ""]
        warnings = comparability_warnings(reports)
        if missing["baseline"] or missing["after"] or warnings:
            reason = "; ".join(warnings) if warnings else "incomplete persona coverage"
            lines += [f"**Comparison unavailable:** {reason}. Do not interpret these data as improvement.", ""]
        else:
            for phase in PHASES:
                data = reports[phase]
                successes = [r["clicks_to_success"] for r in data.values() if r["first_success"]["reached"]]
                lines += [f"- {phase}: {len(successes)}/4 simulated personas reached first success; median successful click count: {median(successes) if successes else 'N/A'}."]
            before = {r["id"]: len(r["personas"]) for r in aggregates["baseline"]}
            after = {r["id"]: len(r["personas"]) for r in aggregates["after"]}
            lines += ["", "| Issue ID | Before affected | After affected | Difference |",
                      "| --- | ---: | ---: | ---: |"]
            for iid in sorted(before.keys() | after.keys()):
                b, a = before.get(iid, 0), after.get(iid, 0)
                lines.append(f"| {iid} | {b}/4 | {a}/4 | {a-b:+d} |")
            if not before and not after:
                lines.append("| — | 0 | 0 | 0 |")
            lines += ["", "Changes in counts are descriptive observations in scripted AI personas, not statistically significant human conversion estimates.", ""]
    lines += ["## Integrity caveats", "", "- Reporter validates fields, but does not verify screenshots, independence, network throttling, actual browser use, or root-cause identity.",
              "- Review screenshots, raw reports, test output and fixes before publication. Do not commit private data.", ""]
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description="Summarize First User Audit reports; never fabricate missing runs")
    p.add_argument("--root", type=Path, default=Path("qa/first-users"), help="Target application's audit reports directory")
    p.add_argument("--output", type=Path, help="Write generated markdown here (default: ROOT/summary.md)")
    p.add_argument("--baseline-only", action="store_true", help="Allow summary before verification")
    p.add_argument("--strict", action="store_true", help="Require all 4 personas in each requested phase")
    args = p.parse_args(argv)
    if args.strict and args.baseline_only:
        p.error("--strict and --baseline-only cannot be combined")
    try:
        required = ("baseline",) if args.baseline_only else PHASES
        reports, missing = load_reports(args.root, required)
        if not reports["baseline"]:
            raise ReportError("no baseline reports found; refusing an empty summary")
        if args.strict and any(missing[phase] for phase in required):
            raise ReportError("missing reports: " + "; ".join(f"{phase}: {', '.join(missing[phase])}" for phase in required if missing[phase]))
        if args.strict:
            warnings = comparability_warnings(reports)
            if warnings:
                raise ReportError("not comparable: " + "; ".join(warnings))
        text = render(args.root, reports, missing, args.baseline_only)
    except ReportError as error:
        p.exit(2, f"Error: {error}\n")
    target = args.output or (args.root / "summary.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
