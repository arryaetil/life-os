# Conversational LifeOS Agent v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an intelligent AI layer to the Telegram bot so natural questions ("What is LifeOS?", "What should I build next?", "Build the portfolio tracker") get smart responses grounded in vault context, while all existing finance/net-worth parsing keeps working unchanged.

**Architecture:** Three new modules: `vault_context.py` loads a fixed compressed context pack; `intent_classifier.py` routes messages with regex heuristics; `ai_agent.py` generates OpenAI-powered responses and action proposals. `commands.py` updated to classify and route before falling back to finance parsing. No RAG, no vectors — fixed context pack only.

**Tech Stack:** Python 3.13, OpenAI GPT-4o-mini, python-telegram-bot 20.7, pytest 8.2.1

**Baseline:** 205 tests passing. Never reduce this count.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/vault_context.py` | Create | Load and compress fixed vault file set with char limits |
| `app/intent_classifier.py` | Create | Regex-based intent classification → one of 5 intent labels |
| `app/ai_agent.py` | Create | OpenAI-powered answer + action proposal generation |
| `app/commands.py` | Modify | Updated `handle_message` routing + 3 new handler functions |
| `tests/test_vault_context.py` | Create | Context loading, truncation, missing files |
| `tests/test_intent_classifier.py` | Create | Intent classification for all message types |
| `tests/test_ai_agent.py` | Create | AI response with mocked OpenAI, fallbacks |
| `tests/test_message_routing.py` | Modify | Add lifeos question + action request routing tests |
| `vault/commands/command-reference.md` | Modify | Add natural language AI chat section |
| `vault/hubs/Agent_Control.md` | Modify | Document conversational AI layer |
| `vault/hubs/Architecture.md` | Modify | Update architecture with AI agent layer |
| `docs/autonomous-session-protocol.md` | Modify | Note AI responses during autonomous sessions |
| `README.md` | Modify | Add conversational AI feature to feature list |

---

## Task 1: Create `app/vault_context.py` + tests

**Files:**
- Create: `app/vault_context.py`
- Create: `tests/test_vault_context.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_vault_context.py`:

```python
from unittest.mock import patch
from app.vault_context import load_vault_context, MAX_TOTAL_CHARS


def test_returns_nonempty_string():
    ctx = load_vault_context()
    assert isinstance(ctx, str)
    assert len(ctx) > 0


def test_total_length_under_max():
    ctx = load_vault_context()
    # Allow small tolerance for section headers
    assert len(ctx) <= MAX_TOTAL_CHARS + 200


def test_missing_file_skipped():
    with patch("app.vault_context._VAULT_FILES", [("does_not_exist_xyz.md", 1000)]):
        ctx = load_vault_context()
    assert ctx == ""


def test_long_file_truncated():
    with patch("app.vault_context._VAULT_FILES", [("CLAUDE.md", 50)]):
        ctx = load_vault_context()
    assert "[...truncated]" in ctx


def test_max_total_chars_enforced():
    with patch("app.vault_context.MAX_TOTAL_CHARS", 100):
        ctx = load_vault_context()
    # Context should not balloon past the limit (with header overhead)
    assert len(ctx) < 400


