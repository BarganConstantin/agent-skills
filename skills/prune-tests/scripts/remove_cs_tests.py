#!/usr/bin/env python3
import argparse
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import scan_cs_tests as scanner  # noqa: E402

TARGET = re.compile(r"^\s*(\w+)\s*(?:\[\s*row\s+(\d{1,6})\s*\])?\s*$")
INLINE_ROW = re.compile(r"\[\s*(?:InlineData|TestCase|DataRow)\b")
ROW_FROM_MEMBER = re.compile(r"\b(?:MemberData|ClassData|TestCaseSource|DynamicData)\b")
ROW_NAME = re.compile(r"\b(?:InlineData|TestCase|DataRow)\b")
DOC_LINE = re.compile(r"[ \t]*///(?!/)")
PAIRED_DIRECTIVES = {"if": "endif", "region": "endregion"}
BRACKET_DEPTH = {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}
NAME = re.compile(r"\b[A-Za-z_]\w{2,}\b")
QUALIFIED_MEMBER = re.compile(r"\b[A-Z]\w*\.[A-Z]\w*\b")
MODIFIERS = r"(?:public|private|protected|internal|static|readonly|const|sealed|override|async|virtual|partial|new|required)"


class Refusal(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove approved C# test methods and data rows, bound to the file content the user approved."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    hash_command = commands.add_parser("hash", help="print the SHA-256 of each file, to record beside its approvals")
    hash_command.add_argument("files", nargs="+")

    remove = commands.add_parser("remove", help="remove test methods and data rows from one file")
    remove.add_argument("file")
    remove.add_argument("--sha256", required=True, help="the hash recorded when the user approved the rows")
    remove.add_argument("--dry-run", action="store_true", help="print what would go, change nothing")
    remove.add_argument("tests", nargs="+", metavar="TEST", help="'Method' or 'Method [row n]', n counted from 1")
    return parser.parse_args()


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_target(text):
    match = TARGET.match(text)
    if match is None:
        raise Refusal(f"not a test name or 'Method [row n]': {text!r}")
    return match.group(1), int(match.group(2)) if match.group(2) else None


def line_start(text, position):
    return text.rfind("\n", 0, position) + 1


def line_end(text, position):
    end = text.find("\n", position)
    return len(text) if end == -1 else end + 1


def previous_line(text, start):
    return text[line_start(text, start - 1):start] if start > 0 else None


def removal_span(text, masked, start, end):
    first, last = line_start(text, start), line_end(text, end - 1)
    blank_before, blank_after = not masked[first:start].strip(), not masked[end:last].strip()
    if blank_before and blank_after:
        return first, last
    if blank_after:
        while start > first and text[start - 1] in " \t":
            start -= 1
        return start, end
    while end < len(text) and text[end] in " \t":
        end += 1
    return start, end


def with_doc_comment(text, without_comments, start):
    if start != line_start(text, start):
        return start
    doc_start = position = start
    while (line := previous_line(text, position)) is not None:
        line_begin = position - len(line)
        doc = bool(DOC_LINE.match(line)) and not without_comments[line_begin:position].strip()
        if line.strip() and not doc:
            return doc_start
        position = line_begin
        if doc:
            doc_start = position
    return doc_start


def without_double_blank_lines(text, start, end):
    if start != line_start(text, start) or end != line_start(text, end):
        return start, end
    before = previous_line(text, start)
    after = text[end:line_end(text, end)]
    if before is not None and not before.strip() and not after.strip():
        return start, line_end(text, end)
    if before is not None and not before.strip() and after.strip().startswith("}"):
        return start - len(before), end
    if before is not None and before.strip().endswith("{") and not after.strip():
        return start, line_end(text, end)
    return start, end


def method_span(text, masked, without_comments, header_start, body_end):
    start, end = removal_span(text, masked, scanner.attribute_run_start(masked, header_start), body_end)
    return with_doc_comment(text, without_comments, start), end


def inline_rows(masked, start, end):
    rows = []
    position = start
    while (position := masked.find("[", position, end)) != -1:
        close = scanner.attribute_end(masked, position)
        if INLINE_ROW.match(masked, position):
            rows.append((position, close))
        position = close
    return rows


def row_span(text, masked, name, row, attributes_start, header_start):
    region = masked[attributes_start:header_start]
    if ROW_FROM_MEMBER.search(region):
        raise Refusal(f"{name} takes rows from a member or class; edit that data by hand")
    rows = inline_rows(masked, attributes_start, header_start)
    if len(rows) != len(ROW_NAME.findall(region)):
        raise Refusal(f"{name} lists rows inside a combined attribute; edit them by hand")
    if not 1 <= row <= len(rows):
        raise Refusal(f"{name} has {len(rows)} data rows, so there is no row {row}")
    start, end = removal_span(text, masked, *rows[row - 1])
    return start, end, len(rows)


def plan(text, targets):
    masked = scanner.code_mask(text)
    without_comments = scanner.code_mask(text, mask_strings=False)
    methods = {}
    for _, header_start, name, _, body_end in scanner.test_methods(masked):
        methods.setdefault(name, []).append((header_start, body_end))
    spans = []
    given = set()
    rows_removed = {}
    for target in targets:
        name, row = parse_target(target)
        if (name, row) in given:
            raise Refusal(f"{target.strip()} is given twice")
        given.add((name, row))
        found = methods.get(name, [])
        if not found:
            raise Refusal(f"no test method named {name}")
        if len(found) > 1:
            raise Refusal(f"{len(found)} test methods are named {name}; edit by hand")
        header_start, body_end = found[0]
        if row is None:
            start, end = method_span(text, masked, without_comments, header_start, body_end)
            spans.append((start, end, f"{name} (line {scanner.line_of(text, header_start)})"))
            continue
        attributes_start = scanner.attribute_run_start(masked, header_start)
        start, end, total = row_span(text, masked, name, row, attributes_start, header_start)
        rows_removed.setdefault(name, set()).add(row)
        if len(rows_removed[name]) == total:
            raise Refusal(f"removing every row of {name} leaves a test with no data; delete the method instead")
        row_text = scanner.collapse(text[start:end])
        spans.append((start, end, f"{name} [row {row}] (line {scanner.line_of(text, start)}): {row_text}"))
    whole = {name for name, row in given if row is None}
    if whole & rows_removed.keys():
        raise Refusal(f"{sorted(whole & rows_removed.keys())[0]} is given whole and by row; give one of them")
    return spans, whole, {name: len(rows) for name, rows in rows_removed.items()}


def merged(text, spans):
    directives = []
    masked = scanner.code_mask(text, directives=directives)
    groups = []
    for start, end, label in sorted(spans):
        if groups and start < groups[-1][1]:
            raise Refusal(f"{groups[-1][2][-1]} and {label} overlap; edit by hand")
        if groups and not text[groups[-1][1]:start].strip():
            groups[-1] = (groups[-1][0], end, groups[-1][2] + [label])
        else:
            groups.append((start, end, [label]))
    groups = [(*without_double_blank_lines(text, start, end), labels) for start, end, labels in groups]
    for start, end, labels in groups:
        check_directives(text, [position for position in directives if start <= position < end], labels[0])
        check_brackets(masked, start, end, labels[0])
    return groups


def directive_words(text, position):
    line = text[position + 1:line_end(text, position)].split("//")[0]
    return line.replace(",", " ").split()


def check_directives(text, positions, label):
    opened = []
    disabled = []
    for position in positions:
        words = directive_words(text, position) or [""]
        keyword = words[0]
        if keyword in PAIRED_DIRECTIVES:
            opened.append(PAIRED_DIRECTIVES[keyword])
        elif keyword in ("elif", "else") and opened[-1:] == ["endif"]:
            pass
        elif opened and keyword == opened[-1]:
            opened.pop()
        elif words[:3] == ["pragma", "warning", "disable"]:
            disabled.append(words[3:])
        elif words[:3] == ["pragma", "warning", "restore"] and words[3:] in disabled:
            disabled.remove(words[3:])
        else:
            raise Refusal(f"a preprocessor line (#{' '.join(words)}) in {label} acts beyond it; edit by hand")
    if opened or disabled:
        raise Refusal(f"a preprocessor block in {label} is left open; edit by hand")


def check_brackets(masked, start, end, label):
    depth = 0
    for char in masked[start:end]:
        depth += BRACKET_DEPTH.get(char, 0)
        if depth < 0:
            break
    if depth != 0:
        raise Refusal(f"the text of {label} does not close its own brackets; edit by hand")


def tests_of(text):
    masked = scanner.code_mask(text)
    return [
        (name, text[attributes:header], text[header:end], len(inline_rows(masked, attributes, header)))
        for attributes, header, name, _, end in scanner.test_methods(masked)
    ]


def without_spans(text, groups):
    pieces, position = [], 0
    for start, end, _ in groups:
        pieces.append(text[position:start])
        position = end
    return "".join(pieces) + text[position:]


def check_result(before, after, groups, whole, rows_removed):
    if scanner.code_mask(after) != without_spans(scanner.code_mask(before), groups):
        raise Refusal("the removal would cut a comment or a string; edit by hand")
    expected = [test for test in tests_of(before) if test[0] not in whole]
    actual = tests_of(after)
    if [(name, body) for name, _, body, _ in expected] != [(name, body) for name, _, body, _ in actual]:
        raise Refusal("the result would change tests that were not named; edit by hand")
    for (name, attributes, _, rows), (_, attributes_after, _, rows_after) in zip(expected, actual):
        if name in rows_removed and rows_after != rows - rows_removed[name]:
            raise Refusal(f"the result would not remove exactly the named rows of {name}; edit by hand")
        if name not in rows_removed and attributes_after != attributes:
            raise Refusal(f"the result would change the attributes of {name}; edit by hand")


def removed_code(masked, groups):
    return "\n".join(masked[start:end] for start, end, _ in groups)


def declares(code, name):
    return re.search(rf"^\s*(?:{MODIFIERS}\s+)+[^=;(\n]*\b{re.escape(name)}\s*(?:[(=;{{<:]|$)", code, re.M) is not None


def file_orphans(removed, result):
    masked = scanner.code_mask(result)
    orphans = []
    for name in sorted(set(NAME.findall(removed))):
        uses = [match.start() for match in re.finditer(rf"\b{re.escape(name)}\b", masked)]
        if len(uses) == 1 and declares(masked[line_start(masked, uses[0]):line_end(masked, uses[0])], name):
            orphans.append(f"{name} (line {scanner.line_of(result, uses[0])})")
    return orphans


def production_orphans(path, masked, removed, result):
    members = sorted(member for member in set(QUALIFIED_MEMBER.findall(removed))
                     if not declares(masked, member.split(".")[0]))
    if not members:
        return []
    top = subprocess.run(["git", "-C", str(path.resolve().parent), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0:
        return []
    root = pathlib.Path(top.stdout.strip())
    patterns = [argument for member in members for argument in ("-e", member)]
    found = subprocess.run(
        ["git", "-C", str(root), "grep", "--untracked", "-h", "-o", "-w", "-F", *patterns,
         "--", "*.cs", f":!{path.resolve().relative_to(root)}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if found.returncode > 1:
        return []
    still_named = set(found.stdout.split()) | set(QUALIFIED_MEMBER.findall(scanner.code_mask(result)))
    return [member for member in members if member not in still_named]


def report_orphans(path, text, groups, result):
    masked = scanner.code_mask(text)
    removed = removed_code(masked, groups)
    in_file = file_orphans(removed, result)
    if in_file:
        print("Left without a reader in this file — check each one, then delete it in the same edit:")
        for orphan in in_file:
            print(f"- {orphan}")
    in_production = production_orphans(path, masked, removed, result)
    if in_production:
        print("Production members only the removed tests named — check for unqualified uses inside their own "
              "type, then propose deleting them in a separate commit:")
        for member in in_production:
            print(f"- {member}")


def write_atomically(path, data):
    path = path.resolve()
    if not os.access(path, os.W_OK):
        raise Refusal(f"{path} is not writable")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
        temporary.write(data)
    shutil.copymode(path, temporary.name)
    os.replace(temporary.name, path)


def remove(path, expected_sha256, targets, dry_run):
    actual = sha256_of(path)
    if actual != expected_sha256.lower():
        raise Refusal(f"{path} changed since the approval (sha256 {actual}); review it again")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refusal(f"{path} is not UTF-8; edit it by hand") from error
    spans, whole, rows_removed = plan(text, targets)
    groups = merged(text, spans)
    result = without_spans(text, groups)
    check_result(text, result, groups, whole, rows_removed)
    if not dry_run:
        write_atomically(path, result.encode("utf-8"))
    verb = "would remove" if dry_run else "removed"
    for label in (label for _, _, labels in groups for label in labels):
        print(f"- {verb} {label}")
    left = len(tests_of(result))
    print(f"{left} test methods {'would be' if dry_run else 'are'} left in {path}")
    if left == 0:
        print("No test is left: delete the file, with the private helpers only those tests used.")
    report_orphans(path, text, groups, result)


def main():
    args = parse_args()
    try:
        if args.command == "hash":
            for file in args.files:
                print(f"{sha256_of(pathlib.Path(file))}  {file}")
        else:
            remove(pathlib.Path(args.file), args.sha256, args.tests, args.dry_run)
    except (Refusal, OSError) as error:
        print(f"Refused: {error}. Nothing was changed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
