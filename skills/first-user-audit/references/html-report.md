# Offline HTML report

After collecting real audit reports, you can generate a **single, static HTML report** to inspect locally. It needs Python 3.10+ and only the standard library.

## Baseline-only report

From the audited application's project root, after the four persona runs:

```bash
python /absolute/path/to/first-user-audit/scripts/html_report.py --root qa/first-users --baseline-only
```

This produces `qa/first-users/summary.html`. Open it locally to review persona completion, prioritized findings, reproduction details, and the tool-capability limitations. Missing persona reports are explicitly labeled, not invented.

## After a permitted fix and verification pass

When all eight comparable reports exist:

```bash
python /absolute/path/to/first-user-audit/scripts/html_report.py \
  --root qa/first-users --strict --verify-evidence --project-root .
```

Strict mode rejects incomplete or incompatible comparisons. With `--verify-evidence`, paths and file existence are checked; **screenshot authenticity and relevance are never verified**. Use `--output /path/to/your-report.html` to select another destination.

The HTML renderer uses the same validation, aggregation, issue-ID conflict and comparability rules as the Markdown reporter. It does not run the agents, browser or tests.

## Share deliberately

- The page does not contain JavaScript, remote dependencies or telemetry. A restrictive content security policy is included.
- All strings from persona reports are escaped as text to prevent HTML/script injection.
- Evidence paths appear as *text*; screenshots are **not** embedded, fetched, or copied.
- Persona capabilities and limitations remain self-reported. A successful JSON parse does not demonstrate actual browser use.
- Review and redact personal data, credentials, and app details in JSON, HTML and referenced screenshots **before sharing**.
- Keep `qa/first-users/` ignored by the audited app. Generated HTML inherits that policy; publishing the file is a human decision.

For the input format see [report-format.md](report-format.md). For controlled historical evidence see the [v0.2.0 example](https://github.com/BarganConstantin/agent-skills/tree/v0.2.0/examples/first-user-demo).
