from datetime import date, datetime, timedelta, timezone
import json
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    MetaData, Table, insert, select, update, desc, text,
)
from app import config

# Railway uses postgres://, SQLAlchemy 2.0 needs postgresql://
_db_url = config.DATABASE_URL.replace("postgres://", "postgresql://", 1)
_engine = create_engine(_db_url)
_metadata = MetaData()

transactions = Table(
    "transactions",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("date", String),
    Column("week_start", String),
    Column("month", String),
    Column("type", String),
    Column("amount", Float),
    Column("description", String),
    Column("category", String),
    Column("tag", String, default=""),
    Column("payment_type", String, default=""),
    Column("is_impulse", Boolean, default=False),
    Column("is_necessary", String, default=""),
    Column("notes", String, default=""),
)

agent_state = Table(
    "agent_state",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("status_type", String),
    Column("severity", String),
    Column("requires_user_action", Boolean, default=False),
    Column("resolved", Boolean, default=False),
    Column("current_module", String),
    Column("current_task", String),
    Column("progress_message", String),
    Column("blocker", String),
    Column("next_task", String),
    Column("git_summary", String),
    Column("handoff_path", String),
    Column("startup_prompt_path", String),
    Column("metadata_json", String),
)

net_worth_snapshots = Table(
    "net_worth_snapshots",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("cash", Float, default=0.0),
    Column("investments", Float, default=0.0),
    Column("crypto", Float, default=0.0),
    Column("savings", Float, default=0.0),
    Column("other_assets", Float, default=0.0),
    Column("liabilities", Float, default=0.0),
    Column("total_net_worth", Float),
    Column("notes", String, default=""),
)

conversations = Table(
    "conversations",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("role", String),     # 'user' or 'assistant'
    Column("content", String),
)

vault_memory = Table(
    "vault_memory",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("key", String, unique=True),
    Column("content", String),
    Column("updated_at", String),
)

# Career Agent tables are isolated from the stable finance schema. Vacancy text is
# untrusted input; only normalized data is persisted and it never controls actions.
career_facts = Table(
    "career_facts", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("category", String, nullable=False),
    Column("label", String, nullable=False),
    Column("value", String, nullable=False),
    Column("verification_status", String, nullable=False),
    Column("source_label", String),
)

career_jobs = Table(
    "career_jobs", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("external_id", String, nullable=False),
    Column("source", String, nullable=False),
    Column("title", String, nullable=False),
    Column("company", String, nullable=False),
    Column("location", String, nullable=False),
    Column("work_mode", String, nullable=False),
    Column("salary", String),
    Column("required_skills_json", String, nullable=False),
    Column("preferred_skills_json", String, nullable=False),
    Column("required_experience", String),
    Column("contract_type", String),
    Column("application_url", String, nullable=False),
    Column("posting_date", String),
    Column("discovered_at", String, nullable=False),
    Column("description", String, nullable=False),
    Column("match_score", Float),
    Column("score_breakdown_json", String, nullable=False, default="{}"),
    Column("strengths_json", String, nullable=False, default="[]"),
    Column("gaps_json", String, nullable=False, default="[]"),
    Column("status", String, nullable=False, default="discovered"),
    Column("is_demo", Boolean, nullable=False, default=False),
)

career_applications = Table(
    "career_applications", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("job_id", Integer, nullable=False, unique=True),
    Column("status", String, nullable=False),
    Column("summary", String, nullable=False),
    Column("cv_claims_json", String, nullable=False),
    Column("unsupported_claims_json", String, nullable=False),
    Column("motivation_letter", String, nullable=False),
    Column("approved_at", String),
    Column("submitted_at", String),
)

career_contacts = Table(
    "career_contacts", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("role", String, nullable=False),
    Column("company", String, nullable=False),
    Column("public_profile_url", String, nullable=False),
    Column("relevance", String, nullable=False),
    Column("message", String, nullable=False),
    Column("status", String, nullable=False, default="draft"),
    Column("follow_up_on", String),
    Column("is_demo", Boolean, nullable=False, default=False),
)

