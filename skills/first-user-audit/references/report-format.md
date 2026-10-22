# Per-persona report format

Create one file per persona and phase:

```
qa/first-users/
  baseline/impatient.json
  baseline/skeptic.json
  baseline/mobile.json
  baseline/breaker.json
  after/impatient.json
  after/skeptic.json
  after/mobile.json
  after/breaker.json
  evidence/*.png
  summary.md                # generated
```

The JSON document uses the following structure. This is an **illustrative schema shape, not a test result**:

```json
{
  "phase": "baseline",
  "persona": "impatient",
  "environment": "http://localhost:3000",
  "app_revision": "local-git-sha-or-other-identifier",
  "first_success": {
    "name": "observed product-specific success predicate",
    "reached": false,
    "evidence": null
  },
  "clicks_to_success": null,
  "would_return": "uncertain",
  "would_return_reason": "a brief, clearly simulated persona judgment",
  "capabilities": {
    "browser_mcp": "verified",
    "independent_subagent": "verified",
    "fresh_browser_context": "verified",
    "viewport_375px": "not-applicable",
    "network_throttling": "not-applicable"
  },
  "issues": [
    {
      "id": "FUA-001",
      "stage": "signup",
      "location": "/signup#submit",
      "summary": "a concise observation, without speculative impact",
      "category": "technical",
      "severity": "major",
      "reproduction": "reproducible steps using only test data",
      "expected": "observable expected behavior",
      "actual": "observable actual behavior",
      "evidence": ["qa/first-users/evidence/baseline-impatient-FUA-001.png"]
    }
  ],
  "limitations": []
}
```

**Vocabulary**:

- `phase`: `baseline` or `after`.
- `persona`: `impatient`, `skeptic`, `mobile`, `breaker`.
- `first_success.reached`: boolean. If `true`, `evidence` must be a non-empty string and `clicks_to_success` must be a non-negative integer. If `false`, `clicks_to_success` must be `null`.
- `would_return`: `yes`, `no`, `uncertain` (simulated, not real user feedback).
- `severity`: `blocker`, `major`, `minor`.
- `category`: `technical`, `pricing`, `terms`, `privacy`.
- `capabilities`: verified, unavailable, unverified, or not-applicable as appropriate; disclose missing real browser/throttling capability.
- `issues[].id`: stable across phases. Duplicates across personas merge **by explicit ID only**; review and merge semantically equivalent IDs before running the reporter.
- `evidence`: relative path(s) within the target project; never embed credentials or raw personal data.

The reporter validates core fields, prints phase completeness, sorts issues by unique personas affected and severity, and compares reachability/clicks between complete runs. The reporter **does not** confirm screenshots really exist, guarantee independence, or infer successful execution from written claims. Store evidence and logs for review.

Run from the audited application root, replacing the absolute path with the installed skill directory:

```bash
python /absolute/path/to/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
python /absolute/path/to/first-user-audit/scripts/summarize.py --root qa/first-users --strict
```
