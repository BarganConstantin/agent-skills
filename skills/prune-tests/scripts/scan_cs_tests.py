#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict

TEST_NAME = r"(?:\w+\.)*(?:(?:[A-Z]\w*)?(?:Fact|Theory)|Test|TestCase|TestCaseSource|TestMethod|DataTestMethod)(?:Attribute)?"
TEST_ATTRIBUTE = re.compile(rf"\[(?:[^\[\]]*?[,\s])?\s*({TEST_NAME})\s*[\](,]")
SKIP_ATTRIBUTE = re.compile(
    rf"[\[,]\s*{TEST_NAME}\s*\([^\]]*\b(?:Skip|Ignore)\s*=|\[\s*Ignore\b"
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
MASK_CANDIDATE = re.compile(r"""[/"'$@#]""")
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
QUALIFIED_CALL = re.compile(r"\b(?:([A-Z]\w*)\s*\.\s*)?([A-Z_]\w*)\s*(?:<[^>]*>)?\s*\(")
TYPE_DECLARATION = re.compile(
    r"\b(partial\s+)?(?:class|record|struct|interface)\s+(\w+)(?:\s*<[^>{]*>)?(?:\s*\([^)]*\))?\s*(?::\s*([^{;]+))?"
)
WHERE_CLAUSE = re.compile(r"\bwhere\b")
HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")
METHOD_DEFINITION = re.compile(r"(?m)^[ \t]*(?:[\w<>\[\],.?]+[ \t]+)+(\w+)[ \t]*(?:<[^>]*>)?[ \t]*\(")
HELPER_DEPTH = 3


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deterministic pre-scan of C# test methods: tests without assertions, constant assertions, "
        "identical tests, tests with the same code but different data, and stub-then-verify of the same member. "
        "Every result is a candidate for a reviewer, never a verdict."
    )
    parser.add_argument("scope", nargs="+", help="test files or folders, for example the test files a branch changed")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    output.add_argument("--list", action="store_true", help="print only the inventory: file:line, method, data rows")
    output.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="print a systematic sample of the scope: every k-th test file by path, about N test methods in all",
    )
    output.add_argument(
        "--folders",
        action="store_true",
        help="print one row per subfolder: tests, tests flagged by the pre-scan, and that share (to pick a probe)",
    )
    parser.add_argument(
        "--changed",
        metavar="BASE",
        help="keep only the tests whose lines the current branch added or changed since BASE (git diff BASE...HEAD); "
        "the other tests of those files stay in the duplicate groups as context",
    )
    return parser.parse_args()


def blank(fragment):
    return re.sub(r"[^\n]", " ", fragment)


def code_mask(text, mask_strings=True, directives=None):
    def literal(fragment):
        return blank(fragment) if mask_strings else fragment

    masked = []
    i, length = 0, len(text)
    while i < length:
        special = MASK_CANDIDATE.search(text, i)
        if special is None:
            masked.append(text[i:])
            break
        if special.start() > i:
            masked.append(text[i:special.start()])
            i = special.start()
        if text.startswith("//", i) or starts_directive(text, i):
            if directives is not None and text[i] == "#":
                directives.append(i)
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


def starts_directive(text, i):
    return text[i] == "#" and not text[text.rfind("\n", 0, i) + 1:i].replace("\ufeff", "").strip()


def string_end(text, start):
    quote = text.index('"', start)
    verbatim = "@" in text[start:quote]
    interpolated = "$" in text[start:quote]
    i = quote + 1
    while i < len(text):
        if verbatim and text.startswith('""', i):
            i += 2
        elif not verbatim and text[i] == "\\":
            i += 2
        elif interpolated and text.startswith("{{", i):
            i += 2
        elif interpolated and text[i] == "{":
            i = hole_end(text, i + 1)
        elif text[i] == '"':
            return i + 1
        else:
            i += 1
    return len(text)


