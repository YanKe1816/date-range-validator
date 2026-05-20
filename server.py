import json
import os
from copy import deepcopy
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse


SERVER_NAME = "date-range-validator"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"
TOOL_NAME = "validate_date_range"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

DEFAULT_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Date Range Validator</title>
  <style>
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f7f0e8 0%, #fffaf5 100%);
      color: #1f2933;
    }
    main {
      max-width: 760px;
      margin: 0 auto;
      padding: 48px 24px 64px;
    }
    h1 {
      font-size: 2.5rem;
      margin-bottom: 0.5rem;
    }
    p, li {
      font-size: 1.05rem;
      line-height: 1.7;
    }
    .panel {
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid #d8c8b8;
      border-radius: 16px;
      padding: 24px;
      margin-top: 24px;
      box-shadow: 0 10px 30px rgba(95, 74, 52, 0.08);
    }
    a {
      color: #8a3b12;
    }
  </style>
</head>
<body>
  <main>
    <h1>Date Range Validator</h1>
    <p>Validate whether a start date and end date form a valid ISO date range.</p>

    <section class="panel">
      <h2>What problem this solves</h2>
      <p>This app gives developers and reviewers a deterministic MCP tool for checking date-range inputs without ambiguity, side effects, or external dependencies.</p>
    </section>

    <section class="panel">
      <h2>Basic usage</h2>
      <ol>
        <li>Connect to the MCP endpoint at <code>/mcp</code>.</li>
        <li>Call <code>initialize</code>, then <code>tools/list</code>.</li>
        <li>Select <code>validate_date_range</code> and pass <code>start_date</code> and <code>end_date</code> in <code>YYYY-MM-DD</code> format.</li>
      </ol>
    </section>

    <section class="panel">
      <h2>Support</h2>
      <p>Email: <a href="mailto:sidcraigau@gmail.com">sidcraigau@gmail.com</a></p>
      <p>Review pages: <a href="/privacy">Privacy</a> | <a href="/terms">Terms</a> | <a href="/support">Support</a></p>
    </section>
  </main>
</body>
</html>
"""

DEFAULT_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Privacy | Date Range Validator</title>
  <style>
    body { font-family: Georgia, "Times New Roman", serif; margin: 0; background: #fcfaf7; color: #1f2933; }
    main { max-width: 820px; margin: 0 auto; padding: 40px 24px 64px; }
    h1, h2 { color: #4b2e1f; }
    p { line-height: 1.75; }
  </style>
</head>
<body>
  <main>
    <h1>Privacy Policy</h1>
    <p>Last updated: 2026-05-20</p>

    <h2>Data handling</h2>
    <p>Date Range Validator processes only the date values that are submitted to the MCP tool for validation.</p>

    <h2>Data sources</h2>
    <p>All inputs come directly from the calling client. The service does not enrich, scrape, or fetch outside data sources.</p>

    <h2>How data is used</h2>
    <p>Submitted values are used only to determine whether the date range is valid and to return a structured validation result.</p>

    <h2>Storage</h2>
    <p>This service is designed to be stateless and does not intentionally store submitted inputs after request processing completes, aside from transient platform-level request handling and logs.</p>

    <h2>Sharing</h2>
    <p>The service does not intentionally share submitted data with third parties except where infrastructure providers necessarily process requests to host the service.</p>

    <h2>Contact methods</h2>
    <p>Privacy questions or deletion requests can be sent to <a href="mailto:sidcraigau@gmail.com">sidcraigau@gmail.com</a>.</p>
  </main>
</body>
</html>
"""

