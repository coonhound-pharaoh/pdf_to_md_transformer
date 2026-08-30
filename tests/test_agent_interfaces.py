"""The agent-facing surfaces: CLI --json/--stdout and the MCP stdio server."""

import io
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from pdf_to_md import mcp_server  # noqa: E402
from pdf_to_md.cli import main as cli_main  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "sample.pdf")


@pytest.fixture(scope="module")
def pdf() -> str:
    if not os.path.exists(FIXTURE):
        from make_fixture import build
        build(FIXTURE)
    return FIXTURE


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_cli_json_report_is_the_only_thing_on_stdout(pdf, tmp_path, capsys):
    rc = cli_main([pdf, "-o", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    report = json.loads(out)  # would raise if logs leaked onto stdout
    assert rc == 0
    assert report["converted"] == 1 and report["failed"] == 0
    entry = report["results"][0]
    assert entry["ok"] and os.path.isfile(entry["output"])


def test_cli_json_reports_failures_without_aborting(pdf, tmp_path, capsys):
    missing = str(tmp_path / "nope.pdf")
    rc = cli_main([missing, pdf, "-o", str(tmp_path), "--json"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["failed"] == 1 and report["converted"] == 1
    assert report["results"][0]["error"] == "not found"
    assert report["results"][1]["ok"]


def test_cli_stdout_mode_emits_markdown_and_writes_nothing(pdf, tmp_path,
                                                           capsys):
    rc = cli_main([pdf, "--stdout"])
    assert rc == 0
    assert "# Turf Management Field Guide" in capsys.readouterr().out
    assert not os.path.exists(os.path.splitext(pdf)[0] + ".md.tmp")


def test_cli_rejects_stdout_with_json(pdf):
    with pytest.raises(SystemExit):
        cli_main([pdf, "--stdout", "--json"])


# --------------------------------------------------------------------------
# MCP server
# --------------------------------------------------------------------------

def _rpc(method, params=None, mid=1):
    return mcp_server.handle_request(
        {"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}}
    )


def test_initialize_advertises_tools():
    result = _rpc("initialize")["result"]
    assert result["protocolVersion"] == mcp_server.PROTOCOL_VERSION
    assert "tools" in result["capabilities"]


def test_tools_list_matches_handlers():
    names = {t["name"] for t in _rpc("tools/list")["result"]["tools"]}
    assert names == set(mcp_server.HANDLERS)


def test_convert_pdf_tool_returns_markdown(pdf):
    res = _rpc("tools/call",
               {"name": "convert_pdf", "arguments": {"path": pdf}})["result"]
    assert res["isError"] is False
    assert "# Turf Management Field Guide" in res["content"][0]["text"]


def test_convert_pdf_tool_truncates_at_max_chars(pdf):
    res = _rpc("tools/call", {"name": "convert_pdf",
                              "arguments": {"path": pdf, "max_chars": 50}})
    text = res["result"]["content"][0]["text"]
    assert "truncated at 50" in text


def test_convert_file_tool_writes_to_outdir(pdf, tmp_path):
    res = _rpc("tools/call",
               {"name": "convert_file",
                "arguments": {"path": pdf, "outdir": str(tmp_path)}})["result"]
    payload = json.loads(res["content"][0]["text"])
    assert os.path.isfile(payload["output"])
    assert payload["bytes"] > 0


def test_pdf_info_tool_reports_pages(pdf):
    res = _rpc("tools/call",
               {"name": "pdf_info", "arguments": {"path": pdf}})["result"]
    info = json.loads(res["content"][0]["text"])
    assert info["pages"] >= 1
    assert info["pages_needing_ocr"] == []
    assert isinstance(info["ocr_available"], bool)


def test_missing_file_is_a_tool_error_not_a_crash():
    res = _rpc("tools/call",
               {"name": "convert_pdf",
                "arguments": {"path": "/no/such.pdf"}})["result"]
    assert res["isError"] is True
    assert "not found" in res["content"][0]["text"]


def test_unknown_tool_is_a_protocol_error():
    assert _rpc("tools/call", {"name": "bogus"})["error"]["code"] == -32602


def test_notifications_get_no_response():
    assert mcp_server.handle_request(
        {"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_serve_loop_answers_line_delimited_json(pdf):
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
    )
    stdout = io.StringIO()
    assert mcp_server.serve(stdin, stdout) == 0
    lines = [json.loads(ln) for ln in stdout.getvalue().splitlines()]
    assert [m["id"] for m in lines] == [1, 2]  # the notification got no reply


def test_malformed_line_gets_a_parse_error():
    stdout = io.StringIO()
    mcp_server.serve(io.StringIO("{not json}\n"), stdout)
    assert json.loads(stdout.getvalue())["error"]["code"] == -32700
