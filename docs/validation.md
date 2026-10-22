# v0.1.0 validation

## Scope

Reviewed all 16 files in the supplied archive, the current [Agent Skills specification](https://agentskills.io/specification), [Playwright MCP documentation](https://github.com/microsoft/playwright-mcp), and [skills CLI documentation](https://github.com/vercel-labs/skills) on 2026-10-22.

The package is an instruction workflow. Installing it does not connect browser tools, create independent agents, enforce permissions, or provide network throttling.

## Local checks

- Python 3.14.6: metadata validator passed for `first-user-audit`.
- Nine deterministic reporter tests passed; six metadata-validator tests passed. Fixtures are synthetic, not browser observations.
- Node.js 24.19.0 and skills CLI 1.7.4: local package discovery found `first-user-audit`.
- MIT license retained at repository root and bundled inside the skill so installations preserve the notice.

The local Codex skill-creator `quick_validate.py` rejects `compatibility` because that helper's allowed-field list omits it. The current public specification explicitly supports this field. It is retained and validated by the repository validator; this helper check is not reported as passing.

## Public installation smoke test

Installed from `BarganConstantin/agent-skills` in a clean temporary directory using Node.js 24.19.0 and skills CLI 1.7.4:

```bash
npx skills add BarganConstantin/agent-skills --list
npx skills add BarganConstantin/agent-skills --skill first-user-audit --agent claude-code --yes
```

Discovery found one skill and installation succeeded. This agent selection copied the package to `.claude/skills/first-user-audit/`. All eight bundled source files matched the installed files byte-for-byte, including references and MIT notice. The installed reporter's `--help` worked and its nine unit tests passed. No global skill installation was used.

## GitHub checks

The public repository uses `main`; description and six topics are configured. Unauthenticated HTTP requests returned 200 for the repository, README, MIT license, skill entrypoint, and skill directory. All 17 relative Markdown file links resolved locally and all four external documentation targets returned HTTP 200.

[Initial CI run](https://github.com/BarganConstantin/agent-skills/actions/runs/39724978321) passed validation and all 15 tests on each of Python 3.10, 3.12, and 3.14. The current candidate must also pass CI before tagging.

## Remaining behavioral validation

No application was audited, no browser session was exercised, and no independent subagent or throttling behavior was tested. A Playwright MCP server and a target application were not configured for this package review. Available browser/subagent integrations were not exercised; their presence alone does not validate this workflow. Installation alone is not behavioral validation.

Before promotion, follow [the supervised audit checklist](../PUBLISHING.md#before-promoting). Record actual versions, safe target, fresh sessions, observed evidence, bounded fixes, and a fresh after-pass. Report unsupported capabilities explicitly.

# v0.2 readiness: controlled local validation

This candidate adds a synthetic localhost demonstration. It does not retroactively turn the published v0.1.0 release into a customer-product study. The original instructions and references used by the testers were copied directly from the immutable `v0.1.0` tag before the run; candidate reporting improvements were evaluated separately.

## Environment and procedure

- Date: 2026-10-22; macOS; Python 3.14.6; Node 24.19.0.
- Microsoft Playwright MCP 0.0.83, HTTP transport at localhost:8931, isolated headless Chrome. Observed browser user agent: HeadlessChrome/155.0.0.0.
- Synthetic Task Cabin fixture at `http://127.0.0.1:4179`, baseline then fixed variants. It binds to loopback, stores data only in browser localStorage, and has no accounts, backend state, payments or external integrations.
- A small command adapter makes real MCP tool calls available to the agent harness. Starting a server alone was not counted as a connection: initialization, tool discovery, navigation, state inspection and a real screenshot succeeded before testing.
- One fresh subagent context per persona and phase, started without inherited conversation history; browser sessions ran sequentially and were closed between runs. Testers received the original skill, target, first-success event and persona instructions, without app source, findings, diffs, or other reports. They shared a filesystem and were instructed not to read other artifacts; this is context separation, not a security isolation claim.
- Each tester verified initially empty local/session storage and a 1280×800 desktop viewport or 375×812 narrow viewport. No server-side reset is needed; the fixture stores nothing server-side. Browser-visible cookie checks do not enumerate HttpOnly cookies.
- No supported throttling tool was exposed. Slow 3G was not tested; resizing did not emulate touch, mobile hardware or a mobile user agent. No latency or performance result is claimed.

## Observed browser results

All eight runs completed their assigned stop/success decisions. Baseline first success: **0/4**. Fixed first success: **4/4**, with 2, 5, 2 and 6 clicks for impatient, skeptic, mobile and breaker respectively. No issue recurred in the fresh verification runs. These are descriptive observations from an intentionally flawed fixture, not a conversion result or general bug-discovery benchmark.

See the [generated example report](../examples/first-user-demo/report.md), [nine reviewed screenshots](../examples/first-user-demo/evidence/), and [source/evidence hashes and consolidation mapping](../examples/first-user-demo/study.json). The original per-run provenance limitations are preserved. The baseline breaker stopped before invalid inputs; the corresponding after-pass coverage cannot be treated as a matched baseline comparison. The verification prompt clarified that expected validation feedback is not an implementation error.

Both baseline and fixed deterministic browser smoke checks passed. Independent code review additionally reproduced two adapter bugs (SSE framing and a session/transcript filename collision); regression tests failed before correction and passed after it. These adapter fixes do not change the demo application or persona findings.

## Compatibility levels

Tested public `main`/`v0.1.0` commit `d0413e6eb5ee64a6b314e92273e2b07e4a9193d1` using skills CLI 1.7.4, Node 24.19.0 and npm 11.17.0 in clean temporary projects, without global installation.

| Client | Discovery and installation | Invocation | Full CLI audit |
| --- | --- | --- | --- |
| Claude Code 2.1.306 | Passed; eight bundled files match the public commit, including references and MIT notice | Native `/first-user-audit` recognized; explicitly requested missing-target preflight response returned | Not tested |
| Codex CLI 0.163.0 | Passed; eight bundled files match the public commit; installed under `.agents/skills/first-user-audit` | Blocked before invocation by the test's macOS write-guard sandbox: `failed to initialize in-process app-server client: Operation not permitted (os error 1)` | Not tested |

The Claude command was a recognition/preflight smoke check, not an independent behavior benchmark: the prompt explicitly requested stopping for a missing target. Both installed reporters passed `--help`. The Codex failure does not establish an authentication or skill-format problem. The separate agent-harness/browser study is not a claim that the same complete workflow was executed through both native CLIs.

The unpublished candidate was also installed from the local checkout into separate clean Claude Code and Codex project directories. All eight bundled files matched each installation, and each installed reporter regenerated the complete reviewed example with strict evidence checks, byte-for-byte identical to the checked-in summary. This checks candidate packaging and reporter execution, not native model/browser execution.

## Reporter reliability

The candidate adds optional `--verify-evidence`/`--project-root` filesystem checks, rejects conflicting stable issue identities in strict mode, prevents comparisons across different environment URLs, and prints reported capability gaps even with eight complete JSON reports. Legacy textual success evidence remains accepted without the new flag. File existence and self-reported capabilities do not establish authenticity, independence or real execution.

Local Python checks: 18 reporter tests plus 15 metadata/HTTP-fixture/adapter tests pass. CI also runs deterministic browser smoke checks against baseline and fixed variants; these checks are not independent personas. The baseline smoke check reproduced blank-name acceptance separately because the baseline breaker persona stopped at the earlier CTA failure.

## Promotion boundary

Use the [demonstration guide](../examples/first-user-demo/README.md) to reproduce the setup. Evidence from intentionally planted defects can support a small, clearly labeled demonstration post after review. It cannot support claims about customer-product defect rates, conversion, retention, general agent reliability, slow networks, touch devices, or successful end-to-end execution in both native CLIs. A supervised audit of another safe application and native Codex execution remain useful next validations.

GitHub private vulnerability reporting was confirmed disabled. [SECURITY.md](../SECURITY.md) recommends enabling GitHub's private advisory mechanism and gives a safe interim contact-request process. No security-setting change was made.
