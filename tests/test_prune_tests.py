#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "skills" / "prune-tests" / "scripts"


def load(module_name):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stryker = load("stryker_redundancy")
trx = load("trx_summary")
scanner = load("scan_cs_tests")
remover = load("remove_cs_tests")

SAMPLE_TESTS = '''
public class PricingTests
{
    [Fact]
    public void Constructor_runs()
    {
        var pricing = new Pricing(); // no assertion { brace in comment }
    }

    [Fact]
    public void Constant_check() => Assert.True(true);

    [Fact]
    public void Different_strings_are_not_constant() => Assert.Equal("a", "b");

    [Fact]
    [Trait("Category", "Unit")]
    public void Standard_rate_adds_twenty_percent()
    {
        Assert.Equal(120, Pricing.Total(100, "standard"));
    }

    [Fact]
    public void Reduced_rate_adds_five_percent()
    {
        Assert.Equal(105, Pricing.Total(100, "reduced"));
    }

    [Fact]
    public void Standard_rate_again()
    {
        // same body, different comment
        Assert.Equal(120, Pricing.Total(100, "standard"));
    }

    [Fact(Skip = "flaky")]
    public void Skipped_test() { }

    [TestCase(1)]
    [TestCase(2)]
    public void Nunit_rows(int value) { Assert.That(value, Is.Positive); }

    [Fact]
    public async Task Stub_then_verify()
    {
        repository.Setup(r => r.Load(It.IsAny<int>())).Returns(order);
        await service.Handle(1);
        repository.Verify(r => r.Load(1), Times.Once);
    }

    [Fact]
    public void String_with_markers_is_not_code()
    {
        var text = "// not a comment { [Fact] }";
        Assert.Equal(27, text.Length);
    }

    [Fact]
    public void Asserts_through_a_helper()
    {
        var total = Pricing.Total(100, "standard");
        TotalIs(total, 120);
    }

    private static void TotalIs(int total, int expected) => ExpectEqual(total, expected);

    private static void ExpectEqual(int actual, int expected) => Assert.Equal(expected, actual);

    [Fact]
    public void Calls_a_helper_that_asserts_nothing()
    {
        Arrange();
    }

    private static void Arrange() { var pricing = new Pricing(); }

    [Fact]
    public void Raw_interpolated_string_with_quotes()
    {
        var html = $$"""<img alt='Pool"}]}' src="{{pool}}">""";
        Assert.Contains("Pool", html);
    }

    [Theory]
    [InlineData("a\\n\\n\\nb", "a<br><br>b")]
    public void Collapses_blank_lines(string input, string expected) => Assert.Equal(expected, Html.From(input));

    [Theory]
    [InlineData("a\\r\\nb", "a<br>b")]
    [InlineData("a\\rb", "a<br>b")]
    public void Normalises_line_endings(string input, string expected) => Assert.Equal(expected, Html.From(input));

    [Theory]
    [InlineData("a\\r\\nb", "a<br>b")]
    [InlineData("a\\rb", "a<br>b")]
    public void Normalises_line_endings_copy(string input, string expected) => Assert.Equal(expected, Html.From(input));

    [Theory]
    [InlineData("x", "y", true)]
    public void Three_parameters(string input, string expected, bool flag) => Assert.Equal(expected, Html.From(input));

    [Fact]
    public void Links_the_url() => Assert.Equal($"<a>{url}</a>", Html.From(url));

    [Fact]
    public void Links_the_truncated_url() => Assert.Equal($"<a>{truncatedUrl}</a>", Html.From(url));
}
'''


class ScanCsTestsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        path = pathlib.Path(cls.directory.name) / "PricingTests.cs"
        path.write_text(SAMPLE_TESTS, encoding="utf-8")
        cls.result = scanner.scan(str(path))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @staticmethod
    def names(rows):
        return sorted(row["test"].rsplit(" ", 1)[1] for row in rows)

    def test_every_test_method_is_found_once(self):
        self.assertEqual(19, self.result["tests"])

    def test_inventory_counts_the_data_rows_of_each_method(self):
        rows = {row["test"].rsplit(" ", 1)[1]: row["rows"] for row in self.result["inventory"]}
        self.assertEqual((0, 2, 2), (rows["Constant_check"], rows["Nunit_rows"], rows["Normalises_line_endings"]))

    def test_a_test_without_any_assertion_is_listed_even_through_helpers(self):
        self.assertEqual(
            ["Calls_a_helper_that_asserts_nothing", "Constructor_runs"], self.names(self.result["no_assertion"])
        )

    def test_constant_assertions_are_listed_and_different_literals_are_not(self):
        self.assertEqual(["Constant_check"], self.names(self.result["constant_assertion"]))

    def test_identical_tests_ignore_comments_but_not_data_rows(self):
        groups = [self.names(group) for group in self.result["identical_tests"]]
        self.assertEqual(
            [["Standard_rate_adds_twenty_percent", "Standard_rate_again"], ["Normalises_line_endings", "Normalises_line_endings_copy"]],
            groups,
        )

    def test_tests_with_the_same_code_and_different_literals_are_merge_candidates(self):
        groups = [self.names(group) for group in self.result["same_code_different_data"]]
        self.assertIn(
            ["Reduced_rate_adds_five_percent", "Standard_rate_adds_twenty_percent", "Standard_rate_again"], groups
        )
        self.assertIn(["Collapses_blank_lines", "Normalises_line_endings", "Normalises_line_endings_copy"], groups)

    def test_a_different_parameter_list_or_interpolation_hole_is_different_code(self):
        grouped = {name for group in self.result["same_code_different_data"] for name in self.names(group)}
        self.assertNotIn("Three_parameters", grouped)
        self.assertNotIn("Links_the_url", grouped)
        self.assertNotIn("Links_the_truncated_url", grouped)

    def test_skipped_tests_are_reported_and_left_out_of_the_other_lists(self):
        self.assertEqual(["Skipped_test"], self.names(self.result["skipped"]))
        self.assertNotIn("Skipped_test", self.names(self.result["no_assertion"]))

    def test_stubbing_and_verifying_the_same_member_is_listed(self):
        rows = self.result["stub_then_verify"]
        self.assertEqual([("Stub_then_verify", ["Load"])], [(r["test"].rsplit(" ", 1)[1], r["members"]) for r in rows])

    def test_string_containing_an_assertion_is_not_flagged_as_constant(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "StringTests.cs"
            path.write_text('''
public class StringTests {
    [Fact]
    public void A() { var message = "Assert.True(true)"; Assert.NotNull(message); }
}
''', encoding="utf-8")
            result = scanner.scan(str(path))
        self.assertEqual([], result["constant_assertion"])

    def test_same_named_helper_in_another_file_does_not_hide_missing_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "Tests.cs").write_text('''
public class FirstTests {
    [Fact]
    public void Has_no_assertion() { ValidateOutcome(); }
    private void ValidateOutcome() { }
}
''', encoding="utf-8")
            (root / "Other.cs").write_text('''
public class Other {
    private void ValidateOutcome() { Assert.True(true); }
}
''', encoding="utf-8")
            result = scanner.scan(str(root))
        self.assertEqual(["Has_no_assertion"], self.names(result["no_assertion"]))

    def test_identical_string_literals_are_a_constant_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "LiteralTests.cs"
            path.write_text('''
public class LiteralTests {
    [Fact]
    public void Same() { Assert.Equal("ready", "ready"); }
}
''', encoding="utf-8")
            result = scanner.scan(str(path))
        self.assertEqual(["Same"], self.names(result["constant_assertion"]))

    def scan_files(self, files):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name, source in files.items():
                (root / name).write_text(source, encoding="utf-8")
            return scanner.scan(str(root))

    def test_a_helper_called_through_its_type_name_counts_as_an_assertion(self):
        result = self.scan_files({
            "WebWriteSweep.cs": '''
public static class WebWriteSweep {
    public static void NoWriteWasSent(Mock<IMediator> mediator) => mediator.Verify(m => m.Send(It.IsAny<object>(), default), Times.Never);
}
''',
            "SweepTests.cs": '''
public class SweepTests {
    [Fact]
    public void Passes_When_OnlyAQueryWasSent() { var mediator = new Mock<IMediator>(); WebWriteSweep.NoWriteWasSent(mediator); }
}
''',
        })
        self.assertEqual([], result["no_assertion"])

    def test_a_helper_in_a_base_class_counts_as_an_assertion(self):
        result = self.scan_files({
            "BaseTests.cs": '''
public abstract class BaseTests {
    protected static void ResultIs(int expected, int actual) => Assert.Equal(expected, actual);
}
''',
            "CalculatorTests.cs": '''
public class CalculatorTests : BaseTests {
    [Fact]
    public void Adds() { ResultIs(2, Calculator.Add(1, 1)); }
}
''',
        })
        self.assertEqual([], result["no_assertion"])

    def test_nunit_ignore_attribute_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "Ignored.cs"
            path.write_text('''
public class IgnoredTests {
    [Test(Ignore = "temporarily disabled")]
    public void Should_not_be_pruned() { }
}
''', encoding="utf-8")
            result = scanner.scan(str(path))
        self.assertEqual(["Should_not_be_pruned"], self.names(result["skipped"]))
        self.assertEqual([], result["no_assertion"])


MEMBER_DATA_TESTS = '''
public class RowsTests
{
    public static TheoryData<int, string> Pairs => new()
    {
        { 1, "a" },
        { 2, "b, c" },
        { 3, "d" },
    };

    public static TheoryData<string> Strings => new()
    {
        "first",
        "second",
        "last, without a trailing comma"
    };

    public static IEnumerable<object[]> Yielded()
    {
        yield return new object[] { 1 };
        yield return new object[] { 2 };
    }

    public static IEnumerable<object[]> Looped()
    {
        foreach (var i in Enumerable.Range(0, 5)) yield return new object[] { i };
    }

    [Theory]
    [MemberData(nameof(Pairs))]
    public void UsesPairs(int n, string s) => Assert.NotNull(s);

    [Theory]
    [MemberData(nameof(Strings))]
    public void UsesStrings(string s) => Assert.NotNull(s);

    [Theory]
    [MemberData(nameof(Yielded))]
    [InlineData(9)]
    public void UsesYielded(int n) => Assert.True(n > 0);

    [Theory]
    [MemberData(nameof(Looped))]
    public void UsesLooped(int n) => Assert.True(n >= 0);

    [Theory]
    [MemberData(nameof(ElsewhereData.Rows), MemberType = typeof(ElsewhereData))]
    public void UsesElsewhere(int n) => Assert.True(n >= 0);
}
'''


class MemberDataRowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        path = pathlib.Path(self.directory.name) / "RowsTests.cs"
        path.write_text(MEMBER_DATA_TESTS, encoding="utf-8")
        result = scanner.scan(str(path))
        self.rows = {row["test"].rsplit(" ", 1)[1]: (row["rows"], row["rows_exact"]) for row in result["inventory"]}

    def tearDown(self):
        self.directory.cleanup()

    def test_rows_of_a_theory_data_initializer_are_counted(self):
        self.assertEqual((3, True), self.rows["UsesPairs"])

    def test_a_last_string_row_without_a_trailing_comma_is_counted(self):
        self.assertEqual((3, True), self.rows["UsesStrings"])

    def test_yield_return_rows_add_to_inline_rows(self):
        self.assertEqual((3, True), self.rows["UsesYielded"])

    def test_rows_built_in_a_loop_are_marked_as_not_counted(self):
        self.assertEqual((1, False), self.rows["UsesLooped"])

    def test_member_data_defined_in_another_type_is_marked_as_not_counted(self):
        self.assertEqual((1, False), self.rows["UsesElsewhere"])


