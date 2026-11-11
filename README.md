# agent-skills

Agent Skills for Claude Code, Codex and other agents that read `SKILL.md`.

## Start here

- **Give your agent a workflow:** choose an [installable skill](#installable-skills) below.
- **Find a saved tool, component library or design reference:** [browse the Reference Library](docs/library.md).
- **Unsure what to choose:** use the [task guide](docs/choose-by-task.md), with examples of what to ask your agent.

Skills are instructions you install and invoke. Library entries are bookmarks with
use cases and caveats; saving a link does not install its project.

## Installable skills

| Skill | Use it when… | Needs |
|---|---|---|
| [first-user-audit](skills/first-user-audit/SKILL.md) | Walks a local web app to a first success in a real browser and records reproducible problems. Never on production. | browser MCP, Python 3.10+ |
| [reference-library](skills/reference-library/SKILL.md) | Offline catalog of saved projects and references. [Browse](docs/library.md). | Python 3.10+ |
| [prune-tests](skills/prune-tests/SKILL.md) | Finds redundant tests and removes only the ones you approve. .NET first. | Python 3.10+, .NET SDK |
| [compass](skills/compass/SKILL.md) | Resume a session: current state, completed work and next step. Read-only. | Python 3.10+, git |
| [figma-design-system](skills/figma-design-system/SKILL.md) | Design tokens, components and states in Figma before code. | Figma MCP |
| [socratic-tutor](skills/socratic-tutor/SKILL.md) | Learn through questions, practice and progress checks. [Source and MIT license](skills/socratic-tutor/UPSTREAM.md). | No extra tools |

## Install

Node.js 22.20+:

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
npx skills add BarganConstantin/agent-skills --skill reference-library
npx skills add BarganConstantin/agent-skills --skill prune-tests
npx skills add BarganConstantin/agent-skills --skill compass
npx skills add BarganConstantin/agent-skills --skill figma-design-system
npx skills add BarganConstantin/agent-skills --skill socratic-tutor
```

Or copy `skills/<name>/` into `~/.claude/skills/` or `.agents/skills/`.

## Saved tools and references

[Browse all saved sources by area](docs/library.md) or use the
[task guide](docs/choose-by-task.md). The library covers UI/UX, Backend/API,
Code Review, Testing/QA and Agent Workflows.

Astryx and HeroUI cover React component systems; 21st.dev helps discover UI
examples and templates. Each library entry explains when it helps and records
prerequisites and licensing notes.

For offline search, open `docs/library-explorer.html` after cloning this repo.
GitHub shows HTML source, not the running explorer. Installed catalogs are
snapshots; they do not sync automatically.

[Install check](.github/workflows/public-install.yml) ·
[Practice app](docs/practice-lab.md) ·
[First run](docs/first-five-testers.md) ·
[Feedback](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml) ·
[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [MIT](LICENSE)
