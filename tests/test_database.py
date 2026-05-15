# tests/test_database.py
import pytest
from sqlalchemy import create_engine
from app import database as db

PARSED = {
    "amount": 14.0,
    "description": "kebab",
    "type": "Expense",
    "is_impulse": False,
    "timestamp": "2026-05-15 12:00:00",
    "date": "2026-05-15",
    "week_start": "2026-05-11",
    "month": "2026-05",
}

@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    """Each test gets a fresh in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db, "_engine", engine)
    db.init_db()
    yield engine

def test_append_transaction_returns_id():
    row_id = db.append_transaction(PARSED, "Food")
    assert row_id == 1

def test_append_transaction_increments_id():
    id1 = db.append_transaction(PARSED, "Food")
    id2 = db.append_transaction(PARSED, "Food")
    assert id2 == id1 + 1

def test_append_transaction_stores_correct_fields():
    db.append_transaction(PARSED, "Food")
    rows = db.get_all_transactions()
    assert len(rows) == 1
    t = rows[0]
    assert t["amount"] == 14.0
    assert t["description"] == "kebab"
    assert t["category"] == "Food"
    assert t["type"] == "Expense"
    assert t["is_impulse"] is False

def test_append_impulse_true():
    parsed_impulse = {**PARSED, "is_impulse": True}
    db.append_transaction(parsed_impulse, "Impulse")
    rows = db.get_all_transactions()
    assert rows[0]["is_impulse"] is True

def test_get_all_transactions_empty():
    rows = db.get_all_transactions()
    assert rows == []

def test_get_all_transactions_ordered_by_id():
    db.append_transaction({**PARSED, "description": "first"}, "Food")
    db.append_transaction({**PARSED, "description": "second"}, "Food")
    rows = db.get_all_transactions()
    assert rows[0]["description"] == "first"
    assert rows[1]["description"] == "second"

def test_undo_last_marks_undone():
    db.append_transaction(PARSED, "Food")
    result = db.undo_last_transaction()
    assert result is not None
    rows = db.get_all_transactions()
    assert rows[-1]["notes"] == "[UNDONE]"

def test_undo_returns_the_record():
    db.append_transaction({**PARSED, "description": "kebab"}, "Food")
    result = db.undo_last_transaction()
    assert result["description"] == "kebab"

def test_undo_empty_db_returns_none():
    result = db.undo_last_transaction()
    assert result is None

def test_undo_marks_last_not_first():
    db.append_transaction({**PARSED, "description": "first"}, "Food")
    db.append_transaction({**PARSED, "description": "second"}, "Food")
    db.undo_last_transaction()
    rows = db.get_all_transactions()
    assert rows[0]["notes"] == ""
    assert rows[1]["notes"] == "[UNDONE]"
