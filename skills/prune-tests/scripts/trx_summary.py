#!/usr/bin/env python3
import argparse
import sys
import xml.etree.ElementTree as ElementTree

TRX_NAMESPACE = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
PASSED = "Passed"
FAILED = "Failed"


def parse_args():
    parser = argparse.ArgumentParser(description="Summarise or compare dotnet test TRX result files.")
    commands = parser.add_subparsers(dest="command", required=True)

    summary = commands.add_parser("summary", help="counts, failing tests and the slowest tests of one run")
    summary.add_argument("trx")
    summary.add_argument("--slowest", type=int, default=15)

    compare = commands.add_parser("compare", help="what changed between a baseline run and a run after pruning")
    compare.add_argument("before")
    compare.add_argument("after")
    return parser.parse_args()


def duration_seconds(text):
    if not text:
        return 0.0
    hours, minutes, seconds = text.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_results(path):
    root = ElementTree.parse(path).getroot()
    results = {}
    for result in root.iterfind(".//t:Results/t:UnitTestResult", TRX_NAMESPACE):
        results[result.get("testName")] = {
            "outcome": result.get("outcome"),
            "seconds": duration_seconds(result.get("duration")),
        }
    return results


def names_with_outcome(results, outcome):
    return sorted(name for name, result in results.items() if result["outcome"] == outcome)


def print_summary(path, slowest):
    results = read_results(path)
    failed = names_with_outcome(results, FAILED)
    passed = names_with_outcome(results, PASSED)
    total_seconds = sum(r["seconds"] for r in results.values())
    print(f"# {path}\n")
    print(f"Tests: {len(results)} | passed: {len(passed)} | failed: {len(failed)} | "
          f"other: {len(results) - len(passed) - len(failed)} | summed test time: {total_seconds:.2f} s\n")
    if failed:
        print(f"## Failing ({len(failed)})\n")
        for name in failed:
            print(f"- `{name}`")
        print()
    print(f"## Slowest {slowest}\n")
    ranked = sorted(results.items(), key=lambda item: item[1]["seconds"], reverse=True)[:slowest]
    for name, result in ranked:
        share = (result["seconds"] / total_seconds * 100) if total_seconds else 0
        print(f"- {result['seconds']:.3f} s ({share:.1f}%) `{name}`")


def print_comparison(before_path, after_path):
    before = read_results(before_path)
    after = read_results(after_path)
    gone = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    regressed = sorted(
        name for name in set(before) & set(after)
        if before[name]["outcome"] == PASSED and after[name]["outcome"] != PASSED
    )
    new_failures = [name for name in added if after[name]["outcome"] != PASSED]
    before_seconds = sum(r["seconds"] for r in before.values())
    after_seconds = sum(r["seconds"] for r in after.values())

    print("# Before / after\n")
    print(f"Tests: {len(before)} -> {len(after)} | summed test time: {before_seconds:.2f} s -> {after_seconds:.2f} s\n")
    print(f"## Passed before, failing now ({len(regressed)})\n")
    for name in regressed:
        print(f"- `{name}` ({after[name]['outcome']})")
    print(f"\n## New and not passing ({len(new_failures)})\n")
    for name in new_failures:
        print(f"- `{name}` ({after[name]['outcome']})")
    print(f"\n## Gone: must match the approved deletions and merged originals ({len(gone)})\n")
    for name in gone:
        print(f"- `{name}`")
    print(f"\n## New: must match the merged [Theory] rows ({len(added)})\n")
    for name in added:
        print(f"- `{name}`")
    return 1 if regressed or new_failures else 0


def main():
    args = parse_args()
    if args.command == "summary":
        print_summary(args.trx, args.slowest)
        return 0
    return print_comparison(args.before, args.after)


if __name__ == "__main__":
    sys.exit(main())
