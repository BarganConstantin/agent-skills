"""GitHub README hero is self-contained, accessible, and safe to render as an image."""
from pathlib import Path
import re
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "assets" / "readme-hero.svg"
NS = {"s": "http://www.w3.org/2000/svg"}


class ReadmeHeroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HERO.read_text(encoding="utf-8")
        cls.root = ET.fromstring(cls.source)

    def test_svg_is_a_portable_sized_and_annotated_image(self):
        self.assertEqual(self.root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(self.root.get("viewBox"), "0 0 1360 520")
        title = self.root.find("s:title", NS)
        desc = self.root.find("s:desc", NS)
        self.assertTrue(title is not None and title.text)
        self.assertTrue(desc is not None and desc.text)
        self.assertIn("evidence", title.text.lower())

    def test_content_is_grounded_and_no_fake_statistics(self):
        for name in ("First User Audit", "Handoff with Receipts",
                     "API Contract Drift", "Reference Library"):
            self.assertIn(name, self.source)
        self.assertNotIn("1000+", self.source)
        self.assertNotIn("downloads", self.source.lower())

    def test_no_remote_content_or_active_scripting(self):
        lower = self.source.lower()
        for forbidden in ("<script", "<foreignobject", "http://www.w3.org/1999/xhtml",
                          "<iframe", "@import", "javascript:", "<style", "data:image"):
            self.assertNotIn(forbidden, lower)
        self.assertNotIn("href=", lower)
        self.assertNotIn("filter=", lower)
        self.assertLess(len(self.source.encode("utf-8")), 14000)

    def test_animation_is_nonessential_and_slow(self):
        animations = self.root.findall(".//s:animate", NS)
        self.assertGreaterEqual(len(animations), 1)
        for item in animations:
            duration = item.get("dur", "")
            self.assertTrue(duration.endswith("s"), duration)
            self.assertGreaterEqual(float(duration[:-1]), 7.0)
            self.assertIn(item.get("attributeName"), ("opacity", "cy"))
            self.assertEqual(item.get("repeatCount"), "2", "Decorative motion must settle instead of looping forever")
        self.assertIn("READY WHEN YOU ARE", self.source)


if __name__ == "__main__":
    unittest.main()
