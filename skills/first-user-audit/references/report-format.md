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

**Quick Check (one agent):** write only `baseline/impatient.json`. Set `capabilities.independent_subagent` to `not-applicable`, since no independently isolated subagent was used. Run the reporter with `--baseline-only` (never `--strict`). It will truthfully show **Completed reports: 1/4** and identify skeptic, mobile and breaker as **not run**. Do not extrapolate findings to the other perspectives or claim fresh independent verification.

**Vocabulary**:

- `phase`: `baseline` or `after`.
- `persona`: `impatient`, `skeptic`, `mobile`, `breaker`.
- `first_success.reached`: boolean. If `true`, `evidence` must be a non-empty string and `clicks_to_success` must be a non-negative integer. By default, textual success proof is accepted for backward compatibility. With `--verify-evidence`, this string must name a screenshot or other evidence file inside the project; textual proof is unsupported in that mode. If `false`, `clicks_to_success` must be `null` and success evidence can be `null`.
- `would_return`: `yes`, `no`, `uncertain` (simulated, not real user feedback).
- `severity`: `blocker`, `major`, `minor`.
- `category`: `technical`, `pricing`, `terms`, `privacy`.
- `capabilities`: verified, unavailable, unverified, or not-applicable as appropriate; disclose missing real browser/throttling capability.
- `issues[].id`: stable across phases. Duplicates across personas merge **by explicit ID only**; review and merge semantically equivalent IDs before running the reporter. A shared ID must have the same category, location, and stage within and across phases. Severity may change. Conflicts block strict mode and suppress before/after comparisons in ordinary mode.
- `location`: use a stable route/component identifier such as `/create#name`; keep transient snapshot references, test identities, query strings and before/after URLs in reproduction details instead. This lets the same issue be compared across fresh sessions.
- `evidence`: relative path(s) within the target project; never embed credentials or raw personal data.

The reporter validates core fields, prints phase completeness, sorts issues by unique personas affected and severity, and compares reachability/clicks between complete, comparable runs. Different environment URLs across phases prevent comparison; app revisions may differ between phases but must be consistent within each phase. Strict mode requires all eight reports and rejects comparability or shared-ID conflicts.

Each phase displays every persona's reported capabilities and limitations. Completed counts mean valid JSON records, not fully capable or successful execution. Capability strings (including `verified`) and limitation declarations are self-reported: they do not prove actual browser use, independence, fresh contexts, or throttling. Empty declarations do not establish capability or absence of limitations. Store evidence and logs for review.

Evidence filesystem validation is optional and independent of `--strict`. With `--verify-evidence`, every issue needs at least one evidence path, and every supplied issue path and non-null success proof must be a non-empty project-relative path resolving to an existing file. Absolute paths, `..` traversal (even if it would resolve inside the project), directories, missing files, and symlinks escaping the project are rejected. Symlinks that resolve to files inside the project are allowed. Paths are based on `--project-root`, which defaults to the current working directory, rather than the reports directory. The JSON schema is unchanged.

Without that flag, the reporter does not check evidence files, and textual success proof and empty issue evidence arrays retain their previous behavior. With it, only filesystem presence and containment are checked: file contents, screenshot authenticity, relevance to the claim, actual tool use, and successful execution remain unverified. A textual proof must be saved as an evidence file before this mode can check its path; existence alone does not validate its contents.

Run from the audited application root, replacing the absolute path with the installed skill directory:

```bash
python /absolute/path/to/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
python /absolute/path/to/first-user-audit/scripts/summarize.py --root qa/first-users --strict
python /absolute/path/to/first-user-audit/scripts/summarize.py --root qa/first-users --strict --verify-evidence --project-root /absolute/path/to/audited-application
```

## Offline HTML presentation (optional)

To inspect the same validated reports as a static offline page, use [html-report.md](html-report.md). It supports baseline-only and strict verification modes and does not change the JSON report contract. Content is HTML-escaped; evidence filenames are printed, not loaded or copied. Review sensitive fields before sharing.
