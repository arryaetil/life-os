from unittest.mock import patch, MagicMock
from app.sheets import append_transaction, get_all_transactions, undo_last_transaction

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

def _mock_sheet(records=None):
    sheet = MagicMock()
    sheet.get_all_records.return_value = records or []
    return sheet

def _patch_sheet(sheet):
    return patch("app.sheets._get_sheet", return_value=sheet)

def test_append_transaction_appends_correct_row():
    sheet = _mock_sheet(records=[{"ID": 1}])
    with _patch_sheet(sheet):
        row_id = append_transaction(PARSED, "Food")

    assert row_id == 2
    appended = sheet.append_row.call_args[0][0]
    assert appended[0] == 2          # ID
    assert appended[5] == "Expense"  # Type
    assert appended[6] == 14.0       # Amount
    assert appended[7] == "kebab"    # Description
    assert appended[8] == "Food"     # Category
    assert appended[11] == "FALSE"   # Is_Impulse

def test_append_transaction_impulse_true():
    parsed_impulse = {**PARSED, "is_impulse": True}
    sheet = _mock_sheet(records=[])
    with _patch_sheet(sheet):
        append_transaction(parsed_impulse, "Impulse")

    appended = sheet.append_row.call_args[0][0]
    assert appended[11] == "TRUE"

def test_append_transaction_id_increments():
    # With 5 existing records, new ID should be 6
    existing = [{"ID": i} for i in range(1, 6)]
    sheet = _mock_sheet(records=existing)
    with _patch_sheet(sheet):
        row_id = append_transaction(PARSED, "Food")
    assert row_id == 6

def test_get_all_transactions_normalizes_fields():
    raw = [{
        "ID": 1, "Timestamp": "2026-05-15 12:00:00", "Date": "2026-05-15",
        "Week_Start": "2026-05-11", "Month": "2026-05", "Type": "Expense",
        "Amount": 14.0, "Description": "kebab", "Category": "Food",
        "Tag": "", "Payment_Type": "", "Is_Impulse": "FALSE",
        "Is_Necessary": "", "Notes": "",
    }]
    sheet = _mock_sheet(records=raw)
    with _patch_sheet(sheet):
        result = get_all_transactions()

    assert len(result) == 1
    t = result[0]
    assert t["amount"] == 14.0
    assert t["is_impulse"] is False
    assert t["category"] == "Food"
    assert t["notes"] == ""

def test_get_all_transactions_is_impulse_true_string():
    raw = [{
        "ID": 1, "Timestamp": "", "Date": "", "Week_Start": "", "Month": "",
        "Type": "Expense", "Amount": 25.0, "Description": "impulse", "Category": "Impulse",
        "Tag": "", "Payment_Type": "", "Is_Impulse": "TRUE",
        "Is_Necessary": "", "Notes": "",
    }]
    sheet = _mock_sheet(records=raw)
    with _patch_sheet(sheet):
        result = get_all_transactions()
    assert result[0]["is_impulse"] is True

def test_get_all_transactions_empty():
    sheet = _mock_sheet(records=[])
    with _patch_sheet(sheet):
        result = get_all_transactions()
    assert result == []

def test_undo_last_transaction_writes_undone_note():
    raw = [
        {"ID": 1, "Amount": 14.0, "Description": "kebab"},
        {"ID": 2, "Amount": 8.5, "Description": "coffee"},
    ]
    sheet = _mock_sheet(records=raw)
    with _patch_sheet(sheet):
        result = undo_last_transaction()

    assert result["Description"] == "coffee"
    # Notes column is index 13 in HEADERS (0-indexed), so 1-indexed = 14
    sheet.update_cell.assert_called_once_with(3, 14, "[UNDONE]")

def test_undo_on_empty_sheet_returns_none():
    sheet = _mock_sheet(records=[])
    with _patch_sheet(sheet):
        result = undo_last_transaction()
    assert result is None
