# Module 1.1 Net Worth Refinements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couple income/expense transactions to live net worth, simplify goals to €30K only, add monthly change KPI, and refine the dashboard.

**Architecture:** The "live net worth" is the latest snapshot's `total_net_worth` plus all income/expense transactions logged since that snapshot. Monthly change compares the live net worth to the value at the start of the current calendar month (from history). The dashboard and commands all read from this live calculation rather than raw snapshot totals.

**Tech Stack:** Python 3.13, FastAPI 0.111, SQLAlchemy 2.0, Jinja2, Chart.js 4.4.0, pytest 8.2.1, python-telegram-bot 20.7

**Baseline:** 155 tests passing. Never reduce this count.

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `app/networth.py` | Modify | Add `calculate_live_net_worth`, `calculate_monthly_change`; update `GOALS` to €30K only; keep `calculate_change` for backward compat |
| `app/commands.py` | Modify | `cmd_networth`, `cmd_goal` use live NW; `cmd_goal` shows single €30K goal |
| `app/dashboard.py` | Modify | `/networth` route: pass `live_nw`, `monthly_change` instead of `change` |
| `app/templates/networth.html` | Modify | Remove €25K card; rename "Change" → "Monthly Net Worth Change"; show live NW |
| `tests/test_networth_logic.py` | Modify | Update GOALS test; add tests for `calculate_live_net_worth`, `calculate_monthly_change` |
| `tests/test_networth_commands.py` | Modify | Update `cmd_goal` test to only check €30K |
| `tests/test_networth_parser.py` | Modify | Add test for `"net worth 15k"` (k-suffix without breakdown) |
| `scripts/reset_networth.py` | Run | Execute against production DB (already exists, no code change) |
| `docs/current-status.md` | Modify | Update module 1.1 status notes |
| `handoff/latest.md` | Modify | Write new handoff at session end |

---

## Task 1: Update `app/networth.py` — GOALS, live NW, monthly change

**Files:**
- Modify: `app/networth.py`
- Test: `tests/test_networth_logic.py`

- [ ] **Step 1: Write failing tests for new functions and updated GOALS**

Add these tests to `tests/test_networth_logic.py`. All will fail because the functions don't exist yet:

```python
# Append to tests/test_networth_logic.py

from app.networth import calculate_live_net_worth, calculate_monthly_change

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
    # All snapshots are in the current reference month → no baseline → None
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
    # Multiple pre-month snapshots → use the latest one
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_logic.py -v 2>&1 | tail -20
```

Expected: Multiple FAILED — `ImportError: cannot import name 'calculate_live_net_worth'` and `AssertionError` for GOALS.

- [ ] **Step 3: Update `app/networth.py`**

Replace the entire file with:

```python
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
    baseline_ts = baseline["timestamp"]
    net = float(baseline["total_net_worth"])
    for t in transactions:
        if t.get("timestamp", "") <= baseline_ts:
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
    pre_month = [s for s in history if s["timestamp"][:7] < reference_month]
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_logic.py -v 2>&1 | tail -30
```

Expected: All tests PASS.

- [ ] **Step 5: Run full suite to catch regressions**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -10
```

Expected: All 155+ tests pass. If `test_goals_has_25k_and_30k` still exists and fails → fix it in the next step.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/networth.py tests/test_networth_logic.py && git commit -m "feat(1.1): add live net worth calculation, monthly change KPI, simplify goals to 30K"
```

---

## Task 2: Update `tests/test_networth_commands.py` — remove €25K goal assertion

**Files:**
- Modify: `tests/test_networth_commands.py`

- [ ] **Step 1: Update the failing test**

In `tests/test_networth_commands.py`, find `test_cmd_goal_shows_25k_and_30k` and replace with:

```python
async def test_cmd_goal_shows_30k():
    from app.commands import cmd_goal
    update = _make_update()
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT):
        await cmd_goal(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "30K" in text or "30k" in text
    assert "25K" not in text and "25k" not in text
```

