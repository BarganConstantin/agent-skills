# Evidence-first evaluation scoring

This directory contains a **local, standard-library Python scorer** for reviewed agent-skill evaluation runs. It does **not** launch an agent, execute browser automation, review screenshots, or independently determine whether a finding is valid.

Its job is to avoid misleading benchmark summaries: incomplete runs stay visible, duplicate issues do not inflate recall, clean fixtures reveal false positives, and matched skill/control pairs are required before publishing a comparison.

## Before scoring

1. Pre-register fixture defects and first-success predicates **before** any agent attempts. Record the app revision, browser, model, agent harness, browser MCP version, initial data, randomized run order, and time/tool/token budget outside the scorecard.
2. Prepare at least one clean fixture (no seeded defects) and a held-out independent application. A public deliberately broken fixture cannot establish generalization.
3. For every fixture and repetition, execute a **control** arm with ordinary QA instructions and a **skill** arm with First User Audit installed. Keep model, tools, budget, and start conditions comparable. Reset backend state, browser storage and test identities between attempts.
4. Save all attempted runs, **including failed and stopped** runs. Review findings separately against the frozen defect truth set. Redact sensitive material before any publication.
5. Use a reviewer who did not generate the agent output where possible. Reviewer labels are not automatically authenticated or checked for bias by the scorer.

See [the full experimental protocol](../docs/evaluation.md).

## Manifest JSON (pre-registered)

The following is an **illustrative shape, not measured data and not an existing fixture**:

```json
{
  "schema_version": 1,
  "fixtures": [
    {"fixture_id": "sample-broken-app", "truth_ids": ["FX-001", "FX-002"]},
    {"fixture_id": "sample-clean-app", "truth_ids": []}
  ]
}
```

A clean fixture deliberately has an empty `truth_ids` list. Its recall is *not applicable*; false-positive findings are still counted.

## Reviewed attempts JSON

After actual executions, record an attempt using this shape. These placeholder strings are **documentation only**, not real evaluation observations:

```json
{
  "schema_version": 1,
  "data_kind": "real_evaluation",
  "runs": [
    {
      "run_id": "unique-real-attempt-id",
      "fixture_id": "sample-broken-app",
      "pair_id": "same-id-for-matched-control-and-skill-repetition",
      "arm": "control",
      "status": "completed",
      "findings": [
        {
          "finding_id": "actual-agent-finding-id",
          "review": {
            "verdict": "matched",
            "truth_id": "FX-001",
            "reviewer": "reviewer-pseudonym",
            "evidence_checked": true,
            "reproduction_checked": true
          }
        }
      ]
    }
  ]
}
```

Allowed verdicts are `matched`, `false_positive`, and `unreviewed`. For false-positive or unreviewed findings, set `truth_id` to `null` or omit it. Completed runs with no findings have `findings: []`. Include every real run; do not copy the example and label it an experiment.

For honest failure accounting, `status` may also be `stopped` or `failed`. These runs remain in output but block an overall paired comparison until the experiment is complete. `pair_id` identifies the *same fixture and repetition* under both arms, not the two outputs from one agent execution.

## Score

From the repository root, with your own saved manifest and actual reviewed attempts:

```bash
python evals/score.py --manifest /path/to/frozen-manifest.json \
  --reviews /path/to/adjudications.json \
  --output /path/to/score.json
```

Outputs include per-run confirmed distinct defect matches, false-positive findings, redundant matches, evidence/reproduction review counts, and recall/precision where defined. Aggregate mean recall and false-positive deltas are supplied **only** if every included fixture has paired complete, reviewed runs. When a fixture has no ground-truth defects, recall is `null`; it still contributes to false-positive comparisons.

**Limitations:** a reviewer can mislabel a finding; simply marking `evidence_checked: true` does not prove the screenshot is genuine. Small synthetic samples do not estimate human conversion, statistical significance, or a model's general capability. Save the independent raw reports and reviewer notes in your own secured workspace.

Run scorer regression tests without installing browser dependencies:

```bash
python -m unittest discover -s tests -v
```

**No skill-vs-control performance results are claimed by this directory until independent runs are collected and published.**
