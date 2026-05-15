import pytest
from app.networth import (
    calculate_net_worth,
    calculate_goal_progress,
    calculate_change,
    ascii_progress_bar,
    GOALS,
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


def test_goals_has_25k_and_30k():
    targets = {g["target"] for g in GOALS}
    assert 25_000.0 in targets
    assert 30_000.0 in targets
