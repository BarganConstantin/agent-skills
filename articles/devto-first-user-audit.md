---
title: Your Signup Works. Would Four First-Time Users Make It Through?
published: false
description: A reproducible pre-launch QA workflow using Agent Skills, Playwright MCP, four simulated first-user personas, and evidence-backed before/after checks.
tags: ai, testing, opensource, webdev
---

A signup flow can pass every integration test and still be hard to use.

Imagine four people arriving at the same product page. One clicks whatever looks like the main button. Another reads the pricing and privacy pages before trusting the signup form. A third uses a narrow phone on a poor connection. The fourth enters bad data, navigates back, and double-clicks Submit.

They might not even reach the same error.

This is the idea behind **First User Audit**, an open-source Agent Skill I put together to run a structured pre-launch browser audit. It uses four simulated first-user behaviors, saves evidence of friction, prioritizes repeated problems, and runs a second pass after safe fixes.

The repository contains the skill, its protocol, a report format, and a small Python reporter with tests:

**[First User Audit on GitHub](https://github.com/BarganConstantin/agent-skills/tree/main/skills/first-user-audit)**

## Start with the first useful outcome

Before an agent opens the browser, it needs to know what the visitor is trying to accomplish.

For one app, that could be creating a workspace and reaching its dashboard. For another, it could be uploading a file and seeing the processed result. A successful signup response is not necessarily the first moment of value.

The skill asks the coding agent to inspect the application and write down a *testable first-success event*:

```text
Audience: a new user trying the product
Start: landing page, signed out
First success: [observable product-specific action and state]
Evidence: [UI state, route, or safe test data proving it]
Environment: localhost or isolated preview
```

If the first-success event is ambiguous, the agent must stop and ask the product owner. Guessing here would make every subsequent click count meaningless.

## Four ways to get stuck

The four personas are intentionally simple. Each changes one part of the visitor's behavior.

| Persona | What it tries | What counts as friction |
| --- | --- | --- |
| Impatient | Skims, clicks the obvious CTA, gives up quickly | An error or unclear next step |
| Skeptic | Checks price, terms, and privacy before signup | Missing or ambiguous commitments |
| Mobile | Tries a 375px viewport, with slow-3G simulation when supported | Hidden controls, horizontal overflow, stalls |
| Breaker | Enters invalid data, navigates back, double-submits | Bad validation, lost state, duplicate actions |

The agents run **sequentially**, not simultaneously. Every persona should begin with a fresh browser context and clean test data. This avoids one test changing the state seen by the next.

A genuine multi-agent runtime can give each persona separate context. If your tool cannot spawn independent subagents, the skill has to say so. Asking one model to pretend it launched four agents gives you weaker evidence and should be labeled accordingly.

The browser layer uses [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp), which gives a compatible AI agent navigation, interaction, snapshots, and screenshots. The skill checks whether those tools are actually connected before trying anything.

This setup matters for the mobile persona in particular. Setting the viewport to 375 CSS pixels can be verified. Simulating slow 3G may require additional browser capabilities. If the available integration cannot throttle the network, the report must say **not tested**, rather than treating an unthrottled mobile run as a slow-3G test.

## A screenshot needs a reproduction path

A screenshot of a broken form is helpful. The state that produced it is more useful.

For each blocker, the agent records the URL, journey stage, attempted action, expected behavior, actual behavior, a reproducible sequence, and the screenshot path. Each persona also records whether it reached first success and how many UI activation clicks it took. If it never succeeds, the click count is `null`.

The files live in the app being audited:

```text
qa/first-users/
├── baseline/
│   ├── impatient.json
│   ├── skeptic.json
│   ├── mobile.json
│   └── breaker.json
├── after/
│   ├── impatient.json
│   ├── skeptic.json
│   ├── mobile.json
│   └── breaker.json
├── evidence/
│   └── screenshots-of-observed-issues.png
└── summary.md
```

The JSON format makes the raw observations inspectable. It also makes it harder to quietly substitute a polished narrative for a failed browser run. The reporter refuses an empty baseline and, in strict mode, refuses to produce a completed comparison when any persona report is missing.

## Rank friction by the people who encounter it

Four personas can hit the same broken Submit button. That is one issue affecting four personas, not four separate bugs.

During consolidation, the agent assigns a stable ID to each issue. Observations share an ID only when they represent the same failure at the same step or component. Similar wording is not enough: two distinct failures on one page should stay separate.

The included reporter sorts by the number of *distinct simulated personas* affected, then severity. It also flags contradictory issue IDs for review. The script does not pretend to be a semantic duplicate detector.

That gives the engineer a practical order in which to investigate. It is not a statistically meaningful measure of how many real customers would be affected.

## Fix, then send someone in who hasn't seen the bug list

The original idea is to fix the issues in one pass. The skill makes that instruction narrower.

Reproducible implementation problems such as unreachable buttons, missing form errors, broken navigation, and unsafe retry behavior can often be fixed with a bounded code change and targeted tests. Pricing, terms of service, and privacy issues are recorded for the owner. Billing, authentication, security-sensitive logic, and production configuration do not get quietly modified by an AI agent.

After the safe fixes, four *fresh* agents repeat the same journeys without seeing the baseline issue list. Each gets the same success condition and persona behavior, but a clean context and reset test state.

Then the reporter produces a before/after comparison of:

- First-success completion for each simulated persona.
- Actual click counts, only for completed journeys.
- Which issue IDs still appear, disappear, or first appear in the second pass.
- Missing capabilities, changed test conditions, and owner decisions still needed.

The aim is to catch regressions and check whether the fix changes observed behavior. Four scripted journeys cannot demonstrate a statistically significant conversion lift.

## Try the skill

With Node.js 22.20+ and npm, install it in a compatible coding-agent project using the [skills CLI](https://www.skills.sh/docs/cli):

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

For an MCP client that supports the following configuration shape, Playwright MCP can be registered as:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest", "--isolated"]
    }
  }
}
```

This is a generic example; MCP client configuration locations vary. An isolated browser profile also does not automatically create isolated agent contexts.

With your application running locally, ask:

```text
Use the first-user-audit skill to test this app before launch.

