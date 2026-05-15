import pytest
from sqlalchemy import create_engine
from app import database as db

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db, "_engine", engine)
    db.init_db()
    yield engine

def test_create_snapshot_returns_id():
    row_id = db.create_net_worth_snapshot({"cash": 1000.0})
    assert row_id == 1

def test_create_snapshot_calculates_total_net_worth():
    db.create_net_worth_snapshot({
        "cash": 1000.0,
        "investments": 5000.0,
        "crypto": 500.0,
        "savings": 2000.0,
        "other_assets": 0.0,
        "liabilities": 1000.0,
    })
    snap = db.get_latest_net_worth_snapshot()
    assert snap["total_net_worth"] == pytest.approx(7500.0)

def test_create_snapshot_liabilities_subtracted():
    db.create_net_worth_snapshot({"cash": 5000.0, "liabilities": 2000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["total_net_worth"] == pytest.approx(3000.0)

def test_get_latest_returns_none_when_empty():
    assert db.get_latest_net_worth_snapshot() is None

def test_get_latest_returns_most_recent():
    db.create_net_worth_snapshot({"cash": 1000.0})
    db.create_net_worth_snapshot({"cash": 2000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["cash"] == pytest.approx(2000.0)

def test_get_history_empty():
    assert db.get_net_worth_history() == []

def test_get_history_returns_oldest_first():
    db.create_net_worth_snapshot({"cash": 1000.0, "notes": "first"})
    db.create_net_worth_snapshot({"cash": 2000.0, "notes": "second"})
    history = db.get_net_worth_history()
    assert len(history) == 2
    assert history[0]["notes"] == "first"
    assert history[1]["notes"] == "second"

def test_get_history_respects_limit():
    for i in range(10):
        db.create_net_worth_snapshot({"cash": float(i * 100)})
    history = db.get_net_worth_history(limit=5)
    assert len(history) == 5

def test_snapshot_defaults_missing_fields_to_zero():
    db.create_net_worth_snapshot({"investments": 8000.0})
    snap = db.get_latest_net_worth_snapshot()
    assert snap["cash"] == pytest.approx(0.0)
    assert snap["liabilities"] == pytest.approx(0.0)
    assert snap["total_net_worth"] == pytest.approx(8000.0)
