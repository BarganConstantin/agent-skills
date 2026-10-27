"""Offline reference library behavior, persistence, deduplication and safety tests."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "reference-library" / "scripts" / "library.py"
CATALOG = SCRIPT.parents[1] / "references" / "catalog.json"
spec = importlib.util.spec_from_file_location("reference_library", SCRIPT)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


class ReferenceLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = library.load(CATALOG)

    def test_saved_links_are_original_sources_with_license_recorded(self):
        entries = {entry["id"]: entry for entry in self.data["entries"]}
        self.assertEqual(len(entries), 9)
        self.assertTrue({"hallmark", "ai-design-skills", "microsoft-aspire", "microsoft-agent-framework", "oasdiff", "playwright-mcp", "playwright-cli", "superpowers", "spec-kit"}.issubset(set(entries)))
        self.assertEqual(entries["hallmark"]["url"], "https://github.com/Nutlope/hallmark")
        self.assertEqual(entries["ai-design-skills"]["url"], "https://github.com/elayadesign/ai-design-skills")
        for item in entries.values():
            self.assertIn(item["license"], ("MIT", "Apache-2.0"))
            self.assertEqual(item["status"], "reference-only")
            self.assertEqual(item["reviewed_at"], "2026-10-27")
            self.assertGreater(len(item["look_for"]), 0)
            self.assertIn("github.com", item["license_source"])
            self.assertGreaterEqual(len(item["categories"]), 1)
            self.assertTrue(item["summary"])

    def test_ui_design_query_returns_relevant_saved_links(self):
        found = library.search(self.data, "UI design for a landing page", 5, "ui-ux")
        self.assertEqual({x["id"] for x in found}, {"hallmark", "ai-design-skills"})
        self.assertTrue(all(x["matched_tags"] for x in found))
        self.assertTrue(all(x["status"] == "reference-only" for x in found))

    def test_motion_query_prefers_motion_design_reference(self):
        found = library.search(self.data, "animated motion video showcase", 5)
        self.assertGreaterEqual(len(found), 1)
        self.assertEqual(found[0]["id"], "ai-design-skills")

    def test_romanian_task_search_finds_saved_design_entries(self):
        found = library.search(self.data, "design interfata pagina", 5)
        self.assertEqual({item["id"] for item in found}, {"hallmark", "ai-design-skills"})

    def test_unrelated_query_returns_no_invented_references(self):
        self.assertEqual(library.search(self.data, "dental insurance tax forms", 5), [])
        self.assertEqual(library.search(self.data, "a si de", 5), [])

    def test_limit_guards_and_tie_order_are_stable(self):
        with self.assertRaises(library.LibraryError):
            library.search(self.data, "design", 0)
        with self.assertRaises(library.LibraryError):
            library.search(self.data, "design", 51)
        result = library.search(self.data, "design", 1)
        self.assertEqual(len(result), 1)

    def test_rejects_unsafe_or_invalid_url(self):
        for bad in ("http://github.com/sample/tool", "https://x:y@github.com/demo",
                    "https://localhost/a", "https://127.0.0.1/a",
                    "https://github.com:1234/demo", "file:///tmp/secret"):
            with self.subTest(url=bad), self.assertRaises(library.LibraryError):
                library.canonical_url(bad)

    def test_catalog_rejects_duplicate_urls(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "catalog.json"
            data = json.loads(json.dumps(self.data))
            duplicate = dict(data["entries"][0])
            duplicate["id"] = "new-other-id"
            data["entries"].append(duplicate)
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(library.LibraryError):
                library.load(path)

    def test_dry_run_does_not_modify_catalog_and_opt_in_write_persists(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "catalog.json"
            original = CATALOG.read_bytes()
            path.write_bytes(original)
            args = ["--catalog", str(path), "add", "--id", "sample-project",
                    "--name", "Sample Project", "--url", "https://github.com/example/sample",
                    "--tags", "design,frontend", "--use-when", "Investigate design patterns"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(library.main(args), 0)
            self.assertEqual(path.read_bytes(), original)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(library.main(args + ["--write"]), 0)
            items = library.load(path)["entries"]
            self.assertEqual(len(items), 10)
            self.assertEqual(items[-1]["status"], "unverified-reference")
            self.assertEqual(items[-1]["license"], "unknown")
            self.assertIsNone(items[-1]["reviewed_at"])
            self.assertEqual(items[-1]["categories"], ["inbox"])
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(library.main(args + ["--write"]), 2)
            self.assertEqual(len(library.load(path)["entries"]), 10)

    def test_taxonomy_has_the_requested_five_domains_and_safe_inbox(self):
        cats = {row["id"]: row for row in library.list_categories(self.data)}
        self.assertEqual(
            set(cats), {"ui-ux", "backend", "review", "testing", "agent-workflows", "inbox"})
        self.assertEqual(cats["ui-ux"]["count"], 2)
        for key in ("backend", "review", "testing", "agent-workflows"):
            self.assertGreaterEqual(cats[key]["count"], 2)
        self.assertEqual(cats["inbox"]["count"], 0)

    def test_category_browse_is_grounded_and_links_to_original_repos(self):
        for key in ("ui-ux", "backend", "review", "testing", "agent-workflows"):
            matches = library.browse(self.data, key)
            self.assertGreater(len(matches), 0)
            self.assertTrue(all(key in e["categories"] for e in matches))
            self.assertTrue(all(e["url"].startswith("https://github.com/") for e in matches))
            self.assertTrue(all(e["summary"] and e["use_when"] for e in matches))
        self.assertEqual(len(library.browse(self.data, None)), 9)

    def test_multi_category_reference_appears_in_multiple_groups_without_duplication(self):
        backend = {e["id"] for e in library.browse(self.data, "backend")}
        review = {e["id"] for e in library.browse(self.data, "review")}
        self.assertIn("oasdiff", backend & review)
        self.assertEqual(len({e["url"] for e in self.data["entries"]}), 9)

    def test_search_category_filters_do_not_leak_other_sections(self):
        found = library.search(self.data, "OpenAPI breaking changes", 20, "review")
        self.assertIn("oasdiff", [item["id"] for item in found])
        self.assertTrue(all("review" in item["categories"] for item in found))
        self.assertEqual(library.search(self.data, "design landing page", 20, "backend"), [])

    def test_unknown_categories_and_malformed_taxonomy_are_rejected(self):
        for op in (lambda: library.search(self.data, "api", 3, "fiction"),
                   lambda: library.browse(self.data, "fiction")):
            with self.assertRaises(library.LibraryError):
                op()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "catalog.json"
            invalid = json.loads(json.dumps(self.data))
            invalid["entries"][0]["categories"] = ["nonexistent"]
            p.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(library.LibraryError):
                library.load(p)

    def test_explicit_categories_can_be_saved_and_invalid_categories_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            base = ["--catalog", str(path), "add", "--id", "new-testing-tool",
                    "--name", "New Test Tool", "--url", "https://github.com/example/new",
                    "--tags", "testing", "--use-when", "Check frontend behavior"]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(library.main(base + ["--categories", "testing,review", "--write"]), 0)
                self.assertEqual(library.main(base + ["--categories", "unknown", "--write"]), 2)
            self.assertEqual(library.load(path)["entries"][-1]["categories"], ["testing", "review"])

    def test_grouped_cli_exposes_source_counts_without_fake_records(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(library.main(["categories"]), 0)
        data = json.loads(out.getvalue())
        self.assertEqual(next(x["count"] for x in data if x["id"] == "ui-ux"), 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(library.main(["browse", "testing"]), 0)
        entries = json.loads(out.getvalue())
        self.assertTrue(all("testing" in entry["categories"] for entry in entries))

    def test_rendered_library_organizes_and_links_every_saved_project(self):
        page = (ROOT / "docs" / "library.md").read_text(encoding="utf-8")
        self.assertIn("assets/library-map.svg", page)
        for heading in ("UI and UX", "Backend and API", "Code Review",
                        "Testing and QA", "Agent Workflows"):
            self.assertIn("### " + heading, page)
        for entry in self.data["entries"]:
            self.assertIn(entry["url"], page)
            self.assertIn(entry["name"], page)
        self.assertIn("do **not** sync automatically", page)

    def test_do_not_follow_symlink_to_write_elsewhere(self):
        with tempfile.TemporaryDirectory() as work:
            destination = Path(work) / "real.json"
            destination.write_text(json.dumps(self.data), encoding="utf-8")
            alias = Path(work) / "catalog.json"
            alias.symlink_to(destination)
            with self.assertRaises(library.LibraryError):
                library.save(alias, self.data)

    def test_skill_links_to_bundled_catalog_and_never_promises_auto_sync(self):
        skill = (ROOT / "skills" / "reference-library" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/catalog.json", skill)
        self.assertIn("not automatically sync", skill.lower())
        self.assertIn("reference-library", (ROOT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