- [ ] **Step 2: Run tests to verify**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_commands.py -v 2>&1 | tail -20
```

Expected: All pass (including the new `test_cmd_goal_shows_30k`).

---

## Task 3: Update `app/commands.py` — live NW in cmd_networth and cmd_goal

**Files:**
- Modify: `app/commands.py`

- [ ] **Step 1: Write failing test for live NW in cmd_networth**

Append to `tests/test_networth_commands.py`:

```python
async def test_cmd_networth_shows_live_total_with_transactions():
    """Live NW = baseline 13000 + income 500 = 13500, not raw snapshot 13000."""
    from app.commands import cmd_networth
    update = _make_update()
    txns = [
        {
            "type": "Income", "amount": 500.0,
            "timestamp": "2026-05-16T10:00:00+00:00",
            "notes": "", "date": "2026-05-16",
            "week_start": "2026-05-13", "month": "2026-05",
            "description": "salary", "category": "Income",
            "tag": "", "payment_type": "", "is_impulse": False, "is_necessary": "",
        }
    ]
    with patch("app.database.get_latest_net_worth_snapshot", return_value=SNAPSHOT), \
         patch("app.database.get_all_transactions", return_value=txns):
        await cmd_networth(update, MagicMock())
    text = update.message.reply_text.call_args[0][0]
    assert "13500.00" in text
    assert "13000.00" not in text or "Baseline" in text  # baseline may be shown
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_commands.py::test_cmd_networth_shows_live_total_with_transactions -v 2>&1 | tail -10
```

Expected: FAIL — shows 13000.00 (snapshot total), not 13500.00.

- [ ] **Step 3: Update `app/commands.py`**

Update the imports at the top of `app/commands.py` to add:

```python
from app.networth import GOALS, calculate_goal_progress, ascii_progress_bar, calculate_live_net_worth
```

(Replace the existing import that includes `GOALS, calculate_goal_progress, ascii_progress_bar`.)

Replace `cmd_networth` with:

```python
async def cmd_networth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet.\n\n"
            "Log your first snapshot:\n"
            "  net worth cash 2000 investments 5000 savings 3000"
        )
        return
    transactions = database.get_all_transactions()
    live_nw = calculate_live_net_worth(snap, transactions)
    date_str = (snap.get("timestamp") or "")[:10]
    lines = [f"💰 Net Worth (Live)\n"]
    lines.append(f"Total: {format_currency(live_nw)}")
    lines.append(f"Baseline ({date_str}): {format_currency(snap['total_net_worth'])}")
    for label, key in [("Cash", "cash"), ("Investments", "investments"),
                       ("Crypto", "crypto"), ("Savings", "savings"),
                       ("Other Assets", "other_assets"), ("Liabilities", "liabilities")]:
        val = snap.get(key, 0.0)
        if val > 0:
            lines.append(f"  {label}: {format_currency(val)}")
    await update.message.reply_text("\n".join(lines))
```

Replace `cmd_goal` with:

```python
async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app import database
    snap = database.get_latest_net_worth_snapshot()
    if not snap:
        await update.message.reply_text(
            "No net worth data yet. Log a snapshot first:\n"
            "  net worth cash 2000 investments 5000"
        )
        return
    transactions = database.get_all_transactions()
    live_nw = calculate_live_net_worth(snap, transactions)
    lines = ["🎯 Financial Goals\n"]
    for goal in GOALS:
        progress = calculate_goal_progress(live_nw, goal["target"])
        bar = ascii_progress_bar(progress["pct"])
        if progress["achieved"]:
            lines.append(f"{goal['label']}: {bar} ✅ Achieved!")
        else:
            lines.append(
                f"{goal['label']}: {bar} {progress['pct']}%\n"
                f"  {format_currency(progress['remaining'])} to go"
            )
    await update.message.reply_text("\n".join(lines))
```

- [ ] **Step 4: Run tests to verify**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_commands.py -v 2>&1 | tail -20
```

