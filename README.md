# agent-skills

Agent Skills for Claude Code, Codex and other agents that read `SKILL.md` files.

## Install

With Node.js 22.20+ and npm:

```bash
npx skills add BarganConstantin/agent-skills --skill <name>
```

Or copy `skills/<name>/` into `~/.claude/skills/` (Claude Code) or `.agents/skills/` (Codex).
Installing copies instructions only; it does not run an agent or connect tools.

## Skills

### first-user-audit

Walks a local web app from the landing page to a first success in a real browser, as one new
user (Quick Check) or four. Records reproducible problems with screenshots. Can apply bounded
fixes and re-verify with fresh agents, only when asked. Never run it against production.

Needs: browser MCP; Python 3.10+ for the report. Docs: [walkthrough](docs/first-user-audit.md),
[practice app](docs/practice-lab.md), [first run in Claude Code / Codex](docs/first-five-testers.md).
Skill: [skills/first-user-audit/SKILL.md](skills/first-user-audit/SKILL.md).

```bash
npx skills add BarganConstantin/agent-skills --skill first-user-audit
```

### handoff-with-receipts

Writes or resumes a handoff between sessions, models or people: intent, decisions, exact Git
state, command output, blockers and the next step. Reports only what it can verify.

Needs: nothing; Git and Python 3.10+ for the optional snapshot.
Skill: [skills/handoff-with-receipts/SKILL.md](skills/handoff-with-receipts/SKILL.md).

```bash
npx skills add BarganConstantin/agent-skills --skill handoff-with-receipts
```

### api-contract-drift

Compares two OpenAPI 3 JSON files offline and lists changes that can break clients: removed
operations, new required parameters or fields, removed responses, stricter security. A clean
result does not prove compatibility.

Needs: Python 3.10+.
Skill: [skills/api-contract-drift/SKILL.md](skills/api-contract-drift/SKILL.md).

```bash
npx skills add BarganConstantin/agent-skills --skill api-contract-drift

python skills/api-contract-drift/scripts/compare_openapi.py \
  --before examples/api-contract-drift/before.json \
  --after examples/api-contract-drift/after.json
```

The example files are synthetic, not a real-API benchmark.
[Report your first result or blocker](https://github.com/BarganConstantin/agent-skills/issues/new?template=api-contract-drift-feedback.yml).

### reference-library

Offline, searchable catalog of saved GitHub projects, tools and design references. Asks before
saving or adopting anything. Browse it in [docs/library.md](docs/library.md).

Needs: Python 3.10+.
Skill: [skills/reference-library/SKILL.md](skills/reference-library/SKILL.md).

```bash
npx skills add BarganConstantin/agent-skills --skill reference-library

python skills/reference-library/scripts/library.py search "landing page" --category ui-ux
```

### prune-tests

Finds tests a suite can lose: duplicates, tests that cannot fail, tests that only check a mock,
copies that belong in one data-driven test. Gives evidence per test and deletes or merges only
the ones you approve. .NET first; optional Stryker.NET proof.

Needs: Python 3.10+; .NET SDK to run the tests.
Skill: [skills/prune-tests/SKILL.md](skills/prune-tests/SKILL.md).

```bash
npx skills add BarganConstantin/agent-skills --skill prune-tests
```

## Development

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_skills.py
python -m unittest discover -s tests
python -m unittest discover -s skills/first-user-audit/tests
```

CI runs these on Python 3.10, 3.12 and 3.14. A second workflow
[installs every skill from this repository](.github/workflows/public-install.yml) when skills
change on `main`, and weekly. See [CONTRIBUTING.md](CONTRIBUTING.md).

[First-run feedback](https://github.com/BarganConstantin/agent-skills/issues/new?template=first-run-feedback.yml) ·
[Security](SECURITY.md) · [MIT License](LICENSE)
