from app.networth_parser import is_net_worth_message, parse_net_worth_message
import pytest


# --- is_net_worth_message ---

def test_detects_net_worth_prefix():
    assert is_net_worth_message("net worth cash 3000 investments 9000") is True

def test_detects_update_net_worth():
    assert is_net_worth_message("update net worth cash 2500 savings 4000") is True

def test_detects_networth_no_space():
    assert is_net_worth_message("networth cash 2k") is True

def test_detects_nw_abbreviation():
    assert is_net_worth_message("nw cash 2k savings 5k") is True

def test_detects_two_nw_keywords():
    assert is_net_worth_message("investments 12k crypto 3k liabilities 1k") is True

def test_detects_three_nw_keywords():
    assert is_net_worth_message("cash 2k savings 5k investments 10k") is True

def test_rejects_regular_transaction():
    assert is_net_worth_message("14 kebab food") is False

def test_rejects_single_nw_keyword_no_trigger():
    assert is_net_worth_message("50 savings account transfer") is False


# --- parse_net_worth_message (regex path, no AI key) ---

def test_parses_full_message():
    result = parse_net_worth_message("net worth cash 3000 investments 9000 crypto 2000")
    assert result["cash"] == pytest.approx(3000.0)
    assert result["investments"] == pytest.approx(9000.0)
    assert result["crypto"] == pytest.approx(2000.0)

def test_parses_k_suffix():
    result = parse_net_worth_message("net worth cash 2k savings 5k investments 10k")
    assert result["cash"] == pytest.approx(2000.0)
    assert result["savings"] == pytest.approx(5000.0)
    assert result["investments"] == pytest.approx(10000.0)

def test_parses_liabilities():
    result = parse_net_worth_message("net worth investments 12k liabilities 2k")
    assert result["liabilities"] == pytest.approx(2000.0)

def test_parses_debt_as_liabilities():
    result = parse_net_worth_message("net worth savings 3000 debt 500")
    assert result["liabilities"] == pytest.approx(500.0)

def test_parses_total_only():
    result = parse_net_worth_message("net worth 15k total")
    assert result["other_assets"] == pytest.approx(15000.0)
    assert result["cash"] == pytest.approx(0.0)
    assert result["liabilities"] == pytest.approx(0.0)

def test_missing_fields_default_to_zero():
    result = parse_net_worth_message("net worth cash 3000")
    assert result["investments"] == pytest.approx(0.0)
    assert result["liabilities"] == pytest.approx(0.0)

def test_returns_all_expected_keys():
    result = parse_net_worth_message("net worth cash 1000")
    assert set(result.keys()) == {"cash", "investments", "crypto", "savings", "other_assets", "liabilities"}
