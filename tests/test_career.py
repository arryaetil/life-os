from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.career import build_application_document, plan_application_fields, score_job, verify_claims


PROFILE = {
    "skills": ["Python", "FastAPI", "SQL", "Power BI", "Git", "Docker"],
    "project_terms": ["ai agents", "integrations", "automation"],
    "target_roles": ["junior ai solutions engineer"],
    "locations": ["eindhoven", "remote"],
}


def test_score_job_is_transparent_and_totals_to_score():
    job = {
        "title": "Junior AI Solutions Engineer",
        "description": "Build AI agents, integrations, and automation.",
        "location": "Eindhoven, Netherlands",
        "work_mode": "hybrid",
        "required_skills": ["Python", "FastAPI", "SQL", "Git"],
        "preferred_skills": ["Docker", "Power BI"],
        "required_experience": "0-2 years",
    }
    result = score_job(job, PROFILE)
    assert result["score"] == 100
    assert sum(result["breakdown"].values()) == result["score"]
    assert result["gaps"] == []


def test_senior_job_is_penalized_and_explained():
    result = score_job({
        "title": "Senior AI Engineer",
        "description": "Own the platform.",
        "location": "Remote",
        "work_mode": "remote",
        "required_skills": ["Python", "Kubernetes"],
        "preferred_skills": [],
        "required_experience": "7+ years",
    }, PROFILE)
    assert result["breakdown"]["early_career_fit"] == 0
    assert "Role appears senior for the current profile" in result["gaps"]


def test_claim_verification_rejects_invented_claim():
    supported = ["Has junior solution engineering experience at ETIL."]
    claims = supported + ["Led a team of 12 engineers."]
    assert verify_claims(claims, supported) == ["Led a team of 12 engineers."]


def test_application_planner_stops_for_captcha_and_ambiguity():
    result = plan_application_fields([
        {"label": "Name", "type": "text", "required": True, "value": "Arrya"},
        {"label": "CAPTCHA", "type": "captcha", "required": True},
        {"label": "Describe your leadership", "type": "text", "ambiguous": True},
    ])
    assert len(result["safe_to_fill"]) == 1
    assert len(result["needs_review"]) == 2
    assert result["may_submit"] is False


@pytest.mark.parametrize("file_format,signature", [("docx", b"PK"), ("pdf", b"%PDF")])
def test_verified_cv_export(file_format, signature):
    application = {"cv_claims": ["Python"], "unsupported_claims": [], "motivation_letter": "Hello"}
    job = {"title": "Junior AI Engineer", "company": "Example"}
    document = build_application_document(application, job, "cv", file_format)
    assert document.read(len(signature)) == signature


@pytest.fixture
def client():
    from app.dashboard import app
    with patch("app.dashboard.create_ptb_app") as mock_factory, patch("app.dashboard.config.LOCAL_POLLING", True):
        mock_factory.return_value = AsyncMock()
        with TestClient(app) as test_client:
            yield test_client


def test_career_page_renders_daily_opportunity(client):
    response = client.get("/career")
    assert response.status_code == 200
    assert "Career command center" in response.text
    assert "Junior AI Solutions Engineer" in response.text
    assert "External actions" in response.text
    assert "Managed through Codex" in response.text
    assert "Run today’s scan" not in response.text


def test_career_page_requires_auth_in_production(client):
    from app.dashboard import config
    with patch.object(config, "LOCAL_POLLING", False), patch.object(config, "CAREER_ACCESS_KEY", "private-key"):
        denied = client.get("/career")
        allowed = client.get("/career", auth=("lifeos", "private-key"))
    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_daily_run_is_idempotent():
    from app import database
    first = database.run_career_daily("2099-01-02")
    second = database.run_career_daily("2099-01-02")
    assert first["run_date"] == second["run_date"]
    assert first["selected_job_id"] == second["selected_job_id"]


def test_approval_is_explicit_and_does_not_mark_submitted(client):
    from app import database
    data = database.get_career_dashboard()
    application = data["application"]
    if application["status"] == "pending_review":
        response = client.post(f"/api/career/applications/{application['id']}/approve")
        assert response.status_code == 200
        approved = response.json()["application"]
        assert approved["status"] == "approved_for_manual_submission"
        assert approved["submitted_at"] is None


def test_codex_command_surface_runs_daily_scan(capsys):
    from scripts.career_agent import main
    with patch("scripts.career_agent.database.init_db"), patch(
        "scripts.career_agent.database.run_career_daily",
        return_value={"run_date": "2099-01-03", "status": "completed"},
    ) as run:
        assert main(["run", "--date", "2099-01-03", "--minimum-score", "70"]) == 0
    run.assert_called_once_with("2099-01-03", 70)
    assert '"status": "completed"' in capsys.readouterr().out


def test_seed_includes_verified_flagship_projects(client):
    from app import database
    facts = database.get_career_dashboard()["facts"]
    projects = {fact["label"]: fact for fact in facts if fact["category"] == "project"}
    assert {"Life OS", "BackyardAI", "KYC4etil", "Network Economics Paper"} <= projects.keys()
    assert all(projects[name]["verification_status"] == "document_verified" for name in (
        "Life OS", "BackyardAI", "KYC4etil", "Network Economics Paper",
    ))


def test_career_fact_can_be_updated_without_duplication(client):
    from app import database
    first = database.set_career_fact("project", "Portfolio proof", "First", "user_confirmed")
    second = database.set_career_fact("project", "Portfolio proof", "Updated", "document_verified", "GitHub")
    assert first["id"] == second["id"]
    matches = [fact for fact in database.get_career_dashboard()["facts"] if fact["label"] == "Portfolio proof"]
    assert len(matches) == 1
    assert matches[0]["value"] == "Updated"
