"""Validate the public beta intake form without inventing tester outcomes."""
from pathlib import Path
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "first-run-feedback.yml"
README = ROOT / "README.md"
GUIDE = ROOT / "docs" / "first-five-testers.md"


class FirstRunIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.form = yaml.safe_load(FORM.read_text(encoding="utf-8"))

    def test_form_has_valid_metadata_and_real_input_controls(self):
        self.assertIsInstance(self.form, dict)
        for key in ("name", "description", "title", "body"):
            self.assertTrue(self.form.get(key), key)
        body = self.form["body"]
        self.assertIsInstance(body, list)
        ids = [item.get("id") for item in body if item.get("id")]
        self.assertEqual(len(ids), len(set(ids)), "issue form IDs must be unique")
        self.assertTrue({"agent", "outcome", "project", "what-worked", "evidence", "privacy"}.issubset(ids))

    def test_form_captures_preflight_failures_not_only_successes(self):
        fields = {item.get("id"): item for item in self.form["body"]}
        values = fields["outcome"]["attributes"]["options"]
        self.assertTrue(any("Could not install" in x for x in values))
        self.assertTrue(any("browser MCP was unavailable" in x for x in values))
        self.assertTrue(any("Stopped safely" in x for x in values))
        self.assertTrue(fields["outcome"]["validations"]["required"])

    def test_private_data_warning_is_mandatory(self):
        fields = {item.get("id"): item for item in self.form["body"]}
        privacy = fields["privacy"]
        self.assertEqual(privacy["type"], "checkboxes")
        self.assertTrue(privacy["attributes"]["options"][0]["required"])
        intro = " ".join(str(x) for x in self.form["body"])
        self.assertIn("credentials", intro.lower())
        self.assertIn("private", intro.lower())

    def test_practice_lab_is_discoverable_and_safe(self):
        readme = README.read_text(encoding="utf-8")
        practice = (ROOT / "docs" / "practice-lab.md").read_text(encoding="utf-8")
        self.assertIn("docs/practice-lab.md", readme)
        self.assertIn("evals/fixtures/activation_lab.py --variant seeded", practice)
        self.assertIn("http://127.0.0.1:8765", practice)
        self.assertIn("QUICK CHECK", practice)
        self.assertIn("NOT RUN", practice)
        self.assertIn("unblinded", practice.lower())
        self.assertTrue((ROOT / "evals" / "fixtures" / "activation_lab.py").is_file())

    def test_first_run_guide_has_copyable_fenced_commands(self):
        """The published guide must render real GitHub Markdown code blocks.

        A prior version escaped every backtick, turning copy/paste instructions
        into literal punctuation instead of fenced code snippets.
        """
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertNotIn(chr(92) + chr(96), guide, "Backticks must not be escaped in guide")
        fences = [line for line in guide.splitlines() if line.startswith("```")]
        self.assertEqual(len(fences), 10, "Five complete fenced snippets expected")
        self.assertEqual(sum(line == "```" for line in fences), 5)
        self.assertEqual(sum(line == "```bash" for line in fences), 4)
        self.assertEqual(sum(line == "```text" for line in fences), 1)

        import re
        blocks = re.findall(r"(?ms)^```(?:bash|text)\n(.*?)^```$", guide)
        self.assertEqual(len(blocks), 5, "All five snippets must be rendered")
        self.assertIn(
            "npx skills add BarganConstantin/agent-skills --skill first-user-audit",
            blocks[0],
        )
        self.assertIn("claude mcp add playwright", blocks[1])
        self.assertIn("codex mcp add playwright", blocks[2])
        self.assertIn("Use first-user-audit in QUICK CHECK mode", blocks[3])
        self.assertIn("summarize.py --root qa/first-users --baseline-only", blocks[4])
        self.assertIn("Do not test production", guide)
        self.assertIn("redact", guide.lower())

    def test_readme_reaches_guide_and_feedback(self):
        readme = README.read_text(encoding="utf-8")
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("docs/first-five-testers.md", readme)
        self.assertIn("template=first-run-feedback.yml", readme)
        self.assertIn("npx skills add BarganConstantin/agent-skills", guide)
        self.assertIn("QUICK CHECK", guide)
        self.assertIn("Codex", guide)
        self.assertIn("Claude Code", guide)


if __name__ == "__main__":
    unittest.main()
