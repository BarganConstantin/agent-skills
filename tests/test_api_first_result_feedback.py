"""Prevent the first-value demo from losing its safe, actionable feedback path."""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "api-contract-drift-feedback.yml"
RESEARCH = ROOT / "docs" / "growth-research.md"


class ApiFirstResultFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.form = yaml.safe_load(FORM.read_text(encoding="utf-8"))
        cls.fields = {item.get("id"): item for item in cls.form["body"] if item.get("id")}

    def test_form_has_unique_fields_and_required_outcome(self):
        self.assertTrue(all(self.form.get(key) for key in ("name", "description", "title", "body")))
        ids = [item.get("id") for item in self.form["body"] if item.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"outcome", "steps", "improvement", "privacy"}.issubset(ids))
        self.assertEqual(self.fields["outcome"]["type"], "dropdown")
        self.assertTrue(self.fields["outcome"]["validations"]["required"])
        self.assertTrue(self.fields["steps"]["validations"]["required"])

    def test_first_run_failures_are_welcome_without_claiming_proof(self):
        options = " ".join(self.fields["outcome"]["attributes"]["options"])
        self.assertIn("three potential client breaks", options)
        self.assertIn("Could not run", options)
        self.assertIn("output differed", options)
        self.assertIn("Not run", options)
        text = str(self.form["body"]).lower()
        self.assertIn("does not", text)
        self.assertIn("real api", text)
        self.assertIn("no ai agent", text)

    def test_public_form_requires_explicit_redaction_acknowledgment(self):
        privacy = self.fields["privacy"]
        self.assertEqual(privacy["type"], "checkboxes")
        self.assertTrue(privacy["attributes"]["options"][0]["required"])
        text = str(self.form["body"]).lower()
        for phrase in ("credentials", "private endpoints", "customer data",
                       "confidential schemas", "personal information"):
            self.assertIn(phrase, text)
        self.assertNotIn("paste your full", text)

    def test_demo_links_directly_to_existing_form(self):
        readme = README.read_text(encoding="utf-8")
        self.assertLess(len(readme), 6200)
        self.assertIn(
            "https://github.com/BarganConstantin/agent-skills/issues/new"
            "?template=api-contract-drift-feedback.yml",
            readme)
        demo_start = readme.index("## See a result in 30 seconds")
        demo_end = readme.index("## Choose your workflow")
        demo = readme[demo_start:demo_end]
        self.assertIn("compare_openapi.py", demo)
        self.assertIn("Report your first result or blocker", demo)
        self.assertIn("not a real-API benchmark", demo)

    def test_research_records_one_bounded_hypothesis_not_adoption_claims(self):
        study = RESEARCH.read_text(encoding="utf-8")
        checkpoint = study.split("## First-result evidence checkpoint — 2026-10-28", 1)[1]
        self.assertEqual(checkpoint.count("**Hypothesis H1"), 1)
        self.assertIn("27 November 2026", checkpoint)
        self.assertIn("Stop condition", checkpoint)
        self.assertIn("DISABLE_TELEMETRY=1", checkpoint)
        self.assertIn("4 stars, 0 forks", checkpoint)
        self.assertIn("4 Agent Skills", study)
        self.assertIn("not", checkpoint.lower())


if __name__ == "__main__":
    unittest.main()
