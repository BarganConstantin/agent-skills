#!/usr/bin/env python3
"""Print the read-only state that compass reads: git, the merge or pull request, and the tracker ticket."""
import argparse
import base64
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 15
MAX_COMMITS = 15
DEFAULT_TARGET = "main"
ISSUE_KEY = re.compile(r"\b([A-Z][A-Z0-9]+)-(\d+)\b")
ORIGIN = re.compile(r"^(?:[a-z][a-z0-9+.-]*://)?(?:[^@/]+@)?([^/:]+)(?::\d+)?[:/](.+?)(?:\.git)?/?$")
TRAILING_NUMBER = re.compile(r"(\d+)$")
FAILED_CHECKS = {"FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "ERROR", "STARTUP_FAILURE"}
RUNNING_CHECKS = {"IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED", "EXPECTED"}
GITHUB_THREADS_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
    "{reviewThreads(first:100){nodes{isResolved}}}}}"
)


def run(args, cwd):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def http_json(url, headers):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except Exception:
        return None


def parse_origin(url):
    match = ORIGIN.match(url.strip()) if url else None
    return (match.group(1).lower(), match.group(2)) if match else (None, None)


def issue_key(branch, texts):
    in_branch = ISSUE_KEY.search(branch or "")
    if in_branch:
        return in_branch.group(0)
    keys = [match for text in texts for match in ISSUE_KEY.finditer(text or "")]
    number = TRAILING_NUMBER.search(branch or "")
    if number and keys:
        return f"{keys[0].group(1)}-{number.group(1)}"
    return keys[0].group(0) if keys else None


def unresolved_gitlab_threads(discussions):
    return sum(
        1 for thread in discussions
        if any(note.get("resolvable") and not note.get("resolved") for note in thread.get("notes", [])))


def summarize_checks(rollup):
    states = {(check.get("conclusion") or check.get("state") or check.get("status") or "").upper() for check in rollup}
    if states & FAILED_CHECKS:
        return "failed"
    if states & RUNNING_CHECKS or any((check.get("status") or "").upper() in RUNNING_CHECKS for check in rollup):
        return "running"
    return "success" if rollup else "none"


def gitlab_review(host, path, branch):
    token = os.environ.get("GITLAB_TOKEN")
    if not token:
        return None
    api = f"https://{host}/api/v4/projects/{urllib.parse.quote(path, safe='')}"
    headers = {"PRIVATE-TOKEN": token}
    found = http_json(
        f"{api}/merge_requests?source_branch={urllib.parse.quote(branch, safe='')}&state=all&order_by=updated_at&per_page=1",
        headers)
    if not found:
        return None
    iid = found[0]["iid"]
    request = http_json(f"{api}/merge_requests/{iid}", headers) or found[0]
    discussions = http_json(f"{api}/merge_requests/{iid}/discussions?per_page=100", headers) or []
    return {
        "label": f"MR !{iid}",
        "state": request.get("state"),
        "draft": request.get("draft"),
        "checks": (request.get("head_pipeline") or {}).get("status", "none"),
        "unresolved": unresolved_gitlab_threads(discussions),
        "url": request.get("web_url"),
        "target": request.get("target_branch"),
        "title": request.get("title", ""),
    }


def github_review(path, branch, cwd):
    raw = run(["gh", "pr", "list", "--repo", path, "--head", branch, "--state", "all", "--limit", "1",
               "--json", "number,state,isDraft,url,baseRefName,title,statusCheckRollup"], cwd)
    pulls = json.loads(raw) if raw else []
    if not pulls:
        return None
    pull = pulls[0]
    owner, name = path.split("/", 1)
    threads_raw = run(["gh", "api", "graphql", "-f", f"query={GITHUB_THREADS_QUERY}", "-f", f"owner={owner}",
                       "-f", f"name={name}", "-F", f"number={pull['number']}"], cwd)
    threads = (json.loads(threads_raw) if threads_raw else {}).get("data", {}).get("repository", {}) \
        .get("pullRequest", {}).get("reviewThreads", {}).get("nodes", [])
    return {
        "label": f"PR #{pull['number']}",
        "state": pull.get("state", "").lower(),
        "draft": pull.get("isDraft"),
        "checks": summarize_checks(pull.get("statusCheckRollup") or []),
        "unresolved": sum(1 for thread in threads if not thread.get("isResolved")),
        "url": pull.get("url"),
        "target": pull.get("baseRefName"),
        "title": pull.get("title", ""),
    }