DEFAULT_TERMS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Terms | Date Range Validator</title>
  <style>
    body { font-family: Georgia, "Times New Roman", serif; margin: 0; background: #fffdf9; color: #1d2730; }
    main { max-width: 820px; margin: 0 auto; padding: 40px 24px 64px; }
    h1, h2 { color: #4b2e1f; }
    p { line-height: 1.75; }
  </style>
</head>
<body>
  <main>
    <h1>Terms of Service</h1>
    <p>Effective date: 2026-05-20</p>

    <h2>Service content</h2>
    <p>Date Range Validator provides a single MCP tool that validates ISO 8601 date ranges and returns structured output.</p>

    <h2>Usage boundaries</h2>
    <p>The service validates only <code>YYYY-MM-DD</code> calendar dates. This service is not professional advice and does not provide scheduling, legal, financial, medical, tax, or other professional advice.</p>

    <h2>User responsibilities</h2>
    <p>Users are responsible for supplying accurate inputs, reviewing outputs, and determining whether the results fit their own workflows and compliance needs.</p>

    <h2>Prohibited usage</h2>
    <p>You may not use the service to attempt unauthorized access, overload the service, submit malicious payloads, or misrepresent the output as professional advice.</p>

    <h2>Change notifications</h2>
    <p>Material updates to these terms will be reflected on this page by updating the effective date and page content.</p>

    <h2>Contact info</h2>
    <p>Questions about these terms can be sent to <a href="mailto:sidcraigau@gmail.com">sidcraigau@gmail.com</a>.</p>
  </main>
</body>
</html>
"""

DEFAULT_SUPPORT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Support | Date Range Validator</title>
  <style>
    body { font-family: Georgia, "Times New Roman", serif; margin: 0; background: #fbf7f2; color: #22303c; }
    main { max-width: 820px; margin: 0 auto; padding: 40px 24px 64px; }
    h1, h2 { color: #4b2e1f; }
    p, li { line-height: 1.75; }
  </style>
</head>
<body>
  <main>
    <h1>Date Range Validator Support</h1>
    <p>Support email: <a href="mailto:sidcraigau@gmail.com">sidcraigau@gmail.com</a></p>

    <h2>Feedback types</h2>
    <ul>
      <li>Bug reports for incorrect validation behavior or page issues</li>
      <li>Deployment and connection questions related to the MCP endpoint</li>
      <li>Submission-review feedback for privacy, terms, or support content</li>
    </ul>

    <h2>Exception handling instructions</h2>
    <p>If the tool returns an error result, include the exact input payload, returned error code, and the time of the request in your support message so the issue can be reproduced safely.</p>
  </main>
</body>
</html>
"""

HTML_PAGES = {
    "index.html": os.environ.get("INDEX_HTML", DEFAULT_INDEX_HTML),
    "privacy.html": os.environ.get("PRIVACY_HTML", DEFAULT_PRIVACY_HTML),
    "terms.html": os.environ.get("TERMS_HTML", DEFAULT_TERMS_HTML),
    "support.html": os.environ.get("SUPPORT_HTML", DEFAULT_SUPPORT_HTML),
}

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Start date in ISO 8601 calendar format YYYY-MM-DD.",
        },
        "end_date": {
            "type": "string",
            "description": "End date in ISO 8601 calendar format YYYY-MM-DD.",
        },
    },
    "required": ["start_date", "end_date"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "start_date": {
            "type": ["string", "null"],
            "description": "Normalized start date in YYYY-MM-DD when validation succeeds.",
        },
        "end_date": {
            "type": ["string", "null"],
            "description": "Normalized end date in YYYY-MM-DD when validation succeeds.",
        },
        "inclusive_days": {
            "type": ["integer", "null"],
            "minimum": 1,
            "description": "Inclusive day count when validation succeeds.",
        },
        "error": {
            "type": ["object", "null"],
            "properties": {
                "code": {
                    "type": "string",
                    "enum": [
                        "missing_field",
                        "invalid_value",
                        "out_of_scope",
                        "internal_error",
                    ],
                },
                "message": {"type": "string"},
                "field": {"type": ["string", "null"]},
            },
            "required": ["code", "message", "field"],
            "additionalProperties": False,
        },
    },
    "required": ["ok", "start_date", "end_date", "inclusive_days", "error"],
    "additionalProperties": False,
}

ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "openWorldHint": False,
}

NOT_DO_BOUNDARIES = [
    "Only validates ISO 8601 calendar dates in YYYY-MM-DD format.",
    "Does not infer time zones, times, locales, or natural-language dates.",
    "Does not repair ambiguous inputs or call external services.",
    "Does not validate business calendars, holidays, or booking rules.",
]

TOOL_DESCRIPTION = (
    "Validate that start_date and end_date are present, parseable as ISO 8601 "
    "calendar dates in YYYY-MM-DD format, and that start_date is not later than "
    "end_date. Returns fixed structured output with deterministic results and the "
    "error contract codes missing_field, invalid_value, out_of_scope, and "
    "internal_error. Boundaries: "
    + " ".join(NOT_DO_BOUNDARIES)
)

TOOL_CONTRACT = {
    "name": TOOL_NAME,
    "title": "Date Range Validator",
    "description": TOOL_DESCRIPTION,
    "inputSchema": INPUT_SCHEMA,
    "outputSchema": OUTPUT_SCHEMA,
    "annotations": ANNOTATIONS,
}

app = FastAPI(title="Date Range Validator", docs_url=None, redoc_url=None, openapi_url=None)


def make_success_result(start_date: str, end_date: str, inclusive_days: int) -> dict:
    return {
        "ok": True,
        "start_date": start_date,
        "end_date": end_date,
        "inclusive_days": inclusive_days,
        "error": None,
    }


