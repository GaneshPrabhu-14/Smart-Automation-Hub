import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub import config, llm, tools
from hub.agent import Agent, _tool_result_content


def _clean():
    config.TASKS_FILE.unlink(missing_ok=True)
    config.DRAFTS_FILE.unlink(missing_ok=True)


def test_analyze_data():
    out = tools.call_tool("analyze_data", {"file": "sales.csv"})
    assert out["top"] == "North" and out["rows"] == 10


def test_read_emails_uses_small_defaults_and_caps_bodies(monkeypatch):
    monkeypatch.setattr(config, "DEFAULT_EMAILS", 5)
    monkeypatch.setattr(config, "EMAIL_BODY_CHARS", 12)
    monkeypatch.setattr(config, "EMAIL_LIVE", False)

    emails = tools.read_emails()

    assert len(emails) == 5
    assert all(len(item["body"]) <= 12 for item in emails)


def test_read_emails_never_exceeds_hard_limit(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LIVE", False)
    assert len(tools.read_emails(limit=100)) <= config.MAX_EMAILS


def test_live_email_bodies_are_truncated(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LIVE", True)
    monkeypatch.setattr(config, "EMAIL_BODY_CHARS", 8)
    monkeypatch.setattr(
        tools, "_fetch_imap", lambda limit, unread_only: [{"body": "long body text"}]
    )
    assert tools.read_emails()[0]["body"] == "long bod"


def test_tool_result_is_capped_and_remains_json():
    content = _tool_result_content({"body": ("x" * 10000) + ("😄" * 1000)})
    parsed = json.loads(content)
    assert len(content) <= config.MAX_TOOL_RESULT_CHARS
    assert parsed["truncated"] is True
    assert parsed["original_characters"] > config.MAX_TOOL_RESULT_CHARS
    assert parsed["preview"]


def test_llm_retries_rate_limit_once_after_delay(monkeypatch):
    class FakeRateLimitError(Exception):
        pass

    monkeypatch.setattr(llm, "RATE_LIMIT_ERRORS", (FakeRateLimitError,))
    monkeypatch.setattr(config, "LLM_RATE_LIMIT_RETRY_SECONDS", 30)
    sleep = Mock()
    monkeypatch.setattr(llm.time, "sleep", sleep)
    create = Mock(side_effect=[FakeRateLimitError("rate limited"), "success"])

    client = llm.LLM()
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert client.complete([{"role": "user", "content": "hello"}]) == "success"
    assert create.call_count == 2
    sleep.assert_called_once_with(30)


def test_unknown_tool_is_handled():
    assert "error" in tools.call_tool("nope", {})


def test_email_to_tasks_flow(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LIVE", False)
    _clean()
    res = Agent()._run_offline("Summarize today's important emails and create a task list")
    assert [s.tool for s in res.steps] == ["read_emails", "create_tasks"]
    assert len(json.loads(config.TASKS_FILE.read_text())) >= 3


def test_reply_creates_drafts_not_sends(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LIVE", False)
    _clean()
    Agent()._run_offline("Reply to my important emails")
    drafts = json.loads(config.DRAFTS_FILE.read_text())
    assert len(drafts) >= 3 and all(d["status"] == "draft" for d in drafts)


def test_send_is_blocked_without_permission(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_LIVE", False)
    monkeypatch.setattr(config, "ALLOW_AGENT_SEND", False)
    _clean()
    tools.STATE["user_asked_send"] = True
    out = tools.call_tool("send_email", {"to": "a@b.com", "subject": "x", "body": "y"})
    assert out["status"] == "draft_saved"  # ALLOW_AGENT_SEND is false by default


def test_report_flow():
    res = Agent()._run_offline("Analyze sales data and generate a report")
    assert res.steps[-1].tool == "generate_report"
