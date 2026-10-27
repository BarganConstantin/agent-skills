# Receipts, provenance and limits

A handoff tells the next agent **what was observed** and **where uncertainty remains**. It is not a cryptographic attestation, a test harness, or an automatic resume command.

## What the optional script can and cannot verify

`scripts/git_snapshot.py` executes only local read-only Git commands:

- `git rev-parse --show-toplevel` confirms the current directory is in a worktree.
- `git rev-parse --verify HEAD` obtains the current commit when one exists.
- `git symbolic-ref --quiet --short HEAD` reads the current branch, when attached.
- `git status --porcelain=v1 --untracked-files=all` counts modified/staged/untracked entries. Paths are deliberately dropped.

It records a UTC timestamp and does **not** read tracked file contents, diffs, Git remote URLs, environment variables or authentication tokens. Local Git configuration can still influence Git behavior; use it only on a trusted local checkout. The script does not automatically install Git, change refs, stage files, commit, fetch or contact GitHub.

**Never confuse Git status with test evidence**: a clean tree can contain bugs; dirty work can be perfectly valid. Snapshot counts can be stale a second later and do not include ignored files. A branch name may contain sensitive words. The human/agent writing the handoff must verify and redact any accompanying free-text details.

## Evidence taxonomy

| Label | Examples | Required treatment |
| --- | --- | --- |
| VERIFIED | observed fresh process exit code 0, selected file read, checked Git SHA | Name the **specific** check and timestamp; do not generalize |
| REPORTED | previous model said CI was green, historical docs claim a fix, user summarized progress | Attribute it to source, re-check before relying on it |
| UNKNOWN | no access to remote CI, couldn't reproduce, not enough time, no safe test env | Name missing capability or next test |

Never label a result VERIFIED merely because another agent wrote it. An output string saying "success" is not enough if the command or artifact is untrustworthy.

## Safe handoff practices

- Write note/artifacts to OS temp directory unless persistence was explicitly requested. Avoid putting a scratch handoff in the Git checkout or accidentally committing it.
- Be explicit about sensitive path/URL/title redaction; **do not paste entire Git status, process environment, `.env`, SSH configuration or private customer screenshots**.
- If you have no Git or Python, write the same fields with `NOT CHECKED`, and identify a narrow command for the next agent to run.
- In resume mode, consider mismatched SHA/branch/dirty counts **potential divergence**, not proof of data loss. Do not reset/rebase/stash or discard state without authorization.

## Source influences and intellectual-property boundary

This skill is an **independent implementation**, informed by the widely adopted idea of compact agent handoffs and explicit verification. We reviewed:

- [Matt Pocock's handoff workflow](https://github.com/mattpocock/skills/tree/main/skills/productivity/handoff) (MIT): concise transfer of task context.
- [Superpowers verification-before-completion](https://github.com/obra/superpowers/tree/main/skills/verification-before-completion) (MIT): verification discipline before status claims.
- [Addy Osmani's doubt-driven-development](https://github.com/addyosmani/agent-skills/tree/main/skills/doubt-driven-development) (MIT): interrogating assumptions.

No upstream skill text, scripts or assets were copied into this new package. The differentiators here are the bundled *path-redacted local Git state capture*, explicit separation of verified/reported/unknown facts and a permission-aware resume reconciliation process. If later importing actual upstream code/text, preserve applicable license and attribution terms instead of merely renaming copied work.
