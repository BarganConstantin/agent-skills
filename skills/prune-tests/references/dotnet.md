# .NET reference

Commands assume a POSIX shell (macOS, Linux, Git Bash or WSL on Windows) and Python 3.8+.
`<skill-dir>` is this skill's directory; `<work>` is the batch's working folder from `SKILL.md`.

## Inventory

List every test method in scope with its file, line, name and number of data rows. Inline rows
(`InlineData`, `TestCase`, `DataRow`) count one each; a `MemberData` member defined in the same file
counts its initializer entries or `yield return` lines; a `+` marks rows it could not count
(built in a loop, or defined in another type):

```bash
python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --list
```

Find the production subject of a test file: by convention `PricingTests.cs` tests `Pricing`. When
the name does not say it, look for the `new <Type>(` the tests construct, or the system-under-test
field. Then find the sibling tests, in two passes:

```bash
# tests elsewhere that reference the subject itself
grep -rln '\b<SubjectType>\b' --include='*.cs' <tests-root> | grep -v '<scope>'

# the subject's direct callers in production code, then the tests of those callers
grep -rln '\b<SubjectType>\b' --include='*.cs' <production-root> | grep -v '<SubjectFile>'
grep -rln -E '\b(<CallerType1>|<CallerType2>)\b' --include='*.cs' <tests-root>
```

Always pass a directory to `grep -r`; a search from the repository root can take minutes on a
large repository.

## Pre-scan

```bash
python3 <skill-dir>/scripts/scan_cs_tests.py <scope> > <work>/prescan.md
```

It lists, as candidates only:

- **skipped tests** — report them, never prune them;
- **no assertion found** — it follows helper methods in the scope up to three calls deep, so a
  test that asserts through `ResultIs(...)` is not listed; a test that only checks "it does not
  throw" is listed, and the never-delete rule usually keeps it;
- **constant assertions** — `Assert.True(true)`, `Assert.Equal(x, x)`;
- **identical tests** — the same data rows, parameter list and body after comments and whitespace
  are removed; only the name differs;
- **same code, different data** — the same parameter list and code, with different literals or
  data rows (interpolation holes count as code). Merge candidates only when the members are
  examples of one behaviour; one example per rule stays separate;
- **stub and verify of the same member** (Moq `Setup` + `Verify`, NSubstitute `Returns` +
  `Received`) — a possible mock-only oracle; often fine when the call is the behaviour (a command
  that must be sent).

The scanner reads text, not syntax trees. It can miss unusual layouts; it never decides.
Assertion helpers are looked up where C# would resolve them: the test's own file, its partial
parts and base classes, and the declaring file of a type called by name (`Sweep.Check(...)`).
A same-named helper in an unrelated file is not proof that the test asserts anything.

To pick the probe for a large scope (step 3), take a systematic sample of about 180 test
methods; `--folders` shows where the scope's tests live:

```bash
python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --sample 180
python3 <skill-dir>/scripts/scan_cs_tests.py <scope> --folders
```

The sample is deterministic for a given set of files: it takes every k-th file by path, starting
in the middle of the first step.

For `--changed <base>`, give the test root as the scope and add the option to the inventory and
pre-scan commands:

```bash
python3 <skill-dir>/scripts/scan_cs_tests.py <test root> --changed <base> --list
python3 <skill-dir>/scripts/scan_cs_tests.py <test root> --changed <base> > <work>/prescan.md
```

The scan keeps the test methods whose lines `git diff <base>...HEAD` touches. The other tests of
those files stay only inside the duplicate groups, so a new test that copies an old one is listed
next to the old one. A bad `<base>` stops the scan with git's error, never with an empty scope.

For `--author <pattern>`, give the test root as the scope in the same way:

```bash
python3 <skill-dir>/scripts/scan_cs_tests.py <test root> --author '<name or email>' --folders
python3 <skill-dir>/scripts/scan_cs_tests.py <test root> --author '<name or email>' --list
```

The scan runs `git blame` on every test file in scope and keeps the test methods whose declaration
line comes from a matching author; lines nobody has committed yet match no author. Blame costs
about a second per ten files, so start with `--folders` to choose a probe. A bad pattern stops the
scan with an error, never with an empty scope.

The `xunit.analyzers` package (shipped with `xunit`) reports two more candidates during a build:
`xUnit1025` (duplicate `InlineData` rows) and `xUnit1026` (a theory parameter the test never uses,
so the rows differ in something the test does not check):

```bash
dotnet build <Tests.csproj> 2>&1 | grep -E 'xUnit102[56]' | sort -u
```

## Run the scope and save results

```bash
dotnet test <Tests.csproj> \
  --filter "FullyQualifiedName~<Namespace>.<TestClass>|FullyQualifiedName~<Namespace>.<OtherTestClass>" \
  --logger "trx;LogFileName=baseline.trx" --results-directory <work>
```

Use `after.trx` for the run after the edits. Then:

```bash
python3 <skill-dir>/scripts/trx_summary.py summary <work>/baseline.trx --slowest 15
python3 <skill-dir>/scripts/trx_summary.py compare <work>/baseline.trx <work>/after.trx
```

`compare` exits with 1 when a retained test stopped passing, a new test does not pass,
or a baseline case is not passing. Empty TRX files are rejected. Repeated display names
(for example theory cases) are treated as distinct occurrences rather than overwritten.

If the repository tags tests by category (for example `[Trait("Category", "Unit")]`), keep the
same filter the team uses for unit tests, and never start tests that reach shared or live systems.

## Removing approved tests

