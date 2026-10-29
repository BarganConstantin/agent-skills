"""Guard the public install workflow against synthetic telemetry and wrong sources."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT / "scripts" / "verify_public_install.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "public-install.yml"
SKILL_NAMES = ("first-user-audit", "handoff-with-receipts", "api-contract-drift", "reference-library", "prune-tests")


class PublicInstallTests(unittest.TestCase):
    def test_ci_installs_from_only_the_intended_repo(self):
        script = REMOTE.read_text(encoding="utf-8")
        self.assertIn('REPOSITORY="BarganConstantin/agent-skills"', script)
        self.assertIn('npx --yes skills@latest add "$REPOSITORY"', script)
        self.assertIn("--agent claude-code --agent codex --copy --yes", script)
        self.assertIn('cmp -s "$file" "$dst/$rel"', script)
        for name in SKILL_NAMES:
            self.assertIn(name, script)
            self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file())

    def test_no_telemetry_or_incorrect_adoption_count(self):
        script = REMOTE.read_text(encoding="utf-8")
        self.assertIn("export DISABLE_TELEMETRY=1", script)
        self.assertIn("export CI=true", script)
        self.assertIn("mktemp -d", script)
        self.assertIn("trap 'rm -rf", script)
        self.assertNotIn("gh repo star", script)

    def test_workflow_does_not_install_a_pr_version_as_published(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("github.repository == 'BarganConstantin/agent-skills'", workflow)

    def test_research_and_docs_link_current_activation_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        study = (ROOT / "docs" / "growth-research.md").read_text(encoding="utf-8")
        self.assertIn("docs/growth-research.md", readme)
        self.assertIn("public-install.yml", readme)
        for name in SKILL_NAMES:
            self.assertIn("--skill " + name, readme)
        self.assertIn("one change at a time", study.lower())
        self.assertIn("375 skills", study)
        self.assertIn("independent", study.lower())


if __name__ == "__main__":
    unittest.main()
