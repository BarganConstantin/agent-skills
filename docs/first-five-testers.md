# Try First User Audit — the first five independent testers

**The goal:** learn whether a developer can complete a real, read-only first-user QA run on *their own safe web app* and whether the resulting findings are useful. This is an invitation for feedback, not a promise of early-access privileges, free consulting, or a request for stars.

You only need an Agent Skills-compatible coding agent and a working browser MCP. **Do not test production**, share client credentials, or post private screenshots. If a prerequisite fails, a report of where you were blocked is just as useful.

## 1. Install the skill in your web-app project

Node.js 22.20+ and npm are recommended for the current skills CLI workflow:

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

This installs the instructions; it does not connect a browser or run an audit. If you would rather confirm that the repository can be discovered *without installing*, use `npx skills add BarganConstantin/agent-skills --list`.

## 2. Connect Playwright MCP to your coding agent

Choose **one** client, not both. These commands register a browser MCP connection; they do not launch the audited application or bypass its permissions.

**Claude Code**

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

Restart/open your coding-agent session and confirm that it exposes actual browser tools. For a browser profile that is discarded on close, configure the server with `--isolated` using your MCP client's documented configuration mechanism, as described in [browser setup](../skills/first-user-audit/references/browser-setup.md). Do not assume that a default persistent browser has clean storage.

**Codex CLI**

```bash
codex mcp add playwright -- npx @playwright/mcp@latest --isolated
codex mcp list
```

The second command only lists configured servers; **still test actual browser navigation** in the agent session. For other clients, refer to [Playwright MCP official setup](https://playwright.dev/mcp/clients) and our [capability checks](../skills/first-user-audit/references/browser-setup.md).

These are *documented setup commands*, not a claim that every OS/client installation has been tested end to end by this repository.

## 3. Start a safe web application

Run your own app on localhost or an isolated preview with synthetic data. Use test accounts; disable or sandbox external notifications, billing and email sending. Confirm the initial URL **and any redirects** remain within permitted test infrastructure. A production URL or an app with unsafe integrations is a valid reason to stop.

Ensure the project ignores `qa/first-users/` (including screenshots, account traces, JSON and HTML reports).

## 4. Ask your agent to do one Quick Check

Copy this into an agent session where the skill is installed:

```text
Use first-user-audit in QUICK CHECK mode on this web app.

Read its SKILL.md and quick-check protocol. Before browsing, verify
the local/isolated environment, browser MCP tools, safe test identities,
and a fresh/resettable browser state. Stop if any safety prerequisite
is missing.

Define one observable first-success event, then follow the first
plausible primary action as a new visitor, without forcing success.
Use real browser interactions and collect screenshots/reproduction
steps for any friction. Never modify the app or business copy.

Write only the impatient baseline JSON and optionally render the
baseline Markdown/HTML summary. Report the actual outcome, 1/4
coverage, and all missing capabilities. Do not invent other personas.
```

The expected deliverable is a single `qa/first-users/baseline/impatient.json`, not a full four-persona evaluation. If Python 3.10+ is available, generate a summary with:

```bash
python /path/to/installed/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
```

Replace the script location with the actual installed skill path. The reporter validates JSON but **does not verify screenshots or agent behavior**.

## 5. Tell us what happened

[**Open the structured Quick Check feedback form**](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml).

Successful run, unclear finding, missing browser tool, blocked install, misleading instructions—all are valuable. Report the agent name and outcome and explain where you got stuck. Before posting, **redact URLs for private environments, secrets, user data and screenshots**. A private report is not required to give feedback; use generalized reproduction steps.

### What we will count

- Each independent tester who *voluntarily* reports an attempt, including failures.
- Whether the skill installed and browser MCP actually connected.
- Whether a safe first journey ran and whether a report was produced.
- Whether any observed issue was independently reproduced by the developer.

**What we won't claim:** anonymous installs as successful audits, reviewer comments as conversion lift, fixture-only outcomes as generalized skill effectiveness, or personal data as marketing material. Testimonials or real-app screenshots are never reused without explicit consent.

If you want the full four-persona workflow after Quick Check, see [the main skill instructions](../skills/first-user-audit/SKILL.md). This beta request is intentionally focused on one initial journey.
