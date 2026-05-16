# Autonomous Session Protocol v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the safe supervision loop so Claude can work autonomously on the laptop while Arrya monitors and decides via Telegram.

**Architecture:** Three layers — `notify_me.py` for high-signal progress/error/complete/handoff, `ask_user.py` for structured decisions with options and recommendation, `docs/autonomous-session-protocol.md` as the canonical protocol reference. No remote shell execution, no arbitrary commands, no new bot commands — only outbound Telegram notifications.

**Tech Stack:** Python 3.13, python-telegram-bot (existing `app/telegram.py`), argparse, pytest 8.2.1, existing `app/database.write_agent_state`

**Baseline:** 173 tests passing. Never reduce this count.

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `scripts/notify_me.py` | Modify | Improve `decision` format: add "Options:" header, "Reply with A/B/C." wording |
| `scripts/ask_user.py` | Create | New script: structured decision with `--question`, `--options`, `--recommendation` |
| `tests/test_notify.py` | Modify | Update decision format assertions to match new wording |
| `tests/test_ask_user.py` | Create | Tests for `format_decision_message` in `ask_user.py` |
| `docs/autonomous-session-protocol.md` | Create | Full protocol reference document |
| `CLAUDE.md` | Modify | Add `ask_user.py`, fix test count, strengthen autonomous workflow rules |
| `vault/context/Operating_Rules.md` | Modify | Add `ask_user.py`, update test count, add terminal-only rule |

---

## Task 1: Improve `notify_me.py` decision format + fix tests

**Files:**
- Modify: `scripts/notify_me.py` (lines 64-66)
- Modify: `tests/test_notify.py`

- [ ] **Step 1: Update `test_notify.py` to reflect the new expected format**

In `tests/test_notify.py`, replace `test_decision_format`:

```python
def test_decision_format():
    result = _format_message("decision", "Choose DB", ["A: PostgreSQL", "B: Supabase"])
    assert "🤔 Decision needed:" in result
    assert "Choose DB" in result
    assert "Options:" in result
    assert "A: PostgreSQL" in result
    assert "B: Supabase" in result
    assert "Reply with A/B/C." in result
    assert "Reply with your choice." not in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_notify.py::test_decision_format -v 2>&1 | tail -5
```

Expected: FAIL — `"Options:" not in result` and `"Reply with A/B/C." not in result`.

- [ ] **Step 3: Update `_format_message` in `scripts/notify_me.py`**

Find the `decision` branch in `_format_message` (currently lines 64-66):

```python
    if status_type == "decision":
        lines = ["🤔 Decision needed:", message] + options + ["Reply with your choice."]
        return "\n".join(lines)
```

Replace with:

```python
    if status_type == "decision":
        lines = ["🤔 Decision needed:", message, "", "Options:"]
        lines.extend(options)
        lines += ["", "Reply with A/B/C."]
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_notify.py -v 2>&1 | tail -15
```

Expected: All 9 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 173 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add scripts/notify_me.py tests/test_notify.py && git commit -m "feat(1.4): improve decision notification format — Options header, A/B/C reply prompt"
```

---

## Task 2: Create `scripts/ask_user.py` + `tests/test_ask_user.py`

**Files:**
- Create: `scripts/ask_user.py`
- Create: `tests/test_ask_user.py`

- [ ] **Step 1: Write the failing tests first**

Create `tests/test_ask_user.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ask_user import format_decision_message


def test_format_basic_decision():
    result = format_decision_message(
        question="Which database?",
        options=["A) PostgreSQL", "B) SQLite"],
        recommendation="",
    )
    assert "🤔 Decision needed:" in result
    assert "Which database?" in result
    assert "Options:" in result
    assert "A) PostgreSQL" in result
    assert "B) SQLite" in result
    assert "Reply with A/B/C." in result
    assert "Recommendation:" not in result


def test_format_decision_with_recommendation():
    result = format_decision_message(
        question="Which approach?",
        options=["A) Fast", "B) Safe"],
        recommendation="A — faster and simpler for this scope",
    )
    assert "Recommendation:" in result
    assert "A — faster and simpler for this scope" in result


def test_format_decision_three_options():
    result = format_decision_message(
        question="Pick storage",
        options=["A) S3", "B) Local disk", "C) PostgreSQL BLOB"],
        recommendation="C — already have the connection",
    )
    assert "C) PostgreSQL BLOB" in result
    assert "C — already have the connection" in result


