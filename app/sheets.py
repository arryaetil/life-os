import json
import gspread
from google.oauth2.service_account import Credentials
from app import config

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_SHEET_NAME = "Transactions"
_HEADERS = [
    "ID", "Timestamp", "Date", "Week_Start", "Month",
    "Type", "Amount", "Description", "Category", "Tag",
    "Payment_Type", "Is_Impulse", "Is_Necessary", "Notes",
]

def _get_sheet() -> gspread.Worksheet:
    creds_dict = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=_SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        return spreadsheet.worksheet(_SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(_SHEET_NAME, rows=1000, cols=len(_HEADERS))
        sheet.append_row(_HEADERS)
        return sheet

def append_transaction(parsed: dict, category: str) -> int:
    sheet = _get_sheet()
    existing = sheet.get_all_records()
    new_id = len(existing) + 1

    row = [
        new_id,
        parsed["timestamp"],
        parsed["date"],
        parsed["week_start"],
        parsed["month"],
        parsed["type"],
        parsed["amount"],
        parsed["description"],
        category,
        "",   # Tag
        "",   # Payment_Type
        "TRUE" if parsed["is_impulse"] else "FALSE",
        "",   # Is_Necessary
        "",   # Notes
    ]
    sheet.append_row(row)
    return new_id

def get_all_transactions() -> list[dict]:
    sheet = _get_sheet()
    records = sheet.get_all_records()
    return [
        {
            "id": r.get("ID"),
            "timestamp": r.get("Timestamp"),
            "date": r.get("Date"),
            "week_start": r.get("Week_Start"),
            "month": r.get("Month"),
            "type": r.get("Type"),
            "amount": float(r.get("Amount") or 0),
            "description": r.get("Description", ""),
            "category": r.get("Category", "Other"),
            "tag": r.get("Tag", ""),
            "payment_type": r.get("Payment_Type", ""),
            "is_impulse": r.get("Is_Impulse") in ("TRUE", True),
            "is_necessary": r.get("Is_Necessary", ""),
            "notes": r.get("Notes", ""),
        }
        for r in records
    ]

def undo_last_transaction() -> dict | None:
    sheet = _get_sheet()
    records = sheet.get_all_records()
    if not records:
        return None
    last_row_index = len(records) + 1  # +1 for header row
    notes_col = _HEADERS.index("Notes") + 1   # 1-indexed
    sheet.update_cell(last_row_index, notes_col, "[UNDONE]")
    return records[-1]