career_daily_runs = Table(
    "career_daily_runs", _metadata,
    Column("run_date", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("selected_job_id", Integer),
    Column("contact_id", Integer),
    Column("result_json", String, nullable=False),
)

career_audit = Table(
    "career_audit", _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String, nullable=False),
    Column("action", String, nullable=False),
    Column("entity_type", String, nullable=False),
    Column("entity_id", String, nullable=False),
    Column("detail_json", String, nullable=False),
)


def init_db() -> None:
    _metadata.create_all(_engine)
    from pathlib import Path
    root = Path(__file__).parent.parent
    _seed_vault = [
        ("coach_memory", root / "vault" / "sessions" / "coach-memory.md"),
        ("goals",        root / "vault" / "personal" / "goals.md"),
        ("values",       root / "vault" / "personal" / "values.md"),
    ]
    for key, path in _seed_vault:
        if get_vault_memory(key) is None and path.exists():
            set_vault_memory(key, path.read_text(encoding="utf-8"))
    seed_career_demo()
    run_career_daily()

def append_transaction(parsed: dict, category: str) -> int:
    with _engine.connect() as conn:
        result = conn.execute(
            insert(transactions).values(
                timestamp=parsed["timestamp"],
                date=parsed["date"],
                week_start=parsed["week_start"],
                month=parsed["month"],
                type=parsed["type"],
                amount=parsed["amount"],
                description=parsed["description"],
                category=category,
                tag="",
                payment_type="",
                is_impulse=parsed["is_impulse"],
                is_necessary="",
                notes="",
            )
        )
        conn.commit()
        return result.inserted_primary_key[0]

def get_all_transactions() -> list[dict]:
    with _engine.connect() as conn:
        result = conn.execute(select(transactions).order_by(transactions.c.id))
        return [dict(row._mapping) for row in result]

def undo_last_transaction() -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(transactions).order_by(desc(transactions.c.id)).limit(1)
        )
        row = result.fetchone()
        if row is None:
            return None
        record = dict(row._mapping)
        conn.execute(
            update(transactions)
            .where(transactions.c.id == record["id"])
            .values(notes="[UNDONE]")
        )
        conn.commit()
        return record


def write_agent_state(fields: dict) -> None:
    if "timestamp" not in fields:
        fields = {**fields, "timestamp": datetime.now(timezone.utc).isoformat()}
    with _engine.connect() as conn:
        conn.execute(insert(agent_state).values(**fields))
        conn.commit()


def read_latest_agent_state(status_type: str | None = None) -> dict | None:
    with _engine.connect() as conn:
        if status_type:
            q = (
                select(agent_state)
                .where(agent_state.c.status_type == status_type)
                .order_by(desc(agent_state.c.id))
                .limit(1)
            )
        else:
            q = select(agent_state).order_by(desc(agent_state.c.id)).limit(1)
        result = conn.execute(q)
        row = result.fetchone()
        if row is None:
            return None
        return dict(row._mapping)


def create_net_worth_snapshot(fields: dict) -> int:
    total = (
        fields.get("cash", 0.0)
        + fields.get("investments", 0.0)
        + fields.get("crypto", 0.0)
        + fields.get("savings", 0.0)
        + fields.get("other_assets", 0.0)
        - fields.get("liabilities", 0.0)
    )
    now = datetime.now(timezone.utc).isoformat()
    with _engine.connect() as conn:
        result = conn.execute(
            insert(net_worth_snapshots).values(
                timestamp=fields.get("timestamp", now),
                cash=fields.get("cash", 0.0),
                investments=fields.get("investments", 0.0),
                crypto=fields.get("crypto", 0.0),
                savings=fields.get("savings", 0.0),
                other_assets=fields.get("other_assets", 0.0),
                liabilities=fields.get("liabilities", 0.0),
                total_net_worth=total,
                notes=fields.get("notes", ""),
            )
        )
        conn.commit()
        return result.inserted_primary_key[0]


def get_latest_net_worth_snapshot() -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(net_worth_snapshots)
            .order_by(desc(net_worth_snapshots.c.id))
            .limit(1)
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


