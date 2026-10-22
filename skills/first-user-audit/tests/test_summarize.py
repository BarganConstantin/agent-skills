"""Deterministic synthetic fixtures; these are not actual browser audit results."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def complete_reports(self):
        for phase in summary.PHASES:
            for persona in summary.PERSONAS:
                self.put(phase, persona, issues=[synthetic_issue()])

    def edit(self, phase, persona, change):
        path = self.root / phase / f"{persona}.json"
        record = json.loads(path.read_text())
        change(record)
        path.write_text(json.dumps(record))

    def test_strict_rejects_identity_conflicts_within_and_across_phases(self):
        for phase in summary.PHASES:
            for field, value in (("category", "privacy"), ("location", "/other"), ("stage", "checkout")):
                with self.subTest(phase=phase, field=field):
                    self.complete_reports()
                    # For after, change every persona: each phase is internally
                    # consistent, so only a cross-phase check can catch this.
                    personas = summary.PERSONAS if phase == "after" else ("mobile",)
                    for persona in personas:
                        self.edit(phase, persona, lambda r: r["issues"][0].update({field: value}))
                    output = self.root / "rejected.md"
                    with self.assertRaises(SystemExit) as ctx:
                        summary.main(["--root", str(self.root), "--strict", "--output", str(output)])
                    self.assertEqual(ctx.exception.code, 2)
                    self.assertFalse(output.exists())
                    summary.main(["--root", str(self.root)])
                    text = (self.root / "summary.md").read_text()
                    self.assertIn("FUA-001: conflicting category/location/stage", text)
                    self.assertIn("Comparison unavailable", text)
                    self.assertNotIn("| FUA-001 | 4/4 | 4/4 |", text)

    def test_severity_changes_and_revision_changes_across_phases_are_allowed(self):
        self.complete_reports()
        for persona in summary.PERSONAS:
            def change(record):
                record["app_revision"] = "fixed-revision"
                record["issues"][0]["severity"] = "minor"
            self.edit("after", persona, change)
        self.assertEqual(summary.main(["--root", str(self.root), "--strict"]), 0)

    def test_cross_phase_environment_mismatch_prevents_comparison(self):
        self.complete_reports()
        for persona in summary.PERSONAS:
            self.edit("after", persona, lambda r: r.update(environment="http://localhost:4000"))
        with self.assertRaises(SystemExit) as ctx:
            summary.main(["--root", str(self.root), "--strict"])
        self.assertEqual(ctx.exception.code, 2)
        summary.main(["--root", str(self.root)])
        text = (self.root / "summary.md").read_text()
        self.assertIn("Comparison unavailable", text)
        self.assertIn("environment URL differs between phases", text)

    def test_complete_reports_disclose_capabilities_and_limitations(self):
        self.complete_reports()
        self.edit("after", "mobile", lambda r: r.update(
            capabilities={"browser_mcp": "unavailable", "network_throttling": "unverified"},
            limitations=["No real browser", "Throttling not exercised"]))
        self.edit("baseline", "skeptic", lambda r: r.update(
            capabilities={"browser_mcp": "verified"}, limitations=["Claim only"]))
        summary.main(["--root", str(self.root), "--strict"])
        text = (self.root / "summary.md").read_text()
        for phrase in ("Completed reports: **4/4**", '"browser_mcp": "unavailable"',
                       '"network_throttling": "unverified"', "No real browser",
                       "Throttling not exercised", '"browser_mcp": "verified"', "Claim only",
                       "not fully capable or successful executions", "do not prove actual use",
                       "Empty capability/limitation declarations"):
            self.assertIn(phrase, text)

    def evidence_project(self):
        project = Path(self.temp.name) / "project"
        evidence = project / "evidence" / "proof.png"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_bytes(b"synthetic evidence, not an authentic screenshot")
        return project

    def test_verify_evidence_cli_with_explicit_root_and_default_cwd(self):
        project = self.evidence_project()
        self.put("baseline", "impatient", reached=True, issues=[synthetic_issue()])
        def change(record):
            record["first_success"]["evidence"] = "evidence/proof.png"
            record["issues"][0]["evidence"] = ["evidence/proof.png"]
        self.edit("baseline", "impatient", change)
        args = ["--root", str(self.root), "--baseline-only", "--verify-evidence"]
        self.assertEqual(summary.main(args + ["--project-root", str(project)]), 0)
        with patch.object(summary.Path, "cwd", return_value=project):
            self.assertEqual(summary.main(args), 0)
        (project / "internal.png").symlink_to(project / "evidence/proof.png")
        self.edit("baseline", "impatient", lambda r: r["first_success"].update(evidence="internal.png"))
        self.assertEqual(summary.main(args + ["--project-root", str(project)]), 0)
        text = (self.root / "summary.md").read_text()
        self.assertIn("Evidence filesystem checks enabled", text)
        self.assertIn("screenshot authenticity are not verified", text)

    def test_default_accepts_textual_success_proof_and_legacy_empty_issue_evidence(self):
        self.put("baseline", "impatient", reached=True, issues=[synthetic_issue()])
        args = ["--root", str(self.root), "--baseline-only"]
        self.assertEqual(summary.main(args), 0)
        self.assertIn("textual success proof is accepted", (self.root / "summary.md").read_text())
        with self.assertRaises(SystemExit) as ctx:
            summary.main(args + ["--verify-evidence", "--project-root", str(self.evidence_project())])
        self.assertEqual(ctx.exception.code, 2)

    def test_verify_evidence_rejects_invalid_paths_for_success_and_issues(self):
        project = self.evidence_project()
        outside = Path(self.temp.name) / "outside.png"
        outside.write_bytes(b"outside")
        (project / "escaped.png").symlink_to(outside)
        (project / "escaped-dir").symlink_to(outside.parent, target_is_directory=True)
        (project / "dangling.png").symlink_to(project / "missing.png")
        values = ["", "   ", None, 42, [], "bad\x00path", "textual proof", "evidence/missing.png",
                  "evidence", str(project / "evidence/proof.png"), "../outside.png",
                  "evidence/../evidence/proof.png", "escaped.png", "escaped-dir/outside.png", "dangling.png"]
        for field in ("success", "issue"):
            for value in values:
                with self.subTest(field=field, value=value):
                    record = synthetic_report("baseline", "impatient", reached=True, issues=[synthetic_issue()])
                    record["first_success"]["evidence"] = value if field == "success" else "evidence/proof.png"
                    record["issues"][0]["evidence"] = [value] if field == "issue" else ["evidence/proof.png"]
                    with self.assertRaises(summary.ReportError):
                        summary._valid_record(record, "baseline", "impatient", Path("fixture.json"),
                                              verify_evidence=True, project_root=project)

    def test_verify_evidence_checks_every_issue_file_and_requires_evidence(self):
        project = self.evidence_project()
        for evidence in ([], ["evidence/proof.png", "missing.png"]):
            with self.subTest(evidence=evidence):
                record = synthetic_report("baseline", "impatient", issues=[synthetic_issue()])
                record["issues"][0]["evidence"] = evidence
                with self.assertRaises(summary.ReportError):
                    summary._valid_record(record, "baseline", "impatient", Path("fixture.json"),
                                          verify_evidence=True, project_root=project)

    def test_verify_evidence_allows_unsuccessful_run_without_success_proof(self):
        record = synthetic_report("baseline", "impatient")
        summary._valid_record(record, "baseline", "impatient", Path("fixture.json"),
                              verify_evidence=True, project_root=self.evidence_project())


if __name__ == "__main__":
    unittest.main()
