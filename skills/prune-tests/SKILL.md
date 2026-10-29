---
name: prune-tests
description: "Find the tests an existing suite can lose — duplicates of a stronger test, tests that cannot fail, tests that restate the implementation or only check a mock, trivia, parameter copies that belong in one data-driven test — with evidence for every verdict, and delete or merge only the rows the user approves. Read-only report first; optional mutation-testing proof. Use when the user says 'prune tests', 'find redundant tests', 'too many tests', 'which tests can we delete', 'remove useless tests', 'test slop', 'clean up AI-written tests', 'dedupe the tests', 'curăță testele', 'teste inutile'. First-class for .NET (xUnit, NUnit, MSTest); the method works for any stack. Not for finding coverage gaps or writing new tests."
license: MIT
compatibility: Any coding agent with repository access; parallel subagents recommended for the review step. Python 3.10+ (standard library only) for the helper scripts; the .NET SDK to run tests; Stryker.NET only for the optional mutation proof. No network or MCP required.
---

# Prune tests

AI agents write many tests that protect nothing: the same behaviour checked three times, expected
values computed with the production formula, mocks asserted against themselves. This skill finds
them, proves each claim with a citation, and removes only what the user approves.

The goal is a smaller suite that still catches every bug the old one caught. It is never a
deletion count.

## Hard rules

- **No quota.** Never aim for a number or a percentage of deletions. If few tests qualify, say so.
- **Every DELETE or MERGE carries evidence** (see `references/criteria.md`, "Evidence rules").
  A row without it becomes KEEP, and the report says why.
- **When in doubt, KEEP.** A wrong deletion costs more than a wrong keep.
- **Nothing changes without the user's yes on that row.** Unattended runs stop after the report.
- **Never delete, skip or loosen a failing test.** Pre-existing failures are reported, not pruned.
- **Never merge across levels.** A unit test never merges with an integration or end-to-end test.
- **Never edit production code.** Test-only seams and helpers left orphaned are listed for a
  separate change.
- **Never commit or push.** The user reviews the diff and commits.
- **Slow is not redundant.** Report slow tests separately; do not delete a test because it is slow.

## Arguments

- `<scope>`: one test project, folder, test class or test file. Required.
  For a whole repository, list the test projects with their test counts, ask which to start
  with, and run one batch per project.
- `--proof`: add the mutation-testing evidence step (step 3). Slow: plan hours per large
  project for .NET.
- `apply`: continue an existing report at step 7, after the user approved rows.

## Working files

`<skill-dir>` is the directory that holds this `SKILL.md`; the scripts live in `<skill-dir>/scripts/`.

Use `<work>` = `.work/prune-tests/<scope-slug>/` at the repository root, where `<scope-slug>` is
the scope path lowercased with every character outside `[a-z0-9._-]` replaced by `-`. Before the
first write, check `git check-ignore -q .work/x`. If `.work/` is not ignored, create
`.work/.gitignore` containing `*` and tell the user.

Read state from these files at every step, never from conversation memory, so a compacted or
resumed session continues where the files say it stopped:

| File | Written in |
|---|---|
| `inventory.md` | step 1 |
| `prescan.md` | step 2 |
| `proof.md` | step 3 (only with `--proof`) |
| `review-<n>.md` | step 4, one per slice |
| `report.md` | step 5 and 6, the numbered decision table and each row's approval state |
| `baseline.trx`, `after.trx` | steps 7 and 9 |

## Steps

### 0. Refuse

Stop and name the remedy when:

- the scope does not exist or holds no tests;
- `apply` is requested and the working tree has changes outside `<work>` (the pruning diff must
  be reviewable on its own);
- `apply` is requested on the default branch.

The report steps (1 to 6) are read-only and may run on any branch with any working tree.

### 1. Inventory

List every test method in scope with its file, line, name and number of data rows. For C#, run
`python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --list`. For each test file, name the
production subject it exercises (the class under test). Then list the sibling tests: tests
elsewhere that reference the subject, **and tests of the subject's direct callers**, because the
stronger twin of a unit test often sits one level up, for example in a handler's test or an
integration project. `references/dotnet.md` has the search commands.

Split the scope into slices of about 60 test methods (not data rows), or about 30 when the tests
set up many mocks. Keep all tests of one production subject in the same slice, because duplicates
live next to each other. Write `inventory.md`.

### 2. Cheap pre-scan

For C#, run `python3 <skill-dir>/scripts/scan_cs_tests.py <scope> > <work>/prescan.md`, then the
analyzer check in `references/dotnet.md`. The scan lists skipped tests, tests with no assertion
(following helpers), constant assertions, identical tests, tests with the same code but different
data, and stub-and-verify of the same member. For other stacks, do the same checks with search
commands. These results are **candidates for the reviewers, not verdicts**. Shared code alone
proves nothing: a file of examples for a pure function will show many "same code" groups whose
members each pin a different rule.

### 3. Mutation proof (only with `--proof`)

