import sys
from pathlib import Path

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from notify_me import _format_message, STATUS_SEVERITY, REQUIRES_ACTION, TYPE_ALIASES


def test_progress_format():
    result = _format_message("progress", "Dashboard started", [])
    assert result == "✅ Progress: Dashboard started"


def test_decision_format():
    result = _format_message("decision", "Choose DB", ["A: PostgreSQL", "B: Supabase"])
    assert "🤔 Decision needed:" in result
    assert "Choose DB" in result
    assert "A: PostgreSQL" in result
    assert "B: Supabase" in result
    assert "Reply with your choice." in result


def test_action_format():
    result = _format_message("manual_action", "Add API key to Railway", [])
    assert "🔧 Manual action needed:" in result
    assert "Add API key to Railway" in result
    assert "Reply DONE when complete." in result


def test_error_format():
    result = _format_message("error", "Tests failing in test_budget.py", [])
    assert "❌ Error:" in result
    assert "Tests failing in test_budget.py" in result


def test_completion_format():
    result = _format_message("completion", "Net worth tracker done.", [])
    assert "🎉 Complete:" in result
    assert "Net worth tracker done." in result


def test_handoff_format():
    result = _format_message("handoff", "", [])
    assert "🔄 Session handoff needed." in result
    assert "claude logout" in result
    assert "handoff/latest.md" in result


def test_severity_mapping():
    assert STATUS_SEVERITY["progress"] == "info"
    assert STATUS_SEVERITY["decision"] == "warning"
    assert STATUS_SEVERITY["manual_action"] == "warning"
    assert STATUS_SEVERITY["error"] == "error"
    assert STATUS_SEVERITY["completion"] == "info"
    assert STATUS_SEVERITY["handoff"] == "warning"


def test_requires_action_mapping():
    assert REQUIRES_ACTION["progress"] is False
    assert REQUIRES_ACTION["decision"] is True
    assert REQUIRES_ACTION["manual_action"] is True
    assert REQUIRES_ACTION["error"] is True
    assert REQUIRES_ACTION["completion"] is False
    assert REQUIRES_ACTION["handoff"] is True


def test_type_aliases():
    assert TYPE_ALIASES["action"] == "manual_action"
    assert TYPE_ALIASES["complete"] == "completion"
