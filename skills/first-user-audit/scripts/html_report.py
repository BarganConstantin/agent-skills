#!/usr/bin/env python3
"""Render validated First User Audit reports as a self-contained offline HTML page.

This is presentation, not a browser-run or screenshot-authenticity verifier.
The page has no JavaScript, remote requests, or third-party dependencies.
"""
import argparse
from html import escape
from pathlib import Path
import json

import summarize as audit


PERSONA_JOBS = {
    "impatient": "First obvious action",
    "skeptic": "Pricing, terms and privacy",
    "mobile": "375px responsive journey",
    "breaker": "Invalid inputs and retries",
}


def e(value):
    """Escape all untrusted report strings before embedding in markup."""
    return escape(str(value), quote=True)


def metric(value, label):
    return '<div class="metric"><strong>' + e(value) + '</strong><span>' + e(label) + '</span></div>'


def persona_card(persona, report):
    if report is None:
        return ('<article class="persona missing"><div class="persona-top"><h3>' + e(persona.title()) +
                '</h3><span class="state">Not run</span></div><p>' + e(PERSONA_JOBS[persona]) +
                '</p><p class="muted">No valid report was supplied for this persona.</p></article>')
    reached = report["first_success"]["reached"]
    tag = '<span class="state success">Reached first success</span>' if reached else '<span class="state stopped">First success not reached</span>'
    clicks = str(report["clicks_to_success"]) if reached else "—"
    caps = json.dumps(report["capabilities"], ensure_ascii=False, sort_keys=True)
    limits = "; ".join(map(str, report["limitations"])) if report["limitations"] else "None declared (not proof of full capability)"
    return (
        '<article class="persona"><div class="persona-top"><h3>' + e(persona.title()) + '</h3>' + tag +
        '</div><p>' + e(PERSONA_JOBS[persona]) + '</p>' +
        '<dl><div><dt>Clicks to success</dt><dd>' + e(clicks) +
        '</dd></div><div><dt>Would return (simulated)</dt><dd>' + e(report["would_return"]) +
        '</dd></div><div><dt>Reported issues</dt><dd>' + e(len(report["issues"])) +
        '</dd></div></dl><details><summary>Capabilities and limitations</summary><p><b>Self-reported capabilities:</b> <code>' +
        e(caps) + '</code></p><p><b>Limitations:</b> ' + e(limits) + '</p></details></article>'
    )


def issue_table(rows):
    if not rows:
        return '<p class="muted">No issues reported in available persona records. This does not prove the application has no issues.</p>'
    items = []
    for issue in rows:
        details = (
            '<details><summary>Reproduction and evidence</summary>' +
            '<p><b>Location:</b> ' + e(issue["location"]) + '</p>' +
            '<p><b>Reproduce:</b> ' + e(issue["reproduction"]) + '</p>' +
            '<p><b>Expected:</b> ' + e(issue["expected"]) + '</p>' +
            '<p><b>Observed:</b> ' + e(issue["actual"]) + '</p>' +
            '<p><b>Evidence paths (not verified by this page):</b> ' +
            e(", ".join(map(str, issue["evidence"])) or "None") + '</p></details>'
        )
        items.append(
            '<tr><td><code>' + e(issue["id"]) + '</code></td><td>' + e(len(issue["personas"])) +
            '/4</td><td>' + e(issue["severity"]) + '</td><td>' + e(issue["category"]) +
            '</td><td>' + e(issue["stage"]) + '</td><td><b>' + e(issue["summary"]) +
            '</b>' + details + '</td></tr>'
        )
    return ('<div class="table-scroll"><table><thead><tr><th>Issue</th><th>Personas</th><th>Severity</th>'
            '<th>Type</th><th>Stage</th><th>Finding</th></tr></thead><tbody>' + "".join(items) +
            '</tbody></table></div>')


def phase_section(phase, data, missing):
    rows, conflicts = audit.aggregate(data)
    successes = sum(1 for record in data.values() if record["first_success"]["reached"])
    head = '<section class="phase"><div class="section-head"><h2>' + e(phase.title()) + '</h2><span class="muted">Simulated QA</span></div>'
    cards = '<div class="metrics">' + metric(f"{len(data)}/4", "Valid persona reports") + metric(f"{successes}/4", "Reached first success") + metric(len(rows), "Distinct reported issues") + '</div>'
    completeness = '<p class="muted">Missing personas: ' + e(", ".join(missing) or "none") + '.</p>'
    if conflicts:
        completeness += '<p class="warning">Issue-ID conflicts require reviewer inspection: ' + e("; ".join(sorted(set(conflicts)))) + '</p>'
    personas = '<div class="personas">' + "".join(persona_card(name, data.get(name)) for name in audit.PERSONAS) + '</div>'
    return head + cards + completeness + personas + '<h3>Ranked findings</h3>' + issue_table(rows) + '</section>'


