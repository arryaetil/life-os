import pytest
from datetime import datetime, timedelta
from app.networth import (
    calculate_net_worth,
    calculate_goal_progress,
    calculate_change,
    ascii_progress_bar,
    GOALS,
    build_net_worth_activity_feed,
    build_net_worth_chart_series,
    calculate_live_net_worth,
    calculate_live_net_worth_series,
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


def test_live_nw_series_starts_with_baseline():
    baseline = _make_baseline(15000.0)
    series = calculate_live_net_worth_series(baseline, [])
    assert series == [{
        "timestamp": "2026-05-01T00:00:00+00:00",
        "label": "2026-05-01",
        "total_net_worth": 15000.0,
        "source": "snapshot",
    }]


def test_live_nw_series_applies_income_and_expenses_chronologically():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        _make_txn("Income", 314.0, ts="2026-05-04T12:00:00+00:00"),
        _make_txn("Expense", 122.0, ts="2026-05-03T12:00:00+00:00"),
        _make_txn("Expense", 14.0, ts="2026-05-02T12:00:00+00:00"),
    ]
    series = calculate_live_net_worth_series(baseline, txns)
    assert [p["total_net_worth"] for p in series] == [
        15000.0,
        14986.0,
        14864.0,
        15178.0,
    ]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15178.0)


def test_live_nw_series_ignores_transfer_investment_and_undone():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        _make_txn("Transfer", 1000.0, ts="2026-05-02T12:00:00+00:00"),
        _make_txn("Investment", 500.0, ts="2026-05-03T12:00:00+00:00"),
        _make_txn("Expense", 25.0, ts="2026-05-04T12:00:00+00:00", undone=True),
        _make_txn("Expense", 40.0, ts="2026-05-05T12:00:00+00:00"),
    ]
    series = calculate_live_net_worth_series(baseline, txns)
    assert [p["total_net_worth"] for p in series] == [15000.0, 14960.0]


def test_live_nw_series_ignores_transactions_before_baseline():
    baseline = _make_baseline(15000.0, timestamp="2026-05-10T00:00:00+00:00")
    txns = [
        _make_txn("Income", 500.0, ts="2026-05-09T12:00:00+00:00"),
        _make_txn("Expense", 100.0, ts="2026-05-10T12:00:00+00:00"),
    ]
    series = calculate_live_net_worth_series(baseline, txns)
    assert [p["total_net_worth"] for p in series] == [15000.0, 14900.0]


def test_chart_series_keeps_every_point_for_small_dataset():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        _make_txn("Expense", 14.0, ts="2026-05-02T12:00:00+00:00"),
        _make_txn("Expense", 122.0, ts="2026-05-03T12:00:00+00:00"),
        _make_txn("Income", 314.0, ts="2026-05-04T12:00:00+00:00"),
    ]
    series = build_net_worth_chart_series(baseline, txns)
    assert [p["total_net_worth"] for p in series] == [15000.0, 14986.0, 14864.0, 15178.0]


def test_chart_series_daily_bucket_for_large_short_range_uses_period_end_values():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = []
    start = datetime.fromisoformat("2026-05-02T08:00:00")
    for i in range(61):
        ts = start + timedelta(days=i // 2, hours=i % 2)
        txns.append(_make_txn("Expense", 1.0, ts=f"{ts.isoformat()}+00:00"))
    series = build_net_worth_chart_series(baseline, txns)
    assert len(series) < 62
    assert series[0]["total_net_worth"] == pytest.approx(15000.0)
    assert series[1]["label"] == "2026-05-02"
    assert series[1]["total_net_worth"] == pytest.approx(14998.0)
    assert series[-1]["total_net_worth"] == pytest.approx(14939.0)


def test_chart_series_weekly_bucket_for_medium_range():
    baseline = _make_baseline(15000.0, timestamp="2026-01-01T00:00:00+00:00")
    txns = [
        _make_txn("Expense", 1.0, ts=f"2026-03-{day:02d}T12:00:00+00:00")
        for day in range(1, 32)
    ] + [
        _make_txn("Expense", 1.0, ts=f"2026-04-{day:02d}T12:00:00+00:00")
        for day in range(1, 31)
    ]
    series = build_net_worth_chart_series(baseline, txns)
    assert len(series) < 62
    assert all(p.get("bucket") == "week" for p in series)
    assert series[-1]["total_net_worth"] == pytest.approx(14939.0)


def test_chart_series_monthly_bucket_for_long_range():
    baseline = _make_baseline(15000.0, timestamp="2025-01-01T00:00:00+00:00")
    txns = [
        _make_txn("Expense", 1.0, ts=f"2026-03-{day:02d}T12:00:00+00:00")
        for day in range(1, 32)
    ] + [
        _make_txn("Expense", 1.0, ts=f"2026-04-{day:02d}T12:00:00+00:00")
        for day in range(1, 31)
    ]
    series = build_net_worth_chart_series(baseline, txns)
    assert all(p.get("bucket") == "month" for p in series)
    assert [p["label"] for p in series] == ["2025-01", "2026-03", "2026-04"]
    assert series[-1]["total_net_worth"] == pytest.approx(14939.0)


def test_chart_series_range_30d_filters_old_points():
    baseline = _make_baseline(15000.0, timestamp="2026-01-01T00:00:00+00:00")
    txns = [
        _make_txn("Expense", 100.0, ts="2026-02-01T12:00:00+00:00"),
        _make_txn("Expense", 20.0, ts="2026-05-01T12:00:00+00:00"),
    ]
    series = build_net_worth_chart_series(
        baseline,
        txns,
        chart_range="30D",
        now=datetime.fromisoformat("2026-05-16T00:00:00"),
    )
    assert [p["total_net_worth"] for p in series] == [14880.0]


def test_activity_feed_includes_baseline_income_and_expense_newest_first():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        {"id": 1, "type": "Expense", "amount": 14.0, "timestamp": "2026-05-02T12:00:00+00:00", "notes": "", "description": "kebab"},
        {"id": 2, "type": "Income", "amount": 314.0, "timestamp": "2026-05-03T12:00:00+00:00", "notes": "", "description": "duo"},
    ]
    feed = build_net_worth_activity_feed(baseline, txns)
    assert [event["event_type"] for event in feed] == ["income", "expense", "baseline"]
    assert [event["impact"] for event in feed[:2]] == [314.0, -14.0]
    assert feed[-1]["amount"] == pytest.approx(15000.0)
    assert feed[-1]["impact"] is None


