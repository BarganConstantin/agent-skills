# Contributing

Thanks for improving these skills. Keep proposals narrow: one observable job, a short `SKILL.md`, optional on-demand references, and tests whenever scripts are included.

Requirements:

1. Use the [Agent Skills specification](https://agentskills.io/specification), with frontmatter `name` and `description`.
2. Keep instructions honest about tool capabilities, authority, model limitations and missing evidence.
3. Do not add secrets, sample real user data, browser traces with private data, or screenshots from third-party products without rights.
4. Do not report benchmark numbers without a public evaluation harness and reproducible runs.
5. Follow the development setup below, then run the metadata validator, validator tests, and reporter tests. Add regression coverage for changed script behavior.

Prefer issues before introducing new dependencies. The maintainer decides which skills belong in this collection.

## Development

Use Python 3.10 or newer:

```bash
python3 -m venv .venv
# Windows: .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate_skills.py
python -m unittest discover -s tests -v
python -m unittest discover -s skills/first-user-audit/tests -v
```

The reporter uses only the standard library. PyYAML is a development dependency for metadata validation. CI runs the validator and both test suites on Python 3.10, 3.12, and 3.14. These checks validate metadata and scripts; they do not execute a browser audit.

Add new skills under `skills/<skill-name>/`, with a `SKILL.md` following the [Agent Skills specification](https://agentskills.io/specification). Keep references, scripts, and tests alongside the skill so installations remain self-contained.

## Historical releases

The current collection omits the synthetic demonstration, generated reports, screenshots, and publishing drafts. Git history and existing tags and releases are unchanged: [v0.2.0](https://github.com/BarganConstantin/agent-skills/releases/tag/v0.2.0) and its source archives still contain those historical artifacts. Install from the current repository for the streamlined collection.