def comparison_section(reports, missing):
    warnings = audit.comparability_warnings(reports)
    if any(missing[p] for p in audit.PHASES):
        warnings.insert(0, "Incomplete persona coverage")
    if warnings:
        return ('<section class="phase"><h2>Before / after</h2><p class="warning"><b>Comparison unavailable:</b> ' +
                e("; ".join(warnings)) + '. Do not interpret these records as improvement.</p></section>')
    baseline = sum(int(r["first_success"]["reached"]) for r in reports["baseline"].values())
    after = sum(int(r["first_success"]["reached"]) for r in reports["after"].values())
    before, _ = audit.aggregate(reports["baseline"])
    following, _ = audit.aggregate(reports["after"])
    before_ids = {x["id"]: len(x["personas"]) for x in before}
    after_ids = {x["id"]: len(x["personas"]) for x in following}
    issues = "".join(
        '<tr><td><code>' + e(iid) + '</code></td><td>' + e(before_ids.get(iid, 0)) +
        '/4</td><td>' + e(after_ids.get(iid, 0)) + '/4</td></tr>'
        for iid in sorted(before_ids.keys() | after_ids.keys())
    ) or '<tr><td colspan="3">No issues in either phase</td></tr>'
    return ('<section class="phase"><h2>Before / after</h2><div class="metrics">' +
            metric(f"{baseline}/4", "Baseline first success") + metric(f"{after}/4", "After-pass first success") +
            metric(len(before_ids), "Distinct baseline issues") + '</div>' +
            '<div class="table-scroll"><table><thead><tr><th>Issue</th><th>Before personas</th><th>After personas</th></tr></thead><tbody>' +
            issues + '</tbody></table></div><p class="muted">Differences describe a few simulated QA journeys. They are not statistically significant human conversion measurements or proof of causality.</p></section>')


