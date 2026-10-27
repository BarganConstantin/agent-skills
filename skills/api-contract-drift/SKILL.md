---
name: api-contract-drift
description: Check whether API changes may break existing clients before merging or releasing. Compare before/after OpenAPI 3 JSON specs offline; identify removed operations, newly required parameters or request fields, and disappearing response codes/media. Give a focused review checklist without pretending a zero-diff result proves compatibility. Use for .NET, Python, Node, Java or any backend exporting OpenAPI.
license: MIT
compatibility: Python 3.10+ for the optional standard-library comparator. Works offline with local OpenAPI 3.x JSON exports; no browser MCP, cloud access or service credentials required.
---

# API Contract Drift

**Is this API change safe for existing clients?** Don't guess based on the diff. Compare old and new *documented* HTTP contracts, report possible client breakages, and explicitly name what static comparison **cannot** assess.

## Preflight

1. Identify the API and the intended base version. Use **two real OpenAPI 3.x JSON snapshots**: one from the deployed/released reference API and one from the proposed build. Export them from trusted local build tools or existing artifacts. **Do not contact production APIs, generate new credentials or upload customer schemas without permission.**
2. Confirm both exports belong to the same API/product and compatible environments. Record source commit, deployment tag or precise filename for each. If the files don't exist, report **NOT TESTED**; do not fabricate a before/after comparison.
3. Verify that the spec is OpenAPI **3.x JSON**. YAML must be converted locally with an approved converter first; do not claim this skill accepts YAML directly. Unresolved remote references are **not fetched**.

## Run the local comparator

Use the standard-library script bundled in this skill:

```bash
python /path/to/api-contract-drift/scripts/compare_openapi.py \
  --before /path/to/previous-openapi.json \
  --after /path/to/proposed-openapi.json
```

Substitute the actual installed location. The script **reads only local JSON files**, performs no network operations or writes, and prints a Markdown checklist. It conservatively checks:

- Removed HTTP operations, including removal of a previously documented path.
- Newly required query/path/header/cookie parameters or previously optional parameters becoming required.
- Request bodies becoming required and newly required **top-level** JSON body properties in straightforward or local-`$ref` schemas.
- Removed accepted request content types, documented response status codes or response content types.

To consume a machine-readable result, pass `--format json`. By default the script returns exit code **0 if it ran successfully**, even with flagged risks, so review reports rather than assuming a successful process is a compatibility verdict. CI integrations may opt into `--fail-on-risk` (exit **1** on a flagged potential break; exit **2** on input/errors).

## Investigate and report

For each flagged change, identify the real consumer contract and whether the change is intentional/versioned. When practical, reproduce affected requests against **an authorized local test server** using fixture data; do not run destructive probes on production.

For every finding record:

- **What changed:** endpoint + method and affected parameter/body/response.
- **Why a client might break:** the old legal request or expected response behavior.
- **Evidence:** exact old/new spec files, comparator output, client test command and observed result **if actually run**.
- **Decision:** restore compatibility, offer deprecation/migration path, release a new major API version, or get owner approval.

**Do not auto-edit billing, authentication, security policy, data retention or production endpoints.** API design and rollout decisions belong to the owner. Do not call a spec comparison equivalent to consumer contract tests.

## Completion contract

Report the number of potential risks, coverage warnings, the exact spec files compared, the command and observed exit code, and what *was not checked*. When there are **zero findings**, say *“No regressions detected in the supported OpenAPI 3 JSON subset; compatibility is unverified outside that subset.”*

The comparator does **not** check all schema nesting/compositions, all enum and type changes, authorization requirements, server/runtime behavior, generated SDK effects, OpenAPI document validity, references to external files/URLs, or unknown vendor extensions. Use a mature comprehensive diff tool such as [oasdiff](https://www.oasdiff.com/docs/breaking-changes) for broader production gates. See [scope and sources](references/limitations.md) for concrete supported cases and caveats.

If a risk cannot be reproduced, label it *potential*, not proven. If you have no usable before/after specs, produce a safe export plan rather than an invented “passed” review.
