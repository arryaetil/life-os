# Architecture Hub

[[LifeOS]] system design.

---

## Layer Responsibilities

| Layer | Technology | Role |
|-------|-----------|------|
| **Telegram** | python-telegram-bot 20.7 | Input + notification channel |
| **FastAPI / Railway** | FastAPI 0.111, uvicorn | Backend runtime, webhook receiver, dashboard server |
| **PostgreSQL** | Railway-managed | Structured data — all module tables |
| **Vault** | Markdown files in `/vault` | Memory and context layer for AI sessions |
| **Claude Code** | Claude Sonnet/Opus | Implementation worker; reads vault, codes, commits |
| **Dashboard** | Jinja2 + Chart.js | Read-only visualisation at Railway URL |

---

## Data Flow

```
User (Telegram)
  ↓ natural language message
FastAPI /webhook
  ↓ owner auth → message routing
AI parser (GPT-4o-mini → regex fallback)
  ↓
PostgreSQL INSERT
  ↓
Telegram reply (status/confirmation)

User (browser)
  ↓ GET /networth etc.
FastAPI route
  ↓ SQLAlchemy SELECT
Jinja2 template render
  ↓
HTML response
```

---

## Why These Choices

See [[architecture-decisions]] for full rationale.

**Short version:**
- PostgreSQL: structured relational data; Railway provides it managed, zero ops
- Railway: zero-config deploy from git push; handles env vars, PostgreSQL, auto-restart
- Telegram: mobile-first, no app to build, API is trivial, natural language fits
- Single repo: all modules share DB, one deploy, one codebase — appropriate at this scale
- Vault: context compression across session rotations

---

## Why Vault / Context Compression Matters

Claude sessions have token limits. When a session ends, all in-session context is lost. Without structured memory:
- Each new session re-reads the full codebase to understand the project
- Token budget wasted on code that hasn't changed
- Risk of rebuilding working features or missing recent decisions

The vault provides compressed, structured operational context. A session reading 6 vault files (≈3K tokens) understands the project as well as one that spent 20K tokens reading code.

---

## Why Handoff Continuity Matters

Complex features span multiple sessions. Without handoff:
- Next session doesn't know what was half-finished
- Duplicate work or conflicting implementations
- Blockers go unseen by the user

`handoff/latest.md` + `agent_state` DB + Telegram notification = zero-loss session handoff.

---

## Future Architecture Considerations

**Separate repos per module** — appropriate once modules have distinct lifecycles, teams, or deploy cadences. Not now — shared DB and single Railway service keep ops simple.

**Auth on dashboard** — currently unprotected. Add HTTP Basic Auth before sharing URL publicly.

**MCP integrations** — considered for future agent capabilities; not in scope until Module 4.
