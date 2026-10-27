#!/usr/bin/env python3
"""Produce a non-destructive, path-redacted Git checkpoint for agent handoffs.

Reads local Git metadata only. Never sends network requests, reads source
contents, runs tests, or attests an agent's claims.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


class SnapshotError(Exception):
    """A Git or filesystem precondition was not met."""


def git(root, *args, optional=False):
    try:
        result = subprocess.run(
            ["git", "-c", "color.ui=false", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError("Git is unavailable or did not finish") from exc
    if result.returncode != 0:
        if optional:
            return None
        # Do not echo stderr: it could contain private working directory names.
        raise SnapshotError("Git command failed: " + args[0])
    return result.stdout.rstrip("\n")


def snapshot(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise SnapshotError("Given project directory does not exist")

    # --show-toplevel is a presence check, not user-visible content.
    git(root, "rev-parse", "--show-toplevel")
    # No git remote URLs, paths, file content, patches, log messages or secrets.
    head = git(root, "rev-parse", "--verify", "HEAD", optional=True)
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", optional=True)
    raw = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    entries = [line for line in raw.splitlines() if line]
    staged = sum(line[:1] not in (" ", "?") for line in entries)
    unstaged = sum(len(line) > 1 and line[1] not in (" ", "?") for line in entries)
    untracked = sum(line.startswith("??") for line in entries)

    return {
        "schema_version": 1,
        "kind": "local_git_snapshot_not_test_evidence",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "head_sha": head,
        "branch": branch if branch else ("(detached)" if head else "(unborn)"),
        "working_tree": {
            "changed_entries": len(entries),
            "staged_entries": staged,
            "unstaged_entries": unstaged,
            "untracked_entries": untracked,
            "clean": not entries,
        },
        "limitations": [
            "The snapshot records Git metadata, not agent intent or tests.",
            "The snapshot does not include file paths, diffs, remotes or source content.",
            "Git status does not show ignored files, and counts can become stale.",
            "Branch names can contain sensitive words; review before sharing.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capture a local, path-redacted Git checkpoint")
    parser.add_argument("--root", type=Path, default=Path("."), help="Local Git project (default: cwd)")
    parser.add_argument("--output", type=Path, help="Optional new JSON file; never overwrites")
    args = parser.parse_args(argv)
    try:
        payload = json.dumps(snapshot(args.root), indent=2) + "\n"
        if args.output:
            # Exclusive creation prevents replacing user files and work artifacts.
            with args.output.open("x", encoding="utf-8") as target:
                target.write(payload)
            print("Checkpoint created; inspect locally before sharing.")
        else:
            print(payload, end="")
        return 0
    except (SnapshotError, FileExistsError, PermissionError, OSError) as exc:
        print("Checkpoint unavailable: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