def review_for(origin, branch, cwd):
    host, path = parse_origin(origin)
    if not host or not branch:
        return None
    if "github" in host:
        return github_review(path, branch, cwd)
    return gitlab_review(host, path, branch)


def jira_token():
    command = os.environ.get("JIRA_TOKEN_CMD")
    if command:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return os.environ.get("JIRA_TOKEN")


def jira_headers(token):
    email = os.environ.get("JIRA_EMAIL")
    if email:
        return {"Authorization": "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()}
    return {"Authorization": f"Bearer {token}"}


def jira_ticket(key):
    base = os.environ.get("JIRA_BASE", "").rstrip("/")
    token = jira_token() if base and key else None
    if not token:
        return []
    headers = jira_headers(token)
    fields = "fields=summary,status,subtasks,parent"
    issue = http_json(f"{base}/rest/api/2/issue/{key}?{fields}", headers)
    if not issue:
        return []
    parent = (issue["fields"].get("parent") or {}).get("key")
    if parent and not issue["fields"].get("subtasks"):
        issue = http_json(f"{base}/rest/api/2/issue/{parent}?{fields}", headers) or issue
    lines = [f"== {issue['key']} [{issue['fields']['status']['name']}] {issue['fields']['summary']}"]
    for subtask in issue["fields"].get("subtasks", []):
        lines.append(f"  {subtask['key']} [{subtask['fields']['status']['name']}] {subtask['fields']['summary']}")
    return lines


def target_branch(review, cwd):
    if review and review.get("target"):
        return review["target"]
    remote_head = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd)
    return remote_head.removeprefix("origin/") if remote_head else DEFAULT_TARGET


def describe(cwd):
    branch = run(["git", "branch", "--show-current"], cwd)
    review = review_for(run(["git", "remote", "get-url", "origin"], cwd), branch, cwd)
    target = target_branch(review, cwd)
    commits = run(["git", "log", "--oneline", f"--max-count={MAX_COMMITS}", f"origin/{target}..HEAD"], cwd)
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd)
    lines = [f"== repo {cwd}", f"branch: {branch or '(detached)'} -> target {target}", f"upstream: {upstream or 'none'}"]
    if upstream == f"origin/{target}":
        lines.append("WARNING: the upstream is the target branch; a bare push would land there")
    lines.append("commits not on the target:")
    lines += ["  " + line for line in commits.splitlines()] or ["  (none)"]
    lines.append("status:")
    lines += ["  " + line for line in run(["git", "status", "--short", "--branch"], cwd).splitlines()]
    if upstream:
        counts = run(["git", "rev-list", "--left-right", "--count", f"{upstream}...HEAD"], cwd).split()
        if len(counts) == 2:
            lines.append(f"behind/ahead upstream: {counts[0]} {counts[1]}")
    if review:
        lines.append(
            f"== {review['label']} {review['state']} draft={review['draft']} checks={review['checks']} "
            f"unresolved threads={review['unresolved']} {review['url']}")
    subjects = run(["git", "log", "--format=%s", f"--max-count={MAX_COMMITS}", f"origin/{target}..HEAD"], cwd)
    key = issue_key(branch, subjects.splitlines() + [(review or {}).get("title", "")])
    return lines + jira_ticket(key)


def main():
    parser = argparse.ArgumentParser(description="Print the read-only state for a compass answer.")
    parser.add_argument("paths", nargs="*", default=["."], help="repository or worktree paths (default: current)")
    args = parser.parse_args()
    for path in args.paths:
        print("\n".join(describe(os.path.abspath(path))))
    worktrees = run(["git", "worktree", "list"], os.path.abspath(args.paths[0]))
    if worktrees:
        print("== worktrees")
        print(worktrees)


if __name__ == "__main__":
    main()
