#!/usr/bin/env bash
# Verify the default-branch public GitHub install; never generate leaderboard telemetry.
set -euo pipefail
test -n "$GITHUB_WORKSPACE"
test -n "$RUNNER_TEMP"
export DISABLE_TELEMETRY=1
export CI=true

REPOSITORY="BarganConstantin/agent-skills"
ROOT="$GITHUB_WORKSPACE"
TEMPDIR="$(mktemp -d "$RUNNER_TEMP/remote-skill-install.XXXXXX")"
trap 'rm -rf "$TEMPDIR"' EXIT
cd "$TEMPDIR"

echo "::group::Discover actual skills through public GitHub"
npx --yes skills@latest add "$REPOSITORY" --list > discovered.txt
for skill in first-user-audit reference-library prune-tests; do
  grep -Fq "$skill" discovered.txt
done
echo "::endgroup::"

echo "::group::Install every skill from GitHub"
for skill in first-user-audit reference-library prune-tests; do
  npx --yes skills@latest add "$REPOSITORY" \
    --skill "$skill" --agent claude-code --agent codex --copy --yes
  for client in ".agents/skills" ".claude/skills"; do
    src="$ROOT/skills/$skill"
    dst="$client/$skill"
    test -f "$dst/SKILL.md"
    while IFS= read -r -d '' file; do
      rel="$(realpath --relative-to="$src" "$file")"
      test -f "$dst/$rel"
      cmp -s "$file" "$dst/$rel"
    done < <(find "$src" -type f -print0)
  done
done
echo "::endgroup::"

echo "::group::No-install preview from public GitHub"
mkdir -p "$TEMPDIR/preview"
cd "$TEMPDIR/preview"
for skill in first-user-audit reference-library prune-tests; do
  npx --yes skills@latest use "$REPOSITORY" --skill "$skill" > "$skill.txt"
  test -s "$skill.txt"
  grep -Fq "$skill" "$skill.txt"
done
test ! -e .agents
test ! -e .claude
echo "::endgroup::"

echo "Public GitHub discovery, installation and no-install preview verified."