def make_error_result(code: str, message: str, field: str | None) -> dict:
    return {
        "ok": False,
        "start_date": None,
        "end_date": None,
        "inclusive_days": None,
        "error": {
            "code": code,
            "message": message,
            "field": field,
        },
    }


def parse_iso_date(raw_value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError(
            json.dumps(
                {
                    "code": "invalid_value",
                    "message": f"{field_name} must be a valid ISO date in YYYY-MM-DD format.",
                    "field": field_name,
                }
            )
        ) from exc


def validate_date_range_logic(arguments: dict) -> dict:
    for field_name in INPUT_SCHEMA["required"]:
        if field_name not in arguments:
            return make_error_result(
                "missing_field",
                f"{field_name} is required.",
                field_name,
            )

    if set(arguments.keys()) != set(INPUT_SCHEMA["properties"].keys()):
        extra_fields = sorted(set(arguments.keys()) - set(INPUT_SCHEMA["properties"].keys()))
        if extra_fields:
            return make_error_result(
                "invalid_value",
                f"Unexpected field(s): {', '.join(extra_fields)}.",
                extra_fields[0],
            )

    start_value = arguments["start_date"]
    end_value = arguments["end_date"]

    if not isinstance(start_value, str):
        return make_error_result(
            "invalid_value",
            "start_date must be a string in YYYY-MM-DD format.",
            "start_date",
        )
    if not isinstance(end_value, str):
        return make_error_result(
            "invalid_value",
            "end_date must be a string in YYYY-MM-DD format.",
            "end_date",
        )

    try:
        start = parse_iso_date(start_value, "start_date")
        end = parse_iso_date(end_value, "end_date")
    except ValueError as exc:
        details = json.loads(str(exc))
        return make_error_result(details["code"], details["message"], details["field"])

    if start > end:
        return make_error_result(
            "out_of_scope",
            "start_date must be earlier than or equal to end_date.",
            "start_date",
        )

    inclusive_days = (end - start).days + 1
    return make_success_result(start.isoformat(), end.isoformat(), inclusive_days)


def json_rpc_success(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def json_rpc_error(request_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def handle_json_rpc(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return json_rpc_error(None, -32600, "Invalid Request")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return json_rpc_error(request_id, -32600, "Invalid Request")

    if method == "initialize":
        return json_rpc_success(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
            },
        )

    if method == "tools/list":
        return json_rpc_success(request_id, {"tools": [deepcopy(TOOL_CONTRACT)]})

    if method == "tools/call":
        if not isinstance(params, dict):
            return json_rpc_error(request_id, -32602, "Invalid params")

        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name != TOOL_NAME:
            return json_rpc_error(request_id, -32602, "Unknown tool")
        if not isinstance(arguments, dict):
            return json_rpc_error(request_id, -32602, "Invalid params")

        try:
            structured_content = validate_date_range_logic(arguments)
        except Exception:
            structured_content = make_error_result(
                "internal_error",
                "An internal error occurred while validating the date range.",
                None,
            )

        return json_rpc_success(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(structured_content, separators=(",", ":"), sort_keys=True),
                    }
                ],
                "structuredContent": structured_content,
                "isError": not structured_content["ok"],
            },
        )

    return json_rpc_error(request_id, -32601, "Method not found")


def html_page_response(filename: str) -> HTMLResponse:
    # Review pages are served from embedded HTML strings so Render does not rely
    # on external template files at runtime. STATIC_DIR remains defined only as
    # repository context for the existing project layout.
    html = HTML_PAGES.get(filename)
    if html is None:
        return HTMLResponse(
            content=(
                "<!DOCTYPE html><html><head><title>404 Not Found</title></head>"
                "<body><h1>404 Not Found</h1><p>The requested page was not found.</p></body></html>"
            ),
            status_code=404,
        )
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
async def homepage():
    # Homepage documents the app purpose, usage, and support links required for review.
    return html_page_response("index.html")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    # Privacy page describes the tool's limited data handling and contact details.
    return html_page_response("privacy.html")


@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    # Terms page states scope, boundaries, user responsibilities, and non-advice status.
    return html_page_response("terms.html")


@app.get("/support", response_class=HTMLResponse)
async def support_page():
    # Support page gives the review team a stable contact path and issue categories.
    return html_page_response("support.html")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.get("/.well-known/openai-apps-challenge")
async def openai_apps_challenge():
    return PlainTextResponse(os.environ.get("OPENAI_APPS_CHALLENGE", ""))


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse(json_rpc_error(None, -32700, "Parse error"), status_code=400)

    return JSONResponse(handle_json_rpc(payload))


def main():
    # Render injects PORT at runtime, and the app must bind to 0.0.0.0 so the
    # platform router can reach it from outside the container. The 8000 fallback
    # keeps local runs simple without changing deployment behavior on Render.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
