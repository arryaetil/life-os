"""
Fixed-context vault loader for the LifeOS AI agent.
Loads a small set of vault/doc files into a compressed context string.
No RAG, no embeddings — simple file reads with character limits.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

_VAULT_FILES = [
    ("CLAUDE.md", 1500),
    ("vault/context/LifeOS.md", 1000),
    ("vault/context/Current_Priorities.md", 800),
    ("vault/context/User_Profile.md", 600),
    ("vault/hubs/Architecture.md", 800),
    ("vault/hubs/Finance.md", 600),
    ("vault/hubs/Agent_Control.md", 600),
    ("vault/projects/finance-lifeos.md", 800),
    ("vault/sessions/recent-sessions.md", 600),
    ("handoff/latest.md", 800),
]

# Files loaded specifically for the coach (separate from general vault context)
COACH_MEMORY_FILES = [
    ("vault/sessions/coach-memory.md", 1600),
    ("vault/personal/goals.md", 1200),
    ("vault/personal/values.md", 1800),
]


def load_coach_memory() -> str:
    """Load coach long-term memory. DB is authoritative; files are fallback."""
    sections = []

    # coach-memory: DB first (survives redeploys), file fallback
    try:
        from app.database import get_vault_memory
        db_memory = get_vault_memory("coach_memory")
    except Exception:
        db_memory = None

    if db_memory:
        sections.append(f"## Coach Memory\n{db_memory[:800]}")
    else:
        path = REPO_ROOT / "vault" / "sessions" / "coach-memory.md"
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()[:800]
            sections.append(f"## Coach Memory\n{text}")

    # goals and values: DB authoritative, file fallback
    for db_key, rel_path, max_chars in [
        ("goals",  "vault/personal/goals.md",  1200),
        ("values", "vault/personal/values.md", 1800),
    ]:
        try:
            text = get_vault_memory(db_key)
        except Exception:
            text = None
        if not text:
            path = REPO_ROOT / rel_path
            try:
                text = path.read_text(encoding="utf-8").strip() if path.exists() else None
            except OSError:
                text = None
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...truncated]"
        sections.append(f"## {rel_path}\n{text}")

    return "\n\n---\n\n".join(sections)

MAX_TOTAL_CHARS = 8000


def load_vault_context() -> str:
    """Load and compress vault context files into a single string."""
    sections = []
    total = 0

    for rel_path, max_chars in _VAULT_FILES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...truncated]"
        section = f"## {rel_path}\n{text}"
        if total + len(section) > MAX_TOTAL_CHARS:
            break
        sections.append(section)
        total += len(section)

    return "\n\n---\n\n".join(sections)
