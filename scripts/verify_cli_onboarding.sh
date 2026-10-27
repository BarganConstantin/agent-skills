#!/usr/bin/env bash
# CLI discovery/install smoke on safe temporary files, never an agent/browser run.
set -euo pipefail
test -n "$GITHUB_WORKSPACE"
test -n "$RUNNER_TEMP"
export DISABLE_TELEMETRY=1
SOURCE="$GITHUB_WORKSPACE/skills/first-user-audit"
WORKDIR="$(mktemp -d "$RUNNER_TEMP/first-user-audit-cli.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

cd "$WORKDIR"
echo "::group::CLI skill discovery without installing"
npx --yes skills@latest add "$GITHUB_WORKSPACE" --list | tee discovery.txt
grep -Fq "first-user-audit" discovery.txt
grep -Fq "handoff-with-receipts" discovery.txt
grep -Fq "api-contract-drift" discovery.txt
grep -Fq "reference-library" discovery.txt
echo "::endgroup::"

echo "::group::Real project-local installation to Claude Code and Codex"
npx --yes skills@latest add "$GITHUB_WORKSPACE" \
  --skill first-user-audit --agent claude-code --agent codex --copy --yes
for target in ".agents/skills/first-user-audit" ".claude/skills/first-user-audit"; do
  test -f "$target/SKILL.md"
  cmp "$SOURCE/SKILL.md" "$target/SKILL.md"
  cmp "$SOURCE/references/quick-check.md" "$target/references/quick-check.md"
  cmp "$SOURCE/scripts/summarize.py" "$target/scripts/summarize.py"
  cmp "$SOURCE/scripts/html_report.py" "$target/scripts/html_report.py"
done
echo "::endgroup::"

echo "::group::Install the evidence-backed handoff skill for both clients"
npx --yes skills@latest add "$GITHUB_WORKSPACE" \
  --skill handoff-with-receipts --agent claude-code --agent codex --copy --yes
HANDOFF="$GITHUB_WORKSPACE/skills/handoff-with-receipts"
for target in ".agents/skills/handoff-with-receipts" ".claude/skills/handoff-with-receipts"; do
  test -f "$target/SKILL.md"
  cmp "$HANDOFF/SKILL.md" "$target/SKILL.md"
  cmp "$HANDOFF/scripts/git_snapshot.py" "$target/scripts/git_snapshot.py"
  cmp "$HANDOFF/assets/handoff-template.md" "$target/assets/handoff-template.md"
  cmp "$HANDOFF/references/evidence-boundaries.md" "$target/references/evidence-boundaries.md"
done
echo "::endgroup::"

echo "::group::Install API Contract Drift for both clients"
npx --yes skills@latest add "$GITHUB_WORKSPACE" \
  --skill api-contract-drift --agent claude-code --agent codex --copy --yes
API="$GITHUB_WORKSPACE/skills/api-contract-drift"
for target in ".agents/skills/api-contract-drift" ".claude/skills/api-contract-drift"; do
  test -f "$target/SKILL.md"
  cmp "$API/SKILL.md" "$target/SKILL.md"
  cmp "$API/scripts/compare_openapi.py" "$target/scripts/compare_openapi.py"
  cmp "$API/references/limitations.md" "$target/references/limitations.md"
done
echo "::endgroup::"

echo "::group::Install the saved reference library for both clients"
npx --yes skills@latest add "$GITHUB_WORKSPACE" \
  --skill reference-library --agent claude-code --agent codex --copy --yes
LIBRARY="$GITHUB_WORKSPACE/skills/reference-library"
for target in ".agents/skills/reference-library" ".claude/skills/reference-library"; do
  test -f "$target/SKILL.md"
  cmp "$LIBRARY/SKILL.md" "$target/SKILL.md"
  cmp "$LIBRARY/references/catalog.json" "$target/references/catalog.json"
  cmp "$LIBRARY/references/curation.md" "$target/references/curation.md"
  cmp "$LIBRARY/scripts/library.py" "$target/scripts/library.py"
done
echo "::endgroup::"

echo "::group::Generate usable prompt without installing or running an agent"
mkdir -p "$WORKDIR/try-without-install"
cd "$WORKDIR/try-without-install"
npx --yes skills@latest use "$GITHUB_WORKSPACE" \
  --skill first-user-audit > skill-prompt.txt
grep -Fq "First User Audit" skill-prompt.txt
grep -Fq "Quick Check" skill-prompt.txt
npx --yes skills@latest use "$GITHUB_WORKSPACE" \
  --skill handoff-with-receipts > handoff-prompt.txt
grep -Fq "Handoff with Receipts" handoff-prompt.txt
npx --yes skills@latest use "$GITHUB_WORKSPACE" \
  --skill api-contract-drift > api-prompt.txt
grep -Fq "API Contract Drift" api-prompt.txt
npx --yes skills@latest use "$GITHUB_WORKSPACE" \
  --skill reference-library > library-prompt.txt
grep -Fq "Reference Library" library-prompt.txt
test ! -d .agents
test ! -d .claude
echo "::endgroup::"
echo "SUCCESS: discovery, client-specific local copy, unchanged files, and skill-use prompt."
