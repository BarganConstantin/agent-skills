---
name: prune-tests
description: "Find the tests an existing suite can lose — duplicates of a stronger test, tests that cannot fail, tests that restate the implementation or only check a mock, trivia, parameter copies that belong in one data-driven test — with evidence for every verdict, and delete or merge only the rows the user approves. Best on a branch's new tests (--changed) or on one author's tests (--author). Read-only report first; a large scope starts with a probe that measures tokens, time and yield and asks whether the full run is worth it; optional mutation-testing proof. Use when the user says 'prune tests', 'find redundant tests', 'too many tests', 'which tests can we delete', 'remove useless tests', 'test slop', 'clean up AI-written tests', 'dedupe the tests', 'curăță testele', 'teste inutile'. First-class for .NET (xUnit, NUnit, MSTest); the method works for any stack. Not for finding coverage gaps or writing new tests."
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
- **Never edit production code without the user's yes on that change.** A deletion can leave
  production members with no reader; they go into a separate commit that the user approves.
- **Never commit or push.** The user reviews the diff and commits.
- **Slow is not redundant.** Report slow tests separately; do not delete a test because it is slow.

## Arguments

- `<scope>`: one test project, folder, test class or test file, or a list of test files. Required.
  For a whole repository, list the test projects with their test counts, ask which to start
  with, and run one batch per project.
- `--changed <base>`: only the test methods the current branch added or changed since `<base>`
  (for example `origin/develop`), that is the tests whose lines `git diff <base>...HEAD` touches.
  The other tests of the same files become sibling tests: the reviewers search them for twins
  and give them no verdict. This is the cheapest and most useful run: it prunes AI-written tests
  before they merge, at a few dozen tests a time, instead of cleaning a large suite afterwards.
  Do not take whole changed files instead: on one suite, 17 merged branches touched 910 test
  methods in files that held 3,005, so whole files cost about three times as much.
- `--author <pattern>`: only the test methods whose declaration line `git blame` gives to an
  author whose `name <email>` matches the pattern (a case-insensitive regular expression), for
  example "the tests I wrote" or the account an AI agent commits under. The other tests of the
  same files become sibling tests, as with `--changed`, and the two options combine. It reads
  who declared the test, not who last touched it: an edit to the body does not move the test to
  another author. Use it when the user names an author instead of a branch.
- `--proof`: add the mutation-testing evidence step (step 4). Slow: plan hours per large
  project for .NET.
- `apply`: continue an existing report at step 8, after the user approved rows.

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
| `estimate.md` | step 3 (only for scopes above 150 test methods) |
| `proof.md` | step 4 (only with `--proof`) |
| `review-<n>.md` | step 5, one per slice |
| `report.md` | steps 6 and 7, the numbered decision table and each row's approval state |
| `baseline.trx`, `after.trx` | steps 8 and 10 |

## Steps

### 0. Refuse

Stop and name the remedy when:

- the scope does not exist or holds no tests;
- `apply` is requested and the working tree has changes outside `<work>` (the pruning diff must
  be reviewable on its own);
- `apply` is requested on the default branch.

The report steps (1 to 7) are read-only and may run on any branch with any working tree.

### 1. Inventory

List every test method in scope with its file, line, name and number of data rows. For C#, run
`python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --list`, with `--changed <base>` or
`--author <pattern>` when the run has them. For other stacks, take the tests inside the diff's
hunks, or the tests whose declaration `git blame` gives to the author. For each test file, name the
production subject it exercises (the class under test). Then list the sibling tests: tests
elsewhere that reference the subject, **and tests of the subject's direct callers**, because the
stronger twin of a unit test often sits one level up, for example in a handler's test or an
integration project. Search the whole production source tree for subjects and callers, not only
the usual layer folders: integrations often live in top-level projects of their own.
`references/dotnet.md` has the search commands.

Split the scope into slices of about 60 test methods (not data rows), or about 30 when the tests
set up many mocks. Keep all tests of one production subject in the same slice, because duplicates
live next to each other, even when that makes the slice larger than the target; split one
subject's tests by test class only above about 90 methods. Write `inventory.md`.

### 2. Cheap pre-scan

For C#, run `python3 <skill-dir>/scripts/scan_cs_tests.py <scope> > <work>/prescan.md` (adding
`--changed <base>` or `--author <pattern>` when the run has them), then the
analyzer check in `references/dotnet.md`. The scan lists skipped tests, tests with no assertion
(following helpers), constant assertions, identical tests, tests with the same code but different
data, and stub-and-verify of the same member. For other stacks, do the same checks with search
commands. These results are **candidates for the reviewers, not verdicts**. Shared code alone
proves nothing: a file of examples for a pure function will show many "same code" groups whose
members each pin a different rule.

### 3. Probe and estimate

Skip this step when the scope holds 150 test methods or fewer, and review it whole.

A large scope can cost many tokens for little gain, and the gain depends on how the tests were
written. Measure it on a sample before spending the full amount.