Follow "Mutation proof" in `references/dotnet.md`: run Stryker with bail disabled, then
`python3 <skill-dir>/scripts/stryker_redundancy.py <mutation-report.json> --by-method > <work>/proof.md`.

A test listed there either kills no mutant, or every mutant it kills is also killed by a named
witness. That is strong evidence, but still not a verdict: a test can assert things no mutant
touched (an exception message, a log entry, a header). The reviewers read both tests.

### 4. Review in parallel

For each slice, start one fresh-context subagent with the brief in
`references/reviewer-brief.md`, filled with the repository root, `<skill-dir>`, the slice's tests,
their production subjects, the sibling test projects from step 1, and the matching lines of
`prescan.md` and `proof.md`.
Run at most four at a time. Use the strongest model available for this step, because it is the
step that decides deletions and a wrong deletion costs more than the tokens, unless the user or
the project's instructions name another model. Write each answer to `review-<n>.md`.

### 5. Reconcile

Read every `review-<n>.md` and apply these checks before anything reaches the user:

1. **Evidence.** A DELETE or MERGE row that lacks the evidence its class requires becomes KEEP,
   with the reason.
2. **Witness must survive.** A row whose witness is itself DELETE gets the witness's witness, if
   that one survives and still covers the claim. Otherwise the row becomes KEEP. Two tests can
   never be each other's only reason to go.
3. **Never-delete list.** Re-check every DELETE and MERGE against "Never delete" in
   `references/criteria.md`.
4. **Cross-slice twins.** A test cited as a witness from another slice must be KEEP there.

### 6. Report and ask

Write `report.md`:

- a summary line: tests in scope, and counts of KEEP, MERGE, DELETE and FIX, with the estimated
  lines removed;
- one numbered table per verdict (DELETE, MERGE, FIX), each row with the test (or `Method [row n]`),
  the class code, the evidence and the confidence;
- KEEP rows only as a count, except "Candidates turned down": every pre-scan or proof candidate
  that ended as KEEP, and every row the reconcile step turned back, each with its reason, so the
  user sees why a flagged test stays;
- "Known-defect pins": tests that record today's wrong behaviour of an open defect;
- orphans the deletions would leave (helpers, fixtures, test-only production seams).

Show the summary and the DELETE and MERGE tables in chat, and give the path of `report.md`.
Ask the user to approve by row number, for example "approve 1-14, 20; reject 15".
Record each answer in `report.md`. Stop here when the run is unattended or nothing was approved.

FIX rows are weak tests of a real contract. They are never deleted here; list them for a
separate rewrite.

### 7. Baseline

Run the scope's tests once and save the result as `<work>/baseline.trx` (command in
`references/dotnet.md`). If any test fails, stop and list the failures. A pre-existing failure
is not a pruning candidate, and pruning on a red baseline hides what the edit broke.

### 8. Apply the approved rows

- **DELETE**: remove the whole test method with its attributes and its doc comment. Remove a
  `using` or import only when nothing else in the file still needs it. For a `Method [row n]`
  row, remove only that data-row attribute.
- **MERGE**: turn the approved group into one data-driven test (`[Theory]` with one data row per
  old case, or the framework's equivalent). Copy every old case's inputs and expected values
  verbatim; a merge never drops or changes a case. Name the merged test after the behaviour.
- Keep each file's line endings and encoding.
- Do not delete helpers, fixtures or production code. Add them to the orphan list.

### 9. Verify

Build and run the same scope again into `<work>/after.trx`, then run
`python3 <skill-dir>/scripts/trx_summary.py compare <work>/baseline.trx <work>/after.trx`.

- "Passed before, failing now" or "New and not passing" must be empty. Otherwise stop and show
  the failures. Do not revert or "fix" on your own; the user decides.
- "Gone" must equal the approved deletions (methods and rows) plus the originals of each merge.
  "New" must equal the merged data rows. Any other difference stops the batch.
- With `--proof`: re-run the same Stryker command and compare the killed mutants. A mutant killed
  before and surviving now names a deletion that lost protection; report it.
- Optional: compare coverage under the same settings. Investigate a drop of more than 2 points,
  but stable coverage does not prove that protection was kept.

### 10. Finish

Show `git diff --stat`, the counts removed, the orphan list and the FIX list. Then show where the
time goes: `python3 <skill-dir>/scripts/trx_summary.py summary <work>/baseline.trx --slowest 15`.
Deleting fast unit tests rarely shortens a test run; a few slow tests usually dominate it, and
they are the place to look when the goal is a faster suite. Stop. The user commits.

## References

- `references/criteria.md` — keep bar, the verdict classes, evidence rules, never-delete list, sources.
- `references/reviewer-brief.md` — the brief for the step 4 subagents.
- `references/dotnet.md` — commands for .NET: inventory, pre-scan, running a scope, merging into
  `[Theory]`, mutation proof.
- `scripts/scan_cs_tests.py`, `scripts/stryker_redundancy.py`, `scripts/trx_summary.py` —
  deterministic helpers, standard library only. Their tests live in the source repository at
  `tests/test_prune_tests.py`.