def hole_end(text, i):
    depth = 1
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
        elif text[i] == '"' or (text[i] in "$@" and text.startswith('"', i + 1)) or text.startswith(('$@"', '@$"'), i):
            i = string_end(text, i)
        elif text[i] == "'":
            match = CHAR_LITERAL.match(text, i)
            i = match.end() if match else i + 1
        else:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
            if depth == 0:
                return i
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
            return header_start, name, position, statement_end(masked, position)
        elif depth == 0 and char == ";":
            return None
        position += 1
    return None


def statement_end(masked, position):
    depth = 0
    for position in range(position, len(masked)):
        char = masked[position]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == ";" and depth == 0:
            return position + 1
    return len(masked)


def previous_code(masked, position):
    position -= 1
    while position >= 0 and masked[position].isspace():
        position -= 1
    return position


def starts_attribute_section(masked, position):
    previous = previous_code(masked, position)
    return previous < 0 or masked[previous] in "{};]"


def attribute_run_start(masked, position):
    start = position
    while (close := previous_code(masked, start)) >= 0 and masked[close] == "]":
        depth = 0
        for open_position in range(close, -1, -1):
            depth += {"]": 1, "[": -1}.get(masked[open_position], 0)
            if depth == 0:
                break
        else:
            return start
        start = open_position
    return start


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


def base_types(base_list):
    names = set()
    depth = 0
    part = []
    for char in WHERE_CLAUSE.split(base_list, maxsplit=1)[0] + ",":
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        elif char == "," and depth == 0:
            leading = re.match(r"\s*([\w.]+)", "".join(part))
            if leading:
                names.add(leading.group(1).rsplit(".", 1)[-1])
            part = []
            continue
        part.append(char)
    return names


class HelperIndex:
    def __init__(self, masked_by_file):
        self.masked_by_file = masked_by_file
        self.files_by_type = defaultdict(set)
        self.bases_by_file = defaultdict(set)
        self.partial_types_by_file = defaultdict(set)
        for path, masked in masked_by_file.items():
            for declaration in TYPE_DECLARATION.finditer(masked):
                partial, name, bases = declaration.groups()
                self.files_by_type[name].add(path)
                self.bases_by_file[path] |= base_types(bases or "")
                if partial:
                    self.partial_types_by_file[path].add(name)
        self.scopes = {}
        self.methods_by_file = {}
        self.cache = {}

    def scope_of(self, path):
        if path not in self.scopes:
            scope, pending = {path}, [path]
            while pending:
                current = pending.pop()
                for name in self.bases_by_file[current] | self.partial_types_by_file[current]:
                    for other in self.files_by_type.get(name, ()):
                        if other not in scope:
                            scope.add(other)
                            pending.append(other)
            self.scopes[path] = frozenset(scope)
        return self.scopes[path]

    def type_scope(self, type_name):
        return frozenset().union(*(self.scope_of(path) for path in self.files_by_type[type_name]))

    def asserts(self, body, path, depth=HELPER_DEPTH):
        if ASSERTION.search(body):
            return True
        if depth == 0:
            return False
        for qualifier, name in set(QUALIFIED_CALL.findall(body)):
            scope = self.type_scope(qualifier) if qualifier in self.files_by_type else self.scope_of(path)
            if self.helper_asserts(name, scope, depth):
                return True
        return False

    def helper_asserts(self, name, scope, depth):
        return any(self.defined_asserts(path, name, depth) for path in sorted(scope))

    def defined_asserts(self, path, name, depth):
        key = (path, name, depth)
        if key not in self.cache:
            self.cache[key] = False
            masked = self.masked_by_file[path]
            self.cache[key] = any(
                self.asserts(masked[start:end], path, depth - 1) for start, end in self.methods_in(path).get(name, ())
            )
        return self.cache[key]

    def methods_in(self, path):
        if path not in self.methods_by_file:
            masked = self.masked_by_file[path]
            methods = defaultdict(list)
            for definition in METHOD_DEFINITION.finditer(masked):
                method = method_at(masked, definition.start())
                if method and method[1] == definition.group(1):
                    methods[method[1]].append((method[2], method[3]))
            self.methods_by_file[path] = methods
        return self.methods_by_file[path]


