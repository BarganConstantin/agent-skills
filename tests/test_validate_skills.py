"""Specification checks against temporary skill packages."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("validator", Path(__file__).resolve().parents[1] / "scripts/validate_skills.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidatorTests(unittest.TestCase):
    def check(self, front, body="Instructions."):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example-skill" / "SKILL.md"
            path.parent.mkdir()
            path.write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")
            return validator.validate(path)

    def test_valid_multiline_metadata(self):
        self.assertEqual(self.check('name: example-skill\ndescription: >\n  Audit a preview.\n  Use before launch.\nmetadata:\n  version: "0.1.0"'), [])

    def test_invalid_yaml_and_duplicates(self):
        for front in ('name: [broken', 'name: example-skill\nname: other\ndescription: Test', '- example-skill'):
            with self.subTest(front=front):
                self.assertTrue(self.check(front))

    def test_required_fields_and_types(self):
        for desc in ('', 'true', '[]', 'x' * 1025):
            with self.subTest(desc=desc):
                self.assertTrue(self.check(f'name: example-skill\ndescription: {desc}'))

    def test_names(self):
        for name in ('Example', '-example', 'example--skill', 'different', 'a' * 65):
            with self.subTest(name=name):
                self.assertTrue(self.check(f'name: {name}\ndescription: Test'))

    def test_optional_fields(self):
        for extra in ('compatibility: ' + 'x' * 501, 'metadata:\n  version: 1', 'license: []'):
            with self.subTest(extra=extra):
                self.assertTrue(self.check('name: example-skill\ndescription: Test\n' + extra))

    def test_requires_body(self):
        self.assertTrue(self.check('name: example-skill\ndescription: Test', ''))


if __name__ == '__main__':
    unittest.main()