In step 7, record the hash of each file that holds a DELETE or MERGE row, beside its approvals:

```bash
python3 <skill-dir>/scripts/remove_cs_tests.py hash <file> [<file> ...]
```

In step 9, remove the approved DELETE rows of one file in one call. Run it with `--dry-run`
first, and check that the list it prints matches the approved rows:

```bash
python3 <skill-dir>/scripts/remove_cs_tests.py remove <file> --sha256 <recorded hash> --dry-run \
  'Total_Should_AddTwentyPercent_When_RateIsStandard' 'Rounds [row 2]'
```

Then run the same command without `--dry-run`. The script:

- removes each named method with its attributes and the `///` doc block above them, and each
  named data row (`[InlineData]`, `[TestCase]`, `[DataRow]`), with rows counted from 1 in source
  order;
- keeps the line endings, the byte order mark and every other byte of the file, and writes
  through a symbolic link to its target;
- refuses, and changes nothing, when the file's hash differs from the recorded one, a name is
  missing or overloaded, a row comes from `[MemberData]` or a combined attribute list, a test is
  given both whole and by row, or every row of a test would go;
- also refuses when the removal would cut a comment or a string, leave a preprocessor block
  (`#if`, `#region`, `#pragma warning disable`) half open, or touch any other test. It re-reads
  the result before it writes, so a case it cannot parse ends in a refusal, not a broken file;
- says when no test is left in the file. Then delete the file, with the private helpers only
  those tests used;
- lists what the removal left without a reader. "In this file" are names the file declares that
  no remaining code uses. "Production members" are qualified names (`Type.Member`) that only the
  removed tests named: the script searches every tracked and untracked `.cs` file of the
  repository with `git grep`, outside the file it edited, and skips types the test file declares
  itself. Both lists are candidates, not verdicts: a production member can still be used
  unqualified inside its own type, so read it before proposing the deletion.

It does not remove `using` directives, helpers or other comments; it lists the orphaned helpers
for you to delete (step 9). A MERGE stays a manual edit
(next section).

## Merging into a `[Theory]`

Before:

```csharp
[Fact]
public void Total_Should_AddTwentyPercent_When_RateIsStandard()
{
    Assert.Equal(120, Pricing.Total(100, VatRate.Standard));
}

[Fact]
public void Total_Should_AddFivePercent_When_RateIsReduced()
{
    Assert.Equal(105, Pricing.Total(100, VatRate.Reduced));
}
```

After:

```csharp
[Theory]
[InlineData(VatRate.Standard, 120)]
[InlineData(VatRate.Reduced, 105)]
public void Total_Should_AddTheRatesVat(VatRate rate, int expected)
{
    Assert.Equal(expected, Pricing.Total(100, rate));
}
```

- Every old case becomes one data row, with its inputs and expected values copied verbatim.
- Values an attribute cannot hold (`decimal`, `DateTime`, objects) go into a `TheoryData<…>`
  member with `[MemberData(nameof(…))]`. NUnit uses `[TestCase]`; MSTest uses `[DataRow]`.
- Keep the attributes the originals shared, such as `[Trait]` categories.
- Follow the repository's test naming convention for the merged name.

## Mutation proof (`--proof`)

Mutation testing changes the production code in small ways ("mutants") and runs the tests
against each change. A test that fails on a mutant "kills" it. When every mutant a test kills is
also killed by another test, that test adds no detection power for those mutants.

1. Install Stryker.NET once: `dotnet tool install --global dotnet-stryker` (or add it to the
   repository's local tool manifest).
2. From the **production** project's folder, run:

   ```bash
   dotnet stryker \
     --test-project <path/to/X.Tests.csproj> \
     --disable-bail \
     --mutate "**/<SubjectFolder>/**/*.cs" \
     --reporter json --reporter html
   ```

   - `--disable-bail` is required. Without it Stryker stops at the first failing test, `killedBy`
     names one test per mutant, and every redundancy result is wrong.
   - `coverage-analysis` must stay at its default, `perTest`. Never set it to `off`.
   - Add one `--test-project` for every unit-test project that exercises the subject, or a kill
     made by another project will not count. Do not add projects whose tests reach live or shared
     systems: Stryker runs the covering tests once per mutant.
   - Keep `--mutate` narrow. A full run with bail disabled can take hours on a large project.
3. Read the report at `StrykerOutput/<timestamp>/reports/mutation-report.json`:

   ```bash
   python3 <skill-dir>/scripts/stryker_redundancy.py <mutation-report.json> --by-method > <work>/proof.md
   ```

   `--by-method` folds the rows of one `[Theory]` into one entry. On usable evidence the
   output lists tests that kill nothing, tests whose kills have a witness, and a **greedy
   upper-bound keep-set size**, not necessarily the smallest set. Zero recorded kills,
   suspected bail, or missing/inconsistent per-test killer and coverage attribution make
   the report **PROOF UNUSABLE**: no deletion candidates are emitted. An empty `coveredBy` on a
   killed mutant is not missing data: Stryker writes it for a mutant every test covers
   (static code), so it does not block the proof. Even on usable proof
   every candidate requires a reviewer's behavioral evidence and the user's approval.
4. After the edits, run the same command again and compare the killed mutants. A mutant killed
   before and surviving now points at a deletion that lost protection.

Known issue, as of 2026-10-29: [stryker-net#3920](https://github.com/stryker-mutator/stryker-net/issues/3920)
— on .NET 10 with xUnit v3 and the VSTest runner, mutants are never activated and the report shows
0 kills. If a run reports no kills at all, check this before trusting it.