def test_format_options_before_recommendation():
    """Options section must appear before Recommendation in the output."""
    result = format_decision_message(
        question="Q?",
        options=["A) X", "B) Y"],
        recommendation="A — better",
    )
    options_pos = result.index("Options:")
    rec_pos = result.index("Recommendation:")
    assert options_pos < rec_pos


def test_format_no_recommendation_omits_section():
    """Empty recommendation must not add a blank Recommendation: header."""
    result = format_decision_message("Q?", ["A) X"], "")
    assert "Recommendation:" not in result


def test_format_reply_prompt_present():
    result = format_decision_message("Q?", ["A) X"], "")
    assert result.strip().endswith("Reply with A/B/C.")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_ask_user.py -v 2>&1 | tail -10
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ask_user'`.

- [ ] **Step 3: Create `scripts/ask_user.py`**

```python
#!/usr/bin/env python3
"""
Send a structured decision request to Telegram and write to agent_state.

Usage:
    python scripts/ask_user.py \
        --question "Which database should we use?" \
        --options "A) PostgreSQL — already in use" "B) SQLite — simpler, no infra" \
        --recommendation "A — PostgreSQL is already configured in Railway"
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from app.telegram import send_telegram_message
from app.database import write_agent_state


def format_decision_message(question: str, options: list[str], recommendation: str) -> str:
    lines = ["🤔 Decision needed:", question, "", "Options:"]
    lines.extend(options)
    if recommendation:
        lines += ["", "Recommendation:", recommendation]
    lines += ["", "Reply with A/B/C."]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a structured decision request to Telegram")
    parser.add_argument("--question", required=True, help="The decision question")
    parser.add_argument(
        "--options", nargs="+", required=True,
        help="Options list, e.g. 'A) PostgreSQL' 'B) SQLite'",
    )
    parser.add_argument(
        "--recommendation", default="",
        help="Short recommendation with reasoning, e.g. 'A — already configured'",
    )
    args = parser.parse_args()

    text = format_decision_message(args.question, args.options, args.recommendation)

    write_agent_state({
        "status_type": "decision",
        "severity": "warning",
        "requires_user_action": True,
        "resolved": False,
        "progress_message": args.question,
        "metadata_json": json.dumps({
            "options": args.options,
            "recommendation": args.recommendation,
        }),
    })

    sent = send_telegram_message(text)
    if sent:
        print("Decision sent to Telegram. Waiting for user response.")
    else:
        print("✗ Telegram failed (state written to DB).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest tests/test_ask_user.py -v 2>&1 | tail -15
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 179 passed (173 + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add scripts/ask_user.py tests/test_ask_user.py && git commit -m "feat(1.4): add ask_user.py — structured decision notifications with options and recommendation"
```

---

## Task 3: Create `docs/autonomous-session-protocol.md`

**Files:**
- Create: `docs/autonomous-session-protocol.md`

- [ ] **Step 1: Create the protocol document**

Write `docs/autonomous-session-protocol.md` with exactly this content:

```markdown
# Autonomous Session Protocol v1

_Last updated: 2026-05-16_

---

## Overview

The laptop runs Claude Code sessions. Telegram is the supervision and decision channel. Claude works autonomously; Arrya monitors remotely.

```
Laptop (Claude Code session)
  → implementation worker
  → sends Telegram notifications for decisions, progress, handoffs

Telegram (Arrya's phone)
  → monitoring layer
  → receives updates
  → sends decisions/approvals back

LifeOS repo + vault
  → persistent memory
  → source of truth between sessions
```

---

## The Core Rule

**Claude must never block waiting for a terminal-only answer.**

If Claude needs a decision, approval, or manual action — it sends a Telegram notification and continues with a safe default or waits for the reply. It does not ask questions in the terminal that Arrya cannot see remotely.

---

## Notification Types and When to Send

### Progress
Send when starting a task, finishing a major sub-step, running tests, creating a commit, or completing a module.

```bash
python scripts/notify_me.py progress "Starting Module 1.2 portfolio table"
python scripts/notify_me.py progress "Tests passing — 178/178"
python scripts/notify_me.py progress "Committed: feat(1.2): add portfolio snapshot table"
```

**Do not send** for every file edit, every function added, or routine steps. High signal only.

### Decision
Send when Claude needs Arrya to choose between approaches, approve an architecture, or confirm a scope.

Use `ask_user.py` for structured decisions:

```bash
python scripts/ask_user.py \
  --question "How should we store portfolio holdings?" \
  --options "A) New table per asset class" "B) JSON column on net_worth_snapshots" \
  --recommendation "A — cleaner queries, easier to extend"
```

Telegram format:
```
🤔 Decision needed:
How should we store portfolio holdings?

Options:
A) New table per asset class
B) JSON column on net_worth_snapshots

