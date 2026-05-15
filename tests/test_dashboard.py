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

def test_home_returns_200(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/")
    assert response.status_code == 200

def test_home_contains_transaction_description(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/")
    assert "kebab" in response.text

def test_home_contains_weekly_spent(client):
    with patch("app.dashboard.sheets.get_all_transactions", return_value=MOCK_TRANSACTIONS):
        response = client.get("/")
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
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=None):
        response = client.get("/networth")
    assert response.status_code == 200

def test_networth_page_empty_state(client):
    with patch("app.dashboard.sheets.get_net_worth_history", return_value=[]), \
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=None):
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
         patch("app.dashboard.sheets.get_latest_net_worth_snapshot", return_value=snap):
        response = client.get("/networth")
    assert "13000.00" in response.text