1. **Pick the probe.** Run `python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --sample 180`.
   It lists a systematic sample of the scope: every k-th test file by path, about 180 test
   methods in all. A sample spread over the whole scope predicts the rest; the densest folder
   does not, because the pre-scan's candidates rarely become deletions (on one suite, none of 16
   confirmed deletions was a pre-scan candidate). When the user names an area to try first,
   sample that area instead. Say which files and why, and what the probe will cost before it
   starts: on one C# suite, ten probes cost 1.7k to 6.6k tokens per test method, and 5 to 16
   minutes per reviewer. The cost rises with the number of places a behaviour can be tested from:
   code reached from several surfaces sends the reviewers through every surface's tests.
2. **Run steps 5 to 7 on the probe only** (step 4 as well when `--proof` is on).
3. **Measure.** Record the tokens and wall-clock time each reviewer used, from the usage the
   runtime reports for subagents. When it reports none, record the lines of test and production
   code the reviewers read instead, and say that the estimate is rougher. Record the test methods
   reviewed, the DELETE and MERGE rows, and the lines they remove.
4. **Estimate the rest** in `<work>/estimate.md`, with `n` the probe's test methods and `N` the
   rest of the scope's:

   | | Probe | Rest of the scope (estimate) |
   |---|---|---|
   | Test methods | n | N |
   | Tokens | t | t / n × N |
   | Time | m | m / n × N, divided by the reviewers running in parallel |
   | Test methods removed | k, that is k / n of the tests (a merge counts the methods it absorbs; a deleted data row counts zero) | k / n × N, given as a range from half to one and a half times |
   | Data rows removed | r | r / n × N |
   | Lines removed | l | the same ratio as the rows |

   The yield estimate is rough: the share varies by area (on one suite, ten areas gave from 0.5%
   to 6.5% of their test methods at high confidence). Give the cost in tokens; convert it to money only with the user's own price per token.
5. **Recommend and ask.** Point to one of three roads and say why the numbers point there:
   - **Continue on the whole scope**: the probe removed a real share, about 5% of its test methods or
     more.
   - **Probe one more area first**: the probe's share sits between the two thresholds, or the
     scope mixes areas written in very different styles. Name the area and its size.
   - **Stop here**: the probe removed under about 2% of its test methods. The suite is already lean, and
     a full run would cost more than it saves.

   The thresholds are a guide, not a rule. Show the probe's DELETE and MERGE tables as well, so
   the user can approve those rows now. Continue only on the user's yes; an unattended run stops
   here. Later batches skip the probe's files and add their rows to the same `report.md`.

### 4. Mutation proof (only with `--proof`)

Follow "Mutation proof" in `references/dotnet.md`: run Stryker with bail disabled, then
`python3 <skill-dir>/scripts/stryker_redundancy.py <mutation-report.json> --by-method > <work>/proof.md`.

If the Stryker report says **PROOF UNUSABLE** (zero killed mutants, suspected bail, or missing
per-test attribution), do not justify any DELETE or MERGE from it. Investigate and rerun
Stryker or proceed with static review alone, marking mutation proof unavailable.
A usable report identifies tests that kill nothing or whose kills have a witness. This
is candidate evidence, not a verdict: a test may assert something no mutant touched
(an exception message, a log entry, a header). The reviewers read both tests.

### 5. Review in parallel

For each slice, start one fresh-context subagent with the brief in
`references/reviewer-brief.md`, filled with the repository root, `<skill-dir>`, the slice's tests,
their production subjects, the sibling test projects from step 1, and the matching lines of
`prescan.md` and `proof.md`.
Run at most four at a time. Use the strongest model available for this step, because it is the
step that decides deletions and a wrong deletion costs more than the tokens, unless the user or
the project's instructions name another model. Each reviewer returns its table in its answer;
the session that runs this skill writes `review-<n>.md` and, later, `report.md`. Some runtimes do
not let a subagent write report files, so never leave that to a reviewer.

### 6. Reconcile

Read every `review-<n>.md` and apply these checks before anything reaches the user:

1. **Evidence.** A DELETE or MERGE row that lacks the evidence its class requires becomes KEEP,
   with the reason.
2. **Witness must survive.** A row whose witness is itself DELETE gets the witness's witness, if
   that one survives and still covers the claim. Otherwise the row becomes KEEP. Two tests can
   never be each other's only reason to go.
3. **Never-delete list.** Re-check every DELETE and MERGE against "Never delete" in
   `references/criteria.md`.
4. **Cross-slice twins.** A test cited as a witness from another slice must be KEEP there.
5. **Witnesses outside the scope.** List every witness that sits in a file outside this run under
   "Witnesses to keep" in `report.md`. A later run whose scope holds that file reads the lists in
   earlier `.work/prune-tests/*/report.md` files first and keeps those tests.

### 7. Report and ask

Write `report.md`:

- a summary line: tests in scope, and counts of KEEP, MERGE, DELETE and FIX, with the estimated
  lines removed;
- one numbered table per verdict (DELETE, MERGE, FIX), each row with the test (or `Method [row n]`),
  the class code, the evidence and the confidence;
- KEEP rows only as a count, except "Candidates turned down": every pre-scan or proof candidate
  that ended as KEEP, and every row the reconcile step turned back, each with its reason, so the
  user sees why a flagged test stays;
