"""Behavioral tests for non-destructive, path-redacted Git snapshot."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = (Path(__file__).resolve().parents[1] / "skills"
          / "handoff-with-receipts" / "scripts" / "git_snapshot.py")
spec = importlib.util.spec_from_file_location("git_snapshot", SCRIPT)
snap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snap)


def run_git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


class GitSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        run_git(self.root, "init", "-q", "-b", "main")
        run_git(self.root, "config", "user.email", "test@example.invalid")
        run_git(self.root, "config", "user.name", "Example Test")
        (self.root / "file.txt").write_text("first\n", encoding="utf-8")
        run_git(self.root, "add", "file.txt")
        run_git(self.root, "commit", "-qm", "first safe commit")

    def test_clean_worktree_has_verified_head_and_zero_counts(self):
        data = snap.snapshot(self.root)
        self.assertEqual(data["kind"], "local_git_snapshot_not_test_evidence")
        self.assertEqual(data["branch"], "main")
        self.assertEqual(data["head_sha"], run_git(self.root, "rev-parse", "HEAD"))
        self.assertEqual(data["working_tree"]["changed_entries"], 0)
        self.assertTrue(data["working_tree"]["clean"])

    def test_dirty_worktree_reports_counts_without_leaking_paths_or_contents(self):
        (self.root / "file.txt").write_text("sensitive-looking-token-12345\n", encoding="utf-8")
        (self.root / "client-secrets-file.txt").write_text("actual-demo-secret\n", encoding="utf-8")
        d = snap.snapshot(self.root)
        self.assertEqual(d["working_tree"]["changed_entries"], 2)
        self.assertEqual(d["working_tree"]["unstaged_entries"], 1)
        self.assertEqual(d["working_tree"]["untracked_entries"], 1)
        text = json.dumps(d)
        for secret in ("client-secrets-file", "sensitive-looking-token", "actual-demo-secret",
                       self.tmp.name, "test@example.invalid"):
            self.assertNotIn(secret, text)

    def test_staged_and_unstaged_changes_are_counted(self):
        (self.root / "file.txt").write_text("second\n", encoding="utf-8")
        run_git(self.root, "add", "file.txt")
        (self.root / "file.txt").write_text("third\n", encoding="utf-8")
        d = snap.snapshot(self.root)
        self.assertEqual(d["working_tree"]["changed_entries"], 1)
        self.assertEqual(d["working_tree"]["staged_entries"], 1)
        self.assertEqual(d["working_tree"]["unstaged_entries"], 1)

    def test_detached_head_is_disclosed(self):
        run_git(self.root, "checkout", "--detach", "-q", "HEAD")
        data = snap.snapshot(self.root)
        self.assertEqual(data["branch"], "(detached)")
        self.assertIsNotNone(data["head_sha"])

    def test_empty_unborn_repository_is_supported(self):
        folder = self.root / "empty"
        folder.mkdir()
        run_git(folder, "init", "-q", "-b", "main")
        data = snap.snapshot(folder)
        self.assertIsNone(data["head_sha"])
        self.assertEqual(data["branch"], "main")

    def test_refuses_non_git_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(snap.SnapshotError):
                snap.snapshot(Path(tmp))

    def test_new_file_writes_json_but_never_overwrites(self):
        output = self.root / "evidence.json"
        self.assertEqual(snap.main(["--root", str(self.root), "--output", str(output)]), 0)
        saved = output.read_text(encoding="utf-8")
        self.assertEqual(json.loads(saved)["schema_version"], 1)
        self.assertEqual(snap.main(["--root", str(self.root), "--output", str(output)]), 2)
        self.assertEqual(output.read_text(encoding="utf-8"), saved)

    def test_paths_with_line_breaks_not_printed(self):
        # Core.quotePath encodes line breaks in porcelain v1 output.
        name = "private\nnewline.txt"
        (self.root / name).write_text("example\n", encoding="utf-8")
        d = snap.snapshot(self.root)
        self.assertEqual(d["working_tree"]["changed_entries"], 1)
        self.assertNotIn("private", json.dumps(d))


if __name__ == "__main__":
    unittest.main()
