import pytest
from sqlalchemy import create_engine
from app import database as db


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db, "_engine", engine)
    db.init_db()
    yield engine


def test_read_returns_none_when_empty():
    assert db.read_latest_agent_state() is None


def test_write_and_read():
    db.write_agent_state({
        "status_type": "progress",
        "severity": "info",
        "requires_user_action": False,
        "resolved": False,
        "progress_message": "Test progress",
    })
    state = db.read_latest_agent_state()
    assert state is not None
    assert state["status_type"] == "progress"
    assert state["progress_message"] == "Test progress"
    assert state["severity"] == "info"


def test_read_returns_latest():
    db.write_agent_state({"status_type": "progress", "progress_message": "first"})
    db.write_agent_state({"status_type": "error", "progress_message": "second"})
    state = db.read_latest_agent_state()
    assert state["progress_message"] == "second"
    assert state["status_type"] == "error"


def test_timestamp_auto_set():
    db.write_agent_state({"status_type": "progress"})
    state = db.read_latest_agent_state()
    assert state["timestamp"] is not None
    assert "T" in state["timestamp"]


def test_read_by_status_type():
    db.write_agent_state({"status_type": "progress", "progress_message": "p1"})
    db.write_agent_state({"status_type": "handoff", "progress_message": "h1"})
    db.write_agent_state({"status_type": "progress", "progress_message": "p2"})
    handoff_state = db.read_latest_agent_state(status_type="handoff")
    assert handoff_state["status_type"] == "handoff"
    assert handoff_state["progress_message"] == "h1"


def test_read_by_type_returns_none_when_no_match():
    db.write_agent_state({"status_type": "progress"})
    state = db.read_latest_agent_state(status_type="handoff")
    assert state is None


def test_read_pending_action_returns_none_when_empty():
    assert db.read_pending_action() is None


def test_read_pending_action_returns_none_when_resolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": True,
    })
    assert db.read_pending_action() is None


def test_read_pending_action_returns_latest_unresolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "first question",
    })
    db.write_agent_state({
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "second question",
    })
    result = db.read_pending_action()
    assert result is not None
    assert result["progress_message"] == "second question"


def test_read_pending_action_ignores_progress_rows():
    db.write_agent_state({
        "status_type": "progress",
        "requires_user_action": False,
        "resolved": False,
    })
    assert db.read_pending_action() is None


def test_resolve_agent_state_marks_row_resolved():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
    })
    pending = db.read_pending_action()
    assert pending is not None
    db.resolve_agent_state(pending["id"])
    assert db.read_pending_action() is None


def test_resolve_agent_state_only_affects_target_row():
    db.write_agent_state({
        "status_type": "decision",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "first",
    })
    db.write_agent_state({
        "status_type": "manual_action",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": "second",
    })
    first = db.read_latest_agent_state(status_type="decision")
    db.resolve_agent_state(first["id"])
    still_pending = db.read_pending_action()
    assert still_pending is not None
    assert still_pending["progress_message"] == "second"