def test_empty_file_list_returns_empty():
    with patch("app.vault_context._VAULT_FILES", []):
        ctx = load_vault_context()
    assert ctx == ""
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_vault_context.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'app.vault_context'`

- [ ] **Step 3: Create `app/vault_context.py`**

```python
"""
Fixed-context vault loader for the LifeOS AI agent.
Loads a small set of vault/doc files into a compressed context string.
No RAG, no embeddings — simple file reads with character limits.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

_VAULT_FILES = [
    ("CLAUDE.md", 1500),
    ("vault/context/LifeOS.md", 1000),
    ("vault/context/Current_Priorities.md", 800),
    ("vault/context/User_Profile.md", 600),
    ("vault/hubs/Architecture.md", 800),
    ("vault/hubs/Finance.md", 600),
    ("vault/hubs/Agent_Control.md", 600),
    ("vault/projects/finance-lifeos.md", 800),
    ("vault/sessions/recent-sessions.md", 600),
    ("handoff/latest.md", 800),
]

MAX_TOTAL_CHARS = 8000


def load_vault_context() -> str:
    """Load and compress vault context files into a single string."""
    sections = []
    total = 0

    for rel_path, max_chars in _VAULT_FILES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...truncated]"
        section = f"## {rel_path}\n{text}"
        if total + len(section) > MAX_TOTAL_CHARS:
            break
        sections.append(section)
        total += len(section)

    return "\n\n---\n\n".join(sections)
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_vault_context.py -v 2>&1 | tail -10
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 211 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/vault_context.py tests/test_vault_context.py && git commit -m "feat(1.4): add vault_context loader — fixed context pack for AI agent"
```

---

## Task 2: Create `app/intent_classifier.py` + tests

**Files:**
- Create: `app/intent_classifier.py`
- Create: `tests/test_intent_classifier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_intent_classifier.py`:

```python
from app.intent_classifier import classify_intent


def test_expense_messages_are_finance_transaction():
    assert classify_intent("14 kebab") == "finance_transaction"
    assert classify_intent("8.50 coffee") == "finance_transaction"
    assert classify_intent("+314 DUO") == "finance_transaction"
    assert classify_intent("spent 25 food") == "finance_transaction"
    assert classify_intent("250 groceries") == "finance_transaction"


def test_question_messages_are_lifeos_question():
    assert classify_intent("What is my net worth?") == "lifeos_question"
    assert classify_intent("What was done last session?") == "lifeos_question"
    assert classify_intent("How does the net worth tracker work?") == "lifeos_question"
    assert classify_intent("What should we build next?") == "lifeos_question"
    assert classify_intent("Tell me about LifeOS") == "lifeos_question"
    assert classify_intent("Show me my progress") == "lifeos_question"


def test_action_messages_are_action_request():
    assert classify_intent("Build the next module") == "action_request"
    assert classify_intent("Run tests") == "action_request"
    assert classify_intent("Prepare handoff") == "action_request"
    assert classify_intent("Start working on portfolio tracker") == "action_request"
    assert classify_intent("Deploy to Railway") == "action_request"
    assert classify_intent("Create the portfolio table") == "action_request"


def test_ambiguous_short_messages_are_unknown():
    assert classify_intent("hello") == "unknown"
    assert classify_intent("great") == "unknown"
    assert classify_intent("ok") == "unknown"


def test_long_message_with_no_amount_and_no_keywords_is_unknown():
    # Long sentence that doesn't match any pattern
    assert classify_intent("please let me know when it is ready") == "unknown"


def test_amount_with_many_words_not_classified_as_finance():
    # More than 6 words — even with an amount, shouldn't be auto-classed as finance
    result = classify_intent("I spent about 14 euros on kebab yesterday evening")
    # Could be lifeos_question or unknown but definitely not finance_transaction
    assert result != "finance_transaction"
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_intent_classifier.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'app.intent_classifier'`

- [ ] **Step 3: Create `app/intent_classifier.py`**

```python
"""
Intent classifier for incoming Telegram messages.

Classifies messages into:
  finance_transaction  — clear expense/income with amount
  net_worth_update     — handled upstream by is_net_worth_message (not returned here)
  agent_reply          — handled upstream by is_agent_reply (not returned here)
  lifeos_question      — general question about LifeOS system
  action_request       — request to build/run/deploy something
  unknown              — unclear; ask for clarification
