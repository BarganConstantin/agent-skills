"""The human-facing library must be generated deterministically from one catalog."""
import copy
import importlib.util
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "render_library.py"
spec = importlib.util.spec_from_file_location("render_library", SOURCE)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class LibraryRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = renderer.load(renderer.CATALOG)
        cls.original = renderer.PAGE.read_text(encoding="utf-8")

    def test_current_page_is_identical_to_catalog_render(self):
        self.assertEqual(renderer.expected(self.original, self.data), self.original)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(renderer.main(["--check"]), 0)

    def test_all_public_references_have_links_from_the_canonical_source(self):
        body = renderer.render(self.data)
        for entry in self.data["entries"]:
            self.assertIn(renderer.safe_link(entry["url"]), body)
            self.assertIn(renderer.plain(entry["name"]), body)
        self.assertIn(str(len(self.data["entries"])) + " unique sources", body)
        self.assertIn(str(sum(
            group["id"] in entry["categories"]
            for group in self.data["categories"] if group["id"] != "inbox"
            for entry in self.data["entries"])) + " category placements", body)
        self.assertIn("Backend / API", body)

    def test_multiple_memberships_do_not_duplicate_catalog_entries(self):
        data = copy.deepcopy(self.data)
        backend = {e["id"] for e in data["entries"] if "backend" in e["categories"]}
        review = {e["id"] for e in data["entries"] if "review" in e["categories"]}
        self.assertIn("oasdiff", backend & review)
        self.assertEqual(len({e["url"] for e in data["entries"]}), len(data["entries"]))

    def test_new_reference_changes_derived_counts_and_page(self):
        data = copy.deepcopy(self.data)
        extra = copy.deepcopy(data["entries"][0])
        extra.update(id="local-demo", name="Local Demo", url="https://github.com/example/demo",
                     categories=["backend", "testing"])
        data["entries"].append(extra)
        refreshed = renderer.expected(self.original, data)
        self.assertIn(str(len(data["entries"])) + " unique sources", refreshed)
        self.assertIn(str(sum(group["id"] in item["categories"]
            for group in data["categories"] if group["id"] != "inbox"
            for item in data["entries"])) + " category placements", refreshed)
        self.assertIn("Local Demo", refreshed)
        self.assertEqual(refreshed.count("Local Demo"), 2)
        self.assertIn("Find exactly what you need", refreshed)

    def test_unverified_inbox_is_displayed_with_warning_not_fake_license(self):
        data = copy.deepcopy(self.data)
        extra = copy.deepcopy(data["entries"][0])
        extra.update(id="unknown-demo", name="Unverified Bookmark",
                     url="https://github.com/example/unreviewed", license="unknown",
                     license_source=None, status="unverified-reference", categories=["inbox"])
        data["entries"].append(extra)
        rendered = renderer.render(data)
        self.assertIn("### Inbox / To Review", rendered)
        self.assertIn("**not yet verified**", rendered)
        self.assertIn("Unverified Bookmark", rendered)
        self.assertIn("| Unverified |", rendered)

    def test_markdown_and_html_from_display_metadata_cannot_inject_tags(self):
        data = copy.deepcopy(self.data)
        data["entries"][0]["summary"] = "<script>alert(1)</script> | untrusted [text]"
        rendered = renderer.render(data)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn(r"\|", rendered)
        self.assertIn(r"\[text\]", rendered)
        self.assertEqual(
            renderer.safe_link("https://github.com/example/tool(a)"),
            "https://github.com/example/tool%28a%29"
        )

    def test_refuses_unsafe_license_urls_even_if_entry_was_marked_reviewed(self):
        data = copy.deepcopy(self.data)
        data["entries"][0]["license_source"] = "javascript:alert(1)"
        with self.assertRaises(renderer.LibraryError):
            renderer.render(data)

    def test_check_never_writes_and_write_requires_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            page = Path(temp) / "library.md"
            page.write_text(self.original, encoding="utf-8")
            with patch.object(renderer, "PAGE", page):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(renderer.main(["--check"]), 0)
                self.assertEqual(page.read_text(encoding="utf-8"), self.original)
                page.write_text(self.original.replace(str(len(self.data["entries"])) + " unique sources", "0 unique sources"),
                                encoding="utf-8")
                changed = page.read_bytes()
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(renderer.main(["--check"]), 1)
                self.assertEqual(page.read_bytes(), changed)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(renderer.main(["--write"]), 0)
                self.assertEqual(page.read_text(encoding="utf-8"), self.original)

    def test_svg_never_embeds_a_stale_fixed_number_of_sources(self):
        svg = (ROOT / "assets" / "library-map.svg").read_text(encoding="utf-8")
        self.assertIn("FIVE AREAS / REFERENCE INDEX", svg)
        self.assertNotIn("NINE SOURCES", svg)
        self.assertEqual(
            len([x for x in self.data["categories"] if x["id"] != "inbox"]), 5)


if __name__ == "__main__":
    unittest.main()
