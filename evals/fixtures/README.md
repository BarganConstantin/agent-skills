# Activation Lab — controlled browser fixture

This is a **synthetic, localhost-only test application** for developing and validating evaluation methods. It is not real customer-product testing, a measured agent benchmark, or evidence of autonomous code repair.

Two versions serve the same tiny self-serve workspace application:

- `seeded`: five deliberately introduced flaws.
- `reference`: a prepared corrected variant with the same pages.

All data is held in the browser's localStorage. There is no network integration, database, account, real email address, payment system or production service.

## Run locally

Requires Python 3.10+:

```bash
python evals/fixtures/activation_lab.py --variant seeded --port 8765
```

Open `http://127.0.0.1:8765/` in an actual browser. For the corrected variant, stop the server and run with `--variant reference`. If you compare the variants, reset browser storage and use the same viewport and test procedure.

The **first-success event** is a test workspace appearing in the UI with a nonempty workspace name and no duplicate workspace records after retries. Do not count simply pressing the button as success.

## Pre-registered seeded issues

| Truth ID | Observable defect | Relevant perspective |
| --- | --- | --- |
| `FX-CTA-01` | Primary homepage "Create free workspace" links to pricing instead of the workspace form | Impatient |
| `FX-PRICING-01` | Pricing route does not disclose the sandbox plan's `$0` cost | Skeptic (owner review) |
| `FX-MOBILE-01` | Primary CTA is hidden with CSS at a 375 CSS-pixel viewport | Mobile |
| `FX-VALIDATION-01` | Empty workspace name is accepted and UI reports a workspace ready | Breaker |
| `FX-IDEMPOTENCY-01` | Repeated form submission creates two identical records | Breaker |

The reference variant addresses those five deliberate defects. The pricing finding is a content/policy decision; the skill must **report it for owner review**, not autonomously rewrite real commercial terms.

The fixture truth set is **public**, so agents can inspect the source and discover it. This is useful as a visible smoke test, but it is **not** a blinded, held-out generalization benchmark. Use an independent unseen application for efficacy claims.

## Verify fixture behavior

Install test-only dependencies (not required to install First User Audit):

```bash
python -m pip install "playwright==1.57.0"
python -m playwright install chromium
python -m unittest discover -s evals/fixtures -p 'test_browser.py' -v
```

The test checks the two versions in Chromium with five deterministic browser scenarios. The associated GitHub Action runs with `--with-deps chromium`. Browser restrictions in some execution environments can prevent localhost access; record those limitations rather than bypassing them.

The browser test does **not** run any agent or simulate the four skill personas. It proves only that the prepared fixture behaves as specified.

## Use with the evaluation scorer

Pre-register these fixtures with `evals/score.py` using the truth IDs above for `activation-lab-seeded` and an empty `truth_ids` list for `activation-lab-reference`. For every repetition, run both **control** and **skill** arms on the same version under the same budget and reset conditions, then independently review findings.

The **control arm must not read the skill** and neither arm should be given this truth table as the task prompt. Because these are public fixtures, publish results as fixture-specific only. Never present a passed Playwright test as a successful agent evaluation.

See [evaluation scoring](../README.md) and [full evaluation protocol](../../docs/evaluation.md).