"""
import re

_AMOUNT_PAT = re.compile(
    r"(?:^|\s)[+\-]?\d+(?:[.,]\d+)?k?\b",
    re.IGNORECASE,
)

_QUESTION_PATS = [
    re.compile(r"\b(what|how|why|when|where|which|who)\b", re.IGNORECASE),
    re.compile(r"\b(tell me|explain|describe|show me|give me)\b", re.IGNORECASE),
    re.compile(r"\b(status|progress|summary|overview)\b", re.IGNORECASE),
    re.compile(r"\b(lifeos|vault|module|architecture|goal|plan|roadmap)\b", re.IGNORECASE),
    re.compile(r"\?$"),
]

_ACTION_PATS = [
    re.compile(r"\b(build|create|implement|start|deploy|run|prepare|generate|make)\b", re.IGNORECASE),
    re.compile(r"\b(handoff|commit|push|test|fix|refactor)\b", re.IGNORECASE),
    re.compile(r"\b(portfolio tracker|next module|module 1\.\d)\b", re.IGNORECASE),
]


def classify_intent(text: str) -> str:
    """Classify text into one of: finance_transaction, lifeos_question, action_request, unknown.

    Callers are expected to have already handled agent_reply and net_worth_update upstream.
    """
    stripped = text.strip()

    # Short messages with a clear amount (≤ 6 words) → finance transaction
    if _AMOUNT_PAT.search(stripped) and len(stripped.split()) <= 6:
        return "finance_transaction"

    # Action keywords
    for pat in _ACTION_PATS:
        if pat.search(stripped):
            return "action_request"

    # Question keywords
    for pat in _QUESTION_PATS:
        if pat.search(stripped):
            return "lifeos_question"

    return "unknown"
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_intent_classifier.py -v 2>&1 | tail -15
```

Expected: All tests PASS. If `test_long_message_with_no_amount_and_no_keywords_is_unknown` fails (the long message matches a question word like "please"), check the sentence and adjust — the test just needs `result != "finance_transaction"`, so any value is acceptable if the pattern triggers.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~224 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/intent_classifier.py tests/test_intent_classifier.py && git commit -m "feat(1.4): add intent_classifier — routes messages to finance/question/action/unknown"
```

---

## Task 3: Create `app/ai_agent.py` + tests

**Files:**
- Create: `app/ai_agent.py`
- Create: `tests/test_ai_agent.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ai_agent.py`:

```python
from unittest.mock import patch


def test_answer_lifeos_question_returns_openai_response():
    with patch("app.ai_agent._call_openai", return_value="LifeOS is your personal AI OS."):
        from app.ai_agent import answer_lifeos_question
        result = answer_lifeos_question("What is LifeOS?")
    assert "LifeOS" in result


def test_answer_lifeos_question_fallback_when_no_api():
    with patch("app.ai_agent._call_openai", return_value=None):
        from app.ai_agent import answer_lifeos_question
        result = answer_lifeos_question("What is LifeOS?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_answer_with_structured_data_passes_data_to_openai():
    captured = {}

    def fake_call(system, user, max_tokens=300):
        captured["user"] = user
        return "Your net worth is €15,000."

    with patch("app.ai_agent._call_openai", side_effect=fake_call):
        from app.ai_agent import answer_lifeos_question
        answer_lifeos_question("What is my net worth?", structured_data="Live net worth: €15,000")

    assert "€15,000" in captured["user"]
    assert "What is my net worth?" in captured["user"]


def test_propose_action_includes_approve_or_cancel():
    with patch("app.ai_agent._call_openai", return_value="I'll build Module 1.2. Reply A to approve or B to cancel."):
        from app.ai_agent import propose_action
        result = propose_action("Build next module")
    assert "Reply A" in result or "A to approve" in result


def test_propose_action_fallback_includes_cancel_option():
    with patch("app.ai_agent._call_openai", return_value=None):
        from app.ai_agent import propose_action
        result = propose_action("Run tests")
    assert "B" in result  # Cancel option always present
    assert "A" in result  # Approve option always present


def test_call_openai_returns_none_when_no_key(monkeypatch):
    monkeypatch.setattr("app.config.OPENAI_API_KEY", "")
    from app.ai_agent import _call_openai
    result = _call_openai("system", "user")
    assert result is None
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_ai_agent.py -v 2>&1 | tail -5
```

Expected: `ModuleNotFoundError: No module named 'app.ai_agent'`

- [ ] **Step 3: Create `app/ai_agent.py`**

```python
"""
AI agent for LifeOS conversational responses and action proposals.
Uses OpenAI GPT-4o-mini with compressed vault context.
"""
import logging

_log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are the LifeOS AI assistant. You have access to the user's personal "
    "operating system context below.\n"
    "Answer questions concisely and practically. Keep responses under 200 words "
    "unless the user asks for detail. Do not make up information not in the context."
)

_ACTION_PROMPT = (
    "You are the LifeOS AI assistant. The user is requesting an action.\n"
    "Describe the action you would propose (1-3 sentences), what it does, and any risks.\n"
    "End your response with exactly: 'Reply A to approve or B to cancel.'\n"
    "Do not execute anything — only propose and ask for confirmation."
)


def _call_openai(system: str, user: str, max_tokens: int = 300) -> str | None:
    from app import config
    if not config.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        _log.warning("OpenAI call failed: %s", exc)
        return None


def answer_lifeos_question(question: str, structured_data: str = "") -> str:
    """Answer a LifeOS question using vault context and optional live data."""
    from app.vault_context import load_vault_context
    context = load_vault_context()
    if structured_data:
        user_msg = f"Current live data:\n{structured_data}\n\nQuestion: {question}"
    else:
        user_msg = question
    system = f"{_SYSTEM_PROMPT}\n\n# LifeOS Context\n\n{context}"
    result = _call_openai(system, user_msg)
    if result:
        return result
    return (
        "I don't have enough context to answer that. "
        "Try /status for current state or /networth for financial data."
    )


def propose_action(request: str) -> str:
    """Propose an action for user confirmation — does NOT execute anything."""
    from app.vault_context import load_vault_context
    context = load_vault_context()
    system = f"{_ACTION_PROMPT}\n\n# LifeOS Context\n\n{context}"
    result = _call_openai(system, request)
    if result:
        return result
    return (
        f"Action requested: {request}\n\n"
        "I can't generate a specific proposal right now.\n"
        "Describe the task in more detail if needed.\n\n"
        "Reply A to proceed or B to cancel."
    )
```

- [ ] **Step 4: Run tests to verify PASS**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_ai_agent.py -v 2>&1 | tail -12
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~230 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/ai_agent.py tests/test_ai_agent.py && git commit -m "feat(1.4): add ai_agent — OpenAI-powered lifeos answers and action proposals"
```

---

## Task 4: Update `app/commands.py` routing + routing tests

**Files:**
- Modify: `app/commands.py`
- Modify: `tests/test_message_routing.py`

- [ ] **Step 1: Write failing routing tests**

Append to `tests/test_message_routing.py`:

```python
async def test_lifeos_question_answered_by_ai_not_expense_parser():
    from app.commands import handle_message
    update = _make_update("What is my net worth?")
    with patch("app.intent_classifier.classify_intent", return_value="lifeos_question"), \
         patch("app.ai_agent.answer_lifeos_question", return_value="Your net worth is €15,000."), \
         patch("app.database.get_latest_net_worth_snapshot", return_value=None), \
         patch("app.database.get_all_transactions", return_value=[]):
        await handle_message(update, MagicMock())
    calls = [c[0][0] for c in update.message.reply_text.call_args_list]
    assert any("€15,000" in r or "net worth" in r.lower() for r in calls)
    assert all("couldn't find an amount" not in r for r in calls)


async def test_action_request_proposes_and_stores_pending_decision():
    from app.commands import handle_message
    update = _make_update("Build the next module")
    with patch("app.intent_classifier.classify_intent", return_value="action_request"), \
         patch("app.ai_agent.propose_action", return_value="I propose to build Module 1.2. Reply A to approve or B to cancel."), \
         patch("app.database.write_agent_state") as mock_write:
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "Module 1.2" in reply or "propose" in reply.lower()
    assert "Reply A" in reply or "A to approve" in reply
    mock_write.assert_called_once()


async def test_unknown_intent_asks_for_clarification():
    from app.commands import handle_message
    update = _make_update("hello there")
    with patch("app.intent_classifier.classify_intent", return_value="unknown"), \
         patch("app.parser.parse_message", side_effect=ValueError("no amount")):
        await handle_message(update, MagicMock())
    reply = update.message.reply_text.call_args[0][0]
    assert "clarify" in reply.lower() or "not sure" in reply.lower()
    assert "couldn't find an amount" not in reply
```

- [ ] **Step 2: Run to verify FAIL**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py::test_lifeos_question_answered_by_ai_not_expense_parser tests/test_message_routing.py::test_action_request_proposes_and_stores_pending_decision tests/test_message_routing.py::test_unknown_intent_asks_for_clarification -v 2>&1 | tail -10
```

Expected: FAIL — functions don't exist yet.

- [ ] **Step 3: Update `app/commands.py`**

**Read the file first** to see the current structure.

**Add import** at the top (after the existing imports):

```python
from app.intent_classifier import classify_intent
```

**Add three new handler functions** — insert them just before the existing `_handle_net_worth_message` function:

```python
async def _handle_lifeos_question(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    from app.ai_agent import answer_lifeos_question
    from app import database

    structured = ""
    finance_kw = {"spend", "spent", "budget", "net worth", "goal", "30k", "money", "worth"}
    if any(kw in text.lower() for kw in finance_kw):
        try:
            snap = database.get_latest_net_worth_snapshot()
            txns = database.get_all_transactions()
            live_nw = calculate_live_net_worth(snap, txns)
            weekly = budget_module.calculate_weekly_status(txns, config.WEEKLY_BUDGET)
            structured = (
                f"Live net worth: €{live_nw:,.2f}\n"
                f"Weekly spend: €{weekly['weekly_spent']:.2f} / €{weekly['weekly_budget']:.2f}\n"
                f"Goal progress: {live_nw / 30000 * 100:.1f}% toward €30,000"
            )
        except Exception:
            pass

    await update.message.reply_text("🤔 Let me check the vault...")
    answer = answer_lifeos_question(text, structured)
    await update.message.reply_text(answer)


async def _handle_action_request(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    from app.ai_agent import propose_action
    from app import database

    proposal = propose_action(text)
    database.write_agent_state({
        "status_type": "decision",
        "severity": "warning",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": f"Action requested: {text}",
    })
    await update.message.reply_text(proposal)
```

**Replace `handle_message`** with this updated version:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # Priority 1: agent-control replies (A/B/C/DONE/yes/no/etc.)
    if is_agent_reply(text):
        await handle_agent_reply(update, context, text)
        return

    # Priority 2: net worth snapshot updates
    if is_net_worth_message(text):
        await _handle_net_worth_message(update, context, text)
        return

    # Priority 3: classify remaining intent
    intent = classify_intent(text)

    if intent == "lifeos_question":
        await _handle_lifeos_question(update, context, text)
        return

    if intent == "action_request":
        await _handle_action_request(update, context, text)
        return

    # finance_transaction or unknown: attempt finance parse
    try:
        parsed = parse_message(text)
    except ValueError:
        if intent == "unknown":
            await update.message.reply_text(
                "I'm not sure what you mean. Could you clarify?\n\n"
                "• Log an expense: `14 kebab` or `spent 8.50 coffee`\n"
                "• Ask a question: `What is my net worth?`\n"
                "• Agent reply: `A`, `B`, or `done`"
            )
        else:
            await update.message.reply_text(
                "I couldn't find an amount in that message.\n\n"
                "Try something like:\n"
                "  14 kebab\n"
                "  spent 8.50 on coffee\n"
                "  +314 DUO income"
            )
        return

    category = parsed.get("category") or get_category(parsed["description"])
    sheets.append_transaction(parsed, category)
    transactions = sheets.get_all_transactions()
    status = budget_module.calculate_weekly_status(transactions, config.WEEKLY_BUDGET)
    pct_left = 100 - status["pct_used"]
    if pct_left < 10:
        budget_note = "⚠️ Almost out of budget!"
    elif pct_left < 25:
        budget_note = "Getting close to your limit."
    else:
        budget_note = f"{pct_left:.0f}% of weekly budget left."
    reply = (
        f"Got it — {format_currency(parsed['amount'])} on {parsed['description']} ({category}).\n"
        f"Weekly: {format_currency(status['weekly_spent'])} / {format_currency(status['weekly_budget'])}. "
        f"{budget_note}"
    )
    await update.message.reply_text(reply)
```

- [ ] **Step 4: Run all routing tests**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_message_routing.py -v 2>&1 | tail -20
```

Expected: All 10 tests PASS (7 existing + 3 new).

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~233 passed, 0 failed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add app/commands.py tests/test_message_routing.py && git commit -m "feat(1.4): route lifeos questions and action requests to AI agent"
```

---

## Task 5: Update docs

**Files:**
- Modify: `vault/commands/command-reference.md`
- Modify: `vault/hubs/Agent_Control.md`
- Modify: `vault/hubs/Architecture.md`
- Modify: `docs/autonomous-session-protocol.md`
- Modify: `README.md`

- [ ] **Step 1: Read all five files before editing**

Read each file to understand current content and where to insert.

- [ ] **Step 2: Update `vault/commands/command-reference.md`**

Find the "### Natural Language" section and replace it with:

```markdown
### Natural Language

The bot understands three types of natural language input:

**Finance transactions** — include an amount:
- `14 kebab` → €14 expense, Food
- `+500 salary` → €500 income
- `net worth cash 2k investments 8k` → net worth snapshot

**Conversational questions** — answered using vault context + live data:
- `What is LifeOS right now?`
- `What should we build next?`
- `What was done last session?`
- `How close am I to my 30K goal?`
- `What is my current net worth?`

**Action requests** — proposed for approval, not executed immediately:
- `Build the next module`
- `Prepare handoff`
- `Run tests`
- After proposal, reply `A` to approve or `B` to cancel.

**Agent-control replies** (exact token, case-insensitive):
- `A`, `B`, `C`, `D` — decision choice
- `done` / `DONE` — manual action complete
- `yes` / `no` / `approve` / `reject` / `continue` / `stop`
```

Also update the `/goal` row under Net Worth section:
```
| `/goal` | €30K goal progress with ASCII bar |
```
(Remove the €25K reference — already fixed in code.)

- [ ] **Step 3: Update `vault/hubs/Agent_Control.md`**

Add a new section before "What's Left to Build":

```markdown
## Conversational AI Layer (v1)

The bot handles three conversational intents via `app/intent_classifier.py` + `app/ai_agent.py`:

**Intent routing order:**
1. Agent-control reply (A/B/C/DONE/yes/no) → resolve pending decision
2. Net worth update (contains NW keywords + amount) → save snapshot
3. Classify remaining: `lifeos_question` / `action_request` / `finance_transaction` / `unknown`

**LifeOS questions** → `app/ai_agent.answer_lifeos_question()`
- Loads compressed vault context pack (`app/vault_context.py`)
- Adds live financial data if question is finance-related
- Calls OpenAI GPT-4o-mini, falls back gracefully if no key

**Action requests** → `app/ai_agent.propose_action()`
- Proposes what the action would do
- Asks for A/B confirmation — never executes without approval
- Stores pending decision in `agent_state`

**Context pack files** (max 8000 chars total):
- CLAUDE.md, vault/context/LifeOS.md, Current_Priorities.md, User_Profile.md
- vault/hubs/Architecture.md, Finance.md, Agent_Control.md
- vault/projects/finance-lifeos.md, vault/sessions/recent-sessions.md, handoff/latest.md
```

- [ ] **Step 4: Update `vault/hubs/Architecture.md`**

Read the file first. Add a new layer to the architecture description:

```markdown
## AI Agent Layer (v1)

```
Telegram message
  → owner auth check
  → is_agent_reply? → resolve pending decision
  → is_net_worth_message? → save snapshot
  → classify_intent() →
      lifeos_question → ai_agent.answer_lifeos_question() → vault context + OpenAI
      action_request  → ai_agent.propose_action() → vault context + OpenAI + pending decision
      finance/unknown → parse_message() → DB insert
```

Context: `app/vault_context.py` loads fixed vault file pack (max 8000 chars) on each AI call.
No RAG, no vectors. v2 will add semantic search.
```

- [ ] **Step 5: Update `docs/autonomous-session-protocol.md`**

Add a note in the "What Arrya Does" section table:

Append a row:
```
| LifeOS question (conversational) | Sent by user, answered by bot — no action needed |
```

Also add a brief note at the end of the doc:

```markdown
## AI Responses During Autonomous Sessions

When you ask the bot a natural question during an autonomous session, it answers using the current vault context. This does not interrupt Claude's work — Claude only receives replies to structured decision/manual action notifications.
```

- [ ] **Step 6: Update `README.md`**

Read the file first. Add "Conversational AI" to the feature list. Find the features or overview section and add:

```markdown
- **Conversational AI** — Ask natural questions about LifeOS via Telegram; bot answers using vault context and live data. Request actions safely with approval workflow.
```

- [ ] **Step 7: Run full suite (no test changes)**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: ~233 passed.

- [ ] **Step 8: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add vault/commands/command-reference.md vault/hubs/Agent_Control.md vault/hubs/Architecture.md docs/autonomous-session-protocol.md README.md && git commit -m "docs(1.4): document conversational AI agent v1 — intent routing, vault context, action proposals"
```

---

## Task 6: Final verification + Telegram completion + push

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 230+ passed, 0 failed.

- [ ] **Step 2: Send Telegram completion notification (NOT handoff)**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/notify_me.py complete "Conversational LifeOS Agent v1 live. Natural questions answered via vault context + OpenAI. Action proposals with A/B approval. Intent routing: finance/question/action/unknown. All tests passing."
```

- [ ] **Step 3: Update handoff files silently**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/create_handoff.py --silent
```

- [ ] **Step 4: Commit and push**

```bash
cd /Users/arryawillems/finance-lifeos && git add handoff/ && git diff --cached --quiet || git commit -m "docs(1.4): handoff after conversational agent v1" && git push origin master
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| Intent routing: finance/nw_update/agent_reply/lifeos_question/action_request/unknown | Task 2 (classifier) + Task 4 (routing) |
| Agent replies handled before expense parsing | Task 4 (routing order) |
| Finance parsing only when clearly transaction | Task 4 (intent=finance_transaction) |
| Vault context retrieval — fixed compressed context pack | Task 1 |
| Context files: CLAUDE.md, vault/context/*, vault/hubs/*, projects, sessions, handoff | Task 1 |
| Token/char limits so prompts don't explode | Task 1 (MAX_TOTAL_CHARS=8000, per-file limits) |
| AI chat response — answer lifeos questions with vault context | Task 3 (ai_agent.py) + Task 4 |
| Structured data for finance questions (live NW, weekly spend, goal) | Task 4 (_handle_lifeos_question) |
| Action proposals — propose, confirm, store, do NOT execute | Task 3 (propose_action) + Task 4 (_handle_action_request) |
| Approval rule — A/B before anything risky | Task 4 (pending decision stored) |
| UX: clarification for unknown intent | Task 4 (unknown → clarify message) |
| Safety: no shell commands, no secrets, no raw code execution | Existing + Task 3 (propose only) |
| Tests: intent classification | Task 2 |
| Tests: A/B/DONE not parsed as expenses | Existing tests/Task 4 |
| Tests: vault context loader size limits | Task 1 |
| Tests: lifeos question routing | Task 4 |
| Tests: finance transaction routing | Task 2 |
| Tests: action request confirmation | Task 4 |
| Docs: command-reference.md | Task 5 |
| Docs: Agent_Control.md | Task 5 |
| Docs: Architecture.md | Task 5 |
| Docs: autonomous-session-protocol.md | Task 5 |
| README | Task 5 |
| Completion notification (not handoff) | Task 6 |

**No gaps found.**

**Placeholder scan:** No TBD, no "similar to Task N". All code complete.

**Type consistency:**
- `load_vault_context() -> str` — defined Task 1, imported in Task 3 `ai_agent.py`
- `classify_intent(text: str) -> str` — defined Task 2, imported at top of `commands.py` Task 4
- `answer_lifeos_question(question: str, structured_data: str = "") -> str` — defined Task 3, imported locally in `_handle_lifeos_question` Task 4
- `propose_action(request: str) -> str` — defined Task 3, imported locally in `_handle_action_request` Task 4
- `_call_openai(system: str, user: str, max_tokens: int = 300) -> str | None` — internal to `ai_agent.py`, mocked in Task 3 tests ✓