Inspect the code and define the first successful user outcome.
Run the four browser personas sequentially with fresh test sessions.
Keep evidence in qa/first-users/. Fix safe technical problems,
then verify with four fresh agents who have not seen the issue list.
Use only localhost or an isolated preview, test accounts, and sandbox payments.
If a required capability is missing, stop and explain what is missing.
```

The collection includes a Python reporter with no runtime dependencies beyond the standard library:

```bash
# Baseline only
python /path/to/first-user-audit/scripts/summarize.py \
  --root qa/first-users --baseline-only

# Full comparison, requiring all eight persona reports
python /path/to/first-user-audit/scripts/summarize.py \
  --root qa/first-users --strict
```

Replace `/path/to/first-user-audit` with the path printed by the installer. Run these commands from the audited application root. Add `qa/first-users/` to that application's ignore rules before collecting artifacts.

## What I tested, and what I haven't

The candidate repository has **18 reporter tests**, six metadata tests, three HTTP fixture tests, and six MCP adapter tests. They cover synthetic report aggregation, missing evidence, conflicting issue IDs, environment mismatches, and transport failures. Unit tests do not establish that a model reliably behaves like a human user.

There is now a [reproducible local demonstration with reviewed screenshots and reports](https://github.com/BarganConstantin/agent-skills/tree/feat/first-user-audit-local-validation/examples/first-user-demo). Its browser sessions used the published v0.1.0 instructions, Microsoft Playwright MCP 0.0.83, and eight fresh agent contexts, running sequentially with fresh browser storage. The fixture has deliberately introduced defects; it is not a customer product.

In that controlled example, no baseline persona reached first success. All four fresh verification personas did, in 2, 5, 2 and 6 clicks. The baseline breaker stopped at the earlier CTA failure, so its invalid-input coverage was not comparable; a separate scripted check reproduced blank-name acceptance. Slow 3G and touch were not tested. Fresh contexts shared a filesystem, so context separation was not a claim of OS-level isolation.

Public skill discovery and project installation were checked for Claude Code and Codex. Claude Code's native command recognized the skill and returned an explicitly requested missing-target preflight stop. The Codex native invocation was blocked during startup by the test's macOS write-guard sandbox, before the skill ran. The browser study used the agent harness and a small real MCP HTTP adapter; it does not establish full browser execution through both native CLIs.

Those observations show that the workflow can collect inspectable evidence in a controlled fixture. They do not measure customer conversion, retention, time saved, or general bug-discovery accuracy. Before publishing this draft, the review-branch example link should be updated to the merged commit.

The biggest uncertainties are also straightforward: AI personas are influenced by their instructions; the same model family may repeat similar blind spots; first-success definitions can be wrong; browser capabilities differ between runtimes; and an AI-run QA pass does not replace accessibility testing or conversations with actual users.

The useful next experiment is to compare this workflow with a fixed Playwright test suite and a small real-user usability session on the same product, with issues categorized before reading the results.

If you try the skill, a good contribution is a reproducible issue it missed, a failure mode it catches consistently, or a change to the protocol that makes the evidence easier to verify.

**Code and contribution guide:** https://github.com/BarganConstantin/agent-skills
