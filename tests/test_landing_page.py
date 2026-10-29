"""Landing-page contract: first value is easy to see; detailed docs stay navigable."""
import re
from pathlib import Path
from urllib.parse import unquote
import unittest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DETAIL = ROOT / "docs" / "first-user-audit.md"
SKILLS = ("first-user-audit", "reference-library", "prune-tests")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")


class LandingPageTests(unittest.TestCase):
    def test_readme_is_short(self):
        content = README.read_text(encoding="utf-8")
        self.assertLess(len(content), 3000)

    def test_each_skill_has_separate_install_command(self):
        text = README.read_text(encoding="utf-8")
        for name in SKILLS:
            self.assertIn("skills/" + name + "/SKILL.md", text)
            self.assertIn("npx skills add BarganConstantin/agent-skills --skill " + name, text)

    def test_original_browser_audit_details_are_preserved(self):
        text = DETAIL.read_text(encoding="utf-8")
        self.assertIn("375 CSS", text)
        self.assertIn("four", text.lower())
        self.assertIn("0/4", text)
        self.assertIn("4/4", text)
        self.assertIn("isolated", text.lower())

    def test_no_broken_relative_markdown_links_in_landing_or_detail(self):
        for filename in (README, DETAIL):
            text = filename.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative = unquote(target.split("#", 1)[0])
                with self.subTest(file=filename.name, target=target):
                    self.assertTrue((filename.parent / relative).exists(), target)

    def test_original_details_not_falsely_claimed_as_agent_efficacy(self):
        landing = README.read_text(encoding="utf-8")
        detail = DETAIL.read_text(encoding="utf-8")
        self.assertIn("not", detail.lower())
        self.assertIn("not a product screenshot", detail)
        self.assertNotIn("benchmark", landing.lower())


if __name__ == "__main__":
    unittest.main()
