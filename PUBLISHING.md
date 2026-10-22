# Release checklist

## Validate a candidate

Use the [development setup](README.md#development) and run:

```bash
python scripts/validate_skills.py
python -m unittest discover -s tests -v
python -m unittest discover -s skills/first-user-audit/tests -v
```

Check the complete diff, relative links, MIT notices, and the public README. Keep the collection at repository root and additional skills under `skills/`. Never publish audit artifacts containing private information.

## Check installation

From a clean temporary project with Node.js 22.20+ and npm:

```bash
npx skills add BarganConstantin/agent-skills --list
npx skills add BarganConstantin/agent-skills --skill first-user-audit --agent claude-code --yes
```

Do not use `--global` for a smoke test. Inspect the installed skill, references, reporter, and license; run the installed reporter's `--help`. Installation checks packaging and discovery, not whether the agent can execute the workflow. Record CLI and runtime versions separately from application testing.

## Publish a release

1. Review the existing GitHub repository before pushing. Preserve unrelated work and never force-push.
2. Push the validated commit to `main` and wait for **Validate skills** to pass on that exact commit.
3. Verify public repository visibility, default branch, license, skill path, and README links.
4. Create the version tag and release from the validated commit. Describe changes and known limitations accurately.
5. Recheck installation from GitHub and record the result in [validation notes](docs/validation.md).

The first release is **v0.1.0 — First User Audit**.

The first release provides the instruction package, report schema/template, standard-library reporter, metadata validator, and synthetic unit tests. It has no production-proven or real-user conversion claims.

## Before promoting

The draft article is [articles/devto-first-user-audit.md](articles/devto-first-user-audit.md); keep `published: false` until the owner chooses to publish it.

- Reproduce the [controlled local demonstration](examples/first-user-demo/README.md), then run a supervised audit against another confirmed isolated application preview. Record the exact agent, browser server, browser version, permission boundaries, and capability gaps.
- Verify four sequential fresh browser sessions and, when available, separate subagent contexts. If not available, label the approximation and get the user's choice before running it.
- Exercise mobile sizing, unsupported throttling, report aggregation, a bounded fix, and fresh verification. Check ignored evidence for secrets before sharing.
- Compare findings with deterministic Playwright tests and human review. Do not claim retention or conversion improvements from simulated personas.
- Use permanent commit links for demonstrated behavior. Recheck article links and test counts before posting to DEV.to, Reddit, Hacker News, or skills.sh. Respect each community's submission rules. Publication and installation do not guarantee directory indexing.
- Use original or properly licensed cover artwork. Publishing the GitHub repository does not authorize publishing the article.
