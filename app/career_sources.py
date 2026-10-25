"""Legitimate public vacancy sources for the Career Agent (Adzuna job search API)."""

from datetime import datetime, timezone
import html
import logging
import re

import httpx

_log = logging.getLogger(__name__)

ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
COUNTRY_NAMES = {"nl": "Netherlands", "de": "Germany", "be": "Belgium"}

# Each entry is one API call; keep the list short to stay inside Adzuna's free daily quota.
ADZUNA_SEARCHES = (
    {"country": "nl", "what": "ai engineer"},
    {"country": "nl", "what": "ai consultant"},
    {"country": "nl", "what_or": "solutions solution", "what": "engineer"},
    {"country": "nl", "what_or": "presales pre-sales"},
    {"country": "nl", "what": "sales engineer"},
    {"country": "nl", "what": "technical sales"},
    {"country": "nl", "what_or": "aml kyc", "what": "analyst"},
    {"country": "nl", "what": "business development saas"},
    {"country": "nl", "what": "KPMG", "what_or": "ai data technology digital"},
    {"country": "nl", "what": "Deloitte", "what_or": "ai data technology digital"},
    {"country": "nl", "what": "PwC", "what_or": "ai data technology digital"},
    {"country": "nl", "what": "EY", "what_or": "ai data technology digital"},
    {"country": "de", "what": "ai engineer", "where": "Aachen"},
)

# Skills recognised in vacancy text; Adzuna gives a short snippet, not a structured requirement list.
KNOWN_SKILLS = (
    "Python", "SQL", "FastAPI", "Power BI", "Power Automate", "Power Apps", "Azure", "Docker",
    "Git", "REST", "API", "PostgreSQL", "React", "TypeScript", "LLM", "OpenAI", "RAG",
    "Machine Learning", "Kubernetes", "AWS", "Salesforce", "CRM", "Excel", "Java", "C#",
)


def adzuna_configured(app_id: str, app_key: str) -> bool:
    return bool(app_id and app_key)


def _params(search: dict, app_id: str, app_key: str, max_days_old: int) -> dict:
    params = {
        "app_id": app_id, "app_key": app_key, "results_per_page": 50,
        "max_days_old": max_days_old, "content-type": "application/json",
    }
    for key in ("what", "what_or", "where"):
        if search.get(key):
            params[key] = search[key]
    return params


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _skills_in(text: str) -> list[str]:
    return [skill for skill in KNOWN_SKILLS if re.search(rf"(?<![a-z]){re.escape(skill.lower())}(?![a-z])", text.lower())]


def normalize_adzuna(result: dict, country: str) -> dict:
    """Map one Adzuna result to the career_jobs shape. Vacancy text is stored as data only."""
    title = _clean(result.get("title", ""))
    description = _clean(result.get("description", ""))
    location = _clean((result.get("location") or {}).get("display_name", ""))
    country_name = COUNTRY_NAMES.get(country, country.upper())
    salary_min, salary_max = result.get("salary_min"), result.get("salary_max")
    salary = None
    if salary_min and salary_max:
        salary = f"€{salary_min:,.0f} – €{salary_max:,.0f}"
    work_text = f"{title} {description}".lower()
    work_mode = "remote" if "remote" in work_text else "hybrid" if "hybrid" in work_text else "on-site"
    return {
        "external_id": str(result.get("id", "")),
        "source": f"adzuna-{country}",
        "title": title,
        "company": _clean((result.get("company") or {}).get("display_name", "")) or "Unknown company",
        "location": f"{location}, {country_name}" if location else country_name,
        "work_mode": work_mode,
        "salary": salary,
        "required_skills": _skills_in(f"{title} {description}"),
        "preferred_skills": [],
        "required_experience": None,
        "contract_type": " ".join(filter(None, (result.get("contract_time"), result.get("contract_type")))) or None,
        "application_url": result.get("redirect_url", ""),
        "posting_date": (result.get("created") or "")[:10] or None,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "description": description,
    }


def fetch_adzuna_jobs(app_id: str, app_key: str, max_days_old: int = 14, client: httpx.Client | None = None) -> dict:
    """Run every configured search; one failing search does not stop the others."""
    jobs, errors = {}, []
    owns_client = client is None
    client = client or httpx.Client(timeout=20)
    try:
        for search in ADZUNA_SEARCHES:
            country = search["country"]
            try:
                response = client.get(ADZUNA_URL.format(country=country), params=_params(search, app_id, app_key, max_days_old))
                response.raise_for_status()
                for result in response.json().get("results", []):
                    job = normalize_adzuna(result, country)
                    if job["external_id"] and job["application_url"]:
                        jobs[(job["source"], job["external_id"])] = job
            except (httpx.HTTPError, ValueError) as exc:
                label = search.get("what") or search.get("what_or")
                errors.append(f"{country}:{label}: {type(exc).__name__}")
                _log.warning("adzuna search failed (%s): %s", label, type(exc).__name__)
    finally:
        if owns_client:
            client.close()
    return {"jobs": list(jobs.values()), "errors": errors}
