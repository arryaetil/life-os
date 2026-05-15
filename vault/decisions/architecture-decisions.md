# Architecture Decisions

---

## Why PostgreSQL

- Relational structure fits financial data (transactions, snapshots, accounts)
- Railway provides managed PostgreSQL with zero ops overhead
- SQLAlchemy 2.0 Core gives full control without ORM magic
- Append-only snapshot pattern (net worth) naturally fits relational tables
- Single instance shared across all modules — no cross-service joins needed at this scale

Alternative considered: SQLite (used locally), Supabase. Railway PostgreSQL wins on zero-config managed hosting.

---

## Why Railway

- Auto-deploys from `master` branch push — zero manual deploy steps
- Automatically injects `DATABASE_URL` for attached PostgreSQL
- Handles env vars, restarts, and HTTPS termination
- No container management or DevOps knowledge required
- Cost: free tier sufficient at single-user scale

Alternative considered: Render, Fly.io, manual VPS. Railway wins on simplicity and managed DB integration.

---

## Why Telegram

- Mobile-first: user always has it open
- No app to build — bot API handles all input/output
- Natural language fits conversational input model
- Webhook-based: Railway receives POST requests, no polling needed in production
- Push notifications are trivial via `send_telegram_message()`
- Owner-only auth is a single chat ID check

Alternative considered: WhatsApp, SMS, custom mobile app. Telegram wins on developer API quality and zero friction.

---

## Why Vault Structure

- Claude sessions rotate when token limits hit — all in-session context is lost
- Without structured memory, each session re-reads the full codebase (wasteful)
- Vault provides compressed operational context: ~3K tokens vs 20K+ to scan code
- Markdown = human-readable + AI-readable + Obsidian-compatible
- No external services, no RAG, no vector DB — just files in the repo

Alternative considered: CLAUDE.md alone, external Notion, comments in code. Vault wins on portability and token efficiency.

---

## Why Separate Project Repos (Future)

Not yet done. When to split:
- Modules have distinct deployment cadences (e.g., health app deploys independently)
- Multiple contributors working on different modules
- Module grows large enough to warrant its own DB, deploy pipeline, or CI

Current state: single repo, single Railway service, shared DB — correct at this scale.

---

## Why Owner-Only Auth

- Dashboard has no auth (by design, read-only for now)
- Bot handles writes — must be restricted to owner only
- Simple: one env var (`TELEGRAM_OWNER_CHAT_ID`), one check (`is_owner()`)
- No tokens, no passwords, no session management
- All handlers wrapped via `owner_only()` decorator in `app/bot.py`

Alternative considered: password commands, token-based auth, IP filtering. Chat ID check wins on simplicity.

---

## Why Handoff System

- Feature work spans multiple Claude sessions (token limits)
- Without handoff: next session doesn't know what was half-done
- `handoff/latest.md` + `agent_state` DB + Telegram notification = complete continuity
- User receives Telegram message with exact continuation instructions
- Vault files provide project-level memory; handoff provides session-level memory

---

## Why Append-Only Net Worth Snapshots

- Full audit trail of net worth over time
- Chart.js trend chart requires historical data points
- No reconciliation or migration needed if schema evolves
- Simple: always INSERT, never UPDATE or DELETE
