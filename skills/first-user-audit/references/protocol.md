# Audit protocol

## Before the test

1. Inspect code and document the persona's intended job and objectively observable first-success predicate.
2. Save app revision, local/preview URL, browser version, time, and any seeded test data. Stabilize the environment; avoid switching builds between persona runs.
3. Establish safe test accounts (e.g. local email sink / example.test identities), test billing mode, and a reset plan for backend records.
4. Pick a shared start condition. A fresh session means fresh cookies, local/session storage, auth state, and relevant server-side test records.
5. Report capabilities honestly: browser MCP, real subagents, screenshots, viewport verification, throttling, and server reset.

## During each persona run

- Follow the assigned behavior, not a scripted successful answer. Record every **activation click or tap** on a meaningful UI control. Define click count consistently; do not count typing, scrolling or keyboard navigation as clicks. Report keyboard-only activations separately.
- Take screenshots on friction, confusion, visible errors, and abandonment. Capture steps for reproduction, including field values only when clearly synthetic and non-sensitive.
- Record stage (e.g. landing, pricing, signup, verify-email, onboarding, activation), current URL path, element/selector, attempted action, visible content, expected outcome, actual outcome and impact.
- Record first success only after the observable predicate holds. If the persona abandons, record `reached: false` and `clicks_to_success: null`.
- A persona's `would_return` is a role-played estimate (`yes`, `no`, `uncertain`), never a claim about actual human retention.

## Between runs

- Wait until the prior agent is finished before assigning the next. No browser/context sharing across agents, no old cookies, no old issue lists.
- Keep the initial instructions, criteria, target app version, viewport and throttling attempts consistent for before/after. Only the intentional code fixes should differ.
- Screenshot filenames should use phase/persona/ID, e.g. `after-skeptic-FUA-004.png`. Keep reports separate in `baseline/` and `after/`.

## Issue consolidation

Two observations are the same issue when they describe the **same underlying failure** at the **same step or component**. Similar language alone is not enough. Provide stable IDs before generating the ranked table, and map after-pass occurrences to those IDs **after** independent testing. When an issue is genuinely new, create a new ID.

Classify problems: `technical`, `pricing`, `terms`, `privacy`. Technical work can be considered for automated fixes only if changes are bounded and not security/billing sensitive. Never rewrite legal or pricing content without the owner's approval.

## How to interpret the report

Four simulated personas uncover some obvious failure modes; they cannot measure human user conversion, provide population-level confidence, or prove the product is usable by all people. A good report distinguishes observed browser behavior from agent speculation, and completed capability tests from unavailable ones.
