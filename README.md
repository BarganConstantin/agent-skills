# agent-skills

Agent Skills for Claude Code, Codex and other agents that read `SKILL.md`.

| Skill | What it does | Needs |
|---|---|---|
| [first-user-audit](skills/first-user-audit/SKILL.md) | Walks a local web app to a first success in a real browser and records reproducible problems. Never on production. | browser MCP, Python 3.10+ |
| [handoff-with-receipts](skills/handoff-with-receipts/SKILL.md) | Writes or resumes a session handoff: intent, decisions, Git state, evidence, next step. | Git, Python 3.10+ (optional) |
| [api-contract-drift](skills/api-contract-drift/SKILL.md) | Lists OpenAPI changes that can break clients. A clean result does not prove compatibility. | Python 3.10+ |
| [reference-library](skills/reference-library/SKILL.md) | Offline catalog of saved projects and references. [Browse](docs/library.md). | Python 3.10+ |
| [prune-tests](skills/prune-tests/SKILL.md) | Finds redundant tests and removes only the ones you approve. .NET first. | Python 3.10+, .NET SDK |

## Install

Node.js 22.20+:

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
npx skills add BarganConstantin/agent-skills --skill handoff-with-receipts
npx skills add BarganConstantin/agent-skills --skill api-contract-drift
npx skills add BarganConstantin/agent-skills --skill reference-library
npx skills add BarganConstantin/agent-skills --skill prune-tests
```

Or copy `skills/<name>/` into `~/.claude/skills/` or `.agents/skills/`.

## Try

```bash
python skills/api-contract-drift/scripts/compare_openapi.py \
  --before examples/api-contract-drift/before.json \
  --after examples/api-contract-drift/after.json
```

The example files are synthetic, not a real-API benchmark.
[Report your first result or blocker](https://github.com/BarganConstantin/agent-skills/issues/new?template=api-contract-drift-feedback.yml).

## Develop

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_skills.py
python -m unittest discover -s tests
python -m unittest discover -s skills/first-user-audit/tests
```

[Install check](.github/workflows/public-install.yml) ·
[Practice app](docs/practice-lab.md) ·
[First run](docs/first-five-testers.md) ·
[Feedback](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT](LICENSE)