def get_first_net_worth_snapshot() -> dict | None:
    """Return the earliest recorded snapshot (the true baseline). Used as
    the anchor for the live net worth series/chart so later automated
    monthly snapshots don't truncate historical chart data."""
    with _engine.connect() as conn:
        result = conn.execute(
            select(net_worth_snapshots)
            .order_by(net_worth_snapshots.c.id)
            .limit(1)
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


def get_net_worth_history(limit: int = 30) -> list[dict]:
    """Return the most recent `limit` snapshots ordered oldest-first."""
    with _engine.connect() as conn:
        result = conn.execute(
            select(net_worth_snapshots)
            .order_by(desc(net_worth_snapshots.c.id))
            .limit(limit)
        )
        rows = [dict(row._mapping) for row in result]
        return list(reversed(rows))


_PENDING_ACTION_TYPES = ("decision", "manual_action", "error", "handoff")


def read_pending_action() -> dict | None:
    """Return the latest unresolved agent_state row that requires user action."""
    with _engine.connect() as conn:
        q = (
            select(agent_state)
            .where(
                agent_state.c.requires_user_action == True,
                agent_state.c.resolved == False,
                agent_state.c.status_type.in_(_PENDING_ACTION_TYPES),
            )
            .order_by(desc(agent_state.c.id))
            .limit(1)
        )
        result = conn.execute(q)
        row = result.fetchone()
        return dict(row._mapping) if row else None


def resolve_agent_state(state_id: int) -> None:
    """Mark a specific agent_state row as resolved=True."""
    with _engine.connect() as conn:
        conn.execute(
            update(agent_state)
            .where(agent_state.c.id == state_id)
            .values(resolved=True)
        )
        conn.commit()


def get_transaction_by_id(tx_id: int) -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(select(transactions).where(transactions.c.id == tx_id))
        row = result.fetchone()
        return dict(row._mapping) if row else None


_EDITABLE_FIELDS = {"amount", "description", "category", "type", "date", "is_impulse", "notes"}


def update_transaction(tx_id: int, fields: dict) -> None:
    safe = {k: v for k, v in fields.items() if k in _EDITABLE_FIELDS}
    if not safe:
        return
    with _engine.connect() as conn:
        conn.execute(update(transactions).where(transactions.c.id == tx_id).values(**safe))
        conn.commit()


def delete_transaction(tx_id: int) -> None:
    from sqlalchemy import delete as _delete
    with _engine.connect() as conn:
        conn.execute(_delete(transactions).where(transactions.c.id == tx_id))
        conn.commit()


def get_vault_memory(key: str) -> str | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(vault_memory).where(vault_memory.c.key == key)
        )
        row = result.fetchone()
        return dict(row._mapping)["content"] if row else None


