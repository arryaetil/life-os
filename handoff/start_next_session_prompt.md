# LifeOS — Next Session Startup Prompt

Paste this as your first message when starting a new Claude session on this repo.

---

I'm continuing work on the LifeOS repo (finance-lifeos).

Please read in this order before doing anything:
1. CLAUDE.md
2. docs/architecture.md
3. docs/current-status.md
4. handoff/latest.md

Then:
- Confirm the current state
- Run `pytest` and confirm all tests pass
- Ask what I'd like to work on next

Rules:
- Do NOT rebuild existing functionality
- Do NOT modify existing passing tests
- Do NOT change the database schema without explicit instruction
- Do NOT commit broken code
- Notify me via `python scripts/notify_me.py` when decisions, blockers, or completions occur
