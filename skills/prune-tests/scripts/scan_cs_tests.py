#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import defaultdict

TEST_ATTRIBUTE = re.compile(r"\[\s*(Fact|Theory|Test|TestCase|TestCaseSource|TestMethod|DataTestMethod)\b")
SKIP_ATTRIBUTE = re.compile(
    r"\[\s*(?:Fact|Theory|Test|TestCase|TestMethod|DataTestMethod)\s*"
    r"\([^\]]*\b(?:Skip|Ignore)\s*=|\[\s*Ignore\b"
)
ASSERTION = re.compile(
    r"\b(Assert|Verify|Expect|Check|Ensure)\w*\s*[.(<]"
    r"|\.Should\w*\s*\("
    r"|\bShould\w*\."
    r"|\.Received\w*\s*\("
    r"|MustHaveHappened|MustNotHaveHappened"
    r"|\.Throw\w*\s*[(<]"
)
CONSTANT_ASSERTION = re.compile(
    r"Assert\.(?:True\s*\(\s*true\s*\)|False\s*\(\s*false\s*\)"
    r"|(?:Equal|Same|StrictEqual)\s*\(\s*([^\s,()][^,()]*?)\s*,\s*\1\s*\))"
)
MOQ_SETUP = re.compile(r"\.Setup\w*\s*\(\s*\w+\s*=>\s*\w+\.(\w+)")
MOQ_VERIFY = re.compile(r"\.Verify\w*\s*\(\s*\w+\s*=>\s*\w+\.(\w+)")
NSUBSTITUTE_RETURNS = re.compile(r"\b\w+\.(\w+)\s*\([^;]*?\)\s*\.Returns\w*\s*\(")
NSUBSTITUTE_RECEIVED = re.compile(r"\.Received\s*\(\s*\d*\s*\)\s*\.(\w+)")
RAW_STRING_START = re.compile(r'\$*("{3,})')
RAW_STRING = re.compile(r'(\$*)("{3,})(.*?)\2', re.DOTALL)
PLAIN_STRING = re.compile(r'(\$@|@\$|\$|@)?"((?:[^"\\]|\\.|"")*)"')
RAW_HOLE = re.compile(r"(?<!\{)\{+([^{}]+)\}+")
PLAIN_HOLE = re.compile(r"(?<!\{)\{(?!\{)([^{}]+)\}")
DATA_ROW = re.compile(r"\[\s*(?:InlineData|TestCase|DataRow|MemberData|ClassData|TestCaseSource)\b")
MEMBER_DATA = re.compile(r"\[\s*MemberData\s*\(\s*(?:nameof\s*\(\s*(?:\w+\s*\.\s*)*(\w+)\s*\)|\"(\w+)\")")
INITIALIZER = re.compile(r"\bnew\b[^;{]*\{")
LOOP = re.compile(r"\b(?:for|foreach|while)\b")
CHAR_LITERAL = re.compile(r"'(?:[^'\\]|\\.)'")
NUMBER_LITERAL = re.compile(r"\b\d[\d_]*(?:\.\d+)?[mMdDfFlLuU]?\b")
BOOLEAN_LITERAL = re.compile(r"\b(?:true|false)\b")
NAME_BEFORE_PARAMETERS = re.compile(r"(\w+)\s*(?:<[^>]*>)?\s*\($")
CALLED_NAME = re.compile(r"\b([A-Z_]\w*)\s*(?:<[^>]*>)?\s*\(")
HELPER_DEPTH = 3


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deterministic pre-scan of C# test methods: tests without assertions, constant assertions, "
        "identical tests, tests with the same code but different data, and stub-then-verify of the same member. "
        "Every result is a candidate for a reviewer, never a verdict."
    )
    parser.add_argument("scope", help="a test file or a folder")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    output.add_argument("--list", action="store_true", help="print only the inventory: file:line, method, data rows")
    output.add_argument(
        "--folders",
        action="store_true",
        help="print one row per subfolder: tests, tests flagged by the pre-scan, and that share (to pick a probe)",
    )
    return parser.parse_args()


def blank(fragment):
    return re.sub(r"[^\n]", " ", fragment)


