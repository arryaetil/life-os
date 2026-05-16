import pytest
from app.networth import (
    calculate_net_worth,
    calculate_goal_progress,
    calculate_change,
    ascii_progress_bar,
    GOALS,
    calculate_live_net_worth,
    calculate_monthly_change,
)


def test_calculate_net_worth_sums_assets():
    snap = {"cash": 1000.0, "investments": 5000.0, "crypto": 500.0,
            "savings": 2000.0, "other_assets": 0.0, "liabilities": 0.0}
    assert calculate_net_worth(snap) == pytest.approx(8500.0)


def test_calculate_net_worth_subtracts_liabilities():
    snap = {"cash": 5000.0, "investments": 0.0, "crypto": 0.0,
            "savings": 0.0, "other_assets": 0.0, "liabilities": 1500.0}
    assert calculate_net_worth(snap) == pytest.approx(3500.0)


def test_calculate_net_worth_handles_missing_keys():
    assert calculate_net_worth({"cash": 2000.0}) == pytest.approx(2000.0)


def test_goal_progress_pct_correct():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["pct"] == pytest.approx(50.0)


def test_goal_progress_remaining_correct():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["remaining"] == pytest.approx(12500.0)


def test_goal_progress_not_achieved():
    result = calculate_goal_progress(12500.0, 25000.0)
    assert result["achieved"] is False


def test_goal_progress_achieved():
    result = calculate_goal_progress(25000.0, 25000.0)
    assert result["achieved"] is True
    assert result["remaining"] == pytest.approx(0.0)


def test_goal_progress_over_100_clamped():
    result = calculate_goal_progress(30000.0, 25000.0)
    assert result["pct"] == pytest.approx(100.0)
    assert result["remaining"] == pytest.approx(0.0)


def test_calculate_change_returns_none_for_single_snapshot():
    history = [{"total_net_worth": 10000.0}]
    assert calculate_change(history) is None


def test_calculate_change_positive_delta():
    history = [
        {"total_net_worth": 10000.0},
        {"total_net_worth": 12000.0},
    ]
    result = calculate_change(history)
    assert result["delta"] == pytest.approx(2000.0)
    assert result["direction"] == "up"


def test_calculate_change_negative_delta():
    history = [
        {"total_net_worth": 12000.0},
        {"total_net_worth": 10000.0},
    ]
    result = calculate_change(history)
    assert result["delta"] == pytest.approx(-2000.0)
    assert result["direction"] == "down"


def test_calculate_change_empty_returns_none():
    assert calculate_change([]) is None


def test_ascii_progress_bar_full():
    assert ascii_progress_bar(100.0) == "▓▓▓▓▓▓▓▓▓▓"


def test_ascii_progress_bar_empty():
    assert ascii_progress_bar(0.0) == "░░░░░░░░░░"


def test_ascii_progress_bar_half():
    bar = ascii_progress_bar(50.0)
    assert bar == "▓▓▓▓▓░░░░░"


# --- calculate_live_net_worth ---

def _make_baseline(total: float, timestamp: str = "2026-05-01T00:00:00+00:00") -> dict:
    return {"total_net_worth": total, "timestamp": timestamp}

def _make_txn(type_: str, amount: float, ts: str = "2026-05-10T12:00:00+00:00", undone: bool = False) -> dict:
    return {"type": type_, "amount": amount, "timestamp": ts, "notes": "[UNDONE]" if undone else ""}


def test_live_nw_no_transactions():
    baseline = _make_baseline(15000.0)
    assert calculate_live_net_worth(baseline, []) == 15000.0


def test_live_nw_adds_income():
    baseline = _make_baseline(15000.0)
    txns = [_make_txn("Income", 500.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15500.0)


def test_live_nw_subtracts_expense():
    baseline = _make_baseline(15000.0)
    txns = [_make_txn("Expense", 200.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(14800.0)


def test_live_nw_ignores_transfer():
    baseline = _make_baseline(15000.0)
    txns = [_make_txn("Transfer", 1000.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)


def test_live_nw_ignores_investment():
    baseline = _make_baseline(15000.0)
    txns = [_make_txn("Investment", 500.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)


def test_live_nw_ignores_undone_transactions():
    baseline = _make_baseline(15000.0)
    txns = [_make_txn("Income", 500.0, undone=True)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)


def test_live_nw_ignores_transactions_before_baseline():
    baseline = _make_baseline(15000.0, timestamp="2026-05-10T00:00:00+00:00")
    txns = [_make_txn("Income", 500.0, ts="2026-05-09T12:00:00+00:00")]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)


def test_live_nw_none_baseline_returns_zero():
    assert calculate_live_net_worth(None, []) == 0.0


def test_live_nw_combined():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        _make_txn("Income", 500.0),
        _make_txn("Expense", 100.0),
        _make_txn("Transfer", 200.0),  # ignored
        _make_txn("Income", 300.0, undone=True),  # ignored
    ]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15400.0)


# --- calculate_monthly_change ---

def test_monthly_change_no_pre_month_history():
    history = [
        {"timestamp": "2026-05-10T00:00:00+00:00", "total_net_worth": 15000.0},
    ]
    result = calculate_monthly_change(15500.0, history, reference_month="2026-05")
    assert result is None


def test_monthly_change_empty_history():
    assert calculate_monthly_change(15500.0, [], reference_month="2026-05") is None


def test_monthly_change_positive_delta():
    history = [
        {"timestamp": "2026-04-30T00:00:00+00:00", "total_net_worth": 14000.0},
        {"timestamp": "2026-05-10T00:00:00+00:00", "total_net_worth": 15000.0},
    ]
    result = calculate_monthly_change(15500.0, history, reference_month="2026-05")
    assert result is not None
    assert result["delta"] == pytest.approx(1500.0)
    assert result["direction"] == "up"


def test_monthly_change_negative_delta():
    history = [
        {"timestamp": "2026-04-30T00:00:00+00:00", "total_net_worth": 16000.0},
    ]
    result = calculate_monthly_change(15500.0, history, reference_month="2026-05")
    assert result is not None
    assert result["delta"] == pytest.approx(-500.0)
    assert result["direction"] == "down"


def test_monthly_change_uses_latest_pre_month_snapshot():
    history = [
        {"timestamp": "2026-03-15T00:00:00+00:00", "total_net_worth": 12000.0},
        {"timestamp": "2026-04-28T00:00:00+00:00", "total_net_worth": 14000.0},
    ]
    result = calculate_monthly_change(15000.0, history, reference_month="2026-05")
    assert result["delta"] == pytest.approx(1000.0)  # 15000 - 14000


# --- GOALS updated to €30K only ---

def test_goals_has_only_30k():
    targets = {g["target"] for g in GOALS}
    assert 30_000.0 in targets
    assert 25_000.0 not in targets


def test_goals_length_is_one():
    assert len(GOALS) == 1


def test_monthly_change_unsorted_history_uses_latest():
    """History passed newest-first must still use the most recent pre-month snapshot."""
    history = [
        {"timestamp": "2026-04-28T00:00:00+00:00", "total_net_worth": 14000.0},
        {"timestamp": "2026-03-15T00:00:00+00:00", "total_net_worth": 12000.0},
    ]
    result = calculate_monthly_change(15000.0, history, reference_month="2026-05")
    assert result["delta"] == pytest.approx(1000.0)  # 15000 - 14000, not 15000 - 12000