- "Known-defect pins": tests that record today's wrong behaviour of an open defect;
- "Witnesses to keep": witnesses outside the scope that later runs must not delete;
- orphans the deletions would leave (helpers, fixtures, test-only production seams);
- the cost of the run: test methods reviewed, tokens and time used, and tokens per test method.

Show the summary and the DELETE and MERGE tables in chat, and give the path of `report.md`.
Ask the user to approve by row number, for example "approve 1-14, 20; reject 15". When the user
approves in advance ("apply what you find"), that covers only the DELETE rows of high confidence
whose witness the session running this skill has read in the code itself; list every other row
for a decision.
Record each answer in `report.md`. Record a SHA-256 content hash for every test file containing
a proposed DELETE or MERGE, alongside its approval rows (for C#,
`python3 <skill-dir>/scripts/remove_cs_tests.py hash <files>`). Before applying, compare the current
hash with the recorded value. Any mismatch invalidates approvals for that file, even if the
commit SHA is unchanged. Stop here when unattended or nothing was approved.

FIX rows are weak tests of a real contract. They are never deleted here; list them for a
separate rewrite.

### 8. Baseline

Run the scope's tests once and save the result as `<work>/baseline.trx` (command in
`references/dotnet.md`). If any test fails, stop and list the failures. A pre-existing failure
is not a pruning candidate, and pruning on a red baseline hides what the edit broke.

### 9. Apply the approved rows

Recheck each affected test file against its SHA-256 from step 7. If a file has changed,
stop and rerun review; never apply approval to stale source.

- **DELETE**: remove the whole test method with its attributes and its doc comment. Remove a
  `using` or import only when nothing else in the file still needs it. For a `Method [row n]`
  row, remove only that data-row attribute. For C#, use `scripts/remove_cs_tests.py` ("Removing
  approved tests" in `references/dotnet.md`): it checks the file's hash and removes all of the
  file's approved rows in one step, or refuses and changes nothing.
- **MERGE**: turn the approved group into one data-driven test (`[Theory]` with one data row per
  old case, or the framework's equivalent). Copy every old case's inputs and expected values
  verbatim; a merge never drops or changes a case. Name the merged test after the behaviour.
- Keep each file's line endings and encoding.
- **Clean the test file.** Read what the removal left without a reader in the same file: helpers,
  fields, constants, harness switches. For C#, `remove_cs_tests.py` lists them. Check each one and
  delete it in the same edit, because a helper that nothing calls tells the next reader that
  something still depends on it. Removing one can orphan the next (a field only the deleted helper
  set), so read the file again after each removal. When every test in a file goes, delete the file
  together with its private helpers.
- **Production members are a separate commit.** The script also lists the production members
  (`Type.Member`) that only the removed tests named. Confirm that nothing uses them unqualified
  inside their own type, then propose deleting them in a separate commit, verified by a build, and
  apply it only on the user's yes. Uniqueness or other checks that a deleted test made may still
  hold elsewhere (for example a `ToDictionary` that throws on a duplicate key); say so in the
  commit body.

### 10. Verify

Build and run the same scope again into `<work>/after.trx`, then run
`python3 <skill-dir>/scripts/trx_summary.py compare <work>/baseline.trx <work>/after.trx`.

- The baseline must include test results and every baseline result must be Passed. The TRX
  helper rejects empty runs, catches non-passing baselines, and compares repeated display
  names as distinct occurrences.
- "Passed before, failing now" or "New and not passing" must be empty. Otherwise stop and show
  the failures. Do not revert or "fix" on your own; the user decides.
- "Gone" must equal the approved deletions (methods and rows) plus the originals of each merge.
  "New" must equal the merged data rows. Any other difference stops the batch.
- With `--proof`: re-run the same Stryker command and compare the killed mutants. A mutant killed
  before and surviving now names a deletion that lost protection; report it.
- Optional: compare coverage under the same settings. Investigate a drop of more than 2 points,
  but stable coverage does not prove that protection was kept.

### 11. Finish

Show `git diff --stat`, the counts removed, the orphan list and the FIX list. Put the production
orphans you did not delete, the FIX list and the known-defect pins into the pull or merge request
description too: reviewers read the request, not `<work>`, and a list that stays in `report.md` is
a list nobody acts on. Then show where the
time goes: `python3 <skill-dir>/scripts/trx_summary.py summary <work>/baseline.trx --slowest 15`.
Deleting fast unit tests rarely shortens a test run; a few slow tests usually dominate it, and
they are the place to look when the goal is a faster suite. Stop. The user commits.

## References

- `references/criteria.md` — keep bar, the verdict classes, evidence rules, never-delete list, sources.
- `references/reviewer-brief.md` — the brief for the step 5 subagents.
- `references/dotnet.md` — commands for .NET: inventory, pre-scan, running a scope, removing
  approved tests, merging into `[Theory]`, mutation proof.
- `scripts/scan_cs_tests.py`, `scripts/remove_cs_tests.py`, `scripts/stryker_redundancy.py`,
  `scripts/trx_summary.py` — deterministic helpers, standard library only. Their tests live in the source repository at
  `tests/test_prune_tests.py`.
