#!/usr/bin/env python3
"""Render the human-readable library page from the canonical reference catalog.

Only local repository files. No external requests, installs or Git operations.
--check is read-only; --write requires explicit opt-in.
"""
import argparse
import html
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "skills" / "reference-library"
sys.path.insert(0, str(LIBRARY / "scripts"))
from library import LibraryError, canonical_url, load  # noqa: E402

CATALOG = LIBRARY / "references" / "catalog.json"
PAGE = ROOT / "docs" / "library.md"
START = "<!-- BEGIN GENERATED LIBRARY — edit catalog.json, not this section -->"
END = "<!-- END GENERATED LIBRARY -->"
HEADING = "## Browse by area"
NEXT = "## Find exactly what you need"
def plain(value):
    """Escape display fields: no source-supplied HTML or Markdown structure."""
    text = " ".join(str(value).split())
    text = html.escape(text, quote=False)
    for character in ("\\", "|", "[", "]", "\x60"):
        text = text.replace(character, "\\" + character)
    return text


def anchor(title):
    """GitHub's markdown heading slug rules for the controlled titles used here."""
    value = re.sub(r"[^\w\- ]", "", title.lower(), flags=re.UNICODE)
    return value.replace(" ", "-")


def safe_link(value):
    """Keep GitHub Markdown links unambiguous and reject unsafe schemes."""
    url = canonical_url(value)
    for char, encoded in (("(", "%28"), (")", "%29"), ('"', "%22"),
                          ("<", "%3C"), (">", "%3E")):
        url = url.replace(char, encoded)
    return url


def table(entries):
    result = [
        "| Original project | Why it's useful | Reach for it when… | License |",
        "| :-- | :-- | :-- | :-- |",
    ]
    for item in entries:
        name = plain(item["name"])
        url = safe_link(item["url"])
        desc = plain(item["summary"])
        reason = plain(item["use_when"])
        license_name = plain(item["license"])
        license_url = item.get("license_source")
        verified = item.get("status") == "reference-only"
        if verified and not isinstance(license_url, str):
            raise LibraryError("Verified references need a reviewed license URL")
        label = ("[" + license_name + "](" + safe_link(license_url) + ")"
                 if verified else "Unverified")
        result.append(
            "| **[" + name + "](" + url + ")** | " + desc
            + " | " + reason + " | " + label + " |"
        )
    return result


def render(data):
    entries = data["entries"]
    categories = [item for item in data["categories"] if item["id"] != "inbox"]
    memberships = sum(
        item["id"] in row["categories"] for item in categories for row in entries
    )
    lines = [HEADING, ""]
    for item in categories:
        matching = sum(item["id"] in row["categories"] for row in entries)
        lines.append(
            "[**" + plain(item["name"]) + "**](#" + anchor(item["name"]) + ")"
            + " · " + str(matching) + " reference" + ("s" if matching != 1 else "")
        )
    lines.extend([
        "",
        "> **" + str(len(entries)) + " unique sources** · "
        + str(memberships) + " category placements. A project may appear in "
        + "more than one section without being duplicated in the catalog. "
        + "New unreviewed bookmarks are collected in the Inbox.",
        "",
        "## Explore saved projects", "",
    ])
    for category in categories:
        matching = [row for row in entries if category["id"] in row["categories"]]
        lines.extend([
            "### " + plain(category["name"]), "",
            plain(category["tagline"]), "",
            *table(matching), "",
        ])

    unreviewed = [row for row in entries if "inbox" in row["categories"]]
    if unreviewed:
        lines.extend([
            "### Inbox / To Review", "",
            "These links were **not yet verified**. Check their owner, "
            "license and current purpose before recommending or using them.",
            "", *table(unreviewed), "",
        ])
    return "\n".join(lines).rstrip()


def expected(existing, data):
    section = START + "\n" + render(data) + "\n" + END
    if START in existing and END in existing:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
        return pattern.sub(lambda _: section, existing, count=1)
    # One-time migration from the hand-written library page. The surrounding
    # guide, safe-save instructions and original illustration remain untouched.
    first = existing.find(HEADING)
    last = existing.find(NEXT)
    if first == -1 or last <= first:
        raise LibraryError("Missing generated markers or legacy section boundaries")
    return existing[:first] + section + "\n\n" + existing[last:]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Render/check the Markdown library index from catalog.json")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--check", action="store_true", help="Read-only CI drift check")
    actions.add_argument("--write", action="store_true", help="Explicitly update the Markdown index")
    args = parser.parse_args(argv)
    try:
        data = load(CATALOG)
        existing = PAGE.read_text(encoding="utf-8")
        output = expected(existing, data)
        if args.check:
            if existing != output:
                print("docs/library.md is stale; run python scripts/render_library.py --write",
                      file=sys.stderr)
                return 1
            print("Reference Library page matches the canonical catalog.")
            return 0
        if existing != output:
            PAGE.write_text(output, encoding="utf-8")
            print("Updated docs/library.md from the canonical catalog.")
        else:
            print("docs/library.md is already in sync.")
        return 0
    except (LibraryError, OSError, UnicodeError, KeyError, TypeError) as exc:
        print("Library render error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
