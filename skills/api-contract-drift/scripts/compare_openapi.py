#!/usr/bin/env python3
"""Conservative offline OpenAPI 3 JSON risk triage, not proof of compatibility."""
import argparse
import json
import sys
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")


def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not str(value.get("openapi", "")).startswith("3.") or not isinstance(value.get("paths"), dict):
        raise ValueError("Expected OpenAPI 3.x JSON document with paths object")
    return value


def resolve(doc, obj, label, warnings):
    seen = set()
    for _ in range(15):
        if not isinstance(obj, dict):
            warnings.add(label + ": unsupported or absent object")
            return None
        if "$ref" not in obj:
            return obj
        ref = obj["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            warnings.add(label + ": external, cyclic, or invalid reference")
            return None
        seen.add(ref)
        ptr = doc
        for chunk in ref[2:].split("/"):
            key = chunk.replace("~1", "/").replace("~0", "~")
            if not isinstance(ptr, dict) or key not in ptr:
                warnings.add(label + ": unresolved local reference")
                return None
            ptr = ptr[key]
        obj = ptr
    warnings.add(label + ": references too deeply nested")
    return None


def parameters(doc, path_item, operation, label, warnings):
    merged = {}
    for source in (path_item.get("parameters", []), operation.get("parameters", [])):
        if not isinstance(source, list):
            warnings.add(label + ": unsupported parameter collection")
            continue
        for param in source:
            entry = resolve(doc, param, label + " parameter", warnings)
            if entry and isinstance(entry.get("name"), str) and isinstance(entry.get("in"), str):
                merged[(entry["in"], entry["name"])] = entry
            else:
                warnings.add(label + ": parameter could not be compared")
    return merged


def body(doc, operation, label, warnings):
    value = operation.get("requestBody")
    return resolve(doc, value, label + " requestBody", warnings) if value is not None else None


def request_schema(doc, request, media, label, warnings):
    entry = request.get("content", {}).get(media, {})
    val = resolve(doc, entry.get("schema"), label + " request schema", warnings)
    if val and any(key in val for key in ("allOf", "anyOf", "oneOf", "not")):
        warnings.add(label + ": composed request schema needs manual review")
        return None
    return val


def compare(before, after):
    problems, warnings = [], set()

    def report(code, where, detail):
        problems.append({"code": code, "operation": where, "detail": detail, "classification": "potentially_breaking"})

    for path, old_path in sorted(before["paths"].items()):
        if not isinstance(old_path, dict):
            warnings.add(path + ": unsupported old path item")
            continue
        new_path = after["paths"].get(path, {})
        if not isinstance(new_path, dict):
            warnings.add(path + ": unsupported new path item")
            continue
        for method in METHODS:
            old = old_path.get(method)
            if not isinstance(old, dict):
                continue
            where = method.upper() + " " + path
            new = new_path.get(method)
            if not isinstance(new, dict):
                report("operation_removed", where, "Previously available operation removed")
                continue
            old_params = parameters(before, old_path, old, where, warnings)
            new_params = parameters(after, new_path, new, where, warnings)
            for key, entry in sorted(new_params.items()):
                if entry.get("required") is True and (
                    key not in old_params or old_params[key].get("required") is not True
                ):
                    report("required_parameter", where, "Newly required " + key[0] + " parameter " + key[1])

            old_body = body(before, old, where, warnings)
            new_body = body(after, new, where, warnings)
            if new_body and new_body.get("required") is True and (not old_body or old_body.get("required") is not True):
                report("required_body", where, "Request body newly required")
            if old_body and new_body:
                old_content = old_body.get("content", {})
                new_content = new_body.get("content", {})
                if not isinstance(old_content, dict) or not isinstance(new_content, dict):
                    warnings.add(where + ": unsupported request content")
                else:
                    for media in sorted(set(old_content) - set(new_content)):
                        report("request_media_removed", where, "Previously accepted request content removed: " + media)
                    for media in sorted(set(old_content) & set(new_content)):
                        a = request_schema(before, old_body, media, where, warnings)
                        b = request_schema(after, new_body, media, where, warnings)
                        if not a or not b:
                            warnings.add(where + ": request schema " + media + " not fully compared")
                            continue
                        past = a.get("required", [])
                        current = b.get("required", [])
                        if not isinstance(past, list) or not isinstance(current, list):
                            warnings.add(where + ": invalid required property declaration")
                            continue
                        for name in sorted(set(current) - set(past)):
                            report("required_property", where, "Newly required " + media + " body property " + str(name))

            old_resp = old.get("responses", {})
            new_resp = new.get("responses", {})
            if not isinstance(old_resp, dict) or not isinstance(new_resp, dict):
                warnings.add(where + ": unsupported response map")
                continue
            for status in sorted(set(old_resp) - set(new_resp)):
                report("response_status_removed", where, "Previously documented response status removed: " + str(status))
            for status in sorted(set(old_resp) & set(new_resp)):
                a = resolve(before, old_resp[status], where + " response " + status, warnings)
                b = resolve(after, new_resp[status], where + " response " + status, warnings)
                if a and b and isinstance(a.get("content", {}), dict) and isinstance(b.get("content", {}), dict):
                    for media in sorted(set(a.get("content", {})) - set(b.get("content", {}))):
                        report("response_media_removed", where, "Response " + status + " media removed: " + media)

    return {
        "schema_version": 1,
        "result": "manual_review_required" if problems or warnings else "no_checked_regressions_found",
        "potential_breaks": problems,
        "warnings": sorted(warnings),
        "disclaimer": "Limited OpenAPI 3 JSON triage, not exhaustive. Does not check all types, security, enums, nested/composed schemas, runtime behavior, or external refs. Zero findings DOES NOT prove compatibility.",
    }


def as_markdown(result):
    lines = [
        "# API Contract Drift", "",
        "Potential client breaks: " + str(len(result["potential_breaks"])) +
        "; coverage warnings: " + str(len(result["warnings"])), ""
    ]
    for item in result["potential_breaks"]:
        lines.append("- " + item["code"] + " at " + item["operation"] + ": " + item["detail"])
    if result["warnings"]:
        lines.append("")
        lines.append("## Requires manual review")
        lines.extend("- " + warning for warning in result["warnings"])
    lines.extend(["", result["disclaimer"]])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare limited OpenAPI 3 JSON client compatibility risks")
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--fail-on-risk", action="store_true", help="Exit 1 only when a potential break is detected")
    args = parser.parse_args(argv)
    try:
        result = compare(load(args.before), load(args.after))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print("Could not compare OpenAPI JSON files: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.format == "json" else as_markdown(result))
    return 1 if args.fail_on_risk and result["potential_breaks"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
