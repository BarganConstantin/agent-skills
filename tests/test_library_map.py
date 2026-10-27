"""Keep the categorized README map accessible, finite and in sync with the catalog."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "skills" / "reference-library" / "references" / "catalog.json"
MAP = ROOT / "assets" / "library-map.svg"
PAGE = ROOT / "docs" / "library.md"


class LibraryMapTests(unittest.TestCase):
    def test_svg_is_accessible_and_static_content_contains_every_area(self):
        root = ET.fromstring(MAP.read_text(encoding="utf-8"))
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.get("viewBox"), "0 0 1280 296")
        self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}title"))
        self.assertIsNotNone(root.find("{http://www.w3.org/2000/svg}desc"))
        text = MAP.read_text(encoding="utf-8")
        for word in ("UI / UX", "Backend", "Code Review", "Testing / QA", "Workflows"):
            self.assertIn(word, text)
        self.assertIn("FIVE AREAS / REFERENCE INDEX", text)

    def test_animation_is_optional_finite_and_without_remote_loading(self):
        root = ET.fromstring(MAP.read_text(encoding="utf-8"))
        elements = root.findall(".//{http://www.w3.org/2000/svg}animate")
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].get("repeatCount"), "2")
        self.assertEqual(elements[0].get("dur"), "10s")
        svg = MAP.read_text(encoding="utf-8").lower()
        for banned in ("<script", "javascript:", "href=", "<foreignobject", "<iframe", "data:image"):
            self.assertNotIn(banned, svg)
        self.assertLess(MAP.stat().st_size, 10000)

    def test_visible_category_counts_reflect_canonical_catalog(self):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        counted = sum(x["id"] != "inbox" for x in data["categories"])
        self.assertEqual(counted, 5)
        self.assertEqual(len(data["entries"]), 9)
        for group in data["categories"]:
            if group["id"] == "inbox":
                continue
            self.assertGreater(sum(group["id"] in row["categories"]
                                   for row in data["entries"]), 0)
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("../assets/library-map.svg", page)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/library.md", readme)
        self.assertIn("assets/library-map.svg", readme)


if __name__ == "__main__":
    unittest.main()
