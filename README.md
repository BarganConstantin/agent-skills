# Agent Skills for Product Builders

Practical skills that help coding agents inspect, test, and improve your application.

## First User Audit

[First User Audit](skills/first-user-audit/SKILL.md) checks the journey from your landing page to a first useful result through four simulated user perspectives. Your agent collects browser evidence, makes bounded technical fixes, and repeats the audit to verify them. Simulated personas complement human usability research; they do not measure real-user conversion.

## Four perspectives

- **Impatient** — tries the obvious next step with minimal reading.
- **Skeptic** — checks pricing, terms, and privacy before committing.
- **Mobile** — checks the journey at a 375 CSS pixel viewport.
- **Breaker** — tries invalid inputs, retries, back navigation, and repeated submissions.

## Quick installation

Run in your application project with Node.js 22.20+ and npm, then choose your agent:

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

Uses the [skills CLI](https://github.com/vercel-labs/skills). Installation adds instructions, references, and a reporter; it does not provide browser tools, subagents, or sandboxing.

## Copy-paste agent prompt

Paste into Claude Code, Codex, or another agent that supports Agent Skills:

```text
Install First User Audit in this project:
npx skills add BarganConstantin/agent-skills --skill first-user-audit

Choose this agent's project-local installation. Verify that you can find
and read the installed SKILL.md and its references, then follow them.
Inspect the application and define a specific, observable first-success
event before testing. Ask me if the intended outcome is ambiguous.

Run the audit only if a safe local or isolated preview environment and
working browser automation are available. Otherwise stop and explain
what is missing. Check available subagents; if independent contexts are
unavailable, ask before using a reduced-isolation alternative.

Run the four perspectives sequentially with reset browser and test data.
Collect real screenshots and reproduction steps, fix only permitted,
bounded technical issues, then verify with fresh contexts when supported.
Report actual results, capability gaps, and remaining owner decisions.
```

## How it works

1. **Define success.** Inspect the app, confirm a safe target, and check browser tools and reset capability.
2. **Observe.** Run each perspective separately and record screenshots, reproduction steps, and whether first success was reached.
3. **Fix safely.** Prioritize observed friction and make focused technical changes with relevant tests. Leave pricing, policies, and sensitive changes for owner review.
4. **Verify.** Repeat under comparable conditions with fresh agents when supported; disclose missing evidence and incomplete runs.

Keep audit artifacts in the target application's ignored `qa/first-users/` directory and review them for sensitive data before sharing. The bundled Python reporter aggregates persona reports; see the [report format and commands](skills/first-user-audit/references/report-format.md).

## Requirements

- An agent that can read Agent Skills and inspect local application code.
- A connected browser MCP with navigation, interactions, screenshots, and browser-state reset. See [browser setup](skills/first-user-audit/references/browser-setup.md).
- A local app or confirmed isolated preview, with test identities and sandbox integrations where needed. Never production accounts, real payments, or customer data.
- Independent subagents for isolated agent contexts. Without them, the skill requires your approval for a clearly labeled approximation.
- Python 3.10+ if using the optional report generator; no Python packages are needed for it.

These are instructions, not enforced permissions or a sandbox. Capabilities depend on the runtime: resizing alone does not test touch devices, and network throttling must be verified separately.

## License and contributions

[MIT license](LICENSE) · [Contributing and development](CONTRIBUTING.md) · [Report a security issue privately](SECURITY.md)
