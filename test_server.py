import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import server


class DateRangeValidatorServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app)

    def call_mcp(self, method: str, params=None, request_id=1):
        response = self.client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_homepage_is_real_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Date Range Validator", response.text)
        self.assertIn("/privacy", response.text)
        self.assertIn("/terms", response.text)
        self.assertIn("/support", response.text)

    def test_privacy_page_contains_required_sections(self):
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Last updated", response.text)
        self.assertIn("sidcraigau@gmail.com", response.text)

    def test_terms_page_contains_non_advice_boundary(self):
        response = self.client.get("/terms")
        self.assertEqual(response.status_code, 200)
        self.assertIn("not professional advice", response.text.lower())

    def test_support_page_contains_required_contact_email(self):
        response = self.client.get("/support")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sidcraigau@gmail.com", response.text)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_openai_apps_challenge_returns_env_value(self):
        with patch.dict(os.environ, {"OPENAI_APPS_CHALLENGE": "challenge-token"}, clear=False):
            response = self.client.get("/.well-known/openai-apps-challenge")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "challenge-token")

    def test_openai_apps_challenge_returns_empty_string_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.get("/.well-known/openai-apps-challenge")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "")

    def test_initialize_returns_required_fields(self):
        body = self.call_mcp("initialize", {"clientInfo": {"name": "test-client"}})
        self.assertEqual(body["result"]["protocolVersion"], server.PROTOCOL_VERSION)
        self.assertEqual(body["result"]["serverInfo"]["name"], server.SERVER_NAME)
        self.assertEqual(body["result"]["serverInfo"]["version"], server.SERVER_VERSION)
        self.assertEqual(body["result"]["capabilities"]["tools"]["listChanged"], False)

    def test_tools_list_returns_full_contract(self):
        body = self.call_mcp("tools/list")
        self.assertEqual(body["result"]["tools"], [server.TOOL_CONTRACT])

    def test_tools_call_returns_successful_structured_output(self):
        body = self.call_mcp(
            "tools/call",
            {
                "name": server.TOOL_NAME,
                "arguments": {
                    "start_date": "2026-05-01",
                    "end_date": "2026-05-03",
                },
            },
        )
        result = body["result"]
        expected = {
            "ok": True,
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "inclusive_days": 3,
            "error": None,
        }
        self.assertEqual(result["structuredContent"], expected)
        self.assertEqual(result["isError"], False)
        self.assertEqual(
            result["content"][0]["text"],
            json.dumps(expected, separators=(",", ":"), sort_keys=True),
        )

    def test_three_consecutive_calls_are_identical(self):
        params = {
            "name": server.TOOL_NAME,
            "arguments": {
                "start_date": "2026-06-10",
                "end_date": "2026-06-12",
            },
        }
        calls = [self.call_mcp("tools/call", params, request_id=index) for index in range(1, 4)]
        results = [call["result"]["structuredContent"] for call in calls]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_missing_field_error_contract(self):
        body = self.call_mcp(
            "tools/call",
            {
                "name": server.TOOL_NAME,
                "arguments": {
                    "start_date": "2026-05-01",
                },
            },
        )
        self.assertEqual(
            body["result"]["structuredContent"],
            {
                "ok": False,
                "start_date": None,
                "end_date": None,
                "inclusive_days": None,
                "error": {
                    "code": "missing_field",
                    "message": "end_date is required.",
                    "field": "end_date",
                },
            },
        )
        self.assertTrue(body["result"]["isError"])

    def test_invalid_value_error_contract(self):
        body = self.call_mcp(
            "tools/call",
            {
                "name": server.TOOL_NAME,
                "arguments": {
                    "start_date": "2026-02-30",
                    "end_date": "2026-03-01",
                },
            },
        )
        self.assertEqual(
            body["result"]["structuredContent"],
            {
                "ok": False,
                "start_date": None,
                "end_date": None,
                "inclusive_days": None,
                "error": {
                    "code": "invalid_value",
                    "message": "start_date must be a valid ISO date in YYYY-MM-DD format.",
                    "field": "start_date",
                },
            },
        )

    def test_out_of_scope_error_contract(self):
        body = self.call_mcp(
            "tools/call",
            {
                "name": server.TOOL_NAME,
                "arguments": {
                    "start_date": "2026-05-03",
                    "end_date": "2026-05-01",
                },
            },
        )
        self.assertEqual(
            body["result"]["structuredContent"],
            {
                "ok": False,
                "start_date": None,
                "end_date": None,
                "inclusive_days": None,
                "error": {
                    "code": "out_of_scope",
                    "message": "start_date must be earlier than or equal to end_date.",
                    "field": "start_date",
                },
            },
        )

    def test_internal_error_contract(self):
        with patch("server.validate_date_range_logic", side_effect=RuntimeError("boom")):
            body = self.call_mcp(
                "tools/call",
                {
                    "name": server.TOOL_NAME,
                    "arguments": {
                        "start_date": "2026-05-01",
                        "end_date": "2026-05-02",
                    },
                },
            )
        self.assertEqual(
            body["result"]["structuredContent"],
            {
                "ok": False,
                "start_date": None,
                "end_date": None,
                "inclusive_days": None,
                "error": {
                    "code": "internal_error",
                    "message": "An internal error occurred while validating the date range.",
                    "field": None,
                },
            },
        )

    def test_unknown_method_returns_json_rpc_error(self):
        body = self.call_mcp("unknown/method")
        self.assertEqual(body["error"]["code"], -32601)
        self.assertEqual(body["error"]["message"], "Method not found")

    def test_invalid_json_returns_parse_error(self):
        response = self.client.post(
            "/mcp",
            content=b"{bad json",
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], -32700)
        self.assertEqual(response.json()["error"]["message"], "Parse error")


if __name__ == "__main__":
    unittest.main()