def code_mask(text, mask_strings=True):
    def literal(fragment):
        return blank(fragment) if mask_strings else fragment

    masked = []
    i, length = 0, len(text)
    while i < length:
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = length if end == -1 else end
            masked.append(blank(text[i:end]))
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = length if end == -1 else end + 2
            masked.append(blank(text[i:end]))
            i = end
        elif raw := RAW_STRING_START.match(text, i):
            quotes = raw.group(1)
            end = text.find(quotes, raw.end())
            end = length if end == -1 else end + len(quotes)
            masked.append(literal(text[i:end]))
            i = end
        elif text[i] == '"' or (text[i] in "$@" and text.startswith('"', i + 1)) or text.startswith(('$@"', '@$"'), i):
            end = string_end(text, i)
            masked.append(literal(text[i:end]))
            i = end
        elif text[i] == "'" and i + 2 < length:
            match = CHAR_LITERAL.match(text, i)
            end = match.end() if match else i + 1
            masked.append(literal(text[i:end]))
            i = end
        else:
            masked.append(text[i])
            i += 1
    return "".join(masked)


def string_end(text, start):
    quote = text.index('"', start)
    verbatim = "@" in text[start:quote]
    i = quote + 1
    while i < len(text):
        if verbatim and text.startswith('""', i):
            i += 2
        elif not verbatim and text[i] == "\\":
            i += 2
        elif text[i] == '"':
            return i + 1
        else:
            i += 1
    return len(text)


def skip_attributes(masked, position):
    while True:
        while position < len(masked) and masked[position].isspace():
            position += 1
        if position >= len(masked) or masked[position] != "[":
            return position
        depth = 0
        while position < len(masked):
            if masked[position] == "[":
                depth += 1
            elif masked[position] == "]":
                depth -= 1
                if depth == 0:
                    position += 1
                    break
            position += 1


def method_at(masked, attribute_start):
    header_start = skip_attributes(masked, attribute_start)
    depth = 0
    position = header_start
    name = None
    while position < len(masked):
        char = masked[position]
        if char == "(":
            if depth == 0 and name is None:
                found = NAME_BEFORE_PARAMETERS.search(masked[header_start:position + 1])
                name = found.group(1) if found else None
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and char == "{":
            return header_start, name, position, matching_brace(masked, position)
        elif depth == 0 and masked.startswith("=>", position):
            end = masked.find(";", position)
            return header_start, name, position, (len(masked) if end == -1 else end + 1)
        elif depth == 0 and char == ";":
            return None
        position += 1
    return None


def matching_brace(masked, open_position):
    depth = 0
    for position in range(open_position, len(masked)):
        if masked[position] == "{":
            depth += 1
        elif masked[position] == "}":
            depth -= 1
            if depth == 0:
                return position + 1
    return len(masked)


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


class HelperIndex:
    def __init__(self, masked_sources):
        self.source = "\n;\n".join(masked_sources)
        self.cache = {}

    def asserts(self, body, depth=HELPER_DEPTH):
        if ASSERTION.search(body):
            return True
        if depth == 0:
            return False
        return any(self.helper_asserts(name, depth) for name in set(CALLED_NAME.findall(body)))

    def helper_asserts(self, name, depth):
        key = (name, depth)
        if key in self.cache:
            return self.cache[key]
        self.cache[key] = False
        definition = re.compile(rf"(?m)^[ \t]*(?:[\w<>\[\],.?]+[ \t]+)+{re.escape(name)}[ \t]*(?:<[^>]*>)?[ \t]*\(")
        for match in definition.finditer(self.source):
            method = method_at(self.source, match.start())
            if method and self.asserts(self.source[method[2]:method[3]], depth - 1):
                self.cache[key] = True
                break
        return self.cache[key]


