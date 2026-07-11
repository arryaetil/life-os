from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

MOCK_TRANSACTIONS = [
    {
        "id": 1, "date": "2026-05-15", "week_start": "2026-05-11",
        "month": "2026-05", "type": "Expense", "amount": 14.0,
        "description": "kebab", "category": "Food", "is_impulse": False,
        "notes": "", "tag": "", "payment_type": "", "is_necessary": "",
        "timestamp": "2026-05-15 12:00:00",
    },
    {
        "id": 2, "date": "2026-05-15", "week_start": "2026-05-11",
        "month": "2026-05", "type": "Income", "amount": 314.0,
        "description": "duo", "category": "Income", "is_impulse": False,
        "notes": "", "tag": "", "payment_type": "", "is_necessary": "",
        "timestamp": "2026-05-15 13:00:00",
    },
]

@pytest.fixture
def client():
    """TestClient with PTB lifespan mocked out. LOCAL_POLLING=True skips webhook registration."""
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, \
         patch("app.dashboard.config.LOCAL_POLLING", True):
        mock_ptb = AsyncMock()
        mock_factory.return_value = mock_ptb
        with TestClient(app) as c:
            yield c

def test_home_returns_financials(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS), \
         patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=None):
        response = client.get("/")
    assert response.status_code == 200
    assert "Financials" in response.text
    assert "Net Worth (Live)" in response.text

def test_expenses_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/expenses")
    assert response.status_code == 200

