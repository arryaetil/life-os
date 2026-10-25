# Handoff — 2026-10-25

## What Was Done
- Integrated a Career Agent MVP into Life OS at `/career`.
- Added isolated SQLAlchemy Core tables for career facts, jobs, applications, contacts, daily runs and audit events.
- Added deterministic transparent scoring, evidence-bound materials, one-opportunity selection and idempotent daily execution.
- Added explicit human approval, manual-only outreach tracking and safe field-planning boundaries for CAPTCHA/ambiguous questions.
- Added in-memory DOCX/PDF document generation and a 07:30 scheduler job.
- Added production-only HTTP Basic protection for all Career pages and APIs.
- Added a responsive Life OS interface and Career test coverage.

## Files Changed
- `app/career.py` — scoring, claim verification, form safety planning and document generation.
- `app/config.py` — `CAREER_ACCESS_KEY` configuration.
- `app/database.py` — isolated Career persistence and workflows.
- `app/dashboard.py` — Career page and API endpoints.
- `app/templates/career.html` — Career command center.
- `app/templates/base.html` — Career navigation and dynamic title.
- `app/static/style.css` — Career UI plus contrast/style cleanup.
- `app/scheduler.py` — daily Career run.
- `tests/test_career.py`, `tests/test_scheduler.py` — feature and scheduler coverage.
- `requirements.txt` — DOCX/PDF libraries.
- Vault/status files — current state and next steps.

## Current State
The Career Agent MVP is complete on branch `feat/career-agent-lifeos`. It operates entirely on clearly labelled demo opportunities and user-confirmed facts, creates no external side effects, and has not been deployed to the live Railway service.

## Bugs / Blockers
- Four unrelated pre-existing test failures remain: one stale category/date expectation and three Telegram message-routing expectations.
- The local Python 3.13 environment cannot start python-telegram-bot 20.7 normally; UI QA used Uvicorn with lifespan disabled. Railway's current deployment remains healthy.
- Live vacancy sources and the private knowledge-base model are intentionally deferred.
- `CAREER_ACCESS_KEY` must be configured in Railway before merge/deployment; username is `lifeos`.

## Next Exact Task
1. Review and merge the Career Agent pull request when ready to deploy.
2. Confirm the Railway deployment and smoke-test `/career` on production.
3. Design the Career knowledge-base privacy/evidence model with the user.
4. Connect one official vacancy feed and replace demo data only after that design is approved.

## Commands to Run
```bash
TELEGRAM_BOT_TOKEN=test DATABASE_URL=sqlite:////tmp/lifeos-test.db LOCAL_POLLING=true pytest -q
TELEGRAM_BOT_TOKEN=test DATABASE_URL=sqlite:////tmp/lifeos-preview.db LOCAL_POLLING=true python3 -c 'from app.database import init_db; init_db()'
TELEGRAM_BOT_TOKEN=test DATABASE_URL=sqlite:////tmp/lifeos-preview.db LOCAL_POLLING=true uvicorn app.dashboard:app --lifespan off
```

## Environment Variables Needed
- TELEGRAM_BOT_TOKEN
- DATABASE_URL
- OPENAI_API_KEY
- WEBHOOK_BASE_URL
- TELEGRAM_WEBHOOK_SECRET
- TELEGRAM_OWNER_CHAT_ID
- CAREER_ACCESS_KEY (required for `/career` in production; username: `lifeos`)
- WEEKLY_BUDGET (default: 90)
- LOCAL_POLLING (true for local dev)

## Do-Not-Touch Warnings
- Do not modify the `transactions` table schema.
- Do not auto-submit applications or auto-send LinkedIn outreach.
- Do not ingest additional private career data until the knowledge-base privacy model is agreed.
