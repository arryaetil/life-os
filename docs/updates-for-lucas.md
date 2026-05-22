# Updates for Lucas — 2026-05-22

Hey Lucas, here's a rundown of the new features added today. Each section explains what it does, which files were changed, and how it works so you can replicate or adapt it.

---

## 1. Bulk Expense Logging via Telegram

**What it does:**
Instead of logging one expense per message, you can now send a list and every line gets logged as a separate transaction. For example:

```
14 kebab
8.50 coffee
5 transport
3.20 water
```

The bot logs all four and replies with a summary + updated weekly budget.

**How it works:**

`app/parser.py` — two new functions:

```python
def is_bulk_message(text: str) -> bool:
    """Return True if 2+ lines each contain an amount."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    amount_lines = [l for l in lines if re.search(r"\d+(?:[.,]\d+)?", l)]
    return len(amount_lines) >= 2

def parse_bulk_message(text: str) -> list[dict]:
    """Parse each amount-bearing line as an independent transaction."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    results = []
    for line in lines:
        if not re.search(r"\d+(?:[.,]\d+)?", line):
            continue
        try:
            parsed = parse_message(line)  # reuses the existing single-line parser
            results.append(parsed)
        except ValueError:
            pass
    return results
```

`app/commands.py` — bulk messages are intercepted before the intent classifier (which only handles single short messages):

```python
# Priority 3: bulk expense list (2+ lines each containing an amount)
if is_bulk_message(text):
    await _handle_bulk_message(update, context, text)
    return
```

The `_handle_bulk_message` handler loops over the parsed list, logs each transaction, then sends one summary reply.

**Key decision:** each line goes through the existing `parse_message()` which calls the AI parser per line. Slightly more API calls but gives accurate category detection per item.

---

## 2. Editable Transactions in the Dashboard

**What it does:**
The `/transactions` page now has **Edit** and **Delete** buttons on every row. Clicking Edit turns the row into inline inputs (amount, description, category, type, date, impulse). Save sends a `PUT` request; Delete sends a `DELETE` request. Changes flow through to all budget/summary calculations automatically since everything derives from the DB.

**How it works:**

`app/database.py` — three new functions:

```python
def get_transaction_by_id(tx_id: int) -> dict | None:
    # SELECT by id

def update_transaction(tx_id: int, fields: dict) -> None:
    # Only allows editing safe fields: amount, description, category,
    # type, date, is_impulse, notes
    safe = {k: v for k, v in fields.items() if k in _EDITABLE_FIELDS}
    # UPDATE WHERE id = tx_id

def delete_transaction(tx_id: int) -> None:
    # Hard DELETE WHERE id = tx_id
```

`app/dashboard.py` — two new API endpoints:

```python
@app.put("/api/transactions/{tx_id}")
async def api_update_transaction(tx_id: int, request: Request):
    data = await request.json()
    sheets.update_transaction(tx_id, data)
    return JSONResponse({"ok": True})

@app.delete("/api/transactions/{tx_id}")
async def api_delete_transaction(tx_id: int):
    sheets.delete_transaction(tx_id)
    return JSONResponse({"ok": True})
```

`app/templates/transactions.html` — each row has two sets of cells (view and edit), toggled with JavaScript. The JS uses `fetch()` to call the REST endpoints:

```javascript
async function saveRow(id) {
    const payload = {};
    row.querySelectorAll('.cell-edit .edit-input').forEach(input => {
        payload[input.name] = input.name === 'amount' ? parseFloat(input.value)
                            : input.name === 'is_impulse' ? input.value === 'true'
                            : input.value;
    });
    await fetch('/api/transactions/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
}

async function deleteRow(id) {
    if (!confirm('Delete this transaction?')) return;
    await fetch('/api/transactions/' + id, { method: 'DELETE' });
    document.getElementById('row-' + id).remove();
}
```

**Note on delete:** We use hard delete here (actual `DELETE FROM transactions`) rather than the soft-delete (marking `notes = '[UNDONE]'`) that `/undo` in Telegram uses. Dashboard delete is intentional, Telegram undo is reversible.

---

## 3. PWA / iPhone Home Screen Optimization

**What it does:**
When added to the iPhone home screen via Safari → Share → Add to Home Screen, the app runs fullscreen with no browser chrome, a dark status bar that blends in, and a native bottom tab bar with icons.

**How it works:**

`app/templates/base.html` — meta tags that tell iOS to treat it as a standalone app:

```html
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#080c14">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Life OS">
<link rel="apple-touch-icon" href="/static/icon-192.png">
```

Also updated the viewport meta to include `viewport-fit=cover` so content can extend under the notch:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

`app/static/manifest.json` — standard PWA manifest (required for Android; supplementary for iOS):

```json
{
  "name": "Life OS",
  "display": "standalone",
  "start_url": "/",
  "background_color": "#080c14",
  "theme_color": "#080c14",
  "icons": [...]
}
```

`app/static/style.css` — safe area insets so content doesn't hide behind the notch or home indicator:

```css
nav {
  padding-top: calc(14px + env(safe-area-inset-top));
}
.container {
  padding-left: max(24px, env(safe-area-inset-left));
  padding-right: max(24px, env(safe-area-inset-right));
}
body {
  padding-bottom: calc(72px + env(safe-area-inset-bottom));
}
```

On mobile (`≤640px`) the nav switches to a **bottom tab bar**:

```css
@media (max-width: 640px) {
  nav {
    position: fixed;
    top: auto;
    bottom: 0;
    justify-content: space-around;
    border-top: 1px solid var(--glass-border);
  }
  .nav-logo { display: none; }
  nav a {
    flex-direction: column;
    align-items: center;
    font-size: 10px;
    min-height: 44px; /* Apple's minimum touch target */
  }
  .nav-icon { display: block; } /* SVG icons, hidden on desktop */
}
```

Each nav link got an inline SVG icon (defined in `base.html`) that is hidden on desktop and shown on mobile.

**Icon files:** `app/static/icon-192.png` and `icon-512.png` are placeholder icons (dark circle). Replace them with proper branded PNGs if you want a custom home screen icon.

---

## Files Changed Summary

| File | What changed |
|------|-------------|
| `app/parser.py` | Added `is_bulk_message()`, `parse_bulk_message()` |
| `app/commands.py` | Bulk message handler + routing |
| `app/database.py` | Added `get_transaction_by_id()`, `update_transaction()`, `delete_transaction()` |
| `app/dashboard.py` | Added `PUT /api/transactions/:id`, `DELETE /api/transactions/:id` |
| `app/templates/transactions.html` | Inline edit/delete UI + JS |
| `app/templates/base.html` | PWA meta tags, SVG nav icons, `viewport-fit=cover` |
| `app/static/style.css` | Bottom tab bar, safe area insets, mobile improvements |
| `app/static/manifest.json` | New — PWA manifest |
| `app/static/icon-192.png` | New — placeholder home screen icon |
| `app/static/icon-512.png` | New — placeholder home screen icon |
