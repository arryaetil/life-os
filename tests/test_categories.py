from unittest.mock import patch, MagicMock
from app.categories import get_category, _keyword_match

def test_food_kebab():
    assert get_category("kebab") == "Food"

def test_food_coffee():
    assert get_category("coffee with a friend") == "Food"

def test_food_grocery():
    assert get_category("lidl groceries") == "Food"

def test_social_date():
    assert get_category("date at cinema") == "Social"

def test_transport_uber():
    assert get_category("uber home") == "Transport"

def test_transport_ns():
    assert get_category("ns train ticket") == "Transport"

def test_project_api():
    assert get_category("api credits openai") == "Project"

def test_health_gym():
    assert get_category("gym monthly") == "Health"

def test_income_duo():
    assert get_category("duo payment") == "Income"

def test_investment_degiro():
    assert get_category("degiro etf") == "Investment"

def test_keyword_match_returns_none_for_unknown():
    assert _keyword_match("xyz123 unknownterm") is None

def test_ai_fallback_openai(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Food"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.categories.OpenAI", return_value=mock_client):
        result = get_category("donor wrap")

    assert result == "Food"

def test_ai_fallback_anthropic(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "ant-test")

    mock_response = MagicMock()
    mock_response.content[0].text = "Food"
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.categories.Anthropic", return_value=mock_client):
        result = get_category("donor wrap")

    assert result == "Food"

def test_no_key_returns_other(monkeypatch):
    monkeypatch.setattr("app.categories.config.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.categories.config.ANTHROPIC_API_KEY", "")
    assert get_category("xyzunknown123") == "Other"

def test_no_false_positive_ah():
    # "ah" was removed from Food keywords to prevent "thanks", "cash" matching
    assert _keyword_match("thanks for the cash payment") is None

def test_no_false_positive_ov():
    # "ov" was removed from Transport keywords to prevent "oven", "loved" matching
    assert _keyword_match("bought an oven") is None


from app.categories import normalize_category, KNOWN_CATEGORIES


def test_normalize_known_category_passthrough():
    assert normalize_category("Food") == "Food"
    assert normalize_category("Transport") == "Transport"
    assert normalize_category("Health") == "Health"


def test_normalize_synonym_maps_to_canonical():
    assert normalize_category("Eating") == "Food"
    assert normalize_category("Meals") == "Food"
    assert normalize_category("Fitness") == "Health"
    assert normalize_category("Sports") == "Health"
    assert normalize_category("Gas") == "Transport"
    assert normalize_category("Fuel") == "Transport"
    assert normalize_category("Shopping") == "Clothing"


def test_normalize_title_cases_dynamic_category():
    assert normalize_category("sports gear") == "Sports Gear"
    assert normalize_category("unknown item") == "Unknown Item"


def test_normalize_empty_returns_other():
    assert normalize_category("") == "Other"
    assert normalize_category("   ") == "Other"


def test_normalize_case_insensitive_synonym():
    assert normalize_category("eating") == "Food"
    assert normalize_category("MEALS") == "Food"
