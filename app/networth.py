GOALS = [
    {"label": "€25K", "target": 25_000.0},
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


def calculate_goal_progress(current: float, target: float) -> dict:
    pct = min(100.0, (current / target * 100.0) if target > 0 else 0.0)
    remaining = max(0.0, target - current)
    return {
        "target": target,
        "pct": round(pct, 1),
        "remaining": remaining,
        "achieved": current >= target,
    }


def calculate_change(history: list[dict]) -> dict | None:
    if len(history) < 2:
        return None
    prev = history[-2]["total_net_worth"]
    latest = history[-1]["total_net_worth"]
    delta = latest - prev
    return {"delta": delta, "direction": "up" if delta >= 0 else "down"}


def ascii_progress_bar(pct: float, width: int = 10) -> str:
    filled = min(width, int(pct / 100.0 * width))
    return "▓" * filled + "░" * (width - filled)
