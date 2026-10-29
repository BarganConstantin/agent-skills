# Criteria

## Keep bar

A test stays when **all** of these hold:

1. It protects a specific observable behaviour, invariant or contract that a caller relies on.
2. A credible bug would make it fail. Name the bug.
3. Its expected values come from a source independent of the code under test: the spec, a worked
   example, a known-good literal. Not from the same formula the code uses.
4. It adds protection the retained tests do not give: a distinct failure mode, an edge case, a
   different boundary, or clearly faster or more precise feedback.
5. A refactor that keeps the behaviour would not break it.

A test that fails 1 or 2 has no reason to exist, except a pin of a known open defect (see "Never
delete"). A test that fails 3 or 5 often guards a real contract badly: that is FIX, not DELETE.

## Verdicts

| Verdict | Meaning |
|---|---|
| KEEP | Passes the keep bar, or the evidence for removing it is not strong enough. |
| DELETE | Remove the test, or one data row of a data-driven test. |
| MERGE | Fold a group of tests that are examples of the same behaviour into one data-driven test, keeping every case. |
| FIX | A weak test of a real contract. Never deleted by this skill; listed for a separate rewrite. |

A verdict applies to a test method, or to one data row of a data-driven test (`Method [row n]`).

MERGE does not judge a test's value: each test in the group may pass the keep bar. It applies
only when the tests are examples of **one** behaviour. Tests that share code but each pin a
different rule stay separate, because each name documents its rule.

## Classes

Every DELETE, MERGE and FIX row names one class. A KEEP row names no class (`—`), unless it was a
candidate; then it names the candidate's class and says why it stays.

| Code | Class | What it looks like | Usual verdict |
|---|---|---|---|
| CF | Cannot fail | No assertion; asserts a value the same test just arranged; `Assert.True(true)`; asserts a constant against itself; asserts only that a non-nullable result is not null. | DELETE when the subject has no contract; FIX when it does |
| EC | Echo | The expected value is computed with the production formula or a helper that re-implements it; a snapshot that only mirrors the current output. | FIX; DELETE only when a correct test of the same behaviour exists (then it is also DU) |
| MK | Mock-only oracle | Asserts what a stub was told to return; verifies a call the test itself stubbed, when the result already shows it; the mock implements the behaviour being asserted. | DELETE when the real behaviour is tested elsewhere or the subject is a pass-through; otherwise FIX |
| DU | Duplicate | Same behaviour, same class of input, same or weaker assertions as a retained test. | DELETE the weaker one |
| LR | Layer replay | Re-proves through a mocked collaborator a contract that a retained test already proves at a stronger boundary. | DELETE the weaker-layer test |
| PD | Parameter copies | Several tests with the same code that differ only in input and expected values, **and** are examples of the same behaviour. One example per rule is not PD. | MERGE into one data-driven test |
| DR | Duplicate data row | A data row that repeats the input class of another row of the same test, so it can only fail when that row fails too. | DELETE the row |
| IC | Implementation-coupled | Asserts call order or call counts, private state, or an exact format or internal value that callers do not rely on; a refactor that keeps the behaviour breaks it. | FIX; DELETE only when a behavioural test of the same contract exists (then it is also DU) |
| TV | Trivia | Auto-properties, a constructor that only assigns, an enum's values, a DTO's property count, behaviour the framework or a library already guarantees, a pass-through wrapper with no logic. | DELETE |
| SC | Scaffolding | Written to sketch an API while building it and no longer guards a contract; exists only to keep a test-only production seam alive; only asserts that something already removed stays absent. | DELETE |

## Evidence rules

- **DU, LR**: cite the witness test as `file:line` and say what makes it at least as strong: the
  same class of input, the same or a stronger assertion, the same or a stronger boundary.
  The witness must be KEEP after reconcile.
- **PD**: cite every member of the group, confirm their code differs only in data, and name the
  one behaviour they all exemplify.
- **DR**: cite the twin row and name the input class both rows share.
- **IC**: quote the assertion and name a behaviour-preserving refactor that would break it.
- **CF, TV, SC**: write a positive statement of why no contract exists, for example "the subject is
  an auto-property with no logic". A missing citation is not evidence.
- **MK**: quote the setup line and the assertion line that mirror each other.
- **EC**: quote the production line that the expected value copies.
- **"No caller found" is never evidence.** Dependency injection, reflection, serialization,
  configuration binding and HTTP routes do not show up in a text search.
- **Similar names and overlapping coverage do not prove equivalence.** Read both tests: their
  inputs, the behaviour they exercise and their assertions.
- **Mutation evidence** (`--proof`) that a test's kills are a subset of the witness's kills is
  strong support for DU or LR. It is still not enough alone, because a test can assert things no
  mutant touched, such as an exception message, a log entry or a header.
- **Uncertain → KEEP**, with the uncertainty written in the row.

## Never delete

Unless the user names the test explicitly:

- a failing or skipped test — report it instead;
- the regression test of a fixed bug (its name or comment mentions a bug or ticket, or
  `git log --follow` shows it arrived with a fix), unless the witness uses the same failing input;
- a pin of a known open defect (its name or comment says it records today's wrong behaviour) —
  list it under "Known-defect pins"; it tells the team when the behaviour changes, and the user
  decides its fate when the defect is fixed;
- the only test of a security, authorization, tenant-isolation, data-deletion or money decision;
- the only test of a contract: public API shape, serialization format, database mapping,
  migrations, configuration defaults, wire protocol. A second test of the same contract may go
  as DU when the witness checks that contract at least as strictly;
- the only test at its boundary, for example the only integration test of a flow;
- a test whose only oracle is "does not throw" when the setup or the call can throw for a real
  reason — the throw is the oracle;
- the negative or edge-case twin of a positive test — the edge case is the distinct failure mode —
  unless a retained witness asserts the same negative or edge input at least as strictly; then it
  is DU like any other test.

## Why these rules

- An LLM verdict alone is often wrong. In a 2024 study, 30% of the test designs ChatGPT flagged as
  redundant were essential for coverage. The study used system-test designs written from
  requirements, not unit-test code, but the lesson carries: a redundancy claim needs evidence.
  ([arXiv 2412.03693](https://arxiv.org/abs/2412.03693))
- Deleting fast unit tests rarely shortens a test run. In
  [PX4 PR #29234](https://github.com/PX4/PX4-Autopilot/pull/29234), 67.6 s of the 67.8 s saved came
  from 13 test binaries that sleep or wait; the other ~600 deleted cases ran in 0.16 s combined,
  and the reviewer requested changes because they still guarded behaviour. The real gain of
  pruning is less churn on refactors and reviews.

## Sources

The criteria above are written in our own words, drawing on:

- Kent Beck, [Test Desiderata](https://testdesiderata.com/) — tests change when behaviour changes, not when structure changes.
- Vladimir Khorikov, *Unit Testing Principles, Practices, and Patterns* (Manning, 2020) — a test's value; trivial code is not worth testing.
- [Software Engineering at Google, ch. 12 "Unit Testing"](https://abseil.io/resources/swe-book/html/ch12.html) — test behaviours through public APIs, not methods.
- Martin Fowler, [Mocks Aren't Stubs](https://martinfowler.com/articles/mocksArentStubs.html) — state verification over interaction verification.
- Justin Searls, [Please don't mock me](https://testdouble.com/insights/please-dont-mock-me) — stubbing and verifying the same call is redundant.
- lox, [Prompt to remove unit tests](https://gist.github.com/lox/9ef443646a4f5a70eadcb09e9b872445) — the keep bar and the delete list.
- melodic-software, [`testing` plugin](https://github.com/melodic-software/claude-code-plugins) (MIT) — duplicate and layer-replay classes, "no caller found is not evidence", mutation gate before and after.
- OpenClaw, [`test-audit`](https://github.com/openclaw/openclaw/tree/main/.agents/skills/test-audit) (MIT) — one primary owner per contract; static or slow is not a reason to delete.
- Microsoft, [`dotnet/skills`](https://github.com/dotnet/skills) (MIT) — near-identical facts become a `[Theory]`.
- pekral, [`test-redundancy`](https://github.com/pekral/test-redundancy) — delete / merge-into-dataset / review, decided from coverage plus what each test asserts.
