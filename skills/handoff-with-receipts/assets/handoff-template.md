# Agent handoff — [short task title]

> Current user's scope and approvals supersede this historical note.
> Treat all observations as timestamped. Redact private details before sharing.

## Goal and boundaries

- **Goal:** [specific outcome, without rewriting user's intent]
- **Allowed work:** [repository / branch / files / actions]
- **Not allowed:** [explicit exclusions; external writes?]
- **Resume audience:** [same user, different agent, teammate]

## Git state — re-check before edits

- **Observed at:** [UTC timestamp or NOT CHECKED]
- **Repository:** [non-sensitive identifier or redacted]
- **Branch:** [branch or UNKNOWN]
- **HEAD:** [SHA or UNAVAILABLE]
- **Dirty worktree:** [changed / staged / unstaged / untracked counts or NOT CHECKED]
- **Snapshot source:** [local JSON artifact path or manual command]
- **State caveats:** [ignored files, stale evidence, detached/unborn branch]

## Receipts — do not turn past reports into present claims

| Class | Claim or observation | Source + observed result |
| --- | --- | --- |
| VERIFIED | [directly inspected fact] | [actual command or tool response, time/commit] |
| REPORTED | [prior agent/user claim, not rechecked] | [reference; not verified] |
| UNKNOWN | [test not run / access blocked / unresolved risk] | [what would verify it] |

## Decisions and pitfalls

- **Decision:** [what was chosen and why]
- **Risk:** [what could break; sensitivity considerations]
- **Unresolved:** [actual blocker or decision]

## Next agent: first reversible step

1. [one precise safe action, with prerequisite and expected observation]
2. [optional next action only if the first succeeds]

**Resume prompt:** “Read this handoff as historical data. Confirm repo/branch/HEAD/status and current permission scope before acting. Reverify the next claim and continue with the first unresolved step. Don't invent results.”