def test_expenses_contains_transaction_description(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/expenses")
    assert "kebab" in response.text

def test_expenses_contains_weekly_spent(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/expenses")
    assert "14.00" in response.text

def test_categories_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/categories")
    assert response.status_code == 200

def test_categories_shows_food(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/categories")
    assert "Food" in response.text

def test_transactions_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/transactions")
    assert response.status_code == 200

def test_transactions_shows_kebab(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/transactions")
    assert "kebab" in response.text

def test_webhook_rejects_wrong_secret():
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, \
         patch("app.dashboard.config.LOCAL_POLLING", True), \
         patch("app.dashboard.config.TELEGRAM_WEBHOOK_SECRET", "correct-secret"):
        mock_ptb = AsyncMock()
        mock_factory.return_value = mock_ptb
        with TestClient(app) as client:
            response = client.post(
                "/webhook",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )
    assert response.status_code == 403

def test_webhook_accepts_correct_secret():
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, \
         patch("app.dashboard.config.LOCAL_POLLING", True), \
         patch("app.dashboard.config.TELEGRAM_WEBHOOK_SECRET", "correct-secret"):
        mock_ptb = AsyncMock()
        mock_ptb.process_update = AsyncMock()
        mock_factory.return_value = mock_ptb
        with patch("app.dashboard._ptb_app", mock_ptb), \
             patch("telegram.Update.de_json", return_value=AsyncMock()):
            with TestClient(app) as client:
                response = client.post(
                    "/webhook",
                    json={"update_id": 1},
                    headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
                )
    assert response.status_code == 200

def test_networth_page_returns_200(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=None), \
         patch("app.dashboard.sheets.get_all_transactions", return_value=[]):
        response = client.get("/networth")
    assert response.status_code == 200

def test_financials_page_returns_200(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=None), \
         patch("app.dashboard.sheets.get_all_transactions", return_value=[]):
        response = client.get("/financials")
    assert response.status_code == 200

def test_networth_page_empty_state(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=None), \
         patch("app.dashboard.sheets.get_all_transactions", return_value=[]):
        response = client.get("/networth")
    assert "No Net Worth" in response.text or "No net worth" in response.text

def test_networth_page_shows_total_when_data(client):
    snap = {
        "id": 1, "timestamp": "2026-05-15T10:00:00+00:00",
        "cash": 2000.0, "investments": 8000.0, "crypto": 0.0,
        "savings": 3000.0, "other_assets": 0.0, "liabilities": 0.0,
        "total_net_worth": 13000.0, "notes": "",
    }
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[snap]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=snap):
        response = client.get("/networth")
    assert "13000.00" in response.text


def test_networth_chart_uses_transaction_adjusted_series(client):
    snap = {
        "id": 1, "timestamp": "2026-05-15T10:00:00+00:00",
        "cash": 2000.0, "investments": 8000.0, "crypto": 0.0,
        "savings": 5000.0, "other_assets": 0.0, "liabilities": 0.0,
        "total_net_worth": 15000.0, "notes": "",
    }
    txns = [
        {"id": 1, "timestamp": "2026-05-15 11:00:00", "type": "Expense", "amount": 14.0, "notes": ""},
        {"id": 2, "timestamp": "2026-05-15 12:00:00", "type": "Expense", "amount": 122.0, "notes": ""},
        {"id": 3, "timestamp": "2026-05-15 13:00:00", "type": "Income", "amount": 314.0, "notes": ""},
        {"id": 4, "timestamp": "2026-05-15 14:00:00", "type": "Transfer", "amount": 500.0, "notes": ""},
    ]
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[snap]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=snap), \
         patch("app.dashboard.sheets.get_all_transactions", return_value=txns):
        response = client.get("/networth")
    assert "15178.00" in response.text
    assert "[15000.0, 14986.0, 14864.0, 15178.0]" in response.text


def test_networth_page_shows_activity_feed_not_snapshot_table(client):
    snap = {
        "id": 1, "timestamp": "2026-05-15T10:00:00+00:00",
        "cash": 2000.0, "investments": 8000.0, "crypto": 0.0,
        "savings": 5000.0, "other_assets": 0.0, "liabilities": 0.0,
        "total_net_worth": 15000.0, "notes": "",
    }
    txns = [
        {"id": 1, "timestamp": "2026-05-15 11:00:00", "type": "Expense", "amount": 14.0, "notes": "", "description": "kebab"},
        {"id": 2, "timestamp": "2026-05-15 12:00:00", "type": "Income", "amount": 314.0, "notes": "", "description": "duo"},
        {"id": 3, "timestamp": "2026-05-15 13:00:00", "type": "Transfer", "amount": 500.0, "notes": "", "description": "savings"},
    ]
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[snap]), \
         patch("app.dashboard.sheets.get_first_net_worth_snapshot", return_value=snap), \
         patch("app.dashboard.sheets.get_all_transactions", return_value=txns):
        response = client.get("/networth")
    assert "Net Worth Activity" in response.text
    assert "Recent Snapshots" not in response.text
    assert "kebab" in response.text
    assert "duo" in response.text
    assert "savings" not in response.text
    assert "Baseline" in response.text


def test_api_categories_returns_list(client):
    with patch("app.dashboard.get_available_categories", return_value=["Food", "Transport", "Other"]):
        response = client.get("/api/categories")
    assert response.status_code == 200
    assert response.json() == ["Food", "Transport", "Other"]


def test_api_create_transaction_with_explicit_category(client):
    with patch("app.dashboard.sheets.append_transaction", return_value=42) as mock_append:
        response = client.post("/api/transactions", json={
            "type": "Expense",
            "amount": 7.5,
            "description": "groceries",
            "category": "Food",
            "date": "2026-06-09",
            "is_impulse": False,
        })

    assert response.status_code == 200
    assert response.json() == {"ok": True, "id": 42, "category": "Food"}

    parsed, category = mock_append.call_args[0]
    assert category == "Food"
    assert parsed["type"] == "Expense"
    assert parsed["amount"] == 7.5
    assert parsed["description"] == "groceries"
    assert parsed["date"] == "2026-06-09"
    assert parsed["week_start"] == "2026-06-08"
    assert parsed["month"] == "2026-06"
    assert parsed["is_impulse"] is False


def test_api_create_transaction_auto_categorizes_when_blank(client):
    with patch("app.dashboard.sheets.append_transaction", return_value=43) as mock_append, \
         patch("app.dashboard.get_category", return_value="Transport") as mock_get_category:
        response = client.post("/api/transactions", json={
            "type": "Expense",
            "amount": 20.40,
            "description": "fuel",
            "category": "",
            "date": "2026-06-09",
        })

    assert response.status_code == 200
    assert response.json()["category"] == "Transport"
    mock_get_category.assert_called_once_with("fuel")
    _, category = mock_append.call_args[0]
    assert category == "Transport"


def test_api_create_transaction_defaults_to_today_when_no_date(client):
    with patch("app.dashboard.sheets.append_transaction", return_value=44) as mock_append:
        response = client.post("/api/transactions", json={
            "type": "Income",
            "amount": 100.0,
            "description": "freelance",
            "category": "Income",
        })

    assert response.status_code == 200
    parsed, _ = mock_append.call_args[0]
    assert parsed["date"] == datetime.now().strftime("%Y-%m-%d")


def test_api_create_transaction_rejects_non_positive_amount(client):
    response = client.post("/api/transactions", json={
        "type": "Expense", "amount": 0, "description": "free thing", "category": "Other",
    })
    assert response.status_code == 400


def test_api_create_transaction_rejects_missing_description(client):
    response = client.post("/api/transactions", json={
        "type": "Expense", "amount": 5.0, "description": "  ", "category": "Other",
    })
    assert response.status_code == 400


def test_api_create_transaction_rejects_invalid_type(client):
    response = client.post("/api/transactions", json={
        "type": "Bogus", "amount": 5.0, "description": "x", "category": "Other",
    })
    assert response.status_code == 400
