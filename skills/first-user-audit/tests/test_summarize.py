"""Deterministic synthetic fixtures; these are not actual browser audit results."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize.py"
spec = importlib.util.spec_from_file_location("first_user_summarize", SCRIPT)
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def synthetic_report(phase, persona, reached=False, issues=None):
    return {
        "phase": phase, "persona": persona,
        "environment": "http://localhost:3000", "app_revision": "synthetic-fixture",
        "first_success": {"name": "example only", "reached": reached,
                          "evidence": "fixture-proof" if reached else None},
        "clicks_to_success": 3 if reached else None,
        "would_return": "uncertain", "would_return_reason": "synthetic test",
        "capabilities": {}, "issues": issues or [], "limitations": []
    }


def synthetic_issue(iid="FUA-001", severity="major"):
    return {"id": iid, "stage": "signup", "location": "/signup#submit",
            "summary": "synthetic only", "category": "technical", "severity": severity,
            "reproduction": "fixture", "expected": "fixture", "actual": "fixture", "evidence": []}


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "qa" / "first-users"

    def tearDown(self):
        self.temp.cleanup()

    def put(self, phase, persona, reached=False, issues=None):
        target = self.root / phase / f"{persona}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(synthetic_report(phase, persona, reached, issues)), encoding="utf8")

    def test_baseline_only_ignores_invalid_after_report(self):
        self.put("baseline", "impatient")
        path = self.root / "after" / "impatient.json"
        path.parent.mkdir()
        path.write_text("not JSON")
        self.assertEqual(summary.main(["--root", str(self.root), "--baseline-only"]), 0)
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--strict"])
        self.assertEqual(ctx.exception.code, 2)

    def test_malformed_enum_types_raise_report_error(self):
        for field in ("category", "severity"):
            report = synthetic_report("baseline", "impatient", issues=[synthetic_issue()])
            report["issues"][0][field] = []
            with self.subTest(field=field), self.assertRaises(summary.ReportError):
                summary._valid_record(report, "baseline", "impatient", Path("fixture.json"))
        report = synthetic_report("baseline", "impatient")
        report["would_return"] = []
        with self.assertRaises(summary.ReportError):
            summary._valid_record(report, "baseline", "impatient", Path("fixture.json"))

    def test_cannot_summarize_no_reports(self):
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--baseline-only"])
        self.assertEqual(ctx.exception.code, 2)

    def test_refuses_incomplete_when_strict(self):
        self.put("baseline", "impatient")
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--strict"])
        self.assertEqual(ctx.exception.code, 2)

    def test_ranked_unique_personas_and_after(self):
        for phase in summary.PHASES:
            for persona in summary.PERSONAS:
                issues = [synthetic_issue()] if phase == "baseline" and persona in {"impatient", "breaker"} else []
                if phase == "baseline" and persona == "skeptic":
                    issues = [synthetic_issue("FUA-002", "blocker")]
                self.put(phase, persona, reached=(phase == "after"), issues=issues)
        self.assertEqual(summary.main(["--root", str(self.root), "--strict"]), 0)
        output = (self.root / "summary.md").read_text()
        self.assertIn("4/4 simulated personas reached first success", output)
        self.assertIn("FUA-001 | 2/4", output)
        self.assertLess(output.index("FUA-001 | 2/4"), output.index("FUA-002 | 1/4"))
        self.assertIn("FUA-001 | 2/4 | 0/4 | -2", output)

    def test_strict_rejects_mismatched_success_criterion(self):
        for phase in summary.PHASES:
            for persona in summary.PERSONAS:
                self.put(phase, persona)
        path = self.root / "after" / "mobile.json"
        record = json.loads(path.read_text())
        record["first_success"]["name"] = "a different predicate"
        path.write_text(json.dumps(record))
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--strict"])
        self.assertEqual(ctx.exception.code, 2)

    def test_rejects_same_phase_multiple_revisions(self):
        for phase in summary.PHASES:
            for persona in summary.PERSONAS:
                self.put(phase, persona)
        path = self.root / "baseline" / "mobile.json"
        record = json.loads(path.read_text())
        record["app_revision"] = "a-different-fixture-revision"
        path.write_text(json.dumps(record))
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--strict"])
        self.assertEqual(ctx.exception.code, 2)

    def test_success_requires_click_count_and_proof(self):
        report = synthetic_report("baseline", "impatient", reached=True)
        report["clicks_to_success"] = None
        with self.assertRaises(summary.ReportError):
            summary._valid_record(report, "baseline", "impatient", Path("fixture.json"))

    def test_issue_id_conflict_is_visible(self):
        a = synthetic_report("baseline", "impatient", issues=[synthetic_issue()])
        other = synthetic_issue()
        other["location"] = "/different"
        b = synthetic_report("baseline", "breaker", issues=[other])
        rows, warnings = summary.aggregate({"impatient": a, "breaker": b})
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]["personas"]), 2)
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
