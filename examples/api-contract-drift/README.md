# Try API Contract Drift in 30 seconds — no account or running server

This is a **controlled, synthetic** OpenAPI 3 example. Both JSON files are local and contain no secrets or real service URLs.

From the repository root, run with Python 3.10+:

\`\`\`bash
python skills/api-contract-drift/scripts/compare_openapi.py \
  --before examples/api-contract-drift/before.json \
  --after examples/api-contract-drift/after.json
\`\`\`

Expected **potential compatibility risks**:

| Operation | Risk | Why a real client might be affected |
| --- | --- | --- |
| \`GET /catalog\` | \`anonymous_access_removed\` | Previously public endpoint now advertises required HTTP bearer authentication |
| \`POST /orders\` | \`required_parameter\` | Old clients may not send new \`X-Region\` header |
| \`POST /orders\` | \`required_property\` | Old clients may omit new required \`accountId\` JSON field |

These three changes are deliberately seeded **only to illustrate detection**. This isn't a measurement of agent accuracy, real customer regression, or proof that the server has changed.

Want machine-readable output for an issue or offline review?

\`\`\`bash
python skills/api-contract-drift/scripts/compare_openapi.py \
  --before examples/api-contract-drift/before.json \
  --after examples/api-contract-drift/after.json \
  --format json
\`\`\`

A successful comparison command exits **0 by default**, even when it reports risks. For an intentionally strict CI gate, add \`--fail-on-risk\`; this controlled example should then exit **1**, after showing the report. Invalid input/execution errors return **2**.

The sample is validated in Python unit tests on 3.10/3.12/3.14. OpenAPI security uses alternatives (\`OR\`) with possibly several simultaneous conditions (\`AND\`), and operation security overrides global security. The comparator follows these declared rules but cannot prove runtime authentication behavior or complete API compatibility. See [exact limitations](../../skills/api-contract-drift/references/limitations.md).

Once you've seen the sample, compare **your own local exported OpenAPI 3 JSON snapshots**. Never send production credentials, modify the production API, or publish private API schemas without permission.
