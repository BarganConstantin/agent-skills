"""Deterministic HTML rendering checks. Synthetic data is not browser evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "html_report.py"
PERSONAS = ("impatient", "skeptic", "mobile", "breaker")


def record(phase, persona, reached=False, issues=None):
    return {
        "phase": phase, "persona": persona,
        "environment": "http://localhost:3000", "app_revision": "synthetic-revision",
        "first_success": {"name": "Create a test workspace", "reached": reached,
                          "evidence": "sample proof only" if reached else None},
        "clicks_to_success": 3 if reached else None,
        "would_return": "uncertain", "would_return_reason": "simulated only",
        "capabilities": {"browser_mcp": "unverified"},
        "limitations": ["No actual browser used"],
        "issues": issues or []
    }


def issue(summary):
    return {
        "id": "FUA-001", "stage": "signup", "location": "/signup#submit",
        "summary": summary, "category": "technical", "severity": "major",
        "reproduction": "Click <save> & retry", "expected": "Safe & valid",
        "actual": "<script>evil()</script>", "evidence": []
    }


class HtmlReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "qa" / "first-users"

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, phase, persona, *, reached=False, issues=None):
        path = self.root / phase / (persona + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record(phase, persona, reached, issues)), encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            capture_output=True, text=True, check=False
        )

    def test_baseline_only_outputs_offline_html_with_missing_personas(self):
        self.put("baseline", "impatient", issues=[issue("<script>alert(1)</script>")])
        response = self.run_cli("--baseline-only")
        self.assertEqual(response.returncode, 0, response.stderr)
        html = (self.root / "summary.html").read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", html)
        self.assertIn("Content-Security-Policy", html)
        self.assertIn("default-src 'none'", html)
        self.assertIn("1/4", html)
        self.assertIn("Missing personas", html)
        self.assertIn("Simulated QA, not real-user research", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;save&gt; &amp; retry", html)
        self.assertNotIn("<script>evil()", html)
        self.assertNotIn("<img", html)

    def test_rejects_missing_reports_in_strict_mode_without_writing(self):
        self.put("baseline", "impatient")
        response = self.run_cli("--strict")
        self.assertEqual(response.returncode, 2)
        self.assertFalse((self.root / "summary.html").exists())

    def test_full_comparable_report_includes_before_after(self):
        for phase in ("baseline", "after"):
            for persona in PERSONAS:
                self.put(phase, persona, reached=phase == "after",
                         issues=[issue("Fixture issue")] if phase == "baseline" else [])
        response = self.run_cli("--strict")
        self.assertEqual(response.returncode, 0, response.stderr)
        html = (self.root / "summary.html").read_text(encoding="utf-8")
        self.assertIn("Before / after", html)
        self.assertIn("4/4", html)
        self.assertIn("FUA-001", html)
        self.assertIn("not statistically significant human conversion", html)

    def test_comparison_unavailable_when_environment_differs(self):
        for phase in ("baseline", "after"):
            for persona in PERSONAS:
                self.put(phase, persona)
        path = self.root / "after" / "mobile.json"
        r = json.loads(path.read_text())
        r["environment"] = "http://localhost:9999"
        path.write_text(json.dumps(r))
        response = self.run_cli()
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertIn("Comparison unavailable", (self.root / "summary.html").read_text())
        response = self.run_cli("--strict")
        self.assertEqual(response.returncode, 2)

    def test_invalid_json_does_not_produce_html(self):
        path = self.root / "baseline" / "impatient.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid", encoding="utf-8")
        response = self.run_cli("--baseline-only")
        self.assertEqual(response.returncode, 2)
        self.assertFalse((self.root / "summary.html").exists())

    def test_custom_output_location(self):
        self.put("baseline", "breaker")
        custom = Path(self.tmp.name) / "custom.html"
        response = self.run_cli("--baseline-only", "--output", str(custom))
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertTrue(custom.is_file())
        self.assertFalse((self.root / "summary.html").exists())

    def test_unsafe_evidence_path_is_rejected_when_verifying(self):
        self.put("baseline", "impatient", issues=[issue("fixture")])
        response = self.run_cli("--baseline-only", "--verify-evidence", "--project-root", str(self.tmp.name))
        self.assertEqual(response.returncode, 2)
        self.assertFalse((self.root / "summary.html").exists())


if __name__ == "__main__":
    unittest.main()
