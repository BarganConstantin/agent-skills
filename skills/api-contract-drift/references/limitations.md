# What API Contract Drift actually checks

The bundled comparator is intentionally **small, offline, readable and conservative**. It accepts two local, UTF-8 OpenAPI 3.x **JSON** files and returns potential breaking changes from a subset of their documented surface.

## Supported checks

| Change | Why it may matter to clients |
| --- | --- |
| Existing route + HTTP method removed | Calls that previously targeted the operation may fail |
| New required parameter | Existing callers that omit it may receive a validation error |
| Existing optional parameter made required | Client libraries may not supply it |
| Request body becomes required | Previously legal empty requests may fail |
| New required top-level JSON request field | Previously legal requests without the field may fail |
| Previously accepted request media type removed | Clients using that content type may be rejected |
| Previously documented response code removed | SDKs and client flows may treat results differently |
| Response media type removed | Existing clients expecting e.g. JSON may fail |

References to `#/components/...` are followed when the pointer is valid, non-cyclic and resolves to a JSON object. Path and operation parameters are merged with operation-level parameters overriding path-level parameters by matching `(in, name)`.

## Known blind spots — do not claim complete coverage

- YAML input, Swagger 2.0, malformed OpenAPI docs, remote refs and schema files.
- Recursive property checks, complex `allOf`, `anyOf`, `oneOf`, `not`, `additionalProperties` constraints and top-level typed arrays.
- Parameter and property type changes, narrowing enum values, numeric/string range changes, changed header serialization and request/response schema compatibility beyond explicit checks.
- New authentication and authorization requirements, `security` scheme changes, rate limits, deprecations, server URL updates, runtime behavior and SDK behavior.
- Invalid or context-dependent response status fallbacks (e.g., `default` and wildcard response keys): treat removals as **review signals**, not proof of breakage.
- Changes whose impact depends on unknown clients. The comparison is static: tests and owner approval are still needed.

If a local reference is missing or cyclic, or a schema uses unsupported composition, the script reports a warning. **Warnings are unresolved coverage**, not a pass. New files may contain internal routes or identifiers: review the report before sharing publicly.

Exit codes: `0` = comparator executed (not a green API); `1` = risk detected in the opt-in `--fail-on-risk` mode; `2` = unusable input or local error.

## Relationship to existing work

This is an **independently written implementation**, not a copied or rebranded script from another project. The general compatibility review patterns were informed by:

- [OpenAPI 3.0 specification](https://spec.openapis.org/oas/v3.0.4), particularly parameter and request-body `required` semantics.
- [GitHub API breaking changes](https://docs.github.com/en/enterprise-cloud@latest/rest/about-the-rest-api/breaking-changes), including removing operations and adding required parameters.
- [oasdiff breaking-change classification](https://www.oasdiff.com/docs/breaking-changes). Its comprehensive rules and engine are substantially more capable; use it for strict production compatibility checking.
- [Addy Osmani's API/interface design skill](https://github.com/addyosmani/agent-skills/tree/main/skills/api-and-interface-design) (MIT), whose engineering-review focus is related but not copied.

No upstream source code, test fixtures or written instructions were copied. The original comparator here uses Python standard library only, offers a narrower explicit contract, and should not be represented as a replacement for established tools.
