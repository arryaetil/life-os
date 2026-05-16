from datetime import date, datetime, timedelta

GOALS = [
    {"label": "€30K", "target": 30_000.0},
]

CHART_RANGES = ("30D", "90D", "YTD", "ALL")
NET_WORTH_ACTIVITY_TYPES = {"Income", "Expense"}


def calculate_net_worth(snapshot: dict) -> float:
    return (
        snapshot.get("cash", 0.0)
        + snapshot.get("investments", 0.0)
        + snapshot.get("crypto", 0.0)
        + snapshot.get("savings", 0.0)
        + snapshot.get("other_assets", 0.0)
        - snapshot.get("liabilities", 0.0)
    )


def calculate_live_net_worth(baseline: dict | None, transactions: list[dict]) -> float:
    series = calculate_live_net_worth_series(baseline, transactions)
    if not series:
        return 0.0
    return series[-1]["total_net_worth"]


def calculate_live_net_worth_series(baseline: dict | None, transactions: list[dict]) -> list[dict]:
    if baseline is None:
        return []
    # Normalize separator: parse_message uses space, snapshots use T (ISO).
    # Space (0x20) < T (0x54) so without normalization all transactions are skipped.
    baseline_ts = baseline["timestamp"].replace(" ", "T")
    net = float(baseline["total_net_worth"])
    series = [{
        "timestamp": baseline["timestamp"],
        "label": baseline["timestamp"][:10],
        "total_net_worth": round(net, 2),
        "source": "snapshot",
    }]
    relevant_transactions = sorted(
        transactions,
        key=lambda t: t.get("timestamp", "").replace(" ", "T"),
    )
    for t in relevant_transactions:
        tx_ts = t.get("timestamp", "").replace(" ", "T")
        if tx_ts <= baseline_ts:
            continue
        if "[UNDONE]" in (t.get("notes") or ""):
            continue
        if t["type"] == "Income":
            net += float(t["amount"])
        elif t["type"] == "Expense":
            net -= float(t["amount"])
        else:
            continue
        series.append({
            "timestamp": t.get("timestamp", ""),
            "label": (t.get("timestamp", "") or "")[:10],
            "total_net_worth": round(net, 2),
            "source": "transaction",
            "transaction_id": t.get("id"),
        })
    return series


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized).replace(tzinfo=None)


def _period_key(dt: datetime, bucket: str) -> str:
    if bucket == "month":
        return dt.strftime("%Y-%m")
    if bucket == "week":
        week_start = dt.date() - timedelta(days=dt.weekday())
        return week_start.strftime("%Y-%m-%d")
    return dt.date().isoformat()


def _period_label(dt: datetime, bucket: str) -> str:
    if bucket == "month":
        return dt.strftime("%Y-%m")
    if bucket == "week":
        week_start = dt.date() - timedelta(days=dt.weekday())
        return week_start.strftime("%Y-%m-%d")
    return dt.date().isoformat()


def _select_bucket(start: datetime, end: datetime) -> str:
    days = max(0, (end.date() - start.date()).days)
    if days <= 60:
        return "day"
    if days <= 366:
        return "week"
    return "month"


def _filter_chart_range(series: list[dict], chart_range: str, now: datetime | None) -> list[dict]:
    if not series:
        return []
    selected = chart_range.upper()
    if selected not in CHART_RANGES:
        selected = "ALL"
    if selected == "ALL":
        return series

    if now is None:
        now = _parse_timestamp(series[-1]["timestamp"])
    if selected == "30D":
        start = now - timedelta(days=30)
    elif selected == "90D":
        start = now - timedelta(days=90)
    else:
        start = datetime(now.year, 1, 1, tzinfo=now.tzinfo)

    filtered = [p for p in series if _parse_timestamp(p["timestamp"]) >= start]
    if filtered:
        return filtered

    return [series[-1]]


def build_net_worth_chart_series(
    baseline: dict | None,
    transactions: list[dict],
    chart_range: str = "ALL",
    now: datetime | None = None,
) -> list[dict]:
    """Return range-filtered, readability-bucketed net worth chart points."""
    raw_series = calculate_live_net_worth_series(baseline, transactions)
    ranged = _filter_chart_range(raw_series, chart_range, now)
    if len(ranged) <= 60:
        return ranged

    start = _parse_timestamp(ranged[0]["timestamp"])
    end = _parse_timestamp(ranged[-1]["timestamp"])
    bucket = _select_bucket(start, end)
    by_period: dict[str, dict] = {}
    for point in ranged:
        dt = _parse_timestamp(point["timestamp"])
        by_period[_period_key(dt, bucket)] = {
            **point,
            "label": _period_label(dt, bucket),
            "bucket": bucket,
        }
    return list(by_period.values())


def build_net_worth_activity_feed(
    baseline: dict | None,
    transactions: list[dict],
    limit: int = 80,
) -> list[dict]:
    """Return newest-first events that explain net worth movement."""
    events: list[dict] = []
    if baseline is not None:
        events.append({
            "timestamp": baseline["timestamp"],
            "event_type": "baseline",
            "description": "Net worth baseline",
            "amount": float(baseline["total_net_worth"]),
            "impact": None,
            "source": "snapshot",
        })
        baseline_ts = baseline["timestamp"].replace(" ", "T")
    else:
        baseline_ts = ""

    for t in transactions:
        if t.get("type") not in NET_WORTH_ACTIVITY_TYPES:
            continue
        if "[UNDONE]" in (t.get("notes") or ""):
            continue
        tx_ts = t.get("timestamp", "").replace(" ", "T")
        if baseline_ts and tx_ts <= baseline_ts:
            continue
        amount = float(t["amount"])
        impact = amount if t["type"] == "Income" else -amount
        events.append({
            "timestamp": t.get("timestamp", ""),
            "event_type": t["type"].lower(),
            "description": t.get("description") or t.get("category") or "Transaction",
            "amount": amount,
            "impact": round(impact, 2),
            "source": "transaction",
            "transaction_id": t.get("id"),
        })

    events.sort(key=lambda e: e["timestamp"].replace(" ", "T"), reverse=True)
    return events[:limit]


def calculate_goal_progress(current: float, target: float) -> dict:
    pct = min(100.0, (current / target * 100.0) if target > 0 else 0.0)
    remaining = max(0.0, target - current)
    return {
        "target": target,
        "pct": round(pct, 1),
        "remaining": remaining,
        "achieved": current >= target,
    }


def calculate_monthly_change(
    current_nw: float,
    history: list[dict],
    reference_month: str | None = None,
) -> dict | None:
    if reference_month is None:
        reference_month = date.today().strftime("%Y-%m")
    pre_month = sorted(
        [s for s in history if s["timestamp"][:7] < reference_month],
        key=lambda s: s["timestamp"],
    )
    if not pre_month:
        return None
    start_nw = float(pre_month[-1]["total_net_worth"])
    delta = round(current_nw - start_nw, 2)
    return {"delta": delta, "direction": "up" if delta >= 0 else "down"}


def calculate_change(history: list[dict]) -> dict | None:
    """Change between last two snapshots. Kept for backward compatibility."""
    if len(history) < 2:
        return None
    prev = history[-2]["total_net_worth"]
    latest = history[-1]["total_net_worth"]
    delta = latest - prev
    return {"delta": delta, "direction": "up" if delta >= 0 else "down"}


def ascii_progress_bar(pct: float, width: int = 10) -> str:
    filled = min(width, int(pct / 100.0 * width))
    return "▓" * filled + "░" * (width - filled)
