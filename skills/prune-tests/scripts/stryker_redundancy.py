#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import defaultdict

KILLED = "Killed"
BAIL_SUSPECT_RATIO = 0.95
PARAMETER_LIST = re.compile(r"\(.*\)$")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "List redundant-test candidates from a Stryker mutation-report.json. "
            "Run Stryker with bail disabled (Stryker.NET: --disable-bail, StrykerJS: disableBail), "
            "otherwise killedBy names only the first failing test and every 'no unique kill' line is wrong."
        )
    )
    parser.add_argument("report", help="path to mutation-report.json")
    parser.add_argument(
        "--by-method",
        action="store_true",
        help="fold parameterised cases (Method(x: 1), Method(x: 2)) into one entry per test method",
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    return parser.parse_args()


def load_report(path):
    with open(path, encoding="utf-8") as report_file:
        return json.load(report_file)


def test_names_by_id(report):
    names = {}
    for test_file in (report.get("testFiles") or {}).values():
        for test in test_file.get("tests") or []:
            names[test["id"]] = test.get("name") or test["id"]
    return names


def make_key_function(names, by_method):
    def key_of(test_id):
        name = names.get(test_id, test_id)
        return PARAMETER_LIST.sub("", name) if by_method else name

    return key_of


def collect_sets(report, key_of):
    kills = defaultdict(set)
    covers = defaultdict(set)
    killers_by_mutant = {}
    killed_with_several_coverers = 0
    killed_by_exactly_one_of_several = 0

    for path, source_file in (report.get("files") or {}).items():
        for mutant in source_file.get("mutants") or []:
            mutant_key = f"{path}#{mutant['id']}"
            coverers = {key_of(t) for t in mutant.get("coveredBy") or []}
            for test in coverers:
                covers[test].add(mutant_key)
            if mutant.get("status") != KILLED:
                continue
            killers = {key_of(t) for t in mutant.get("killedBy") or []}
            killers_by_mutant[mutant_key] = killers
            for test in killers:
                kills[test].add(mutant_key)
            if len(coverers) > 1:
                killed_with_several_coverers += 1
                if len(killers) == 1:
                    killed_by_exactly_one_of_several += 1

    bail_suspected = (
        killed_with_several_coverers > 0
        and killed_by_exactly_one_of_several / killed_with_several_coverers >= BAIL_SUSPECT_RATIO
    )
    return kills, covers, killers_by_mutant, bail_suspected


def find_subsumed(kills, killers_by_mutant):
    subsumed = []
    for test in sorted(kills):
        own = kills[test]
        if not own:
            continue
        witnesses = set.intersection(*(killers_by_mutant[m] for m in own)) - {test}
        if not witnesses:
            continue
        stricter = [w for w in witnesses if kills[w] != own]
        if stricter:
            closest = min(stricter, key=lambda w: (len(kills[w]), w))
            subsumed.append({"test": test, "kills": len(own), "witness": closest, "witness_kills": len(kills[closest]), "relation": "subset"})
            continue
        equal_with_smaller_name = sorted(w for w in witnesses if w < test)
        if equal_with_smaller_name:
            subsumed.append({"test": test, "kills": len(own), "witness": equal_with_smaller_name[0], "witness_kills": len(own), "relation": "equal"})
    return subsumed


def greedy_keep_set(kills, killers_by_mutant):
    uncovered = set(killers_by_mutant)
    keep = []
    while uncovered:
        best = max(sorted(kills), key=lambda t: len(kills[t] & uncovered))
        gained = kills[best] & uncovered
        if not gained:
            break
        keep.append(best)
        uncovered -= gained
    return keep


def analyse(report, by_method):
    names = test_names_by_id(report)
    key_of = make_key_function(names, by_method)
    kills, covers, killers_by_mutant, bail_suspected = collect_sets(report, key_of)
    all_tests = {key_of(t) for t in names} | set(covers) | set(kills)
    return {
        "tests": len(all_tests),
        "killed_mutants": len(killers_by_mutant),
        "bail_suspected": bail_suspected,
        "greedy_keep_set": len(greedy_keep_set(kills, killers_by_mutant)),
        "kill_nothing": sorted(
            ({"test": t, "covers": len(covers[t])} for t in covers if not kills.get(t)),
            key=lambda row: row["test"],
        ),
        "subsumed": find_subsumed(kills, killers_by_mutant),
        "not_reached": sorted(t for t in all_tests if t not in covers),
    }


def print_markdown(result, report_path):
    print("# Stryker redundancy candidates\n")
    print(f"Report: `{report_path}`  ")
    print(
        f"Tests: {result['tests']} | killed mutants: {result['killed_mutants']} | "
        f"{result['greedy_keep_set']} tests are enough to kill all of them\n"
    )
    if result["bail_suspected"]:
        print(
            "> WARNING: almost every killed mutant names exactly one killer although several tests cover it. "
            "The run probably had bail ON. Re-run with bail disabled before trusting the lists below.\n"
        )
    print("These are candidates, not verdicts. A test can assert something no mutant touched "
          "(an exception message, a log line, a header). Read both tests before any deletion.\n")

    print(f"## Cover mutated code but kill nothing ({len(result['kill_nothing'])})\n")
    for row in result["kill_nothing"]:
        print(f"- `{row['test']}` covers {row['covers']} mutants")

    print(f"\n## Every kill is also made by another test ({len(result['subsumed'])})\n")
    if result["subsumed"]:
        print("| test | kills | witness | witness kills | relation |")
        print("|---|---|---|---|---|")
        for row in result["subsumed"]:
            print(f"| `{row['test']}` | {row['kills']} | `{row['witness']}` | {row['witness_kills']} | {row['relation']} |")

    print(f"\n## No mutant reached these tests: no conclusion ({len(result['not_reached'])})\n")
    for test in result["not_reached"]:
        print(f"- `{test}`")


def main():
    args = parse_args()
    result = analyse(load_report(args.report), args.by_method)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        print_markdown(result, args.report)


if __name__ == "__main__":
    main()