Expected: All pass including `test_cmd_networth_shows_live_total_with_transactions`.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/commands.py tests/test_networth_commands.py && git commit -m "feat(1.1): use live net worth in cmd_networth and cmd_goal; single 30K goal"
```

---

## Task 4: Add parser test for "net worth 15k"

**Files:**
- Modify: `tests/test_networth_parser.py`

- [ ] **Step 1: Add test**

Append to `tests/test_networth_parser.py`:

```python
def test_parses_total_only_k_suffix_no_breakdown():
    """'net worth 15k' should set other_assets=15000, liabilities=0."""
    result = parse_net_worth_message("net worth 15k")
    assert result["other_assets"] == pytest.approx(15000.0)
    assert result["liabilities"] == pytest.approx(0.0)
    assert result["cash"] == pytest.approx(0.0)
```

- [ ] **Step 2: Run to verify it passes immediately (parser already handles this)**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_networth_parser.py::test_parses_total_only_k_suffix_no_breakdown -v 2>&1 | tail -5
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add tests/test_networth_parser.py && git commit -m "test(1.1): add parser test for 'net worth 15k' k-suffix without breakdown"
```

---

## Task 5: Update `app/dashboard.py` — live NW and monthly change

**Files:**
- Modify: `app/dashboard.py`

- [ ] **Step 1: Update `/networth` route**

In `app/dashboard.py`, update the import of `networth` functions:

```python
from app import networth as nw_module
```

(Already present — no change needed here.)

Replace the `networth_page` function with:

```python
@app.get("/networth")
async def networth_page(request: Request):
    latest = sheets.get_latest_net_worth_snapshot()
    history = sheets.get_net_worth_history(limit=30)
    all_transactions = sheets.get_all_transactions()
    live_nw = nw_module.calculate_live_net_worth(latest, all_transactions)
    monthly_change = nw_module.calculate_monthly_change(live_nw, history)
    goals = [
        {**g, **nw_module.calculate_goal_progress(live_nw, g["target"])}
        for g in nw_module.GOALS
    ]
    allocation = []
    max_asset = 1.0
    if latest:
        raw = [
            {"label": "Cash",         "amount": latest["cash"],         "color": ""},
            {"label": "Investments",  "amount": latest["investments"],   "color": ""},
            {"label": "Crypto",       "amount": latest["crypto"],        "color": ""},
            {"label": "Savings",      "amount": latest["savings"],       "color": ""},
            {"label": "Other Assets", "amount": latest["other_assets"],  "color": ""},
            {"label": "Liabilities",  "amount": latest["liabilities"],   "color": "danger"},
        ]
        allocation = [a for a in raw if a["amount"] > 0]
        pos_amounts = [a["amount"] for a in allocation]
        max_asset = max(pos_amounts) if pos_amounts else 1.0
    chart_labels = [s["timestamp"][:10] for s in history]
    chart_values = [s["total_net_worth"] for s in history]
    return templates.TemplateResponse(request, "networth.html", {
        "active_page": "networth",
        "latest": latest,
        "live_nw": live_nw,
        "history": history,
        "monthly_change": monthly_change,
        "goals": goals,
        "allocation": allocation,
        "max_asset": max_asset,
        "chart_labels": chart_labels,
        "chart_values": chart_values,
    })
```

Note: `change` is replaced by `monthly_change`, `live_nw` is now passed explicitly.

- [ ] **Step 2: Verify dashboard still imports and runs**

```bash
cd /Users/arryawillems/finance-lifeos && python -c "from app.dashboard import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run dashboard tests**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_dashboard.py -v 2>&1 | tail -20
```

Expected: All pass (dashboard tests mock DB, so template variable changes may need attention — fix any failures).

If `test_dashboard.py` tests the `/networth` route and checks for `change` key: update the mock to use `monthly_change` instead.

