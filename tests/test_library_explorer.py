"""The offline interactive explorer must be self-contained, safe and in sync."""
import copy
import importlib.util
from html.parser import HTMLParser
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "render_library.py"
spec = importlib.util.spec_from_file_location("render_library_browser", SOURCE)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class ElementInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []
    def handle_starttag(self, tag, attributes):
        self.found.append((tag, dict(attributes)))


class OfflineExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = renderer.load(renderer.CATALOG)
        cls.template = renderer.TEMPLATE.read_text(encoding="utf-8")
        cls.published = renderer.EXPLORER.read_text(encoding="utf-8")

    def test_published_explorer_is_generated_from_exact_catalog(self):
        self.assertEqual(
            self.published, renderer.render_explorer(self.data, self.template))
        self.assertNotIn(renderer.DATA_MARKER, self.published)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(renderer.main(["--check"]), 0)

    def test_entire_catalog_is_embedded_for_truly_offline_search(self):
        html = self.published
        self.assertEqual(html.count('id="library-data"'), 1)
        begin = '<script id="library-data" type="application/json">'
        serialized = html.split(begin, 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(serialized), self.data)
        self.assertEqual(len(self.data["entries"]), 10)
        self.assertTrue(all(x["url"] in html for x in self.data["entries"]))

    def test_page_is_usable_and_accessible_with_keyboard_controls(self):
        page = ElementInspector()
        page.feed(self.published)
        ids = {attrs.get("id") for _, attrs in page.found}
        for required in ("library-data", "filters", "search", "clear", "status",
                         "cards", "empty", "total"):
            self.assertIn(required, ids)
        search_inputs = [attrs for tag, attrs in page.found if tag == "input"
                         and attrs.get("id") == "search"]
        self.assertEqual(search_inputs[0].get("type"), "search")
        self.assertIn('aria-live="polite"', self.published)
        self.assertIn('aria-pressed', self.template)
        self.assertIn("prefers-reduced-motion: reduce", self.template)
        self.assertIn("event.key === \"/\"", self.template)
        self.assertIn('replaceChildren()', self.template)
        self.assertIn(".textContent =", self.template)
        self.assertNotIn("innerHTML", self.template)

    def test_no_runtime_fetch_or_external_script_dependencies(self):
        self.assertIn("connect-src 'none'", self.template)
        self.assertIn("default-src 'none'", self.template)
        self.assertIn("base-uri 'none'", self.template)
        self.assertIn("object-src 'none'", self.template)
        self.assertNotIn("<script src=", self.template)
        self.assertNotIn("<link rel=\"stylesheet\"", self.template)
        for forbidden in ("fetch(", "XMLHttpRequest(", "localStorage", "sessionStorage",
                          "document.cookie", "eval(", "new Function("):
            self.assertNotIn(forbidden, self.template)

    def test_user_content_cannot_break_out_of_embedded_data_script(self):
        data = copy.deepcopy(self.data)
        data["entries"][0]["summary"] = '</script><img src=x onerror=alert("oops")> &'
        output = renderer.render_explorer(data, self.template)
        self.assertEqual(output.count("</script>"), 2)  # one JSON data tag, one app code
        self.assertNotIn("</script><img", output)
        self.assertIn(r"\u003c/script\u003e", output)
        begin = '<script id="library-data" type="application/json">'
        payload = output.split(begin, 1)[1].split("</script>", 1)[0]
        self.assertEqual(json.loads(payload)["entries"][0]["summary"],
                         data["entries"][0]["summary"])

    def test_check_does_not_mutate_html_and_write_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "explorer.html"
            stale = self.published.replace("Good ideas deserve", "Old obsolete copy")
            file.write_text(stale, encoding="utf-8")
            with patch.object(renderer, "EXPLORER", file):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(renderer.main(["--check"]), 1)
                self.assertEqual(file.read_text(encoding="utf-8"), stale)
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(renderer.main(["--write"]), 0)
                self.assertEqual(file.read_text(encoding="utf-8"), self.published)

    def test_catalog_change_is_reflected_without_hand_editing_the_template(self):
        data = copy.deepcopy(self.data)
        addition = copy.deepcopy(data["entries"][0])
        addition["id"] = "local-synthetic-demo"
        addition["name"] = "Synthetic local example"
        addition["url"] = "https://github.com/example/synthetic"
        addition["categories"] = ["backend", "testing"]
        data["entries"].append(addition)
        result = renderer.render_explorer(data, self.template)
        start = '<script id="library-data" type="application/json">'
        payload = json.loads(result.split(start, 1)[1].split("</script>", 1)[0])
        self.assertEqual(len(payload["entries"]), len(self.data["entries"]) + 1)
        self.assertEqual(payload["entries"][-1]["name"], "Synthetic local example")

    def test_duplicate_marker_is_refused(self):
        with self.assertRaises(renderer.LibraryError):
            renderer.render_explorer(self.data, self.template.replace(
                renderer.DATA_MARKER,
                renderer.DATA_MARKER + renderer.DATA_MARKER))


if __name__ == "__main__":
    unittest.main()
