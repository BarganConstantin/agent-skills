# Five-minute practice lab: try First User Audit without your own app

**No SaaS signup, staging environment, credentials, payment details or customer data.** The repository includes a tiny local web app with deliberately planted onboarding problems. It runs with Python's standard library on `127.0.0.1`, so an agent with a real browser connection can make its first **read-only Quick Check** safely.

This is an **unblinded, public training fixture**, not a performance benchmark. The fixture source and answers are public. Browser CI verifies fixture behavior, not that an AI agent finds its defects.

## Start the sample app

In a terminal:

```bash
git clone https://github.com/BarganConstantin/agent-skills.git
cd agent-skills
python evals/fixtures/activation_lab.py --variant seeded --port 8765
```

Leave the terminal running. On systems where `python` is not available, use `python3` or `py`.

Open **http://127.0.0.1:8765/** in your own browser to confirm the fixture is reachable. The app stores only dummy workspace names in the browser's localStorage and makes no external API calls.

## Install the skill and connect your browser

In a **second terminal**, from the cloned repository root, install it to your coding agent:

```bash
npx skills add . --skill first-user-audit
```

Node.js 22.20+ and npm are required for the documented CLI path. The command only installs skill files: it does **not** run an audit or connect the browser.

Connect [Microsoft Playwright MCP](../skills/first-user-audit/references/browser-setup.md) through your coding agent. The agent must actually expose working navigation, interaction and screenshot tools. If the browser MCP cannot reach `127.0.0.1:8765`, stop and report the obstacle; a shell command alone does not grant browser access. For Claude Code and Codex-specific setup guidance, see [first-run guide](first-five-testers.md).

Ensure `qa/first-users/` is ignored in the target checkout, as supplied by this repository's `.gitignore`. Do not copy screenshots or traces containing private data into public issues.

## Run the Quick Check

Start your coding agent **inside the cloned repository**, with the sample web server still running. Paste:

```text
Use first-user-audit in QUICK CHECK mode, audit only.

Target: http://127.0.0.1:8765/
Environment: local Python stdlib synthetic training fixture; no external
accounts, notifications, payments, or production data.
First-success criterion: create a local workspace named "Sample Project"
and observe the "Workspace ready" state. A button click by itself is not
success.

Preflight the actual browser MCP connection, browser storage reset, and
the ignored qa/first-users/ artifact directory. Then follow the single
impatient visitor's first plausible primary CTA. Stop honestly if that
visitor is blocked or would abandon. Capture real browser screenshots
and reproduce what happened; do not modify the sample application.

Save only baseline/impatient.json, optionally generate baseline-only
Markdown/HTML with the installed reporter, and explicitly identify the
other three personas as NOT RUN. Do not claim independent subagents,
automated fixes, real users or conversion improvement.
```

You should see **either** an evidence-backed blocker **or** proof that the defined first-success state was reached. Do not prescribe a specific conclusion or make up screenshots.

## View or share the result

With Python 3.10+ you can generate a Markdown or HTML summary. Replace `/path/to/first-user-audit` with your installed skill directory:

```bash
python /path/to/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
python /path/to/first-user-audit/scripts/html_report.py --root qa/first-users --baseline-only
```

The reporter accepts incomplete four-persona coverage and should say **1/4** (or **0/4** if a valid report couldn't be generated). Evidence validation may optionally check local file paths and existence, but it does *not* prove screenshot authenticity or browser execution.

Inspect the generated `qa/first-users/summary.md` or `qa/first-users/summary.html` locally. Never commit private screenshots or test artifacts. If something is unclear, [open a first-run feedback issue](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml).

## Want to inspect the intentionally seeded problems?

Once your first run is over, read the [fixture's five known defects and verification tests](../evals/fixtures/README.md). Reading the answer key before the test makes it harder to judge what an agent independently notices—even though this example is not a blinded evaluation in any case.

For an evaluation on an unseen, independent app, use the [paired evaluation protocol](evaluation.md) instead. A successful local sample does **not** establish effectiveness on external real-world projects.