- [ ] **Step 4: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/dashboard.py && git commit -m "feat(1.1): dashboard uses live net worth and monthly change KPI"
```

---

## Task 6: Update `app/templates/networth.html` — monthly change label, live NW, single goal

**Files:**
- Modify: `app/templates/networth.html`

- [ ] **Step 1: Rewrite the template**

Replace the entire content of `app/templates/networth.html` with:

```html
{% extends "base.html" %}
{% block content %}

<div class="kpi-grid">

  <div class="glass-card">
    <div class="kpi-label">Net Worth (Live)</div>
    <div class="kpi-value {% if live_nw >= 0 %}positive{% else %}danger{% endif %}">
      {{ live_nw | format_currency }}
    </div>
    {% if latest %}
    <div class="kpi-sub">baseline {{ latest.timestamp[:10] }}: {{ latest.total_net_worth | format_currency }}</div>
    {% else %}
    <div class="kpi-sub">No data yet</div>
    {% endif %}
  </div>

  <div class="glass-card">
    <div class="kpi-label">Monthly Net Worth Change</div>
    {% if monthly_change %}
    <div class="kpi-value {% if monthly_change.delta >= 0 %}positive{% else %}danger{% endif %}">
      {% if monthly_change.delta >= 0 %}+{% endif %}{{ monthly_change.delta | format_currency }}
    </div>
    <div class="kpi-sub">vs start of this month</div>
    {% else %}
    <div class="kpi-value" style="color: var(--text-secondary);">—</div>
    <div class="kpi-sub">Insufficient history</div>
    {% endif %}
  </div>

  {% for goal in goals %}
  <div class="glass-card">
    <div class="kpi-label">Goal {{ goal.label }}</div>
    <div class="kpi-value {% if goal.achieved %}positive{% else %}accent{% endif %}">
      {{ goal.pct }}%
    </div>
    <div class="progress-track">
      <div class="progress-fill {% if goal.achieved %}positive{% endif %}"
           style="width: {{ goal.pct }}%"></div>
    </div>
    <div class="kpi-sub">
      {% if goal.achieved %}
        🎉 Achieved!
      {% else %}
        {{ goal.remaining | format_currency }} to go
      {% endif %}
    </div>
  </div>
  {% endfor %}

</div>

{% if latest %}

<div class="glass-card" style="margin-bottom: 20px;">
  <div class="section-header">Asset Breakdown (Baseline)</div>
  {% if allocation %}
    {% for a in allocation %}
    <div class="cat-row">
      <div class="cat-name">{{ a.label }}</div>
      <div class="cat-track">
        <div class="cat-fill {% if a.color == 'danger' %}danger-fill{% endif %}"
             style="width: {{ (a.amount / max_asset * 100) | round(1) }}%"></div>
      </div>
      <div class="cat-amount {% if a.color == 'danger' %}danger{% endif %}">
        {{ a.amount | format_currency }}
      </div>
    </div>
    {% endfor %}
  {% else %}
    <p style="color: var(--text-secondary); font-size: 14px;">No asset breakdown available.</p>
  {% endif %}
</div>

<div class="glass-card" style="margin-bottom: 20px;">
  <div class="section-header">Net Worth Over Time</div>
  {% if history | length >= 1 %}
  <div style="position: relative; height: 240px;">
    <canvas id="nwChart"></canvas>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script>
    (function() {
      const ctx = document.getElementById('nwChart');
      const labels = {{ chart_labels | tojson }};
      const values = {{ chart_values | tojson }};
      // Append live NW as the rightmost point if it differs from last snapshot
      const liveNw = {{ live_nw }};
      const today = new Date().toISOString().slice(0, 10);
      if (labels.length === 0 || labels[labels.length - 1] !== today) {
        labels.push('Live');
        values.push(liveNw);
      } else {
        values[values.length - 1] = liveNw;
      }
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Net Worth',
            data: values,
            borderColor: '#3F5AF5',
            backgroundColor: 'rgba(63,90,245,0.08)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#3F5AF5',
            pointBorderColor: '#3F5AF5',
            pointRadius: 4,
            pointHoverRadius: 6,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: 'rgba(8,12,20,0.9)',
              borderColor: 'rgba(255,255,255,0.1)',
              borderWidth: 1,
              callbacks: {
                label: function(ctx) { return '€' + ctx.parsed.y.toLocaleString('en-IE', {minimumFractionDigits: 2}); }
              }
            }
          },
          scales: {
            x: {
              ticks: { color: 'rgba(255,255,255,0.45)', font: { size: 11 } },
              grid:  { color: 'rgba(255,255,255,0.05)' }
            },
            y: {
              ticks: {
                color: 'rgba(255,255,255,0.45)',
                font: { size: 11 },
                callback: function(v) { return '€' + v.toLocaleString(); }
              },
              grid: { color: 'rgba(255,255,255,0.05)' }
            }
          }
        }
      });
    })();
  </script>
  {% else %}
  <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.7;">
    Log a snapshot to see your net worth trend.<br>
    Send via Telegram: <code style="background:rgba(255,255,255,0.08);padding:2px 8px;border-radius:4px;">net worth 15000</code>
  </p>
  {% endif %}