def set_vault_memory(key: str, content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _engine.connect() as conn:
        existing = conn.execute(
            select(vault_memory).where(vault_memory.c.key == key)
        ).fetchone()
        if existing:
            conn.execute(
                update(vault_memory)
                .where(vault_memory.c.key == key)
                .values(content=content, updated_at=now)
            )
        else:
            conn.execute(
                insert(vault_memory).values(key=key, content=content, updated_at=now)
            )
        conn.commit()


def save_message(role: str, content: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with _engine.connect() as conn:
        conn.execute(insert(conversations).values(timestamp=ts, role=role, content=content))
        conn.commit()


def get_recent_messages(limit: int = 20) -> list[dict]:
    """Return the most recent `limit` messages ordered oldest-first."""
    with _engine.connect() as conn:
        result = conn.execute(
            select(conversations).order_by(desc(conversations.c.id)).limit(limit)
        )
        rows = [dict(r._mapping) for r in result]
        return list(reversed(rows))


def _career_row(row) -> dict:
    record = dict(row._mapping)
    for field in (
        "required_skills", "preferred_skills", "score_breakdown", "strengths",
        "gaps", "cv_claims", "unsupported_claims", "result", "detail",
    ):
        raw_key = f"{field}_json"
        if raw_key in record:
            raw_value = record.pop(raw_key)
            default = "{}" if field in {"score_breakdown", "result", "detail"} else "[]"
            record[field] = json.loads(raw_value or default)
    return record


def seed_career_demo() -> None:
    """Seed an honest demo slice. User-confirmed facts come from the supplied brief."""
    now = datetime.now(timezone.utc).isoformat()
    with _engine.begin() as conn:
        facts = [
            {"category": "education", "label": "Current education", "value": "Currently completing Economics & Business Economics at Maastricht University.", "verification_status": "user_confirmed", "source_label": "Career Agent brief"},
            {"category": "experience", "label": "Solution engineering", "value": "Has junior solution engineering experience at ETIL.", "verification_status": "user_confirmed", "source_label": "Career Agent brief"},
            *[
                {"category": "skill", "label": skill, "value": skill, "verification_status": "user_confirmed", "source_label": "Career Agent brief"}
                for skill in ("Python", "FastAPI", "SQL", "Power BI", "Git", "Docker")
            ],
            {"category": "project", "label": "AI applications", "value": "Has worked on AI agents, research tools, business applications, integrations, and automation.", "verification_status": "user_confirmed", "source_label": "Career Agent brief"},
            {"category": "project", "label": "Life OS", "value": "Built an AI product that combines natural-language interaction, FastAPI, PostgreSQL, automated workflows, a web dashboard, and Railway deployment.", "verification_status": "document_verified", "source_label": "https://github.com/arryaetil/life-os"},
            {"category": "project", "label": "BackyardAI", "value": "Built a commercial visual-AI concept for installers and contractors that combines address-based imagery, 3D rendering, AI analysis, and image editing to visualise products in a customer's garden.", "verification_status": "document_verified", "source_label": "https://github.com/arryaetil/poolpipeline"},
            {"category": "project", "label": "KYC4etil", "value": "Built a human-in-the-loop public-source research workbench that finds, validates, ranks, and presents workforce evidence for reviewer decisions.", "verification_status": "document_verified", "source_label": "https://github.com/arryaetil/KYC4etil"},
            {"category": "project", "label": "Network Economics Paper", "value": "Co-authored an empirical network-economics paper using WIOD data, network centrality, GVC measures, and econometric models to analyse the relationship between production-network position and wages.", "verification_status": "document_verified", "source_label": "https://github.com/arryaetil/07-network-paper"},
            {"category": "career_goal", "label": "GitHub portfolio", "value": "Showcase Life OS, BackyardAI, KYC4etil, and the Network Economics Paper as four flagship GitHub projects.", "verification_status": "user_confirmed", "source_label": "User instruction, 2026-10-25"},
        ]
        for fact in facts:
            exists = conn.execute(select(career_facts.c.id).where(
                career_facts.c.category == fact["category"],
                career_facts.c.label == fact["label"],
            )).fetchone()
            if not exists:
                conn.execute(insert(career_facts).values(**fact))
        if not conn.execute(select(career_jobs.c.id).limit(1)).fetchone():
            jobs = [
                ("demo-ai-1", "Junior AI Solutions Engineer", "Northstar Systems", "Eindhoven, Netherlands", "hybrid", ["Python", "FastAPI", "SQL", "Git"], ["Docker", "Power BI"], "0–2 years", "Build AI business applications, integrations and agent workflows in an early-career team with mentorship and structured learning."),
                ("demo-bi-2", "Junior Business Intelligence Consultant", "Meridian Advisory", "Maastricht, Netherlands", "hybrid", ["SQL", "Power BI"], ["Python"], "Graduate or up to 2 years", "Translate business questions into dashboards and data products in a graduate consulting role with training and client exposure."),
                ("demo-senior-3", "Senior Platform AI Engineer", "Example Cloud", "Remote", "remote", ["Python", "Kubernetes", "AWS"], ["Terraform"], "7+ years", "Senior staff-level role owning production cloud architecture and mentoring multiple teams. Requires 7+ years."),
            ]
            conn.execute(insert(career_jobs), [
                {"external_id": external_id, "source": "demo", "title": title, "company": company, "location": location, "work_mode": work_mode, "salary": None, "required_skills_json": json.dumps(required), "preferred_skills_json": json.dumps(preferred), "required_experience": experience, "contract_type": "Full-time", "application_url": "https://example.com/career-demo", "posting_date": date.today().isoformat(), "discovered_at": now, "description": description, "match_score": None, "score_breakdown_json": "{}", "strengths_json": "[]", "gaps_json": "[]", "status": "discovered", "is_demo": True}
                for external_id, title, company, location, work_mode, required, preferred, experience, description in jobs
            ])
        if not conn.execute(select(career_contacts.c.id).limit(1)).fetchone():
            conn.execute(insert(career_contacts).values(
                name="Maya de Vries", role="AI Solutions Lead", company="Northstar Systems",
                public_profile_url="https://example.com/career-demo/contact",
                relevance="Demo contact: leads an early-career AI solutions team at the intersection of engineering and client consulting.",
                message="Hi Maya, I’m building my career around AI engineering and solution consulting, and your work leading AI solutions teams stood out. I’d value hearing what skills matter most for someone entering this field. Would you be open to connecting?",
                status="draft", follow_up_on=(date.today() + timedelta(days=7)).isoformat(), is_demo=True,
            ))


def run_career_daily(run_date: str | None = None, minimum_score: int = 65) -> dict:
    from app.career import score_job, verify_claims

    run_date = run_date or date.today().isoformat()
    with _engine.begin() as conn:
        existing = conn.execute(select(career_daily_runs).where(career_daily_runs.c.run_date == run_date)).fetchone()
        if existing:
            return _career_row(existing)

        facts = [_career_row(row) for row in conn.execute(select(career_facts))]
        profile = {
            "skills": [fact["value"] for fact in facts if fact["category"] == "skill"],
            "project_terms": ["ai agents", "research tools", "integrations", "automation"],
            "target_roles": ["junior ai engineer", "junior ai solutions engineer", "ai application developer", "junior solution engineer", "associate solutions consultant", "junior business intelligence consultant", "junior data / ai consultant", "technical consultant"],
            "locations": ["limburg", "eindhoven", "maastricht", "heerlen", "aachen", "remote"],
        }
        jobs = [_career_row(row) for row in conn.execute(select(career_jobs).where(career_jobs.c.status == "discovered"))]
        for job in jobs:
            scored = score_job(job, profile)
            conn.execute(update(career_jobs).where(career_jobs.c.id == job["id"]).values(
                match_score=scored["score"], score_breakdown_json=json.dumps(scored["breakdown"]),
                strengths_json=json.dumps(scored["strengths"]), gaps_json=json.dumps(scored["gaps"]),
            ))
            job.update({"match_score": scored["score"], "score_breakdown": scored["breakdown"], "strengths": scored["strengths"], "gaps": scored["gaps"]})
        selected = max(jobs, key=lambda item: item["match_score"], default=None)
        if selected and selected["match_score"] < minimum_score:
            selected = None

        if selected:
            claims = [fact["value"] for fact in facts if fact["category"] in {"education", "experience", "skill", "project"} and fact["verification_status"] in {"user_confirmed", "document_verified"}]
            supported = [fact["value"] for fact in facts if fact["verification_status"] in {"user_confirmed", "document_verified"}]
            unsupported = verify_claims(claims, supported)
            conn.execute(insert(career_applications).values(
                job_id=selected["id"], status="blocked_by_claims" if unsupported else "pending_review",
                summary=f"Evidence-bound materials for {selected['title']} at {selected['company']}.",
                cv_claims_json=json.dumps(claims), unsupported_claims_json=json.dumps(unsupported),
                motivation_letter=(f"Dear hiring team at {selected['company']},\n\nI am interested in the {selected['title']} position because it aligns with my focus on AI engineering, solution engineering, and client-facing technology work. My user-confirmed profile includes experience with {', '.join(profile['skills'][:4])}. I would welcome the opportunity to learn more about the team and discuss where my current experience can contribute.\n\nKind regards"),
            ))
            conn.execute(update(career_jobs).where(career_jobs.c.id == selected["id"]).values(status="selected"))

        contact = conn.execute(select(career_contacts).where(career_contacts.c.status == "draft").order_by(career_contacts.c.id).limit(1)).fetchone()
        result = {"jobs_scored": len(jobs), "application_prepared": bool(selected), "reason": "Best qualified opportunity selected." if selected else "No job cleared the configured threshold."}
        conn.execute(insert(career_daily_runs).values(run_date=run_date, status="completed", selected_job_id=selected["id"] if selected else None, contact_id=contact.id if contact else None, result_json=json.dumps(result)))
        conn.execute(insert(career_audit).values(timestamp=datetime.now(timezone.utc).isoformat(), action="daily_run_completed", entity_type="daily_run", entity_id=run_date, detail_json=json.dumps(result)))
        return {"run_date": run_date, "status": "completed", "selected_job_id": selected["id"] if selected else None, "contact_id": contact.id if contact else None, "result": result}


def get_career_dashboard() -> dict:
    run_date = date.today().isoformat()
    with _engine.connect() as conn:
        run_row = conn.execute(select(career_daily_runs).where(career_daily_runs.c.run_date == run_date)).fetchone()
        run = _career_row(run_row) if run_row else None
        jobs = [_career_row(row) for row in conn.execute(select(career_jobs).order_by(desc(career_jobs.c.match_score)))]
        facts = [_career_row(row) for row in conn.execute(select(career_facts).order_by(career_facts.c.category, career_facts.c.id))]
        contacts = [_career_row(row) for row in conn.execute(select(career_contacts).order_by(desc(career_contacts.c.id)))]
        application = None
        if run and run["selected_job_id"]:
            row = conn.execute(select(career_applications).where(career_applications.c.job_id == run["selected_job_id"])).fetchone()
            application = _career_row(row) if row else None
        audits = [_career_row(row) for row in conn.execute(select(career_audit).order_by(desc(career_audit.c.id)).limit(8))]
        return {"run": run, "jobs": jobs, "facts": facts, "contacts": contacts, "application": application, "audits": audits}


def set_career_fact(category: str, label: str, value: str, verification_status: str, source_label: str | None = None) -> dict:
    allowed_statuses = {"user_confirmed", "document_verified", "unverified"}
    if verification_status not in allowed_statuses:
        raise ValueError("Invalid verification status")
    if not all(item.strip() for item in (category, label, value)):
        raise ValueError("Category, label, and value are required")
    with _engine.begin() as conn:
        row = conn.execute(select(career_facts).where(
            career_facts.c.category == category.strip(),
            career_facts.c.label == label.strip(),
        )).fetchone()
        values = {
            "category": category.strip(), "label": label.strip(), "value": value.strip(),
            "verification_status": verification_status, "source_label": source_label,
        }
        if row:
            conn.execute(update(career_facts).where(career_facts.c.id == row.id).values(**values))
            return {**values, "id": row.id}
        result = conn.execute(insert(career_facts).values(**values))
        return {**values, "id": result.inserted_primary_key[0]}


def get_career_application_bundle(application_id: int) -> tuple[dict, dict]:
    with _engine.connect() as conn:
        row = conn.execute(select(career_applications).where(career_applications.c.id == application_id)).fetchone()
        if not row:
            raise LookupError("Application not found")
        application = _career_row(row)
        job_row = conn.execute(select(career_jobs).where(career_jobs.c.id == application["job_id"])).fetchone()
        if not job_row:
            raise LookupError("Job not found")
        return application, _career_row(job_row)


def approve_career_application(application_id: int) -> dict:
    with _engine.begin() as conn:
        row = conn.execute(select(career_applications).where(career_applications.c.id == application_id)).fetchone()
        if not row:
            raise LookupError("Application not found")
        application = _career_row(row)
        if application["unsupported_claims"]:
            raise ValueError("Unsupported claims must be resolved before approval")
        if application["status"] != "pending_review":
            raise ValueError("Only pending applications can be approved")
        approved_at = datetime.now(timezone.utc).isoformat()
        conn.execute(update(career_applications).where(career_applications.c.id == application_id).values(status="approved_for_manual_submission", approved_at=approved_at))
        detail = {"boundary": "Approval permits manual submission only; Life OS took no external action."}
        conn.execute(insert(career_audit).values(timestamp=approved_at, action="application_approved", entity_type="application", entity_id=str(application_id), detail_json=json.dumps(detail)))
        return {**application, "status": "approved_for_manual_submission", "approved_at": approved_at}


def mark_career_contact_sent(contact_id: int) -> None:
    with _engine.begin() as conn:
        if not conn.execute(select(career_contacts.c.id).where(career_contacts.c.id == contact_id)).fetchone():
            raise LookupError("Contact not found")
        conn.execute(update(career_contacts).where(career_contacts.c.id == contact_id).values(status="sent_manually"))
        conn.execute(insert(career_audit).values(timestamp=datetime.now(timezone.utc).isoformat(), action="outreach_marked_sent", entity_type="contact", entity_id=str(contact_id), detail_json=json.dumps({"boundary": "User reported a manual send; Life OS sent no message."})))
