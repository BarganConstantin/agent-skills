"""Deterministic tests for conservative OpenAPI client-risk triage."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "api-contract-drift" / "scripts" / "compare_openapi.py"
spec = importlib.util.spec_from_file_location("compare_openapi", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def app():
    return {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "post": {
                    "requestBody": {"required": False, "content": {
                        "application/json": {"schema": {
                            "type": "object", "properties": {"name": {"type": "string"}},
                            "required": []}}}},
                    "responses": {"201": {"description": "Created", "content": {
                        "application/json": {"schema": {"type": "object"}}}}}
                }
            }
        }
    }


def codes(before, after):
    return [x["code"] for x in guard.compare(before, after)["potential_breaks"]]


class ContractGuardTests(unittest.TestCase):
    def setUp(self):
        self.old = app()
        self.new = copy.deepcopy(self.old)

    def test_identical_document_is_not_called_a_proof(self):
        result = guard.compare(self.old, self.new)
        self.assertFalse(result["potential_breaks"])
        self.assertIn("NOT prove compatibility", result["disclaimer"])

    def test_removing_operation_is_flagged(self):
        del self.new["paths"]["/items"]["post"]
        self.assertEqual(codes(self.old, self.new), ["operation_removed"])

    def test_adding_required_query_parameter_is_flagged(self):
        self.new["paths"]["/items"]["post"]["parameters"] = [
            {"in": "query", "name": "page", "required": True, "schema": {"type": "integer"}}]
        self.assertIn("required_parameter", codes(self.old, self.new))

    def test_optional_query_parameter_is_not_flagged(self):
        self.new["paths"]["/items"]["post"]["parameters"] = [
            {"in": "query", "name": "page", "required": False}]
        self.assertNotIn("required_parameter", codes(self.old, self.new))

    def test_optional_parameter_becomes_required(self):
        self.old["paths"]["/items"]["parameters"] = [{"in": "header", "name": "X-Id", "required": False}]
        self.new["paths"]["/items"]["parameters"] = [{"in": "header", "name": "X-Id", "required": True}]
        self.assertIn("required_parameter", codes(self.old, self.new))

    def test_operation_parameter_overrides_path_parameter(self):
        self.old["paths"]["/items"]["parameters"] = [{"in": "query", "name": "x", "required": False}]
        self.old["paths"]["/items"]["post"]["parameters"] = [{"in": "query", "name": "x", "required": True}]
        self.new = copy.deepcopy(self.old)
        self.assertEqual(codes(self.old, self.new), [])

    def test_request_body_now_required(self):
        self.new["paths"]["/items"]["post"]["requestBody"]["required"] = True
        self.assertIn("required_body", codes(self.old, self.new))

    def test_new_required_body_property(self):
        schema = self.new["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        schema["properties"]["id"] = {"type": "string"}
        schema["required"] = ["id"]
        self.assertIn("required_property", codes(self.old, self.new))

    def test_optional_body_property_does_not_trigger(self):
        schema = self.new["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        schema["properties"]["tag"] = {"type": "string"}
        self.assertNotIn("required_property", codes(self.old, self.new))

    def test_local_schema_ref_is_resolved(self):
        for obj in (self.old, self.new):
            obj["components"] = {"schemas": {"Item": {"type": "object", "required": []}}}
            obj["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
                "$ref": "#/components/schemas/Item"}
        self.new["components"]["schemas"]["Item"]["required"] = ["name"]
        self.assertIn("required_property", codes(self.old, self.new))

    def test_unresolved_ref_warns_and_does_not_invent_break(self):
        self.new["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
            "$ref": "https://untrusted.invalid/openapi.json#/types/Item"}
        result = guard.compare(self.old, self.new)
        self.assertTrue(result["warnings"])
        self.assertNotIn("required_property", [x["code"] for x in result["potential_breaks"]])

    def test_removed_response_status_and_media_are_flagged(self):
        del self.new["paths"]["/items"]["post"]["responses"]["201"]
        self.assertIn("response_status_removed", codes(self.old, self.new))
        self.new = copy.deepcopy(self.old)
        del self.new["paths"]["/items"]["post"]["responses"]["201"]["content"]["application/json"]
        self.assertIn("response_media_removed", codes(self.old, self.new))

    def test_removed_request_media_is_flagged(self):
        self.new["paths"]["/items"]["post"]["requestBody"]["content"] = {}
        self.assertIn("request_media_removed", codes(self.old, self.new))

    def test_composed_schema_is_incomplete_not_false_clean(self):
        schema = self.new["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        schema.clear()
        schema["allOf"] = [{"type": "object", "required": ["id"]}]
        result = guard.compare(self.old, self.new)
        self.assertEqual(result["result"], "manual_review_required")
        self.assertTrue(result["warnings"])

    def test_root_security_added_breaks_anonymous_operation(self):
        self.new["components"] = {"securitySchemes": {
            "Token": {"type": "apiKey", "in": "header", "name": "X-Token"}}}
        self.new["security"] = [{"Token": []}]
        self.assertIn("anonymous_access_removed", codes(self.old, self.new))

    def test_operation_can_override_root_security_to_allow_anonymous(self):
        self.new["security"] = [{"Token": []}]
        self.new["paths"]["/items"]["post"]["security"] = []
        self.assertNotIn("anonymous_access_removed", codes(self.old, self.new))

    def test_optional_auth_with_empty_requirement_is_not_removed(self):
        self.old["security"] = [{"Token": []}, {}]
        self.new["security"] = [{"Token": []}, {}]
        self.assertNotIn("anonymous_access_removed", codes(self.old, self.new))

    def test_removing_anonymous_alternative_is_flagged(self):
        self.old["security"] = [{"Token": []}, {}]
        self.new["security"] = [{"Token": []}]
        self.assertIn("anonymous_access_removed", codes(self.old, self.new))

    def test_dropping_existing_auth_alternative_is_flagged(self):
        self.old["security"] = [{"Token": []}, {"OAuth": ["read"]}]
        self.new["security"] = [{"OAuth": ["read"]}]
        self.assertIn("security_alternative_tightened", codes(self.old, self.new))

    def test_newly_required_oauth_scope_is_flagged(self):
        self.old["security"] = [{"OAuth": ["read"]}]
        self.new["security"] = [{"OAuth": ["read", "write"]}]
        self.assertIn("security_alternative_tightened", codes(self.old, self.new))

    def test_looser_security_is_not_flagged(self):
        self.old["security"] = [{"OAuth": ["read", "write"]}]
        self.new["security"] = [{"OAuth": ["read"]}, {}]
        self.assertNotIn("security_alternative_tightened", codes(self.old, self.new))

    def test_same_auth_scheme_with_changed_mechanism_is_flagged(self):
        self.old["security"] = [{"Token": []}]
        self.new["security"] = [{"Token": []}]
        self.old["components"] = {"securitySchemes": {
            "Token": {"type": "apiKey", "name": "X-Token", "in": "header"}}}
        self.new["components"] = {"securitySchemes": {
            "Token": {"type": "http", "scheme": "bearer"}}}
        self.assertIn("security_scheme_changed", codes(self.old, self.new))

    def test_security_scheme_description_only_change_is_not_flagged(self):
        self.old["security"] = [{"Token": []}]
        self.new["security"] = [{"Token": []}]
        self.old["components"] = {"securitySchemes": {
            "Token": {"type": "apiKey", "name": "X-Token", "in": "header",
                      "description": "Old copy"}}}
        self.new["components"] = {"securitySchemes": {
            "Token": {"type": "apiKey", "name": "X-Token", "in": "header",
                      "description": "New copy"}}}
        self.assertNotIn("security_scheme_changed", codes(self.old, self.new))

    def test_malformed_security_creates_warning_not_fabricated_finding(self):
        self.new["security"] = [{"Token": "not-a-list"}]
        result = guard.compare(self.old, self.new)
        self.assertTrue(any("security" in warning for warning in result["warnings"]))
        self.assertFalse(any("anonymous_access_removed" == x["code"] for x in result["potential_breaks"]))

    def test_root_security_overridden_on_existing_operations(self):
        self.old["security"] = [{"Token": []}]
        self.old["paths"]["/items"]["post"]["security"] = []
        self.new["security"] = [{"Token": []}]
        self.new["paths"]["/items"]["post"]["security"] = [{"Token": []}]
        self.assertIn("anonymous_access_removed", codes(self.old, self.new))

    def test_rejects_invalid_version(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "api.json"
            file.write_text('{"openapi":"2.0","paths":{}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                guard.load(file)

    def test_cli_optional_risk_exit_status(self):
        self.new["paths"] = {}
        with tempfile.TemporaryDirectory() as d:
            before, after = Path(d) / "old.json", Path(d) / "new.json"
            before.write_text(json.dumps(self.old), encoding="utf-8")
            after.write_text(json.dumps(self.new), encoding="utf-8")
            self.assertEqual(guard.main(["--before", str(before), "--after", str(after)]), 0)
            self.assertEqual(guard.main(["--before", str(before), "--after", str(after), "--fail-on-risk"]), 1)


if __name__ == "__main__":
    unittest.main()
