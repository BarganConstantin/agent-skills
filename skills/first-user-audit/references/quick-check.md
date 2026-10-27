# Quick Check — one first-user journey

**What it is:** a smaller, read-only entry point to First User Audit. It uses the **current agent** to make **one real browser attempt** from the landing page to the first observable product value. It is **not** four independently isolated personas, a statistically valid usability study, or a production smoke test.

## What you need

- A local or explicitly isolated preview of an app; never use production or real customer accounts. Confirm the URL is safe, including redirects and third-party side effects.
- An agent with actual connected browser tools (such as [Playwright MCP](browser-setup.md)), working navigation/interactions/screenshots, and the ability to reset browser state. Installing the skill alone does not connect a browser.
- Test-only identities, sandbox integrations and backend-reset steps wherever the flow mutates state.
- A target project configured to ignore `qa/first-users/`, which may contain sensitive screenshots and logs.

**Independent subagents are not required in Quick Check.** Mark `independent_subagent: not-applicable` because this is explicitly one agent in one context, not a lower-isolation approximation to the four-persona experiment.

## Steps

1. Read the application code, relevant routes, and its expected first-time user journey. Define a **specific first-success state** before browsing, such as a test workspace created and shown on the dashboard, with proof visible in UI or test data. If ambiguous, ask the owner rather than guessing.
2. Record the target local/preview URL, app revision, browser/tool capability, and a fresh unauthenticated test start. Reset cookies, storage, auth and relevant backend state as safely as possible.
3. Use the `impatient` behavior in the [audit protocol](protocol.md): skim the landing page and click the first plausible primary CTA with minimal reading. Continue until **first success is objectively observed** or until the first meaningful error/ambiguity where this persona would abandon. **Do not force a happy path after abandonment.**
4. Capture real browser screenshots at friction (and success if reached), plus URL/route, expected/actual state, and reproduction steps. Never fabricate tool use, performance results or screen captures; redact credentials and personal data.
5. Write only `qa/first-users/baseline/impatient.json` using the [report schema](report-format.md). If first success was not reached, use `first_success.reached: false` and `clicks_to_success: null`. Set `capabilities.independent_subagent: "not-applicable"`; accurately mark screenshot/browser availability and limitations.
6. If Python 3.10+ is available, run the baseline-only reporter from the **target app root** (substitute the installed skill's actual path):

   ```bash
   python /path/to/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
   ```

   Optionally generate the [offline HTML report](html-report.md) using `html_report.py --root qa/first-users --baseline-only`. Use `--verify-evidence --project-root .` only when all evidence file paths are real and local. Otherwise report missing evidence explicitly.

7. Stop after the **one** journey. Report `Completed reports: 1/4` (or `0/4` if no valid record), explicitly list `skeptic`, `mobile`, and `breaker` as **not run**, and say that **cross-persona prioritization, fresh independent verification, and after-pass improvements were not tested**. Do not modify app code, pricing, policy, billing, configuration or product copy.

## Escalate to the full audit

If Quick Check reveals friction or the developer wants broader coverage, suggest **Audit only** (four personas, separate contexts when supported) or **Audit + Fix + Verify** (explicit opt-in, safety restrictions preserved). Those modes require checking independent subagent support or gaining explicit approval for a disclosed reduced-isolation alternative.

A single successful Quick Check **does not** demonstrate that the complete onboarding works for mobile, skeptical users, or adverse inputs. A single failed Quick Check **does not** estimate customer abandonment or retention.