def tests_in_file(path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    masked = code_mask(text)
    without_comments = code_mask(text, mask_strings=False)
    seen_headers = set()
    tests = []
    for attribute in TEST_ATTRIBUTE.finditer(masked):
        attributes_start = masked.rfind("\n", 0, attribute.start()) + 1
        method = method_at(masked, attributes_start)
        if not method:
            continue
        header_start, name, body_start, body_end = method
        if header_start in seen_headers or not name:
            continue
        seen_headers.add(header_start)
        attributes_text = masked[attributes_start:header_start]
        tests.append({
            "file": str(path),
            "line": line_of(text, header_start),
            "name": name,
            "skipped": bool(SKIP_ATTRIBUTE.search(attributes_text)),
            "data_rows": data_rows(masked, without_comments, attributes_start, header_start),
            "row_count": row_count(masked, without_comments, attributes_start, header_start),
            "signature": re.sub(rf"\b{re.escape(name)}\b", "M", without_comments[header_start:body_start], count=1),
            "body": without_comments[body_start:body_end],
            "masked_body": masked[body_start:body_end],
        })
    return tests, masked


def data_rows(masked, without_comments, start, end):
    rows = []
    position = start
    while (position := masked.find("[", position, end)) != -1:
        close = attribute_end(masked, position)
        if DATA_ROW.match(masked, position):
            rows.append(collapse(without_comments[position:close]))
        position = close
    return rows


def row_count(masked, without_comments, start, end):
    count, exact = 0, True
    position = start
    while (position := masked.find("[", position, end)) != -1:
        close = attribute_end(masked, position)
        if DATA_ROW.match(masked, position):
            member = MEMBER_DATA.match(without_comments, position)
            rows = member_row_count(masked, without_comments, member.group(1) or member.group(2)) if member else None
            if member is None and not masked.startswith(("[ClassData", "[TestCaseSource"), position):
                rows = 1
            count += rows if rows is not None else 1
            exact = exact and rows is not None
        position = close
    return count, exact


def member_row_count(masked, plain, name):
    definition = re.compile(rf"\b{re.escape(name)}\s*(?:\(\s*\))?\s*(=>|=(?!=)|\{{)")
    for match in definition.finditer(masked):
        region_start, region_end = member_region(masked, match)
        region = masked[region_start:region_end]
        if "yield return" in region:
            return None if LOOP.search(region) else region.count("yield return")
        initializer = INITIALIZER.search(masked, region_start, region_end)
        if initializer:
            return top_level_elements(masked, plain, initializer.end() - 1)
    return None


def member_region(masked, match):
    if match.group(1) == "{":
        return match.end() - 1, matching_brace(masked, match.end() - 1)
    depth = 0
    for position in range(match.end(), len(masked)):
        char = masked[position]
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth -= 1
        elif char == ";" and depth == 0:
            return match.end(), position
    return match.end(), len(masked)


def top_level_elements(masked, plain, open_brace):
    depth = 0
    commas = 0
    last_separator = open_brace
    for position in range(open_brace + 1, len(masked)):
        char = masked[position]
        if char in "({[":
            depth += 1
        elif char in ")}]":
            if depth == 0:
                trailing = plain[last_separator + 1:position].strip()
                return commas + (1 if trailing else 0)
            depth -= 1
        elif char == "," and depth == 0:
            commas += 1
            last_separator = position
    return None


def attribute_end(masked, open_position):
    depth = 0
    for position in range(open_position, len(masked)):
        if masked[position] == "[":
            depth += 1
        elif masked[position] == "]":
            depth -= 1
            if depth == 0:
                return position + 1
    return len(masked)


def collapse(text):
    return " ".join(text.split())


def exact_shape(test):
    return collapse(" ".join(test["data_rows"]) + " " + test["signature"] + " " + test["body"])


def data_shape(test):
    code = collapse(test["signature"] + " " + test["body"])
    code = RAW_STRING.sub(lambda m: string_placeholder(m.group(1), m.group(3), RAW_HOLE), code)
    code = PLAIN_STRING.sub(lambda m: string_placeholder(m.group(1), m.group(2), PLAIN_HOLE), code)
    for pattern, placeholder in ((CHAR_LITERAL, "'C'"), (NUMBER_LITERAL, "0"), (BOOLEAN_LITERAL, "B")):
        code = pattern.sub(placeholder, code)
    return code


def string_placeholder(prefix, content, hole_pattern):
    if "$" not in (prefix or ""):
        return '"S"'
    return '"S' + "".join("{" + collapse(hole) + "}" for hole in hole_pattern.findall(content)) + '"'


def digest(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def groups_by(tests, shape):
    groups = defaultdict(list)
    for test in tests:
        groups[digest(shape(test))].append(test)
    return [group for group in groups.values() if len(group) > 1]


def stub_then_verify(test):
    body = test["masked_body"]
    moq = set(MOQ_SETUP.findall(body)) & set(MOQ_VERIFY.findall(body))
    nsubstitute = set(NSUBSTITUTE_RETURNS.findall(body)) & set(NSUBSTITUTE_RECEIVED.findall(body))
    return sorted(moq | nsubstitute)


def scan(scope):
    root = pathlib.Path(scope)
    files = [root] if root.is_file() else sorted(p for p in root.rglob("*.cs") if not {"bin", "obj"} & set(p.parts))
    parsed = [tests_in_file(path) for path in files]
    tests = [test for file_tests, _ in parsed for test in file_tests]
    # Same-named helpers in unrelated files must not mask missing assertions.
    helpers_by_file = {str(path): HelperIndex([masked]) for path, (_, masked) in zip(files, parsed)}
    active = [test for test in tests if not test["skipped"]]
    exact_groups = groups_by(active, exact_shape)
    exact_members = {id(test) for group in exact_groups for test in group}
    data_groups = [
        group for group in groups_by(active, data_shape)
        if not all(id(test) in exact_members for test in group)
    ]
    return {
        "tests": len(tests),
        "files": len({test["file"] for test in tests}),
        "inventory": [dict(where(t), rows=t["row_count"][0], rows_exact=t["row_count"][1]) for t in tests],
        "skipped": [where(t) for t in tests if t["skipped"]],
        "no_assertion": [where(t) for t in active if not helpers_by_file[t["file"]].asserts(t["masked_body"])],
        "constant_assertion": [where(t) for t in active if CONSTANT_ASSERTION.search(t["masked_body"])],
        "identical_tests": [[where(t) for t in group] for group in exact_groups],
        "same_code_different_data": [[where(t) for t in group] for group in data_groups],
        "stub_then_verify": [dict(where(t), members=m) for t in active if (m := stub_then_verify(t))],
    }


def where(test):
    return {"test": f"{test['file']}:{test['line']} {test['name']}"}


def print_markdown(result):
    print("# Pre-scan\n")
    print(f"{result['tests']} test methods in {result['files']} files. Candidates for the reviewers, not verdicts.\n")
    sections = [
        ("Skipped (report, never prune)", result["skipped"]),
        ("No assertion found (a helper or a throw may still be the oracle)", result["no_assertion"]),
        ("Constant assertion", result["constant_assertion"]),
        ("Stub and verify the same member", result["stub_then_verify"]),
    ]
    for title, rows in sections:
        print(f"## {title} ({len(rows)})\n")
        for row in rows:
            members = f" — {', '.join(row['members'])}" if "members" in row else ""
            print(f"- `{row['test']}`{members}")
        print()
    for title, groups in (
        ("Identical tests (same data rows, parameters and body)", result["identical_tests"]),
        ("Same code, different data (merge only if they protect the same behaviour)", result["same_code_different_data"]),
    ):
        print(f"## {title} ({len(groups)} groups)\n")
        for number, group in enumerate(groups, 1):
            print(f"- G{number}: " + "; ".join(f"`{row['test']}`" for row in group))
        print()


ROOT_FILES = "(files in the scope root)"


def flagged_tests(result):
    rows = result["no_assertion"] + result["constant_assertion"] + result["stub_then_verify"]
    groups = result["identical_tests"] + result["same_code_different_data"]
    return {row["test"] for row in rows} | {row["test"] for group in groups for row in group}


def folder_of(test_reference, root):
    path = pathlib.Path(test_reference.rsplit(" ", 1)[0].rsplit(":", 1)[0])
    parts = path.relative_to(root).parts if root.is_dir() else ()
    return parts[0] if len(parts) > 1 else ROOT_FILES


def folder_summary(result, scope):
    root = pathlib.Path(scope)
    flagged = flagged_tests(result)
    folders = defaultdict(lambda: {"tests": 0, "flagged": 0})
    for row in result["inventory"]:
        folder = folders[folder_of(row["test"], root)]
        folder["tests"] += 1
        folder["flagged"] += row["test"] in flagged
    summary = [
        {"folder": name, "tests": f["tests"], "flagged": f["flagged"], "density": f["flagged"] / f["tests"]}
        for name, f in folders.items()
    ]
    return sorted(summary, key=lambda row: (-row["density"], -row["tests"], row["folder"]))


def print_folders(summary):
    print("| folder | tests | flagged by pre-scan | density |")
    print("|---|---|---|---|")
    for row in summary:
        print(f"| {row['folder']} | {row['tests']} | {row['flagged']} | {row['density']:.0%} |")
    total_tests = sum(row["tests"] for row in summary)
    total_flagged = sum(row["flagged"] for row in summary)
    density = total_flagged / total_tests if total_tests else 0
    print(f"| **total** | {total_tests} | {total_flagged} | {density:.0%} |")


def print_inventory(result):
    for row in result["inventory"]:
        plus = "" if row["rows_exact"] else "+"
        rows = f" ({row['rows']}{plus} data rows)" if row["rows"] else ""
        print(f"{row['test']}{rows}")
    total = sum(r["rows"] for r in result["inventory"])
    at_least = "" if all(r["rows_exact"] for r in result["inventory"]) else "at least "
    print(f"\n{result['tests']} test methods, {at_least}{total} data rows, {result['files']} files")
    if at_least:
        print("A + marks member data the scanner could not count (built in a loop, or defined in another file).")


def main():
    args = parse_args()
    if not pathlib.Path(args.scope).exists():
        print(f"Scope not found: {args.scope}", file=sys.stderr)
        return 2
    result = scan(args.scope)
    if args.list:
        print_inventory(result)
    elif args.folders:
        print_folders(folder_summary(result, args.scope))
    elif args.json:
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        print_markdown(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