</div>

<div class="glass-card">
  <div class="section-header">Recent Snapshots</div>
  <table class="glass-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Net Worth</th>
        <th>Cash</th>
        <th>Investments</th>
        <th>Savings</th>
        <th>Liabilities</th>
      </tr>
    </thead>
    <tbody>
      {% for s in history | reverse %}
      <tr>
        <td>{{ s.timestamp[:10] }}</td>
        <td><strong>{{ s.total_net_worth | format_currency }}</strong></td>
        <td>{{ s.cash | format_currency }}</td>
        <td>{{ s.investments | format_currency }}</td>
        <td>{{ s.savings | format_currency }}</td>
        <td>{{ s.liabilities | format_currency }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% else %}

<div class="glass-card">
  <div class="section-header">No Net Worth Data Yet</div>
  <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.9;">
    Log your first snapshot via Telegram:<br><br>
    <code style="background:rgba(255,255,255,0.08);padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:8px;">net worth 15000</code><br>
    <code style="background:rgba(255,255,255,0.08);padding:4px 10px;border-radius:6px;display:inline-block;margin-bottom:8px;">net worth cash 2000 investments 5000 savings 3000</code><br><br>
    Or send <code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;">/networth</code> to the bot.
  </p>
</div>

{% endif %}

{% endblock %}
```

Key changes vs old template:
- KPI 1: "Net Worth (Live)" uses `live_nw` (not `latest.total_net_worth`); shows baseline date and value as subtitle
- KPI 2: "Monthly Net Worth Change" uses `monthly_change` (not `change`); shows "vs start of this month" subtitle; shows "Insufficient history" fallback
- Only one goal card rendered (€30K only, since GOALS now has one entry)
- Section renamed "Asset Breakdown (Baseline)" to clarify it's from snapshot
- Chart: appends "Live" data point showing live NW
- Chart shows `history | length >= 1` (not `>= 2`) since we always show the live point

- [ ] **Step 2: Verify template syntax (dry run)**

```bash
cd /Users/arryawillems/finance-lifeos && python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('app/templates'))
t = env.get_template('networth.html')
print('Template OK')
"
```

Expected: `Template OK`

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: All pass (templates are not tested in unit tests but dashboard route tests should still pass).

- [ ] **Step 4: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/templates/networth.html && git commit -m "feat(1.1): refine net worth dashboard — monthly change KPI, live NW, single 30K goal"
```

---

## Task 7: Reset production DB to clean baseline

**Files:**
- Run: `scripts/reset_networth.py` (no code change needed — script already exists and is correct)

- [ ] **Step 1: Dry run to verify**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/reset_networth.py --dry-run
```

Expected output shows transaction count (untouched) and snapshot count. No changes made.

- [ ] **Step 2: Execute reset**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/reset_networth.py
```

