# Operating Rules

Rules every Claude session must follow when working in this repo.

---

## Repo Boundaries

- Work only inside `/Users/arryawillems/finance-lifeos/` (the repo root)
- Never access files outside the repo
- Never read, print, modify, or commit `.env` content or secrets
- Never delete files without explicit user approval

---

## Destructive Actions

- Never modify the `transactions` table schema
- Never rebuild a module marked DONE in `docs/current-status.md`
- Never force-push or reset history
- Never drop or truncate database tables
- Never skip tests before committing a completed feature

---

## Test Discipline

- 179+ tests must remain passing at all times (`pytest`)
- New features must include new tests
- Run `pytest` before every commit
- Never reduce the test count

---

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

---

## Commit Discipline

- Format: `<type>(<scope>): <description>` — e.g. `feat(1.2): add portfolio table`
- Commit after each completed, tested feature
- Never commit broken tests or un-runnable code
- Prefer small focused commits over large batched ones

---

## Handoff Workflow

When tokens are running low or session is ending:
1. Run `python scripts/create_handoff.py`
2. This writes `handoff/latest.md`, sends Telegram notification, writes state to PostgreSQL
3. Next session reads `handoff/latest.md` for exact continuation point

---

## Vault Maintenance

Update vault files when:
- Major work completes → update `vault/sessions/recent-sessions.md`
- Architecture changes → update `vault/hubs/Architecture.md`
- Priorities shift → update `vault/context/Current_Priorities.md`
- Session ends → update `vault/sessions/recent-sessions.md` + run `create_handoff.py`

Keep vault files concise. No bloated documentation.

---

## Context Loading Order

Every session must read these files before writing any code:

1. `CLAUDE.md`
2. `vault/context/LifeOS.md`
3. `vault/context/Current_Priorities.md`
4. `vault/hubs/Architecture.md`
5. `vault/projects/finance-lifeos.md`
6. `vault/sessions/recent-sessions.md`
7. `handoff/latest.md`