DUPLICATED_FOLDER = '''
public class ATests
{
    [Fact]
    public void First() { Assert.Equal(2, Calculator.Add(1, 1)); }

    [Fact]
    public void Second() { Assert.Equal(2, Calculator.Add(1, 1)); }

    [Fact]
    public void Third() { Assert.Equal(0, Calculator.Subtract(1, 1)); }
}
'''

CLEAN_FOLDER = '''
public class BTests
{
    [Fact]
    public void Sums() { Assert.Equal(3, Calculator.Sum(new[] { 1, 2 })); }

    [Fact]
    public void Throws() { Assert.Throws<DivideByZeroException>(() => Calculator.Divide(1, 0)); }
}
'''

ROOT_FILE = '''
public class RootTests
{
    [Fact]
    public void Multiplies() { Assert.Equal(6, Calculator.Multiply(2, 3)); }
}
'''


class SeveralScopesTests(unittest.TestCase):
    def test_a_list_of_changed_files_is_scanned_as_one_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "ATests.cs").write_text(DUPLICATED_FOLDER, encoding="utf-8")
            (root / "BTests.cs").write_text(CLEAN_FOLDER, encoding="utf-8")
            (root / "Untouched.cs").write_text(ROOT_FILE, encoding="utf-8")
            result = scanner.scan([str(root / "ATests.cs"), str(root / "BTests.cs")])
        self.assertEqual(5, result["tests"])
        self.assertEqual(2, result["files"])
        self.assertEqual(1, len(result["identical_tests"]))

BEFORE_BRANCH = """public class CartTests
{
    [Fact]
    public void Adds() => Assert.Equal(2, Cart.Add(1, 1));

    [Fact]
    public void Empties() => Assert.Empty(Cart.Clear());

    [Fact]
    public void OldCopyA() => Assert.Equal(3, Cart.Add(1, 2));

    [Fact]
    public void OldCopyB() => Assert.Equal(3, Cart.Add(1, 2));
}
"""

AFTER_BRANCH = """public class CartTests
{
    [Fact]
    public void Adds() => Assert.Equal(2, Cart.Add(1, 1));

    [Fact]
    public void Empties() => Assert.Empty(Cart.Clear(true));

    [Fact]
    public void OldCopyA() => Assert.Equal(3, Cart.Add(1, 2));

    [Fact]
    public void OldCopyB() => Assert.Equal(3, Cart.Add(1, 2));

    [Fact]
    public void AddsAgain() => Assert.Equal(2, Cart.Add(1, 1));
}
"""


class ChangedSinceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        self.git("init", "-q", "-b", "main")
        (self.root / "CartTests.cs").write_text(BEFORE_BRANCH, encoding="utf-8")
        (self.root / "UntouchedTests.cs").write_text(ROOT_FILE, encoding="utf-8")
        self.commit("base")
        (self.root / "CartTests.cs").write_text(AFTER_BRANCH, encoding="utf-8")
        self.commit("branch")
        self.result = scanner.scan(str(self.root), "HEAD~1")

    def tearDown(self):
        self.directory.cleanup()

    def git(self, *arguments):
        subprocess.run(["git", "-C", str(self.root), *arguments], check=True, capture_output=True)

    def commit(self, message):
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-q", "-m", message)

    def names(self, rows):
        return sorted(row["test"].rsplit(" ", 1)[1] for row in rows)

    def test_only_the_tests_the_branch_added_or_changed_are_in_scope(self):
        self.assertEqual(["AddsAgain", "Empties"], self.names(self.result["inventory"]))
        self.assertEqual(3, self.result["context_tests"])

    def test_a_new_copy_of_an_old_test_is_grouped_with_the_old_one(self):
        self.assertEqual([["Adds", "AddsAgain"]], [self.names(group) for group in self.result["identical_tests"]])

    def test_a_bad_base_is_an_error_not_an_empty_scope(self):
        with self.assertRaisesRegex(ValueError, "git failed"):
            scanner.scan(str(self.root), "no-such-ref")


ANA_WROTE = """public class CartTests
{
    [Fact]
    public void Adds()
    {
        Assert.Equal(2, Cart.Add(1, 1));
    }

    [Fact]
    public void Empties() => Assert.Empty(Cart.Clear());
}
"""

BOB_EDITED = """public class CartTests
{
    [Fact]
    public void Adds()
    {
        Assert.Equal(2, Cart.Add(1, 1, rounding: true));
    }

    [Fact]
    public void Empties() => Assert.Empty(Cart.Clear());

    [Fact]
    public void AddsAgain() => Assert.Equal(2, Cart.Add(1, 1));
}
"""

BOB_FILE = """public class BobTests
{
    [Fact]
    public void Multiplies() => Assert.Equal(6, Calculator.Multiply(2, 3));
}
"""


class AuthorScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        self.git("init", "-q", "-b", "main")
        (self.root / "CartTests.cs").write_text(ANA_WROTE, encoding="utf-8")
        self.commit("Ana", "ana@example.com")
        (self.root / "CartTests.cs").write_text(BOB_EDITED, encoding="utf-8")
        (self.root / "BobTests.cs").write_text(BOB_FILE, encoding="utf-8")
        self.commit("Bob", "bob@example.com")

    def tearDown(self):
        self.directory.cleanup()

    def git(self, *arguments):
        subprocess.run(["git", "-C", str(self.root), *arguments], check=True, capture_output=True)

    def commit(self, name, email):
        self.git("add", "-A")
        self.git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-q", "-m", name)

    def names(self, result):
        return sorted(row["test"].rsplit(" ", 1)[1] for row in result["inventory"])

    def test_only_the_tests_the_author_declared_are_in_scope(self):
        result = scanner.scan(str(self.root), author="ana")
        self.assertEqual(["Adds", "Empties"], self.names(result))
        self.assertEqual(1, result["files"])
        self.assertEqual(1, result["context_tests"])

    def test_an_edit_to_the_body_does_not_change_who_wrote_the_test(self):
        result = scanner.scan(str(self.root), author="bob")
        self.assertEqual(["AddsAgain", "Multiplies"], self.names(result))

    def test_the_pattern_matches_the_email_too(self):
        result = scanner.scan(str(self.root), author="bob@example")
        self.assertEqual(["AddsAgain", "Multiplies"], self.names(result))

    def test_the_author_and_the_changed_filters_both_apply(self):
        result = scanner.scan(str(self.root), "HEAD~1", author="ana")
        self.assertEqual(["Adds"], self.names(result))

    def test_a_test_nobody_committed_yet_is_not_in_scope(self):
        (self.root / "CartTests.cs").write_text(
            BOB_EDITED.replace("}\n}\n", "}\n\n    [Fact]\n    public void Drafted() => Assert.True(Cart.Ready());\n}\n"),
            encoding="utf-8")
        result = scanner.scan(str(self.root), author="bob")
        self.assertEqual(["AddsAgain", "Multiplies"], self.names(result))

    def test_the_scope_line_names_the_author(self):
        result = scanner.scan(str(self.root), author="ana")
        self.assertIn("written by authors matching 'ana'", scanner.scope_line(result))

    def test_a_bad_pattern_is_an_error_not_an_empty_scope(self):
        with self.assertRaisesRegex(ValueError, "--author"):
            scanner.scan(str(self.root), author="(")


class SystematicSampleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        for number in range(20):
            tests = "".join(
                f"    [Fact] public void Case{case}() {{ Assert.Equal({case}, Calculator.Id({case})); }}\n" for case in range(3)
            )
            (self.root / f"File{number:02d}Tests.cs").write_text(f"public class File{number:02d}Tests {{\n{tests}}}\n", encoding="utf-8")
        self.result = scanner.scan(str(self.root))

    def tearDown(self):
        self.directory.cleanup()

    def test_every_kth_file_is_taken_until_the_target(self):
        step, sample = scanner.systematic_sample(self.result, 15)
        self.assertEqual(4, step)
        self.assertEqual(["File02Tests.cs", "File06Tests.cs", "File10Tests.cs", "File14Tests.cs", "File18Tests.cs"],
                         [pathlib.Path(path).name for path, _ in sample])
        self.assertEqual(15, sum(count for _, count in sample))

    def test_the_sample_spans_the_whole_scope_not_only_its_start(self):
        _, sample = scanner.systematic_sample(self.result, 30)
        names = [pathlib.Path(path).name for path, _ in sample]
        self.assertIn("File19Tests.cs", names)
        self.assertEqual(10, len(names))


class FolderSummaryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        for relative, source in (("A/ATests.cs", DUPLICATED_FOLDER), ("B/BTests.cs", CLEAN_FOLDER), ("RootTests.cs", ROOT_FILE)):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def summary(self):
        return scanner.folder_summary(scanner.scan(str(self.root)), str(self.root))

    def test_each_subfolder_gets_its_tests_and_the_share_the_pre_scan_flagged(self):
        rows = {row["folder"]: (row["tests"], row["flagged"]) for row in self.summary()}
        self.assertEqual({"A": (3, 2), "B": (2, 0), scanner.ROOT_FILES: (1, 0)}, rows)

    def test_the_densest_folder_comes_first(self):
        self.assertEqual(["A", "B", scanner.ROOT_FILES], [row["folder"] for row in self.summary()])

    def test_the_printed_table_ends_with_the_totals(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            scanner.print_folders(self.summary())
        self.assertEqual("| **total** | 6 | 2 | 33% |", output.getvalue().strip().splitlines()[-1])


def mutant(mutant_id, status, covered_by, killed_by):
    return {"id": mutant_id, "status": status, "coveredBy": covered_by, "killedBy": killed_by}


def report(mutants, tests):
    return {
        "schemaVersion": "2",
        "files": {"src/Pricing.cs": {"language": "cs", "mutants": mutants}},
        "testFiles": {"tests/PricingTests.cs": {"tests": [{"id": i, "name": n} for i, n in tests.items()]}},
    }


TESTS = {
    "a": "PricingTests.Total_adds_tax",
    "b": "PricingTests.Total_adds_tax_and_rounds",
    "c": "PricingTests.Total_adds_tax_copy",
    "d": "PricingTests.Constructor_sets_fields",
    "e": "PricingTests.Discount_is_capped",
    "f": "OtherTests.Never_reaches_pricing",
}

MUTANTS = [
    mutant("1", "Killed", ["a", "b", "c", "d"], ["a", "b", "c"]),
    mutant("2", "Killed", ["a", "b", "c", "d"], ["a", "b", "c"]),
    mutant("3", "Killed", ["b", "d"], ["b"]),
    mutant("4", "Killed", ["e"], ["e"]),
    mutant("5", "Survived", ["d", "e"], []),
]


class StrykerRedundancyTests(unittest.TestCase):
    def setUp(self):
        self.result = stryker.analyse(report(MUTANTS, TESTS), by_method=False)
        self.subsumed = {row["test"]: row for row in self.result["subsumed"]}

    def test_a_test_whose_kills_a_stronger_test_also_makes_is_a_subset_candidate(self):
        row = self.subsumed["PricingTests.Total_adds_tax"]
        self.assertEqual(("PricingTests.Total_adds_tax_and_rounds", "subset"), (row["witness"], row["relation"]))

    def test_equal_twins_under_a_stronger_test_both_point_to_the_stronger_one(self):
        row = self.subsumed["PricingTests.Total_adds_tax_copy"]
        self.assertEqual(("PricingTests.Total_adds_tax_and_rounds", "subset"), (row["witness"], row["relation"]))

    def test_a_test_with_a_unique_kill_is_never_a_candidate(self):
        self.assertNotIn("PricingTests.Discount_is_capped", self.subsumed)
        self.assertNotIn("PricingTests.Total_adds_tax_and_rounds", self.subsumed)

    def test_a_test_that_covers_code_but_kills_nothing_is_listed(self):
        self.assertEqual(["PricingTests.Constructor_sets_fields"], [r["test"] for r in self.result["kill_nothing"]])

    def test_a_test_no_mutant_reached_gets_no_verdict(self):
        self.assertEqual(["OtherTests.Never_reaches_pricing"], self.result["not_reached"])

    def test_greedy_keep_set_covers_all_kills_in_fixture(self):
        self.assertEqual(2, self.result["greedy_keep_set"])
        self.assertEqual(4, self.result["killed_mutants"])

    def test_equal_kill_sets_keep_the_first_name_and_list_the_other(self):
        tests = {"x": "T.Alpha", "y": "T.Beta"}
        result = stryker.analyse(report([mutant("1", "Killed", ["x", "y"], ["x", "y"])], tests), by_method=False)
        self.assertEqual(
            [{"test": "T.Beta", "kills": 1, "witness": "T.Alpha", "witness_kills": 1, "relation": "equal"}],
            result["subsumed"],
        )

    def test_a_run_with_bail_on_is_flagged(self):
        bailed = [mutant(str(i), "Killed", ["a", "b"], ["a"]) for i in range(20)]
        self.assertTrue(stryker.analyse(report(bailed, TESTS), by_method=False)["bail_suspected"])
        self.assertFalse(self.result["bail_suspected"])

    def test_by_method_folds_theory_rows_into_one_entry(self):
        tests = {"r1": "T.Rounds(value: 1)", "r2": "T.Rounds(value: 2)", "s": "T.Other"}
        mutants = [mutant("1", "Killed", ["r1", "s"], ["r1"]), mutant("2", "Killed", ["r2", "s"], ["r2", "s"])]
        result = stryker.analyse(report(mutants, tests), by_method=True)
        self.assertEqual([("T.Other", "T.Rounds")], [(r["test"], r["witness"]) for r in result["subsumed"]])

    def test_deleting_every_listed_test_keeps_every_kill(self):
        listed = {row["test"] for row in self.result["subsumed"]} | {r["test"] for r in self.result["kill_nothing"]}
        still_killed = {
            m["id"] for m in MUTANTS
            if m["status"] == "Killed" and any(TESTS[t] not in listed for t in m["killedBy"])
        }
        self.assertEqual({"1", "2", "3", "4"}, still_killed)


    def test_zero_kills_makes_proof_unusable(self):
        result = stryker.analyse(report([mutant("1", "Survived", ["a"], [])], TESTS), by_method=False)
        self.assertFalse(result["proof_usable"])
        self.assertEqual([], result["kill_nothing"])
        self.assertEqual([], result["subsumed"])
        self.assertIsNone(result["greedy_keep_set"])

    def test_bail_suspicion_blocks_prune_candidates(self):
        bailed = [mutant(str(i), "Killed", ["a", "b"], ["a"]) for i in range(20)]
        result = stryker.analyse(report(bailed, TESTS), by_method=False)
        self.assertTrue(result["bail_suspected"])
        self.assertFalse(result["proof_usable"])
        self.assertEqual([], result["subsumed"])
        self.assertEqual([], result["kill_nothing"])

    def test_killed_mutant_without_killer_metadata_blocks_proof(self):
        result = stryker.analyse(report([mutant("1", "Killed", ["a", "b"], [])], TESTS), by_method=False)
        self.assertEqual(["src/Pricing.cs#1"], result["incomplete_kills"])
        self.assertFalse(result["proof_usable"])
        self.assertEqual([], result["kill_nothing"])

    def test_a_static_mutant_covered_by_every_test_keeps_the_proof_usable(self):
        static = dict(mutant("1", "Killed", [], ["a"]), static=True)
        result = stryker.analyse(report([static, mutant("2", "Killed", ["a", "b"], ["a", "b"])], TESTS), by_method=False)
        self.assertTrue(result["proof_usable"], result["warnings"])
        self.assertEqual([], result["incomplete_kills"])

    def test_killer_not_in_coverage_blocks_proof(self):
        result = stryker.analyse(report([mutant("1", "Killed", ["a"], ["b"])], TESTS), by_method=False)
        self.assertFalse(result["proof_usable"])


TRX_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>{rows}</Results>
</TestRun>"""


def trx_file(directory, file_name, rows):
    body = "".join(
        f'<UnitTestResult testName="{name}" outcome="{outcome}" duration="{duration}" />'
        for name, outcome, duration in rows
    )
    path = pathlib.Path(directory) / file_name
    path.write_text(TRX_TEMPLATE.format(rows=body), encoding="utf-8")
    return str(path)


class TrxSummaryTests(unittest.TestCase):
    def test_durations_are_read_in_seconds(self):
        self.assertAlmostEqual(3723.25, trx.duration_seconds("01:02:03.2500000"))

    def test_results_keep_outcome_and_duration_per_test(self):
        with tempfile.TemporaryDirectory() as directory:
            path = trx_file(directory, "run.trx", [("A", "Passed", "00:00:01.5"), ("B", "Failed", "00:00:00.1")])
            results = trx.read_results(path)
        self.assertEqual({"A": {"outcome": "Passed", "seconds": 1.5}, "B": {"outcome": "Failed", "seconds": 0.1}}, results)

    def compare(self, before_rows, after_rows):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            before = trx_file(directory, "before.trx", before_rows)
            after = trx_file(directory, "after.trx", after_rows)
            return trx.print_comparison(before, after)

    def test_compare_fails_when_a_retained_test_stops_passing(self):
        exit_code = self.compare(
            [("A", "Passed", "00:00:00.1"), ("B", "Passed", "00:00:00.1")],
            [("A", "Failed", "00:00:00.1")],
        )
        self.assertEqual(1, exit_code)

    def test_compare_fails_when_a_merged_theory_row_does_not_pass(self):
        exit_code = self.compare(
            [("A", "Passed", "00:00:00.1")],
            [("A", "Passed", "00:00:00.1"), ("T.Rounds(value: 1)", "Failed", "00:00:00.1")],
        )
        self.assertEqual(1, exit_code)

    def test_compare_passes_when_only_deleted_tests_are_gone(self):
        exit_code = self.compare(
            [("A", "Passed", "00:00:00.1"), ("B", "Passed", "00:00:00.1")],
            [("A", "Passed", "00:00:00.1")],
        )
        self.assertEqual(0, exit_code)


    def test_duplicate_display_names_do_not_hide_a_failing_theory_row(self):
        self.assertEqual(1, self.compare(
            [("T.Same", "Passed", "00:00:00.1"), ("T.Same", "Passed", "00:00:00.1")],
            [("T.Same", "Passed", "00:00:00.1"), ("T.Same", "Failed", "00:00:00.1")],
        ))

    def test_non_passing_baseline_blocks_pruning(self):
        self.assertEqual(1, self.compare(
            [("A", "NotExecuted", "00:00:00.0")],
            [("A", "Passed", "00:00:00.1")],
        ))

    def test_empty_trx_is_not_treated_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = trx_file(directory, "empty.trx", [])
            with self.assertRaisesRegex(ValueError, "no test results"):
                trx.read_results(path)

PRICING_FILE = """public class PricingTests
{
    [Fact]
    public void Keeps() => Assert.Equal(1, Pricing.Id(1));

    /// <summary>Same as Keeps.</summary>
    [Fact]
    [Trait("Category", "Unit")]
    public void Duplicate()
    {
        Assert.Equal("}", Pricing.Brace());
    }

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void Rounds(int value) => Assert.Equal(value, Pricing.Id(value));

    [Fact]
    public void Last() => Assert.True(Pricing.Ready);
}
"""

DUPLICATE_METHOD = """    /// <summary>Same as Keeps.</summary>
    [Fact]
    [Trait("Category", "Unit")]
    public void Duplicate()
    {
        Assert.Equal("}", Pricing.Brace());
    }

"""


class RemoveCsTestsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.directory.name) / "PricingTests.cs"

    def tearDown(self):
        self.directory.cleanup()

    def write(self, text, newline="\n", bom=False):
        data = text.replace("\n", newline).encode("utf-8")
        self.path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
        return remover.sha256_of(self.path)

    def remove(self, sha256, *targets, dry_run=False):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            remover.remove(self.path, sha256, list(targets), dry_run)
        return output.getvalue()

    def test_a_method_goes_with_its_attributes_and_doc_comment(self):
        sha256 = self.write(PRICING_FILE)
        self.remove(sha256, "Duplicate")
        self.assertEqual(PRICING_FILE.replace(DUPLICATE_METHOD, ""), self.path.read_text(encoding="utf-8"))

    def test_line_endings_and_the_byte_order_mark_are_kept(self):
        sha256 = self.write(PRICING_FILE, newline="\r\n", bom=True)
        self.remove(sha256, "Last")
        data = self.path.read_bytes()
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"Last", data)
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))
        self.assertTrue(data.endswith(b"value));\r\n}\r\n"))

    def test_a_row_goes_and_the_other_rows_stay(self):
        sha256 = self.write(PRICING_FILE)
        output = self.remove(sha256, "Rounds [row 2]")
        self.assertIn("[InlineData(1)]\n    [InlineData(3)]\n", self.path.read_text(encoding="utf-8"))
        self.assertIn("Rounds [row 2] (line 16): [InlineData(2)]", output)

    def test_neighbouring_methods_go_together_without_a_blank_line_before_the_brace(self):
        sha256 = self.write(PRICING_FILE)
        self.remove(sha256, "Rounds", "Last")
        self.assertTrue(self.path.read_text(encoding="utf-8").endswith("Pricing.Brace());\n    }\n}\n"))

    def test_the_last_test_gone_says_to_delete_the_file(self):
        sha256 = self.write(PRICING_FILE)
        output = self.remove(sha256, "Keeps", "Duplicate", "Rounds", "Last")
        self.assertIn("0 test methods are left", output)
        self.assertIn("delete the file", output)
        self.assertEqual("public class PricingTests\n{\n}\n", self.path.read_text(encoding="utf-8"))

    def test_a_dry_run_changes_nothing(self):
        sha256 = self.write(PRICING_FILE)
        output = self.remove(sha256, "Duplicate", dry_run=True)
        self.assertIn("would remove Duplicate", output)
        self.assertEqual(PRICING_FILE, self.path.read_text(encoding="utf-8"))

    def assertRefused(self, message, sha256, *targets):
        before = self.path.read_bytes()
        with self.assertRaisesRegex(remover.Refusal, message):
            self.remove(sha256, *targets)
        self.assertEqual(before, self.path.read_bytes())

    def test_a_file_changed_since_the_approval_is_refused(self):
        self.write(PRICING_FILE)
        self.assertRefused("changed since the approval", "0" * 64, "Duplicate")

    def test_removing_every_row_is_refused(self):
        sha256 = self.write(PRICING_FILE)
        self.assertRefused("delete the method instead", sha256, "Rounds [row 1]", "Rounds [row 2]", "Rounds [row 3]")

    def test_a_method_given_whole_and_by_row_is_refused(self):
        sha256 = self.write(PRICING_FILE)
        self.assertRefused("whole and by row", sha256, "Rounds", "Rounds [row 1]")

    def test_an_unknown_or_overloaded_name_is_refused(self):
        sha256 = self.write(PRICING_FILE.replace("public void Last()", "public void Keeps(int unused)"))
        self.assertRefused("2 test methods are named Keeps", sha256, "Keeps")
        self.assertRefused("no test method named Missing", sha256, "Missing")

    def test_rows_from_member_data_are_refused(self):
        sha256 = self.write(PRICING_FILE.replace("[InlineData(3)]", "[MemberData(nameof(More))]"))
        self.assertRefused("from a member", sha256, "Rounds [row 1]")

def two_tests(first_test, second_test="    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n"):
    return "public class T\n{\n" + first_test + "\n" + second_test + "}\n"


B_ONLY = "public class T\n{\n    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n}\n"


class RemoveCsTestsEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.directory.name) / "T.cs"

    def tearDown(self):
        self.directory.cleanup()

    def removed(self, text, *targets):
        self.path.write_text(text, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            remover.remove(self.path, remover.sha256_of(self.path), list(targets), False)
        self.output = output.getvalue()
        return self.path.read_text(encoding="utf-8")

    def assertRefused(self, message, text, *targets):
        self.path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(remover.Refusal, message):
            remover.remove(self.path, remover.sha256_of(self.path), list(targets), False)
        self.assertEqual(text, self.path.read_text(encoding="utf-8"))

    def test_a_nested_string_in_an_interpolation_hole_does_not_take_the_next_test(self):
        text = two_tests('    [Fact]\n    public void A() { var s = $"{(open ? "{" : "")}"; Assert.Equal("", s); }\n')
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_closing_brace_in_a_hole_string_does_not_end_the_method(self):
        text = two_tests('    [Fact]\n    public void A()\n    {\n        var s = $"{Wrap("}")}";\n        Assert.Equal("x", s);\n    }\n')
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_an_expression_bodied_test_with_a_block_lambda_goes_whole(self):
        text = two_tests("    [Fact]\n    public void A() => Assert.Throws<ArgumentException>(() => { var x = new Foo(null); x.Run(); });\n")
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_an_attribute_after_the_previous_brace_leaves_that_brace(self):
        text = "public class T\n{\n    [Fact]\n    public void A()\n    {\n    } [Fact]\n    public void B()\n    {\n    }\n}\n"
        self.assertEqual("public class T\n{\n    [Fact]\n    public void A()\n    {\n    }\n}\n", self.removed(text, "B"))

    def test_a_region_line_ending_in_a_bracket_stays(self):
        for region in ("    #region Odd ]\n", "    #region Slow tests [integration]\n"):
            text = two_tests("    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n",
                             region + "    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n    #endregion\n")
            expected = "public class T\n{\n    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n\n" + region + "    #endregion\n}\n"
            self.assertEqual(expected, self.removed(text, "B"))

    def test_a_quote_in_a_region_line_does_not_hide_the_test(self):
        text = two_tests('    #region 12" screen\n    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n    #endregion\n')
        self.assertNotIn("public void A", self.removed(text, "A"))

    def test_rows_are_counted_in_source_order_across_an_if_block(self):
        text = two_tests("    [InlineData(1)]\n#if NET8_0_OR_GREATER\n    [InlineData(2)]\n#endif\n    [Theory]\n"
                         "    [InlineData(3)]\n    [InlineData(4)]\n    public void A(int x) => Assert.True(x > 0);\n")
        after = self.removed(text, "A [row 1]")
        self.assertNotIn("[InlineData(1)]", after)
        self.assertIn("[InlineData(3)]", after)

    def test_a_directive_pair_split_by_the_span_is_refused(self):
        pragma = two_tests('    #pragma warning disable xUnit1004\n    [Fact(Skip = "flaky")]\n    #pragma warning restore xUnit1004\n'
                           "    public void A() { Assert.True(Cart.Open); }\n")
        self.assertRefused("preprocessor", pragma, "A")

    def test_the_doc_comment_goes_when_the_method_ends_in_a_comment(self):
        for ending in ("    public void A()\n    {\n    } // end A\n", "    public void A() => Assert.True(Cart.Open); // quick\n"):
            text = two_tests("    /// <summary>Old.</summary>\n    [Fact]\n" + ending)
            self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_doc_comment_separated_by_a_blank_line_goes_too(self):
        text = two_tests("    /// <summary>Old.</summary>\n\n    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n")
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_four_slash_comment_stays(self):
        text = two_tests("    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n",
                         "    //// Disabled: [Fact] public void Old() { }\n    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n")
        self.assertIn("    //// Disabled:", self.removed(text, "A"))

    def test_the_last_row_on_a_shared_line_leaves_no_trailing_space(self):
        text = two_tests("    [Theory]\n    [InlineData(1)] [InlineData(2)]\n    public void A(int x) => Assert.True(x > 0);\n")
        self.assertIn("    [InlineData(1)]\n    public void A", self.removed(text, "A [row 2]"))

    def test_a_huge_row_number_is_refused(self):
        self.assertRefused("not a test name", B_ONLY, "B [row " + "1" * 5000 + "]")

    def test_a_block_comment_that_runs_past_the_line_is_never_cut(self):
        after_brace = two_tests("    [Fact]\n    public void A() { } /* see\n       issue 12 */\n")
        self.assertRefused("comment or a string", after_brace, "A")
        before_attributes = "public class T\n{\n    /* disabled for now\n    */ [Fact]\n    public void A() { }\n}\n"
        self.assertRefused("comment or a string", before_attributes, "A")

    def test_a_commented_out_test_and_its_doc_above_the_target_stay(self):
        kept = "    /// <summary>Old behaviour.</summary>\n    // [Fact]\n    // public void Old() { }\n\n"
        text = two_tests(kept + "    /// <summary>A</summary>\n    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n")
        self.assertEqual("public class T\n{\n" + kept + "    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n}\n",
                         self.removed(text, "A"))

    def test_doc_like_lines_inside_a_comment_or_a_string_stay(self):
        for kept in ("    /*\n    /// x\n    // y */\n", '    const string H = @"\n    /// gen\n    //";\n'):
            text = two_tests(kept + "    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n")
            self.assertEqual("public class T\n{\n" + kept + "\n    [Fact]\n    public void B() { Assert.True(Cart.Ready); }\n}\n",
                             self.removed(text, "A"))

    def test_a_symlinked_file_is_updated_through_the_link(self):
        real = pathlib.Path(self.directory.name) / "real"
        real.mkdir()
        target = real / "T.cs"
        target.write_text(two_tests("    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n"), encoding="utf-8")
        self.path.symlink_to(target)
        with contextlib.redirect_stdout(io.StringIO()):
            remover.remove(self.path, remover.sha256_of(self.path), ["A"], False)
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(B_ONLY, target.read_text(encoding="utf-8"))

    def test_balanced_directives_inside_the_removed_test_are_accepted(self):
        pragma = ("    [Fact]\n    public void A()\n    {\n#pragma warning disable CS0618\n        Legacy.Run();\n"
                  "#pragma warning restore CS0618\n    }\n")
        self.assertEqual(B_ONLY, self.removed(two_tests(pragma), "A"))
        guarded = ("    [Theory]\n    [InlineData(1)]\n#if NET8_0_OR_GREATER\n    [InlineData(2)]\n#else\n    [InlineData(3)]\n#endif\n"
                   "    public void A(int x) => Assert.True(x > 0);\n")
        self.assertEqual(B_ONLY, self.removed(two_tests(guarded), "A"))

    def test_a_directive_that_changes_the_rest_of_the_file_is_refused(self):
        self.assertRefused("preprocessor", two_tests("    [Fact]\n    public void A()\n    {\n#nullable enable\n        Run();\n    }\n"), "A")

    def test_a_comment_line_that_starts_with_a_hash_is_not_a_directive(self):
        text = two_tests("    [Fact]\n    public void A()\n    {\n        /*\n        #1 regression\n        */\n        Run();\n    }\n")
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_test_attribute_in_a_list_or_with_its_full_name_is_found(self):
        for attribute in ('[Trait("Category", "Unit"), Fact]', "[Xunit.Fact]", "[FactAttribute]", "[SkippableFact]"):
            text = two_tests(f"    {attribute}\n    public void A() {{ Assert.True(Cart.Open); }}\n")
            self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_region_on_the_first_line_after_a_byte_order_mark_is_a_directive(self):
        text = '﻿#region Tests "big\n' + two_tests("    [Fact]\n    public void A() { Assert.True(Cart.Open); }\n") + "#endregion\n"
        self.assertNotIn("public void A", self.removed(text, "A"))

    def test_a_comment_inside_an_interpolation_hole_is_skipped(self):
        text = two_tests('    [Fact]\n    public void A() { var s = $"{x /* { */}"; Assert.Equal("", s); }\n')
        self.assertEqual(B_ONLY, self.removed(text, "A"))

    def test_a_collection_expression_is_not_a_test_attribute(self):
        text = two_tests("    [Fact]\n    public void A()\n    {\n        Run(filters: [new ReportDraftFact(\"Status\", \"Booked\")]);\n    }\n")
        names = [name for _, _, name, _, _ in scanner.test_methods(scanner.code_mask(text))]
        self.assertEqual(["A", "B"], names)

    def run_script(self, *arguments):
        script = SCRIPTS / "remove_cs_tests.py"
        return subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True)

    def test_a_folder_or_an_unwritable_file_is_refused_without_a_traceback(self):
        self.path.write_text(B_ONLY, encoding="utf-8")
        sha256 = remover.sha256_of(self.path)
        self.path.chmod(0o444)
        try:
            for arguments in (("hash", self.directory.name), ("remove", str(self.path), "--sha256", sha256, "B")):
                run = self.run_script(*arguments)
                self.assertEqual(1, run.returncode)
                self.assertIn("Refused:", run.stderr)
                self.assertNotIn("Traceback", run.stderr)
                self.assertNotIn("removed", run.stdout)
        finally:
            self.path.chmod(0o644)
        self.assertEqual(B_ONLY, self.path.read_text(encoding="utf-8"))

HELPER_FILE = """public class T
{
    private static readonly int[] Known = [2];

    [Fact]
    public void A() => Assert.Equal(4, Twice(2) + Catalogue.Keys.Length + (Known.Contains(2) ? 0 : 1));

    [Fact]
    public void B() => Assert.True(Catalogue.All.Length > Known.Length);

    private static int Twice(int x) => x * 2;
}
"""


class OrphanReportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        self.path = self.root / "T.cs"

    def tearDown(self):
        self.directory.cleanup()

    def remove(self, *targets):
        self.path.write_text(HELPER_FILE, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            remover.remove(self.path, remover.sha256_of(self.path), list(targets), False)
        return output.getvalue()

    def test_a_private_helper_only_the_removed_test_called_is_reported(self):
        output = self.remove("A")
        self.assertIn("Left without a reader in this file", output)
        self.assertIn("- Twice (line 8)", output)

    def test_a_helper_a_kept_test_still_calls_is_not_reported(self):
        output = self.remove("B")
        self.assertNotIn("Twice", output)
        self.assertNotIn("Left without a reader", output)

    def test_a_production_member_only_the_removed_test_named_is_reported(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "Catalogue.cs").write_text(
            "public static class Catalogue\n{\n    public static int[] Keys => [];\n    public static int[] All => [1];\n}\n",
            encoding="utf-8")
        (self.root / "Report.cs").write_text("public static class Report { public static int Count => Catalogue.All.Length; }\n",
                                              encoding="utf-8")
        output = self.remove("A")
        self.assertIn("Production members only the removed tests named", output)
        self.assertIn("- Catalogue.Keys", output)
        self.assertNotIn("Catalogue.All", output)
        self.assertNotIn("Known.Contains", output)


if __name__ == "__main__":
    unittest.main()