Expected:
```
Transactions in DB : <N>  (will not be touched)
Net worth snapshots: <M>  (will be deleted)
Deleted all net worth snapshots.
Inserted baseline snapshot (id=1, total_net_worth=15000).
Verified: {..., 'total_net_worth': 15000.0, 'other_assets': 15000.0, ...}
```

- [ ] **Step 3: Verify via bot command (send to Telegram manually)**

Send `/networth` to the bot — should show:
```
💰 Net Worth (Live)
Total: €15,000.00
Baseline (today's date): €15,000.00
  Other Assets: €15,000.00
```

Send `/goal` — should show:
```
🎯 Financial Goals
€30K: ▓▓▓▓▓░░░░░ 50.0%
  €15,000.00 to go
```

---

## Task 8: Update docs and write handoff

**Files:**
- Modify: `docs/current-status.md`
- Modify: `handoff/latest.md`

- [ ] **Step 1: Update `docs/current-status.md`**

Find the Module 1.1 section and update to reflect:
- Live net worth calculation (transactions coupled)
- Monthly change KPI
- Single €30K goal
- Clean €15,000 baseline in production

- [ ] **Step 2: Run full suite one final time**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: All 165+ tests passing (155 baseline + 15+ new).

- [ ] **Step 3: Send Telegram completion notification**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/notify_me.py complete "Module 1.1 refinements complete: live NW coupled to transactions, monthly change KPI, single 30K goal, clean 15K baseline. All tests pass."
```

- [ ] **Step 4: Write handoff**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/create_handoff.py
```

- [ ] **Step 5: Final commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add docs/ handoff/ && git commit -m "docs(1.1): update status and handoff after refinements"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task that implements it |
|---|---|
| Fix parser — "net worth 15621 total" liabilities bug | Already fixed in prior session; Task 4 adds k-suffix test |
| total_net_worth populated correctly, not liabilities | Already correct; existing tests confirm |
| Reset/create €15K baseline | Task 7 |
| Couple transactions to live NW | Task 1 (function), Task 3 (commands), Task 5 (dashboard) |
| Expenses reduce NW automatically | Task 1 (calculate_live_net_worth Expense case) |
| Income increases NW automatically | Task 1 (calculate_live_net_worth Income case) |
| Transfers not double-counted | Task 1 (Transfer type ignored) |
| Remove €25K KPI | Task 1 (GOALS), Task 2 (tests), Task 6 (template) |
| Progress toward €30K | Task 1 (GOALS), Task 3 (commands), Task 5 (dashboard) |
| Monthly Net Worth Change KPI | Task 1 (function), Task 5 (dashboard), Task 6 (template) |
| Positive/negative delta styling | Task 6 (template: positive/danger classes) |
| Insufficient data fallback | Task 6 (template: "Insufficient history") |
| Dashboard premium/clean | Task 6 (template rewrite) |
| Net worth KPI card | Task 6 |
| Monthly change KPI card | Task 6 |
| Progress bar | Task 6 (existing progress-track/fill) |
| Asset breakdown | Task 6 (existing, renamed "Baseline") |
| Recent snapshots table | Task 6 (existing) |
| Chart.js trend chart | Task 6 (enhanced with live NW point) |
| Chart empty state | Task 6 (>= 1 history instead of >= 2) |
| Tests for all above | Tasks 1–4 |
| Docs updated | Task 8 |
| Full test suite preserved | All tasks run full suite |

**No gaps found.**

**Placeholder scan:** No TBD, TODO, or "similar to Task N" patterns in this plan. All code blocks are complete.

**Type consistency:**
- `calculate_live_net_worth(baseline: dict | None, transactions: list[dict]) -> float` — used consistently in Tasks 1, 3, 5
- `calculate_monthly_change(current_nw: float, history: list[dict], reference_month: str | None = None) -> dict | None` — used consistently in Tasks 1, 5, 6
- `GOALS` — list of one dict after Task 1; Tasks 2, 3, 6 consume it with same structure
- Template variables: `live_nw` (float), `monthly_change` (dict|None), `goals` (list) — set in Task 5, consumed in Task 6 ✓