Recommendation:
A — cleaner queries, easier to extend

Reply with A/B/C.
```

Arrya replies with: `A`, `B`, or `C`.

### Manual Action
Send when Arrya must do something before Claude can continue.

```bash
python scripts/notify_me.py action "Add OPENAI_API_KEY to Railway environment variables:
1. Go to Railway → finance-lifeos → Variables
2. Add: OPENAI_API_KEY = <your key>
3. Redeploy if needed
Reply DONE when complete."
```

Arrya replies: `DONE`

**Examples of manual actions:**
- Add env var to Railway
- Switch Claude account (logout/login)
- Approve a Railway deployment
- Set GitHub remote after new repo creation

### Error / Blocker
Send immediately when tests fail unexpectedly, a tool errors, or work is blocked.

```bash
python scripts/notify_me.py error "Tests failing in test_networth_db.py: AssertionError at line 42. Blocker: DB schema mismatch."
```

### Complete
Send when a module, sub-module, or major task finishes.

```bash
python scripts/notify_me.py complete "Module 1.2 portfolio tracker done. 185/185 tests passing. Dashboard updated."
```

### Handoff
Send when session/context limit is near or work must stop. Always run `create_handoff.py` — never just the notify.

```bash
python scripts/create_handoff.py
```

This writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, records state to PostgreSQL, and sends the Telegram notification.

---

## What Claude Does When Receiving a Reply

Claude cannot receive Telegram replies during a session — it only sends. Replies inform the **next** session.

For decisions, Claude should:
1. Send the decision notification.
2. If work can continue safely without the answer → proceed with the conservative option and note it.
3. If work cannot continue → send a handoff and stop.

---

## What Arrya Does

| Telegram message | Action |
|---|---|
| `✅ Progress: ...` | Read, no reply needed |
| `🤔 Decision needed: ...` | Reply with `A`, `B`, or `C` |
| `🔧 Manual action needed: ...` | Do the steps, reply `DONE` |
| `❌ Error: ...` | Diagnose, fix remotely if possible, or open laptop |
| `🎉 Complete: ...` | Read, no reply needed |
| `🔄 Session handoff needed` | Open laptop, switch account, start new session with handoff prompt |

---

## What Still Requires the Laptop

These actions cannot be done remotely via Telegram and require returning to the laptop:

- Starting a new Claude Code session
- Switching Claude accounts (`claude logout` / `claude login`)
- Providing a new high-level task prompt
- Resolving a merge conflict
- Debugging a local-only environment issue (env file, venv, etc.)
- Reviewing and approving a large architectural change
- Inspecting a test failure that can't be described in a short message

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/notify_me.py` | All notification types | `python scripts/notify_me.py <type> "<msg>"` |
| `scripts/ask_user.py` | Structured decision with options + recommendation | `python scripts/ask_user.py --question "..." --options "A) ..." --recommendation "..."` |
| `scripts/create_handoff.py` | Generate handoff files + notify | `python scripts/create_handoff.py` |

### notify_me.py types

| Type | Alias | When to use |
|------|-------|-------------|
| `progress` | — | Starting task, milestone, test pass, commit |
| `decision` | — | Simple decision (use ask_user.py for structured) |
| `manual_action` | `action` | Arrya must do something manually |
| `error` | — | Test failure, blocker, unexpected error |
| `complete` | — | Module or task complete |
| `handoff` | — | Rarely used directly — use create_handoff.py instead |

---

## Safety Rules

