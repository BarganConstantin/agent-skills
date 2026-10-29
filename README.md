# agent-skills

Agent Skills for Claude Code, Codex and other agents that read `SKILL.md`.

| Skill | What it does | Needs |
|---|---|---|
| [first-user-audit](skills/first-user-audit/SKILL.md) | Walks a local web app to a first success in a real browser and records reproducible problems. Never on production. | browser MCP, Python 3.10+ |
| [reference-library](skills/reference-library/SKILL.md) | Offline catalog of saved projects and references. [Browse](docs/library.md). | Python 3.10+ |
| [prune-tests](skills/prune-tests/SKILL.md) | Finds redundant tests and removes only the ones you approve. .NET first. | Python 3.10+, .NET SDK |

## Install

Node.js 22.20+:

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
npx skills add BarganConstantin/agent-skills --skill reference-library
npx skills add BarganConstantin/agent-skills --skill prune-tests
```

Or copy `skills/<name>/` into `~/.claude/skills/` or `.agents/skills/`.

## Try

Search the reference library offline:

```bash
python skills/reference-library/scripts/library.py search "landing page" --category ui-ux
```

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
