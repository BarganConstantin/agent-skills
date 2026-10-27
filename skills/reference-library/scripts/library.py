#!/usr/bin/env python3
"""Offline, installable reference-library lookup and opt-in bookmark capture.

No network calls, code imports from indexed projects, Git writes, or installs.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
from urllib.parse import urlsplit, urlunsplit

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "references" / "catalog.json"
ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOKEN = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "and", "the", "for", "from", "to", "with", "in", "of", "my",
        "la", "de", "si", "sa", "un", "o", "cu", "pentru", "mai", "pe", "in", "este"}


class LibraryError(ValueError):
    """Invalid local catalog or attempted unsafe change."""


def normalize(value):
    stripped = unicodedata.normalize("NFKD", value)
    return "".join(char for char in stripped if not unicodedata.combining(char)).casefold()


def words(value):
    return set(TOKEN.findall(normalize(value))) - STOP


def canonical_url(value):
    try:
        p = urlsplit(value.strip())
    except ValueError as exc:
        raise LibraryError("Invalid URL") from exc
    try:
        host, port = p.hostname, p.port
    except ValueError as exc:
        raise LibraryError("Invalid reference URL host or port") from exc
    if p.scheme != "https" or not host or "." not in host or p.username or p.password or port:
        raise LibraryError("References require a public HTTPS URL without credentials or port")
    if host in ("localhost", "127.0.0.1") or any(x.isspace() for x in value):
        raise LibraryError("Private or malformed references are not accepted")
    if any(ord(char) < 32 for char in value):
        raise LibraryError("URL contains control characters")
    return urlunsplit(("https", host.lower(), p.path.rstrip("/") or "/", p.query, p.fragment))


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise LibraryError("Cannot load catalog") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise LibraryError("Expected catalog schema_version 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise LibraryError("Catalog entries must be an array")
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise LibraryError("Catalog needs a nonempty category taxonomy")
    valid_categories = set()
    for category in categories:
        if not isinstance(category, dict):
            raise LibraryError("Categories must be objects")
        identifier = category.get("id")
        if (not isinstance(identifier, str) or not ID.fullmatch(identifier)
                or identifier in valid_categories or not isinstance(category.get("name"), str)
                or not category["name"].strip()
                or not isinstance(category.get("tagline"), str)
                or not category["tagline"].strip()):
            raise LibraryError("Category IDs must be unique slugs with a name and description")
        valid_categories.add(identifier)
    ids, urls = set(), set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise LibraryError("Catalog entries must be objects")
        key = entry.get("id")
        if not isinstance(key, str) or not ID.fullmatch(key) or key in ids:
            raise LibraryError("Catalog IDs must be unique, lowercase slugs")
        name, url, tags = entry.get("name"), entry.get("url"), entry.get("tags")
        if not isinstance(name, str) or not name.strip():
            raise LibraryError("Every reference needs a name")
        if not isinstance(url, str):
            raise LibraryError("Every reference needs a URL")
        safe_url = canonical_url(url)
        if safe_url in urls:
            raise LibraryError("Catalog contains a duplicate URL")
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise LibraryError("Reference tags must be an array of strings")
        if not isinstance(entry.get("use_when"), str):
            raise LibraryError("Every reference needs an explicit use_when explanation")
        groups = entry.get("categories")
        if (not isinstance(groups, list) or not groups or
                len(set(groups)) != len(groups) or any(
                    not isinstance(group, str) or group not in valid_categories for group in groups
                )):
            raise LibraryError("Every reference needs unique valid category IDs")
        if not isinstance(entry.get("summary"), str) or not entry["summary"].strip():
            raise LibraryError("Every reference needs a short summary")
        ids.add(key)
        urls.add(safe_url)
    return data


def match(entry, query):
    requested = words(query)
    if not requested:
        return 0, []
    tags = entry["tags"]
    tag_sets = [(tag, words(tag)) for tag in tags]
    name_words = words(entry["name"] + " " + entry["id"])
    context_words = words(" ".join([
        entry["use_when"], " ".join(entry.get("look_for", [])),
    ]))
    matched_tags = sorted(
        tag for tag, tokens in tag_sets if requested.intersection(tokens)
    )
    score = sum(6 for term in requested if any(term in tokens for _, tokens in tag_sets))
    score += sum(3 for term in requested if term in name_words)
    score += sum(1 for term in requested if term in context_words)
    return score, matched_tags


def validate_category(data, category):
    if category is not None and category not in {x["id"] for x in data["categories"]}:
        raise LibraryError("Unknown category: " + str(category))
    return category


def browse(data, category):
    validate_category(data, category)
    return [
        {"id": entry["id"], "name": entry["name"], "url": entry["url"],
         "summary": entry["summary"], "categories": entry["categories"],
         "use_when": entry["use_when"], "status": entry["status"],
         "license": entry["license"]}
        for entry in data["entries"] if category is None or category in entry["categories"]
    ]


def list_categories(data):
    return [
        {"id": group["id"], "name": group["name"], "tagline": group["tagline"],
         "count": sum(group["id"] in entry["categories"] for entry in data["entries"])}
        for group in data["categories"]
    ]


def search(data, query, limit, category=None):
    validate_category(data, category)
    if limit < 1 or limit > 50:
        raise LibraryError("Limit must be between 1 and 50")
    ranked = []
    for entry in data["entries"]:
        if category is not None and category not in entry["categories"]:
            continue
        score, tags = match(entry, query)
        if score > 0:
            ranked.append((score, entry["id"], tags, entry))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [{"id": entry["id"], "name": entry["name"], "url": entry["url"],
             "score": score, "matched_tags": tags, "use_when": entry["use_when"],
             "status": entry["status"], "categories": entry["categories"],
             "summary": entry["summary"]} for score, _, tags, entry in ranked[:limit]]


def prepare_reference(data, args):
    if not ID.fullmatch(args.id):
        raise LibraryError("ID must be a lowercase hyphenated slug")
    new_url = canonical_url(args.url)
    if any(item["id"] == args.id or canonical_url(item["url"]) == new_url
           for item in data["entries"]):
        raise LibraryError("Reference already saved; update/review its existing record")
    requested_categories = [value.strip() for value in args.categories.split(",") if value.strip()]
    if (not requested_categories or len(requested_categories) != len(set(requested_categories))
            or any(cat not in {group["id"] for group in data["categories"]} for cat in requested_categories)):
        raise LibraryError("Choose valid, non-duplicate categories; new bookmarks default to inbox")
    tags = [tag.strip().lower() for tag in args.tags.split(",") if tag.strip()]
    if not tags or len(tags) > 30 or any(not ID.fullmatch(t) for t in tags):
        raise LibraryError("Provide 1-30 comma-separated lowercase tag slugs")
    if not args.name.strip() or not args.use_when.strip():
        raise LibraryError("Provide a project name and when it would be useful")
    return {
        "id": args.id, "name": args.name.strip(), "url": new_url,
        "owner": "not-verified", "type": "reference",
        "license": "unknown", "license_source": None,
        "reviewed_at": None, "status": "unverified-reference",
        "tags": sorted(set(tags)), "categories": requested_categories,
        "summary": args.use_when.strip(), "use_when": args.use_when.strip(),
        "look_for": [], "cautions": [
            "Not independently inspected. Verify scope, ownership, license and current docs before using.",
            "Indexed only; no external software has been installed or executed.",
        ],
    }


def save(path, data):
    target = Path(path)
    if target.is_symlink():
        raise LibraryError("Refusing to overwrite a symlink catalog")
    # Replace atomically only after an explicit --write; preserve existing data on error.
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=target.parent, prefix=".reference-library-",
                                         suffix=".tmp", delete=False) as output:
            name = output.name
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search or curate your offline agent reference library")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG,
                        help="Catalog file (default: bundled references/catalog.json)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("categories", help="List category names, purposes and reference counts")
    listing = sub.add_parser("list", help="Show saved references, optionally filtered")
    listing.add_argument("--category", help="Category slug, e.g. backend")
    browsing = sub.add_parser("browse", help="Explore sources belonging to one category")
    browsing.add_argument("category", help="Category slug, e.g. testing")
    find = sub.add_parser("search", help="Recommend saved references for a task")
    find.add_argument("query", help="Task description, e.g. 'landing page animation'")
    find.add_argument("--limit", type=int, default=5)
    find.add_argument("--category", help="Optional category filter, e.g. review")
    show = sub.add_parser("show", help="Show exactly one saved reference")
    show.add_argument("id")
    add = sub.add_parser("add", help="Prepare a bookmark; --write required to save it")
    add.add_argument("--id", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--url", required=True)
    add.add_argument("--tags", required=True)
    add.add_argument("--categories", default="inbox",
                     help="Comma-separated category IDs; default inbox for later review")
    add.add_argument("--use-when", required=True)
    add.add_argument("--write", action="store_true",
                     help="Explicitly change the local catalog file; never syncs Git/other copies")
    args = parser.parse_args(argv)
    try:
        data = load(args.catalog)
        if args.command == "categories":
            result = list_categories(data)
        elif args.command == "list":
            result = browse(data, args.category)
        elif args.command == "browse":
            result = browse(data, args.category)
        elif args.command == "show":
            result = next((e for e in data["entries"] if e["id"] == args.id), None)
            if result is None:
                raise LibraryError("No saved reference with ID " + args.id)
        elif args.command == "search":
            result = search(data, args.query, args.limit, args.category)
        else:
            result = prepare_reference(data, args)
            if args.write:
                data["entries"].append(result)
                save(args.catalog, data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "add":
            print("Saved locally; commit/sync manually." if args.write else
                  "PREVIEW ONLY; add --write to persist locally.", file=sys.stderr)
        elif args.command == "search" and not result:
            print("No relevant saved reference. Do not invent one.", file=sys.stderr)
        return 0
    except LibraryError as exc:
        print("Reference library: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
