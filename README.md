# First User Audit

**Your app works. Can a first-time visitor reach the first useful result?**

First User Audit is an [Agent Skill](https://agentskills.io/specification) for **simulated first-user QA**. Run a safe, one-journey **Quick Check** or a four-persona browser audit to see where a new visitor gets stuck—with real screenshots, reproducible steps and an optional read-only HTML report. Bounded technical fixes and fresh verification require a separate opt-in.

[![Validate skills](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml)
[![MIT licensed](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Not a conversion study.** These are simulated, heuristic QA journeys—not real users, usability research, or evidence of improved business conversion.

## Try it: one journey, no application changes

Install in your web application project (Node.js 22.20+ and npm):

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

Then tell your Agent Skills-compatible coding agent:

```text
Use first-user-audit in QUICK CHECK mode on my locally running app.
Define the first useful user outcome, check browser tools and safety,
then follow one fresh visitor's primary path with real browser evidence.
Do not change my app. Report actual findings and mark the other
three personas as not run.
```

**One run, one real browser journey, no independent subagents required.** You get a reproducible first-impression report and can escalate to four personas later. See the [Quick Check protocol](skills/first-user-audit/references/quick-check.md).

Before running: you **must have a working browser MCP**, a local or confirmed isolated preview (not production), a clean test browser session, and safe test identities/data. See the [Playwright MCP setup](skills/first-user-audit/references/browser-setup.md). Installing the skill does **not** install browser tools, subagents, or sandboxing. Python 3.10+ is optional for rendering reports.

Want the full test? Ask: *Use first-user-audit in AUDIT-ONLY mode. Run all four isolated personas, capture evidence, and do not edit my app.* Genuine independent subagents are required unless you explicitly approve a disclosed lower-isolation alternative.

### What it catches (controlled historical example)

| Browser observation | What was recorded |
| --- | --- |
| Primary start CTA led nowhere | Impatient and breaker personas stopped at the same issue |
| 375px viewport pushed the CTA offscreen | Mobile persona could not proceed |
| Privacy link returned 404 | Skeptic persona could not inspect the policy |

These are documented observations from our **deliberately broken v0.2.0 fixture**, not real-customer outcomes or evidence of autonomous fixing. Review the [raw screenshot evidence and report](https://github.com/BarganConstantin/agent-skills/tree/v0.2.0/examples/first-user-demo).
## Four perspectives, one measurable goal

| Perspective | What it tries to uncover |
| --- | --- |
| **Impatient** | Is the obvious first action enough to get started? |
| **Skeptic** | Are price, commitment, privacy and terms understandable? |
| **Mobile** | Can someone progress at a verified 375 CSS-pixel viewport? |
| **Breaker** | Do validation, retries, back navigation and duplicate actions work? |

Define **first success** before testing: e.g. *a fresh test account creates a workspace and reaches its dashboard*. "Clicked Sign up" is usually not the outcome.

### What you get

- One persona report in Quick Check or four reports in a full audit, with actual clicks *to success* (or `null` when blocked), issues, completion counts and capability gaps.
- Concrete screenshots, reproduction steps and stable issue IDs; evidence must be inspected for personal data before sharing.
- A prioritized Markdown summary, plus an **optional offline HTML report** to review findings visually. The local Python tools validate report consistency; `--verify-evidence` checks paths and existence, **not screenshot authenticity**.
- In **Audit + Fix + Verify** mode: owner-approved bounded technical fixes, relevant tests and four fresh verification runs, with honest before/after limitations.

Reports live under the **target application's ignored** `qa/first-users/` directory. The [report schema and commands](skills/first-user-audit/references/report-format.md) explain how to inspect them. Python 3.10+ is only needed for the optional reporter.

For a standalone report you can open locally, run the [offline HTML reporter](skills/first-user-audit/references/html-report.md) after collecting persona JSON. It escapes report content, makes no network requests, and deliberately does not embed potentially sensitive screenshots.

## See a reviewed, controlled example

The [v0.2.0 Task Cabin demo](https://github.com/BarganConstantin/agent-skills/tree/v0.2.0/examples/first-user-demo) includes screenshots, eight persona reports, the fixture and [reviewed findings](https://github.com/BarganConstantin/agent-skills/blob/v0.2.0/examples/first-user-demo/report.md).

| Prepared demo fixture | First success |
| --- | --- |
| Baseline with deliberate defects | **0 of 4** simulated personas |
| Separately prepared fixed variant | **4 of 4** simulated personas |

This is **not** evidence that the skill autonomously fixed bugs in an unknown app or improved human conversion. The fixed version was prepared in advance. CI reran deterministic validation, **not** the eight agent-led browser sessions. The demo was deliberately removed from the current source tree to keep installations lean; its tagged archive remains inspectable.

## Choose the workflow

| Mode | Changes app code? | Verification | Start here? |
| --- | --- | --- | --- |
| **Quick Check** (explicit) | No | One browser journey, 1/4 coverage, no subagents required | **Start here** |
| **Audit only** (default) | No | Four baseline persona runs, evidence and a prioritized report | For broader coverage |
| **Audit + Fix + Verify** | Bounded technical changes only; sensitive changes require approval | Four baseline runs and four fresh verification runs when supported | After reviewing first audit |

The skill [defines exact safety boundaries and run instructions](skills/first-user-audit/SKILL.md). In **all modes**, a missing safe environment or browser connection means **stop**, not fabricated results. Quick Check uses one agent by design; approximating the *full four-persona audit* with one agent requires explicit consent and must never be described as independent.

## Scope and limits

**Good fit:** browser-based signup, onboarding, self-serve activation and first-value journeys before launch or after UX changes.

**Not covered:** production accounts, real payments, security penetration testing, actual human retention, representative user sampling, genuine touch-device testing by viewport resize alone, or automatic permission to change auth, billing, privacy or production configuration. Run real-user research alongside simulated QA.

**Compatibility:** installation uses the open [skills CLI](https://github.com/vercel-labs/skills). Agent execution requires actual connected browser tools and the runtime capabilities described above. Successful installation does not prove end-to-end execution in each agent.

## Contribute and verify

Found a reproducible obstacle, have a redacted real-app case study, or see a failure mode we missed? [Open an issue](https://github.com/BarganConstantin/agent-skills/issues). Contributions should include the smallest safe reproduction and relevant regression tests. See [CONTRIBUTING.md](CONTRIBUTING.md).

We're working toward repeatable **with-skill vs without-skill** behavior evaluation—not manufactured benchmark wins. Read the [evaluation protocol](docs/evaluation.md) and the [local reviewed-run scorer](evals/README.md); propose a test case. **No real comparative benchmark results are claimed yet.**

If the skill helps with your project, a [GitHub star](https://github.com/BarganConstantin/agent-skills) helps other developers find it. Practical bug reports and successful reproduction steps are even more valuable.

[MIT license](LICENSE) · [Security and private vulnerability reporting](SECURITY.md) · [v0.2.0 controlled demo](https://github.com/BarganConstantin/agent-skills/releases/tag/v0.2.0)