- **No remote shell execution.** Telegram is read-only input for Claude — Claude cannot execute commands from Telegram messages.
- **No arbitrary commands.** Claude only runs scripts within the repo.
- **No secrets in notifications.** Never include API keys, tokens, or `.env` content in Telegram messages.
- **No file deletion.** Without explicit user approval in the task prompt.
- **No transactions table schema changes.** Ever.
```

- [ ] **Step 2: Verify file was written**

```bash
ls -la /Users/arryawillems/finance-lifeos/docs/autonomous-session-protocol.md
```

Expected: File exists, nonzero size.

- [ ] **Step 3: Run full suite (no test changes here)**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 179 passed.

- [ ] **Step 4: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add docs/autonomous-session-protocol.md && git commit -m "docs(1.4): add autonomous session protocol v1"
```

---

## Task 4: Update `CLAUDE.md` and `vault/context/Operating_Rules.md`

**Files:**
- Modify: `CLAUDE.md`
- Modify: `vault/context/Operating_Rules.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Make these targeted edits to `CLAUDE.md`:

**Edit 1** — Fix the stale test count in "Preserve Tests":

Find:
```
- The test suite (`tests/`) has 74 passing tests. Never reduce that count.
```

Replace with:
```
- The test suite (`tests/`) currently has 179+ passing tests. Never reduce that count.
```

**Edit 2** — Expand the "Notify via Telegram" section under "Autonomous Workflow Rules":

Find:
```
### Notify via Telegram
Run `python scripts/notify_me.py <type> "<message>"` whenever:
- A decision is needed from the user → `notify_me.py decision "..." "A:..." "B:..."`
- Manual setup is required (Railway env vars, etc.) → `notify_me.py action "..."`
- Deployment approval is needed → `notify_me.py action "..."`
- Tests fail unexpectedly → `notify_me.py error "..."`
- A module or task completes → `notify_me.py complete "..."`
- A blocker occurs → `notify_me.py error "Blocked: ..."`
- Session/context/token limit is nearing → run `create_handoff.py` immediately
```

Replace with:
```
### Notify via Telegram

**Terminal-only questions are not acceptable during autonomous sessions.** If Claude needs a decision, approval, or clarification, it must send a Telegram notification — not ask in the terminal.

Use `scripts/notify_me.py` for high-signal updates:

| When | Command |
|------|---------|
| Starting task or milestone | `notify_me.py progress "..."` |
| Tests passing or failing | `notify_me.py progress "..."` or `notify_me.py error "..."` |
| Commit created | `notify_me.py progress "Committed: feat(...)"` |
| Simple decision needed | `notify_me.py decision "..." "A:..." "B:..."` |
| Structured decision with recommendation | `python scripts/ask_user.py --question "..." --options "A) ..." --recommendation "..."` |
| Manual setup required (Railway, env vars) | `notify_me.py action "..."` |
| Deployment approval needed | `notify_me.py action "..."` |
| Test failure or blocker | `notify_me.py error "..."` |
| Module or task complete | `notify_me.py complete "..."` |
| Session ending or tokens low | `python scripts/create_handoff.py` |

See `docs/autonomous-session-protocol.md` for full supervision protocol, response format, and safety rules.
```

**Edit 3** — Fix the stale test count in the `tests/` line of Repo Layout:

Find:
```
  tests/             — 74 passing tests
```

Replace with:
```
  tests/             — 179+ passing tests
```

- [ ] **Step 2: Update `vault/context/Operating_Rules.md`**

**Edit 1** — Fix test count in "Test Discipline":

Find:
```
- 150 tests must remain passing at all times (`pytest`)
```

Replace with:
```
- 179+ tests must remain passing at all times (`pytest`)
```

**Edit 2** — Replace the entire "Telegram Supervision" section:

Find:
```
## Telegram Supervision

All bot handlers are owner-gated via `app/auth.py → owner_only()`. Only `TELEGRAM_OWNER_CHAT_ID` can use the bot.

Claude sends notifications via `scripts/notify_me.py`:

| When | Command |
|------|---------|
| Task started or milestone | `notify_me.py progress "..."` |
| Decision needed | `notify_me.py decision "..." "A:..." "B:..."` |
| Manual setup needed (Railway, env vars) | `notify_me.py action "..."` |
| Test failure or blocker | `notify_me.py error "..."` |
| Module or task complete | `notify_me.py complete "..."` |
| Session ending | `python scripts/create_handoff.py` |
```

Replace with:
```
## Telegram Supervision

All bot handlers are owner-gated via `app/auth.py → owner_only()`. Only `TELEGRAM_OWNER_CHAT_ID` can use the bot.

**Terminal-only questions are not acceptable.** During autonomous sessions, Claude must route all decisions and blockers through Telegram — not ask in the terminal.

