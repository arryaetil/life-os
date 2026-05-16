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
  → Arrya replies with decisions/approvals

LifeOS repo + vault
  → persistent memory
  → source of truth between sessions
```

---

## The Core Rule

**Claude must never block waiting for a terminal-only answer.**

If Claude needs a decision, approval, or manual action — it sends a Telegram notification. It does not ask questions in the terminal that Arrya cannot see remotely.

---

## Notification Types and When to Send

### Progress
Send when starting a task, finishing a major sub-step, running tests, creating a commit, or completing a module.

```bash
python scripts/notify_me.py progress "Starting Module 1.2 portfolio table"
python scripts/notify_me.py progress "Tests passing — 185/185"
python scripts/notify_me.py progress "Committed: feat(1.2): add portfolio snapshot table"
```

Do not send for every file edit or routine step. High signal only.

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

Examples of manual actions:
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
Send when session/context limit is near or work must stop. Always run `create_handoff.py` — never just the notify type.

```bash
python scripts/create_handoff.py
```

This writes `handoff/latest.md`, updates `handoff/start_next_session_prompt.md`, records state to PostgreSQL, and sends the Telegram notification.

---

## What Claude Does When It Needs a Decision

Claude cannot receive Telegram replies during a running session — it only sends. Replies inform the **next** session via `handoff/latest.md`.

When Claude hits a decision point:
1. Send the decision notification via `ask_user.py`.
2. If work can safely continue without the answer → proceed with the conservative option, note it clearly.
3. If work cannot continue → run `create_handoff.py` and stop.

---

## What Arrya Does

| Telegram message | Action |
|---|---|
| `✅ Progress: ...` | Read only, no reply needed |
| `🤔 Decision needed: ...` | Reply with `A`, `B`, or `C` |
| `🔧 Manual action needed: ...` | Do the steps, reply `DONE` |
| `❌ Error: ...` | Diagnose, fix remotely if possible, or open laptop |
| `🎉 Complete: ...` | Read only, no reply needed |
| `🔄 Session handoff needed` | Open laptop, switch account, start new session with handoff prompt |

---

## What Still Requires the Laptop

These cannot be done remotely via Telegram and require returning to the laptop:

- Starting a new Claude Code session
- Switching Claude accounts (`claude logout` / `claude login`)
- Providing a new high-level task prompt
- Resolving a merge conflict
- Debugging a local-only environment issue (env file, venv, etc.)
- Inspecting a complex test failure that can't be described in a short message
- Reviewing a large architectural change before approving it

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/notify_me.py` | All notification types | `python scripts/notify_me.py <type> "<msg>"` |
| `scripts/ask_user.py` | Structured decision with options + recommendation | `python scripts/ask_user.py --question "..." --options "A) ..." --recommendation "..."` |
| `scripts/create_handoff.py` | Generate handoff files + send Telegram notification | `python scripts/create_handoff.py` |

### notify_me.py types

| Type | Alias | When to use |
|------|-------|-------------|
| `progress` | — | Starting task, milestone, test pass, commit created |
| `decision` | — | Simple decision (use `ask_user.py` for structured decisions) |
| `manual_action` | `action` | Arrya must do something manually |
| `error` | — | Test failure, blocker, unexpected error |
| `complete` | — | Module or task complete |
| `handoff` | — | Rarely used directly — use `create_handoff.py` instead |

---

## Safety Rules

- **No remote shell execution.** Telegram is one-way output from Claude — Claude cannot execute commands from Telegram replies.
- **No arbitrary commands.** Claude only runs scripts within the repo.
- **No secrets in notifications.** Never include API keys, tokens, or `.env` content in any Telegram message.
- **No file deletion** without explicit user approval in the task prompt.
- **No transactions table schema changes.** Ever.
