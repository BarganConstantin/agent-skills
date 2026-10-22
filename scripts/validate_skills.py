#!/usr/bin/env python3
"""Validate Agent Skills metadata using the public specification."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently accepting the last value."""


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ValueError("metadata keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def validate(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)(.*)\Z", content, re.S)
    if not match:
        return [f"{path}: missing YAML frontmatter"]
    try:
        fields = yaml.load(match[1], Loader=UniqueKeyLoader)
    except (yaml.YAMLError, ValueError) as exc:
        return [f"{path}: invalid YAML: {exc}"]
    if not isinstance(fields, dict):
        return [f"{path}: frontmatter must be a mapping"]
    errors = []
    def error(message):
        errors.append(f"{path}: {message}")
    name, desc = fields.get("name"), fields.get("description")
    if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        error("invalid name")
    if name != path.parent.name:
        error("skill folder and name differ")
    if not isinstance(desc, str) or not desc.strip() or len(desc) > 1024:
        error("invalid description")
    for key, limit in (("compatibility", 500), ("license", None), ("allowed-tools", None)):
        if key in fields:
            value = fields[key]
            if not isinstance(value, str) or not value.strip() or (limit and len(value) > limit):
                error(f"invalid {key}")
    if "metadata" in fields:
        metadata = fields["metadata"]
        if not isinstance(metadata, dict) or any(not isinstance(v, str) for v in metadata.values()):
            error("metadata must map string keys to string values")
    if not match[2].strip():
        error("missing instructions")
    return errors


def main() -> int:
    files = sorted(SKILLS.glob("*/SKILL.md"))
    if not files:
        print("No skills found")
        return 1
    errors = [error for path in files for error in validate(path)]
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Validated {len(files)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
