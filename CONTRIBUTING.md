# Contributing

Thanks for improving these skills. Keep proposals narrow: one observable job, a short `SKILL.md`, optional on-demand references, and tests whenever scripts are included.

Requirements:

1. Use the [Agent Skills specification](https://agentskills.io/specification), with frontmatter `name` and `description`.
2. Keep instructions honest about tool capabilities, authority, model limitations and missing evidence.
3. Do not add secrets, sample real user data, browser traces with private data, or screenshots from third-party products without rights.
4. Do not report benchmark numbers without a public evaluation harness and reproducible runs.
5. Follow the [development setup](README.md#development), then run the metadata validator, validator tests, and reporter tests. Add regression coverage for changed script behavior.

Prefer issues before introducing new dependencies. The maintainer decides which skills belong in this collection.
