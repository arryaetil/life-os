from datetime import date

GOALS = [
    {"label": "€30K", "target": 30_000.0},
]


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
    if baseline is None:
        return 0.0
    # Normalize separator: parse_message uses space, snapshots use T (ISO).
    # Space (0x20) < T (0x54) so without normalization all transactions are skipped.
    baseline_ts = baseline["timestamp"].replace(" ", "T")
    net = float(baseline["total_net_worth"])
    for t in transactions:
        if t.get("timestamp", "").replace(" ", "T") <= baseline_ts:
            continue
        if "[UNDONE]" in (t.get("notes") or ""):
            continue
        if t["type"] == "Income":
            net += float(t["amount"])
        elif t["type"] == "Expense":
            net -= float(t["amount"])
    return round(net, 2)


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