def render_html(reports, missing, baseline_only=False, verified=False):
    phases = audit.PHASES[:1] if baseline_only else audit.PHASES
    success_name = next(iter(reports["baseline"].values()))["first_success"]["name"]
    sections = "".join(phase_section(phase, reports[phase], missing[phase]) for phase in phases)
    if not baseline_only:
        sections += comparison_section(reports, missing)
    check_note = (
        "Evidence path containment and file existence were checked by the reporter. Screenshot contents, authenticity and relevance were NOT verified."
        if verified else
        "Evidence file existence was NOT checked. Screenshot contents, authenticity and relevance were NOT verified."
    )
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; img-src 'none'; connect-src 'none'">
<title>First User Audit — simulated QA report</title>
<style>
:root { color-scheme: light dark; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; background: #f8fafb; color: #172a36; }
* { box-sizing: border-box; }
body { margin: 0; line-height: 1.5; }
main { max-width: 1140px; margin: auto; padding: 48px 28px 80px; }
h1 { font-size: clamp(2rem, 4vw, 3.1rem); line-height: 1.14; letter-spacing: -.045em; margin: 12px 0 16px; }
h2 { letter-spacing: -.025em; font-size: 1.55rem; margin: 0; }
h3 { margin: 0 0 12px; font-size: 1.08rem; }
p { max-width: 80ch; }
header { margin-bottom: 32px; }
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .75rem; font-weight: 800; color: #42618b; }
.subtitle { font-size: 1.09rem; max-width: 73ch; }
.muted { color: #57707e; font-size: .9rem; }
.phase { background: #fff; border: 1px solid #dfe7ed; border-radius: 16px; padding: 28px; margin: 24px 0; }
.section-head, .persona-top { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.metrics, .personas { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 24px 0; }
.metric { background: #edf3f7; border-radius: 12px; padding: 16px 18px; }
.metric strong { display: block; font-size: 1.8rem; letter-spacing: -.05em; font-variant-numeric: tabular-nums; }
.metric span { color: #516e80; font-size: .84rem; }
.personas { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.persona { border: 1px solid #dfe7ed; border-radius: 12px; padding: 20px; min-width: 0; }
.persona.missing { border-style: dashed; }
.persona p { color: #526c7d; font-size: .9rem; }
.state { display: inline-block; border-radius: 999px; background: #e9edf0; padding: 5px 10px; font-size: .75rem; font-weight: 700; }
.state.success { color: #12633d; background: #d9f4e3; }
.state.stopped { color: #9b4414; background: #fce8d5; }
dl { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
dl div { min-width: 0; } dt { color: #5b7080; font-size: .75rem; } dd { margin: 0; font-weight: 700; overflow-wrap: anywhere; }
.table-scroll { overflow-x: auto; margin: 18px 0; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; min-width: 620px; }
th { background: #edf3f7; text-align: left; font-size: .75rem; letter-spacing: .04em; }
th, td { padding: 12px; border-bottom: 1px solid #dfe7ed; vertical-align: top; }
td { overflow-wrap: anywhere; }
details { margin: 14px 0 0; }
summary { font-size: .83rem; cursor: pointer; color: #255d85; font-weight: 700; }
details p { font-size: .84rem; overflow-wrap: anywhere; }
code { font-size: .83rem; white-space: pre-wrap; overflow-wrap: anywhere; }
.notice, .warning { border-left: 3px solid #bc874e; padding: 10px 14px; background: #fff8ee; color: #744718; border-radius: 0 8px 8px 0; }
.notice { background: #eaf3f8; border-left-color: #417ba2; color: #234b66; }
.footer { color: #587080; padding-top: 18px; font-size: .85rem; }
@media (max-width: 760px) { main { padding: 24px 14px 48px; } .phase { padding: 20px 14px; } .metrics { grid-template-columns: 1fr 1fr; } .personas { grid-template-columns: 1fr; } }
@media (prefers-color-scheme: dark) {
:root { background: #10191f; color: #e6edf2; }
.eyebrow { color: #a9c7f8; } .muted, .footer, .persona p { color: #aec1cb; }
.phase, .persona { background: #18252d; border-color: #334752; }
.metric, th { background: #233744; } .metric span, dt { color: #b1c4cd; }
th,td { border-color: #344752; } summary { color: #99c9fa; }
.notice { background: #1d3647; color: #bfe0ff; }
.warning { background: #3b3022; color: #fce2ba; }
.state { background: #33444e; } .state.success { background: #254e3a; color: #baf3d0; }
.state.stopped { background: #503621; color: #f8d9b5; }
}
@media print { :root { color-scheme: light; } main { max-width: 100%; padding: 0; } .phase, .persona { break-inside: avoid; } }
</style>
</head>
<body><main><header>
<div class="eyebrow">First User Audit · Local report</div>
<h1>Where first-time users get stuck</h1>
<p class="subtitle"><b>First-success event:</b> """ + e(success_name) + """</p>
<p class="notice"><b>Simulated QA, not real-user research.</b> These reports are agent observations and judgments, not measurements of conversion or retention. Review for personal data before sharing.</p>
</header>""" + sections + """
<section class="phase"><h2>Evidence and integrity notes</h2>
<p>""" + e(check_note) + """</p>
<p>Capability claims (browser MCP, subagents, viewport and throttling) are self-reported. This HTML generator cannot verify actual browser use, true agent independence, identity of root causes, or test-environment isolation.</p>
<p>Evidence paths are intentionally printed as text, not embedded or fetched. The report is fully offline and makes no network requests. Inspect and redact reports and screenshots before publication.</p>
</section><p class="footer">Generated from locally supplied report JSON. No telemetry, scripts or external assets.</p>
</main></body></html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a static, offline HTML report from First User Audit JSON")
    parser.add_argument("--root", type=Path, default=Path("qa/first-users"))
    parser.add_argument("--output", type=Path, help="HTML destination (default: ROOT/summary.html)")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--verify-evidence", action="store_true")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.strict and args.baseline_only:
        parser.error("--strict and --baseline-only cannot be combined")
    try:
        required = ("baseline",) if args.baseline_only else audit.PHASES
        reports, missing = audit.load_reports(args.root, required, verify_evidence=args.verify_evidence,
                                              project_root=args.project_root)
        if not reports["baseline"]:
            raise audit.ReportError("no baseline reports found; refusing empty HTML")
        if args.strict:
            absent = [f"{p}: {', '.join(missing[p])}" for p in required if missing[p]]
            if absent:
                raise audit.ReportError("missing reports: " + "; ".join(absent))
            warnings = audit.comparability_warnings(reports)
            if warnings:
                raise audit.ReportError("not comparable: " + "; ".join(warnings))
        html = render_html(reports, missing, baseline_only=args.baseline_only, verified=args.verify_evidence)
        output = args.output or args.root / "summary.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(html, encoding="utf-8")
        print(f"Wrote {output} (offline HTML; inspect and redact before sharing)")
        return 0
    except (audit.ReportError, OSError, UnicodeError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