Claude sends notifications via `scripts/notify_me.py` and `scripts/ask_user.py`:

| When | Command |
|------|---------|
| Task started or milestone | `notify_me.py progress "..."` |
| Tests pass/fail | `notify_me.py progress "..."` / `notify_me.py error "..."` |
| Commit created | `notify_me.py progress "Committed: ..."` |
| Simple decision needed | `notify_me.py decision "..." "A:..." "B:..."` |
| Structured decision with recommendation | `scripts/ask_user.py --question "..." --options "A) ..." --recommendation "..."` |
| Manual setup needed (Railway, env vars) | `notify_me.py action "..."` |
| Test failure or blocker | `notify_me.py error "..."` |
| Module or task complete | `notify_me.py complete "..."` |
| Session ending | `python scripts/create_handoff.py` |

Full protocol: `docs/autonomous-session-protocol.md`
```

- [ ] **Step 3: Run full suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -3
```

Expected: 179 passed.

- [ ] **Step 4: Commit**

```bash
cd /Users/arryawillems/finance-lifeos && git add CLAUDE.md vault/context/Operating_Rules.md && git commit -m "docs(1.4): update CLAUDE.md and Operating_Rules with supervision protocol v1"
```

---

## Task 5: Final verification, Telegram notification, handoff, push

**Files:**
- Modify: `handoff/latest.md` (via script)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/arryawillems/finance-lifeos && python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: 179 passed, 0 failed.

- [ ] **Step 2: Verify ask_user.py CLI works end-to-end**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/ask_user.py \
  --question "Test: does this reach Telegram?" \
  --options "A) Yes, it works" "B) No, something is broken" \
  --recommendation "A — if you can read this, it works"
```

Expected output: `Decision sent to Telegram. Waiting for user response.`

- [ ] **Step 3: Send Telegram completion notification**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/notify_me.py complete "Autonomous Session Protocol v1 complete. ask_user.py live, decision format improved, protocol doc written. 179 tests passing."
```

- [ ] **Step 4: Write handoff**

```bash
cd /Users/arryawillems/finance-lifeos && python scripts/create_handoff.py
```

- [ ] **Step 5: Final commit if handoff modified anything**

```bash
cd /Users/arryawillems/finance-lifeos && git add handoff/ && git diff --cached --quiet || git commit -m "docs(1.4): handoff after autonomous session protocol v1"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Decision routing via Telegram (never terminal-only) | Task 4 (CLAUDE.md rule) + Task 3 (protocol doc) |
| Decision format: Decision needed / Options A/B/C / Recommendation / Reply with A/B/C | Task 1 (notify_me.py) + Task 2 (ask_user.py) |
| Manual action format: Manual action needed / steps / Reply DONE | Existing notify_me.py already correct — Task 3 documents it |
| Progress updates: high-signal milestones | Existing notify_me.py progress type — Task 4 documents when to use |
| Handoff notifications: what done / what next / where to continue | Existing create_handoff.py — Task 3 documents it |
| Completion notifications | Existing notify_me.py complete type — Task 3 documents it |
| `scripts/ask_user.py` — sends decision, writes agent_state, prints confirmation | Task 2 |
| `scripts/notify_me.py` — supports all types | Task 1 (decision format improvement) |
| `scripts/create_handoff.py` — generates handoff + notifies | Already complete — documented in Task 3 |
| `docs/autonomous-session-protocol.md` | Task 3 |
| Update `vault/context/Operating_Rules.md` | Task 4 |
| Update `CLAUDE.md` | Task 4 |
| Tests: notification formatting | Task 1 (updated) + Task 2 (new) |
| Tests: ask_user behavior | Task 2 |
| Tests: no regression | Every task runs full suite |
| Safety rules: no remote shell, no arbitrary commands, no secrets in notifications | Task 3 (protocol doc Safety Rules section) + Task 4 (CLAUDE.md Never section already covers this) |

**Gaps:** None.

**Placeholder scan:** No TBD, no "similar to Task N", all code is complete.

**Type consistency:**
- `format_decision_message(question: str, options: list[str], recommendation: str) -> str` — used in Task 2 implementation and Task 2 tests consistently.
- `_format_message(status_type: str, message: str, options: list[str]) -> str` — signature unchanged from existing; Task 1 only changes the return value body. Tests import from `scripts/` path consistently.
