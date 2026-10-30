#!/usr/bin/env python3
import importlib.util
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills" / "compass" / "scripts" / "state.py"
spec = importlib.util.spec_from_file_location("compass_state", SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

NO_TOKENS = {"GITLAB_TOKEN": "", "JIRA_BASE": "", "JIRA_TOKEN": "", "JIRA_TOKEN_CMD": "", "JIRA_EMAIL": ""}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class OriginTests(unittest.TestCase):
    def test_reads_host_and_path_from_every_remote_form(self):
        cases = {
            "https://gitlab.example.com/group/sub/project.git": ("gitlab.example.com", "group/sub/project"),
            "git@github.com:owner/repo.git": ("github.com", "owner/repo"),
            "ssh://git@gitlab.example.com:2222/group/project.git": ("gitlab.example.com", "group/project"),
            "https://oauth2:not-a-secret@GitLab.Example.com/group/project": ("gitlab.example.com", "group/project"),
            "https://github.com/owner/repo/": ("github.com", "owner/repo"),
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(expected, state.parse_origin(url))

    def test_a_local_path_has_no_forge(self):
        self.assertEqual((None, None), state.parse_origin("/srv/git/project.git"))
        self.assertEqual((None, None), state.parse_origin(""))


class IssueKeyTests(unittest.TestCase):
    def test_a_key_in_the_branch_wins(self):
        self.assertEqual("ABC-12", state.issue_key("feature/ABC-12-login", ["XYZ-9 other work"]))

    def test_a_bare_branch_number_takes_the_prefix_from_the_commits(self):
        self.assertEqual("ABC-12", state.issue_key("feature/me/12", ["fix(login): ABC-13 keep the session"]))

    def test_a_bare_branch_number_takes_the_prefix_from_the_request_title(self):
        self.assertEqual("ABC-12", state.issue_key("feature/me/12", ["no key here", "Draft: ABC-13"]))

    def test_without_a_branch_number_the_first_key_in_the_commits_is_used(self):
        self.assertEqual("ABC-13", state.issue_key("feature/login", ["ABC-13 first", "ABC-14 second"]))

    def test_no_key_anywhere_gives_none(self):
        self.assertIsNone(state.issue_key("feature/me/12", ["plain subject"]))
        self.assertIsNone(state.issue_key("", []))


class ReviewSummaryTests(unittest.TestCase):
    def test_counts_only_resolvable_threads_that_are_still_open(self):
        discussions = [
            {"notes": [{"resolvable": True, "resolved": False}]},
            {"notes": [{"resolvable": True, "resolved": True}]},
            {"notes": [{"resolvable": False, "resolved": False}]},
            {"notes": [{"resolvable": True, "resolved": True}, {"resolvable": True, "resolved": False}]},
        ]
        self.assertEqual(2, state.unresolved_gitlab_threads(discussions))

    def test_a_failed_check_outranks_a_running_one(self):
        rollup = [{"status": "IN_PROGRESS", "conclusion": ""}, {"status": "COMPLETED", "conclusion": "FAILURE"}]
        self.assertEqual("failed", state.summarize_checks(rollup))

    def test_a_running_check_outranks_finished_ones(self):
        rollup = [{"status": "IN_PROGRESS", "conclusion": ""}, {"status": "COMPLETED", "conclusion": "SUCCESS"}]
        self.assertEqual("running", state.summarize_checks(rollup))

    def test_finished_checks_without_a_failure_are_a_success(self):
        rollup = [{"status": "COMPLETED", "conclusion": "SUCCESS"}, {"state": "SUCCESS"}]
        self.assertEqual("success", state.summarize_checks(rollup))
        self.assertEqual("none", state.summarize_checks([]))


class GitStateTests(unittest.TestCase):
    def test_lists_only_the_commits_the_branch_adds_to_the_target(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, NO_TOKENS):
            remote, work = os.path.join(root, "remote.git"), os.path.join(root, "work")
            git(root, "init", "--quiet", "--bare", "--initial-branch=main", remote)
            git(root, "clone", "--quiet", remote, work)
            for args in (("config", "user.email", "dev@example.com"), ("config", "user.name", "Dev"), ("config", "commit.gpgsign", "false"),
                         ("commit", "--quiet", "--allow-empty", "-m", "base"), ("push", "--quiet", "origin", "main"),
                         ("switch", "--quiet", "-c", "feature/12"),
                         ("commit", "--quiet", "--allow-empty", "-m", "ABC-13 add the reset link")):
                git(work, *args)

            lines = state.describe(work)

        self.assertIn("branch: feature/12 -> target main", lines)
        self.assertIn("upstream: none", lines)
        commits = lines[lines.index("commits not on the target:") + 1:lines.index("status:")]
        self.assertEqual(1, len(commits))
        self.assertIn("ABC-13 add the reset link", commits[0])
        self.assertFalse(any(line.startswith("WARNING") for line in lines))

    def test_warns_when_the_branch_tracks_the_target(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(os.environ, NO_TOKENS):
            remote, work = os.path.join(root, "remote.git"), os.path.join(root, "work")
            git(root, "init", "--quiet", "--bare", "--initial-branch=main", remote)
            git(root, "clone", "--quiet", remote, work)
            for args in (("config", "user.email", "dev@example.com"), ("config", "user.name", "Dev"), ("config", "commit.gpgsign", "false"),
                         ("commit", "--quiet", "--allow-empty", "-m", "base"), ("push", "--quiet", "origin", "main"),
                         ("switch", "--quiet", "-c", "feature/12", "--track", "origin/main")):
                git(work, *args)

            lines = state.describe(work)

        self.assertIn("WARNING: the upstream is the target branch; a bare push would land there", lines)


if __name__ == "__main__":
    unittest.main()
