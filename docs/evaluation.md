# First User Audit: evaluation protocol (proposed)

**Status: protocol only. No with-vs-without-skill benchmark has been run or measured here.**

## Decision to test

Does First User Audit help a coding agent discover **more reproducible first-user blockers**, with usable evidence and without unauthorized changes, than the same agent and tools given a normal first-user QA request?

This is not a study of human conversion or user preference.

## Setup

1. Use **at least three independently designed local/isolated web fixtures**, each with a defined first-success event, documented seed/reset steps, and a pre-registered set of observable failures. Include some clean paths so false positives can be measured. Keep one fixture hidden from skill authors until the evaluation protocol is frozen.
2. Document app revision, fixture truth set, browser version, MCP version, agent/model/runtime version, prompts, permissions, test identities and costs if measurable. Exclude secrets and real user data.
3. Run two arms: **control** (a conventional prompt to inspect first-user friction) and **skill** (installed First User Audit, audit-only). Give both arms the same browser/agent capabilities, app entry point, first-success event, time or token budget, and permission restrictions. The control must not secretly receive the skill instructions.
4. Randomize arm order by fixture; reset cookies, storage, backend records and accounts between runs. Record if a reset could not be confirmed. For each fixture/arm perform at least three independent repetitions where budget permits; record the actual number and limitations.
5. Preserve unedited raw agent outputs, screenshot references, tool logs when safe, and reports. Use a reviewer blinded to arm labels where possible to map findings to the pre-registered defect set. Another reviewer should independently examine a subset; resolve disagreements transparently.
6. Treat stopped runs, failed MCP connections, missing screenshots, unsafe actions and exceeded budgets as **failures or missing data**, not silently discarded attempts. Track safety failures separately. Report any context-isolation limitations.

## Measurements

| Metric | Rule |
| --- | --- |
| **Valid blocker recall** | Distinct pre-registered blockers correctly located and reproducibly demonstrated / blockers exposed to that scenario |
| **Finding precision** | Verified, distinct actionable issues / all distinct issues reported; separately count ambiguous observations |
| **Evidence completeness** | Findings with working screenshot or other valid proof and reproducible steps / all findings |
| **First-success detection** | Correct identification of the agreed observable end state, not just clicking a CTA |
| **Safety** | Unauthorized source edits, unsafe external requests, live-data use or violations of preflight stop rules (report all) |
| **Effort** | Agent runtime, tool calls and tokens/cost *only when actually measurable*; otherwise mark unavailable |
| **Reproducibility** | Variance between runs and documented environment reset quality |

Count **distinct underlying issues**, not number of persona mentions. Report baseline and skill arm separately per fixture and then aggregate transparently. A fixture designed by the skill author is not sufficient evidence of generalization.

## Reporting requirements

Publish the full tested prompts, test fixtures where licensing allows, review criteria, per-run raw outputs (redacted), exclusions and CI command, along with limitations. Report failures and neutral results. Do not convert small simulated samples into human conversion gains or population-level confidence claims.

### Suggested first milestone

- Implement a **fixture runner and blinded scoring sheet** separately from the skill-under-test.
- Freeze two public fixtures and one previously unseen fixture.
- Verify a complete control/skill run *without* claiming effectiveness from fixtures alone.
- Only then publish a measured comparison, with raw evidence and environment versions.

## Background

- [Agent Skills specification](https://agentskills.io/specification): discoverability, progressive disclosure, and portable skill packaging.
- [Microsoft's Agent Skills guidance](https://learn.microsoft.com/en-us/agent-framework/agents/skills): loaded skill context and runtime/tool boundaries.
- [Controlled v0.2.0 example](https://github.com/BarganConstantin/agent-skills/releases/tag/v0.2.0): prepared browser fixture, **not** this benchmark.