def test_activity_feed_ignores_non_net_worth_transaction_types_and_undone():
    baseline = _make_baseline(15000.0, timestamp="2026-05-01T00:00:00+00:00")
    txns = [
        _make_txn("Transfer", 1000.0, ts="2026-05-02T12:00:00+00:00"),
        _make_txn("Investment", 500.0, ts="2026-05-03T12:00:00+00:00"),
        _make_txn("Expense", 25.0, ts="2026-05-04T12:00:00+00:00", undone=True),
        _make_txn("Expense", 40.0, ts="2026-05-05T12:00:00+00:00"),
    ]
    feed = build_net_worth_activity_feed(baseline, txns)
    assert [event["event_type"] for event in feed] == ["expense", "baseline"]
    assert feed[0]["impact"] == pytest.approx(-40.0)


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


# --- space-format timestamp tests (production format from parse_message) ---

def _make_txn_prod(type_: str, amount: float, ts: str = "2026-05-16 14:00:00") -> dict:
    """Transaction with space-format timestamp exactly as parse_message generates it."""
    return {"type": type_, "amount": amount, "timestamp": ts, "notes": ""}


def test_live_nw_expense_reduces_nw_with_prod_timestamps():
    """baseline 15000 + expense 10 = 14990 (space-format timestamps from parse_message)."""
    baseline = {"total_net_worth": 15000.0, "timestamp": "2026-05-16T10:23:40.072485+00:00"}
    txns = [_make_txn_prod("Expense", 10.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(14990.0)


def test_live_nw_income_increases_nw_with_prod_timestamps():
    """baseline 15000 + income 100 = 15100 (space-format timestamps from parse_message)."""
    baseline = {"total_net_worth": 15000.0, "timestamp": "2026-05-16T10:23:40.072485+00:00"}
    txns = [_make_txn_prod("Income", 100.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15100.0)


def test_live_nw_combined_prod_timestamps():
    """baseline 15000 + income 100 - expense 10 = 15090."""
    baseline = {"total_net_worth": 15000.0, "timestamp": "2026-05-16T10:23:40.072485+00:00"}
    txns = [
        _make_txn_prod("Income", 100.0),
        _make_txn_prod("Expense", 10.0),
    ]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15090.0)


def test_live_nw_transfer_ignored_with_prod_timestamps():
    """Transfers must not affect net worth even with space-format timestamps."""
    baseline = {"total_net_worth": 15000.0, "timestamp": "2026-05-16T10:23:40.072485+00:00"}
    txns = [_make_txn_prod("Transfer", 500.0), _make_txn_prod("Investment", 200.0)]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)


def test_live_nw_prod_ts_before_baseline_skipped():
    """Transactions with space-format timestamps before the baseline must be skipped."""
    baseline = {"total_net_worth": 15000.0, "timestamp": "2026-05-16T14:00:00+00:00"}
    # Transaction at 13:00 local = before 14:00 UTC baseline
    txns = [_make_txn_prod("Expense", 50.0, ts="2026-05-16 13:00:00")]
    assert calculate_live_net_worth(baseline, txns) == pytest.approx(15000.0)
