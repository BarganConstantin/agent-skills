# Agent Skills for Developers

**Four focused skills. Real checks, explicit limits, no account required.** Pick one workflow for Claude Code, Codex, or another compatible coding agent.

[![Validate skills](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/BarganConstantin/agent-skills/actions/workflows/validate.yml)
[![Public GitHub install](https://github.com/BarganConstantin/agent-skills/actions/workflows/public-install.yml/badge.svg)](https://github.com/BarganConstantin/agent-skills/actions/workflows/public-install.yml)
[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

| Choose a skill | Problem it helps you solve | Prerequisites |
| --- | --- | --- |
| **[Handoff with Receipts](skills/handoff-with-receipts/SKILL.md)** | Continue a coding task in a fresh session without confusing previous claims with verified Git state | No MCP; Git/Python optional |
| **[API Contract Drift](skills/api-contract-drift/SKILL.md)** | Flag potentially breaking changes between two OpenAPI 3 JSON versions | Offline Python 3.10+ |
| **[First User Audit](skills/first-user-audit/SKILL.md)** | See where a first-time visitor is blocked on a local web app, with actual browser evidence | Browser MCP + safe preview |
| **[Reference Library](skills/reference-library/SKILL.md)** | Find saved project inspirations when working on UI, motion or developer tools; add new bookmarks intentionally | Offline Python 3.10+; no MCP |

## See a result in 30 seconds (no AI agent needed)

The **API Contract Drift** comparator comes with two synthetic OpenAPI documents and three deliberately planted problems. Clone the repo and run:

```bash
git clone https://github.com/BarganConstantin/agent-skills.git
cd agent-skills
python skills/api-contract-drift/scripts/compare_openapi.py \
  --before examples/api-contract-drift/before.json \
  --after examples/api-contract-drift/after.json
```

The report flags **three potential client-breaking changes**: a formerly public endpoint requiring authentication, a new mandatory request header, and a new mandatory JSON body field. Those are *controlled fixture results*, **not** proof of agent quality, live API behavior, or full OpenAPI compatibility.

[See the example and expected output](examples/api-contract-drift/README.md) · [Read exact limitations](skills/api-contract-drift/references/limitations.md)

## Install a skill into your coding agent

With Node.js 22.20+ and npm, choose **one**:

```bash
npx skills add BarganConstantin/agent-skills --skill handoff-with-receipts
# or
npx skills add BarganConstantin/agent-skills --skill api-contract-drift
# or
npx skills add BarganConstantin/agent-skills --skill first-user-audit
# or
npx skills add BarganConstantin/agent-skills --skill reference-library
```

The Skills CLI copies the selected skill instructions into your agent environment; it does **not** automatically execute a task. We [test installation from the public GitHub repository](.github/workflows/public-install.yml) for Claude Code and Codex with CI telemetry disabled. These tests do not count as independent user adoption.

Not ready to install? Preview one skill's instructions without adding it:

```bash
npx skills use BarganConstantin/agent-skills --skill handoff-with-receipts
```

## What to ask your agent

**Handoff with Receipts**

> Use handoff-with-receipts to prepare a continuation note. Verify the current branch, HEAD, and dirty worktree if Git is available. Separate VERIFIED facts from REPORTED history and UNKNOWNs. Preserve my scope restrictions. Don't commit or push anything.

**Reference Library**

> Use reference-library to search what I've saved for my current design or coding task. Show relevant original sources, why they help, and tradeoffs before proposing an approach. Do not install or copy anything automatically.

The initial library includes [Hallmark](https://github.com/Nutlope/hallmark) and [Elaya AI Design Skills](https://github.com/elayadesign/ai-design-skills). [Search, curate and sync rules](skills/reference-library/references/curation.md). Saving into one installed copy does **not** sync to your other projects.

**API Contract Drift**

> Use api-contract-drift with my old and new OpenAPI 3 JSON exports. Identify potential client-breaking changes, show evidence and limitations. Do not modify my API.

### Try Quick Check

**First User Audit**

> Use first-user-audit in QUICK CHECK mode on my safe local web app. Define one first-success event, verify browser tools, and follow a new visitor's first journey. Capture actual evidence. Do not edit my app. Label the remaining three personas NOT RUN.

Requires a **real connected browser MCP**, a localhost or verified isolated preview, and safe test data. If any prerequisite is missing, the skill must stop rather than fabricate findings.

#### No web app ready? Try the practice lab

The repository includes a [localhost-only synthetic app](docs/practice-lab.md) with intentionally seeded onboarding issues. You can use it to practice browser QA without using a customer's app. It is **not** an independent agent evaluation.

### Need a deeper audit?

First User Audit also supports four distinct browser perspectives (impatient, skeptic, mobile, breaker) and an opt-in bounded fix/verify mode. Read the [full walkthrough](docs/first-user-audit.md) and [safety preflight](skills/first-user-audit/references/browser-setup.md). We do not claim an independently proven model performance lift.

## Real feedback is more valuable than synthetic popularity

Trying a skill for the first time, even if setup fails? [Share what happened](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml). Report only redacted steps: no credentials, private code or client URLs. [First-five-testers guide](docs/first-five-testers.md).

Our [growth research](docs/growth-research.md) tracks testable decisions rather than fabricated installs or stars. Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and the [MIT license](LICENSE). If these tools help your project, a GitHub star makes them easier to discover.
