# Agent Skills for Product Builders

Small, inspectable workflows for AI coding agents. Each skill has one job, explicit safety boundaries, and evidence you can review.

## Skills

| Skill | What it does | Status |
| --- | --- | --- |
| [First User Audit](skills/first-user-audit/SKILL.md) | Guides four simulated browser journeys from landing page to first success, records friction, and checks bounded fixes. | v0.1 — unvalidated in a real application |

### Install

From your application repository (Node.js 22.20+ and npm):

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

Then ask your agent:

> Use first-user-audit on my local app. Inspect the code to define the first successful user outcome. Test four isolated personas in sequence, collect evidence, fix only safe technical issues, and re-test with fresh agents if the runtime supports them. Stop if browser automation is unavailable.

[skills CLI documentation](https://github.com/vercel-labs/skills) covers agent selection and global installs. The command installs instructions; it does **not** install Playwright MCP or supply subagents for your agent runner.

### Prerequisites

- An agent runtime that can read Agent Skills and inspect local project code.
- A working Playwright MCP connection and a locally running app or isolated preview.
- A subagent mechanism if you want four *genuinely distinct* agent contexts. Without it, the skill must report reduced isolation, not pretend it used four subagents.
- Test accounts and payment sandbox, if your product needs them.
- Python 3.10+ only if using the bundled reporter; it needs no third-party packages.

Public-repository installation was checked with skills CLI 1.7.4 and Node.js 24.19.0 in a clean temporary project; see [validation notes](docs/validation.md). This does not verify browser execution.

See [browser setup](skills/first-user-audit/references/browser-setup.md) and [protocol](skills/first-user-audit/references/protocol.md).

## Design principles

- **Evidence, not invented outcomes.** Logs, URLs, reproduction steps, screenshots, and first-success proof are recorded per persona.
- **First success over page views.** Each project defines its own observable first-use outcome.
- **Independent runs.** Personas use sequential, isolated browser sessions; the after-pass is tested by fresh subagents that have not read the issue list.
- **Safe boundaries.** Only local/preview. Never real payments or production writes. Pricing, privacy, and legal text stay with the owner.
- **No false promises.** If browser access, throttling, or subagent isolation is missing, say so. Simulated personas do not replace usability studies with humans.

## Workflow

1. Confirm a safe target, connected browser tools, reset strategy, and available agent isolation.
2. Define the observable first-success event from the application code.
3. Run impatient, skeptic, mobile, and breaker personas sequentially with fresh sessions.
4. Review evidence, assign stable issue IDs, and rank by distinct affected personas.
5. Make permitted, bounded fixes with focused tests.
6. Repeat with fresh contexts and disclose incomplete or incomparable runs.

### Output

Generated evidence stays in `qa/first-users/` inside the **target application**. Add `qa/first-users/` to that application's ignore rules before collecting evidence; this collection's `.gitignore` does not configure the target project. Review artifacts for sensitive data before sharing.

The included standard-library Python reporter ranks explicitly grouped issues by the number of distinct personas affected. It does not infer that two different issue IDs are duplicates. See [report format](skills/first-user-audit/references/report-format.md).

```bash
# From the audited application's root, using the installed skill's absolute path
python /path/to/first-user-audit/scripts/summarize.py --root qa/first-users --baseline-only
python /path/to/first-user-audit/scripts/summarize.py --root qa/first-users --strict
```

Replace `/path/to/first-user-audit` with the installation path printed by the CLI. For a collection checkout, use `<checkout>/skills/first-user-audit`. Keep the working directory at the audited app root so `--root` resolves there.

## Compatibility and limitations

These are instructions, not a sandbox or technical permission enforcement. The agent and its operator remain responsible for tool permissions and side effects.

This follows the open [Agent Skills specification](https://agentskills.io/specification). Actual support for subagents, screenshots, network throttling, environment reset, and safe file editing varies by runtime. The skill checks availability and must disclose gaps. It is an AI-assisted QA workflow, **not** a measured conversion study or a substitute for accessibility, security, legal, or human usability review.

## Development

```bash
python3 -m venv .venv
# Windows: .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate_skills.py
python -m unittest discover -s tests -v
python -m unittest discover -s skills/first-user-audit/tests -v
```

The reporter uses only the standard library. Repository validation uses pinned PyYAML to parse actual YAML, reject duplicate keys, and check specification fields. CI runs validation and unit tests on Python 3.10, 3.12, and 3.14.

See [PUBLISHING.md](PUBLISHING.md) for release checks and the remaining supervised application test. Installation is separate from execution; no real-application audit is claimed for v0.1.0.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Propose focused skills, observable success criteria, and tests. Claims of browser or model benchmarks require reproducible evidence.

## License

MIT. See [LICENSE](LICENSE).
