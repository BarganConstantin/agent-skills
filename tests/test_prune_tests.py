#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import pathlib
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

    def test_greedy_keep_set_is_the_smallest_set_that_kills_everything(self):
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


if __name__ == "__main__":
    unittest.main()
