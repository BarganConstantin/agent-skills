# First User Audit

**Your app works. Can a first-time visitor reach the first useful result?**

First User Audit is an [Agent Skill](https://agentskills.io/specification) for **simulated first-user QA**. It sends four *sequential* browser personas through a local or isolated preview of your web app, records where they get stuck, and gives you screenshots and reproduction steps. Optionally, it can make bounded technical fixes and run an independent verification pass.

[![Validate skills](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml)
[![MIT licensed](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Not a conversion study.** These are simulated, heuristic QA journeys—not real users, usability research, or evidence of improved business conversion.

## Try it: install once, audit without changing code

From your application project (Node.js 22.20+ and npm):

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

Then paste this into an Agent Skills-compatible coding agent with access to your application:

```text
Use first-user-audit in AUDIT-ONLY mode.
Read the installed SKILL.md and its referenced protocol.
Inspect this application and define a specific, observable first-success event.
Test only a local app or confirmed isolated preview with test accounts.
Preflight the browser MCP, session reset and independent subagent capabilities;
stop if browser tools or a safe environment are missing.
If independent contexts are unavailable, ask before using a clearly
labeled, lower-isolation alternative.

Run the four perspectives sequentially against the same first-success
criterion. Capture genuine screenshots and reproducible obstacles.
Do not modify the application. Generate a baseline-only report, clearly
distinguishing observations from estimates and missing capabilities.
```

**Requires more than installing a skill:** connect a browser-capable MCP client (see [browser setup](skills/first-user-audit/references/browser-setup.md)); run a safe local/isolated app; supply test identities and a backend-data reset strategy. The skill does **not** install browser tooling or subagents, and is not a security sandbox.

## Four perspectives, one measurable goal

| Perspective | What it tries to uncover |
| --- | --- |
| **Impatient** | Is the obvious first action enough to get started? |
| **Skeptic** | Are price, commitment, privacy and terms understandable? |
| **Mobile** | Can someone progress at a verified 375 CSS-pixel viewport? |
| **Breaker** | Do validation, retries, back navigation and duplicate actions work? |

Define **first success** before testing: e.g. *a fresh test account creates a workspace and reaches its dashboard*. "Clicked Sign up" is usually not the outcome.

### What you get

- Four persona reports with reachability, actual clicks *to success* (or `null` when blocked), issues and capability gaps.
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
| **Audit only** (default) | No | Four baseline persona runs, evidence and a prioritized report | **Yes** |
| **Audit + Fix + Verify** | Bounded technical changes only; sensitive changes require approval | Four baseline runs and four fresh verification runs when supported | After reviewing first audit |

The skill [defines exact safety boundaries and run instructions](skills/first-user-audit/SKILL.md). In both modes, if you lack a safe environment or working browser tools, **stop** rather than generating imaginary findings. A single-agent approximation requires explicit consent and must never be described as independent subagents.

## Scope and limits

**Good fit:** browser-based signup, onboarding, self-serve activation and first-value journeys before launch or after UX changes.

**Not covered:** production accounts, real payments, security penetration testing, actual human retention, representative user sampling, genuine touch-device testing by viewport resize alone, or automatic permission to change auth, billing, privacy or production configuration. Run real-user research alongside simulated QA.

**Compatibility:** installation uses the open [skills CLI](https://github.com/vercel-labs/skills). Agent execution requires actual connected browser tools and the runtime capabilities described above. Successful installation does not prove end-to-end execution in each agent.

## Contribute and verify

Have a reproducible obstacle, a real app case study with redacted evidence, or a failure mode we missed? [Open an issue](https://github.com/BarganConstantin/agent-skills/issues). Contributions should include the smallest safe reproduction and relevant regression tests. See [CONTRIBUTING.md](CONTRIBUTING.md).

We're working toward repeatable **with-skill vs without-skill** behavior evaluation—not manufactured benchmark wins. Read the [evaluation protocol](docs/evaluation.md) and propose a test case.

[MIT license](LICENSE) · [Security and private vulnerability reporting](SECURITY.md) · [v0.2.0 controlled demo](https://github.com/BarganConstantin/agent-skills/releases/tag/v0.2.0)