def has_constant_assertion(test):
    return any(test["masked_body"][m.start()] != " " for m in CONSTANT_ASSERTION.finditer(test["body"]))


def test_methods(masked):
    seen_headers = set()
    for attribute in TEST_ATTRIBUTE.finditer(masked):
        if not starts_attribute_section(masked, attribute.start()):
            continue
        attributes_start = attribute_run_start(masked, attribute.start())
        method = method_at(masked, attributes_start)
        if not method:
            continue
        header_start, name, body_start, body_end = method
        if header_start in seen_headers or not name:
            continue
        seen_headers.add(header_start)
        yield attributes_start, header_start, name, body_start, body_end


def tests_in_file(path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    masked = code_mask(text)
    without_comments = code_mask(text, mask_strings=False)
    tests = []
    for attributes_start, header_start, name, body_start, body_end in test_methods(masked):
        attributes_text = masked[attributes_start:header_start]
        tests.append({
            "file": str(path),
            "line": line_of(text, header_start),
            "start_line": line_of(text, attributes_start),
            "end_line": line_of(text, body_end - 1),
            "name": name,
            "skipped": bool(SKIP_ATTRIBUTE.search(attributes_text)),
            "data_rows": data_rows(masked, without_comments, attributes_start, header_start),
            "row_count": row_count(masked, without_comments, attributes_start, header_start),
            "signature": anonymous_signature(without_comments[header_start:body_start], name),
            "body": without_comments[body_start:body_end],
            "masked_body": masked[body_start:body_end],
        })
    return tests, masked


def anonymous_signature(header, name):
    parameters = header.find("(")
    position = header.rfind(name, 0, parameters if parameters != -1 else len(header))
    return header if position == -1 else header[:position] + "M" + header[position + len(name):]


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


def files_in(scopes):
    found = set()
    for scope in [scopes] if isinstance(scopes, str) else scopes:
        root = pathlib.Path(scope)
        if root.is_file():
            found.add(root)
        else:
            found.update(p for p in root.rglob("*.cs") if not {"bin", "obj"} & set(p.parts))
    return sorted(found)


def git(*arguments):
    result = subprocess.run(["git", *arguments], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ValueError(f"git failed: {result.stderr.strip()}")
    return result.stdout


def added_lines(base, scopes):
    paths = [pathlib.Path(scope).resolve() for scope in scopes]
    folder = str(paths[0] if paths[0].is_dir() else paths[0].parent)
    root = pathlib.Path(git("-C", folder, "rev-parse", "--show-toplevel").strip())
    diff = git(
        "-C", folder, "-c", "core.quotePath=false", "diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames",
        "--diff-filter=AM", "--src-prefix=a/", "--dst-prefix=b/", f"{base}...HEAD", "--", *map(str, paths),
    )
    added = defaultdict(list)
    path = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            name = line[4:].strip().strip('"')
            path = str((root / name[2:]).resolve()) if name.startswith("b/") else None
        elif path and (hunk := HUNK.match(line)):
            start, count = int(hunk.group(1)), int(hunk.group(2) or "1")
            if count:
                added[path].append((start, start + count - 1))
    return dict(added)


def touches(test, ranges):
    return any(start <= test["end_line"] and end >= test["start_line"] for start, end in ranges)


def scan(scope, changed_since=None):
    files = files_in(scope)
    ranges = None
    if changed_since is not None:
        added = added_lines(changed_since, [scope] if isinstance(scope, str) else scope)
        ranges = {str(path): added[str(path.resolve())] for path in files if str(path.resolve()) in added}
        files = [path for path in files if str(path) in ranges]
    parsed = [tests_in_file(path) for path in files]
    every_test = [test for file_tests, _ in parsed for test in file_tests]
    tests = every_test if ranges is None else [t for t in every_test if touches(t, ranges[t["file"]])]
    in_scope = {id(test) for test in tests}
    helpers = HelperIndex({str(path): masked for path, (_, masked) in zip(files, parsed)})
    every_active = [test for test in every_test if not test["skipped"]]
    active = [test for test in every_active if id(test) in in_scope]
    exact_groups = groups_by(every_active, exact_shape)
    exact_members = {id(test) for group in exact_groups for test in group}
    data_groups = [
        group for group in groups_by(every_active, data_shape)
        if not all(id(test) in exact_members for test in group)
    ]

    def with_scope(groups):
        return [group for group in groups if any(id(test) in in_scope for test in group)]

    return {
        "tests": len(tests),
        "files": len({test["file"] for test in tests}),
        "changed_since": changed_since,
        "context_tests": len(every_test) - len(tests),
        "inventory": [dict(where(t), rows=t["row_count"][0], rows_exact=t["row_count"][1]) for t in tests],
        "skipped": [where(t) for t in tests if t["skipped"]],
        "no_assertion": [where(t) for t in active if not helpers.asserts(t["masked_body"], t["file"])],
        "constant_assertion": [where(t) for t in active if has_constant_assertion(t)],
        "identical_tests": [[where(t) for t in group] for group in with_scope(exact_groups)],
        "same_code_different_data": [[where(t) for t in group] for group in with_scope(data_groups)],
        "stub_then_verify": [dict(where(t), members=m) for t in active if (m := stub_then_verify(t))],
    }


def scope_line(result):
    if result["changed_since"] and not result["tests"]:
        return f"No test method was added or changed since {result['changed_since']}"
    line = f"{result['tests']} test methods"
    if result["changed_since"]:
        line += f" added or changed since {result['changed_since']}"
    line += f" in {result['files']} files"
    if result["changed_since"]:
        line += f"; the other {result['context_tests']} tests of those files are context, not scope"
    return line


def where(test):
    return {"test": f"{test['file']}:{test['line']} {test['name']}"}


def print_markdown(result):
    print("# Pre-scan\n")
    print(f"{scope_line(result)}. Candidates for the reviewers, not verdicts.\n")
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


def file_of(test_reference):
    return test_reference.rsplit(" ", 1)[0].rsplit(":", 1)[0]


def systematic_sample(result, target):
    tests_per_file = defaultdict(int)
    for row in result["inventory"]:
        tests_per_file[file_of(row["test"])] += 1
    files = sorted(tests_per_file)
    if not files or target < 1:
        return 1, []
    step = max(1, round(sum(tests_per_file.values()) / target))
    return step, [(path, tests_per_file[path]) for path in files[step // 2::step]]


def print_sample(result, target):
    step, sample = systematic_sample(result, target)
    total_files = len({file_of(row["test"]) for row in result["inventory"]})
    print(f"Systematic sample: 1 in every {step} of {total_files} test files, {len(sample)} files, "
          f"{sum(count for _, count in sample)} test methods (target {target}).\n")
    for path, count in sample:
        print(f"- `{path}` ({count} tests)")


def flagged_tests(result):
    rows = result["no_assertion"] + result["constant_assertion"] + result["stub_then_verify"]
    groups = result["identical_tests"] + result["same_code_different_data"]
    return {row["test"] for row in rows} | {row["test"] for group in groups for row in group}


def folder_of(test_reference, root):
    path = pathlib.Path(test_reference.rsplit(" ", 1)[0].rsplit(":", 1)[0])
    parts = path.relative_to(root).parts if root.is_dir() else ()
    return parts[0] if len(parts) > 1 else ROOT_FILES


def folder_summary(result, scope):
    scopes = [scope] if isinstance(scope, str) else scope
    root = pathlib.Path(scopes[0]) if len(scopes) == 1 else pathlib.Path(os.path.commonpath(scopes))
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
    print(f"\n{scope_line(result)}. Data rows: {at_least}{total}.")
    if at_least:
        print("A + marks member data the scanner could not count (built in a loop, or defined in another file).")


def main():
    args = parse_args()
    missing = [scope for scope in args.scope if not pathlib.Path(scope).exists()]
    if missing:
        print(f"Scope not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    try:
        result = scan(args.scope, args.changed)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    if args.list:
        print_inventory(result)
    elif args.sample is not None:
        print_sample(result, args.sample)
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
