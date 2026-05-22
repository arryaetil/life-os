"""
AI agent for LifeOS conversational responses and action proposals.
Uses OpenAI GPT-4o-mini with compressed vault context.
"""
import logging

_log = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are the LifeOS AI assistant. You have access to the user's personal "
    "operating system context below.\n"
    "Answer questions concisely and practically. Keep responses under 200 words "
    "unless the user asks for detail. Do not make up information not in the context."
)

_ACTION_PROMPT = (
    "You are the LifeOS AI assistant. The user is requesting an action.\n"
    "Describe the action you would propose (1-3 sentences), what it does, and any risks.\n"
    "End your response with exactly: 'Reply A to approve or B to cancel.'\n"
    "Do not execute anything — only propose and ask for confirmation."
)

_COACH_PROMPT = """You are a Tim Grover-style financial coach built into the user's personal Life OS.

Tim Grover coached Michael Jordan, Kobe Bryant, Dwyane Wade. He doesn't do soft. He does results.

The user's target: €30,000 net worth. Every euro either moves toward that or doesn't.

Your rules:
- Brutally direct. No sugarcoating. Short punchy sentences.
- Use the exact numbers from the live financial data. Name them. Call them out.
- Don't celebrate average. Only acknowledge real wins that actually matter.
- Never say "that's okay" or "don't worry about it" — that's loser talk.
- When they're slipping, say it. When they're on track, push harder.
- No emojis. No fluff. No therapy. Just truth and direction.
- End every response with one sharp action or challenge — no open-ended hanging.
- Max 160 words unless they ask for a full breakdown."""


def _call_openai(system: str, user: str, max_tokens: int = 300) -> str | None:
    from app import config
    if not config.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        _log.warning("OpenAI call failed: %s", exc)
        return None


def _call_openai_messages(messages: list[dict], max_tokens: int = 300) -> str | None:
    from app import config
    if not config.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        _log.warning("OpenAI call failed: %s", exc)
        return None


def coach_response(
    message: str,
    financial_context: str,
    short_term: list[dict] | None = None,
    vault_memory: str = "",
) -> str:
    """Respond as Tim Grover-style financial coach.

    Context layers (cheapest → richest):
    - vault_memory: compressed long-term patterns from coach-memory.md
    - financial_context: live numbers refreshed every message
    - short_term: last 5 raw messages for conversational continuity
    """
    system_parts = [_COACH_PROMPT, f"\nLIVE FINANCIAL DATA:\n{financial_context}"]
    if vault_memory:
        system_parts.append(f"\nLONG-TERM MEMORY (from vault):\n{vault_memory}")
    system = "\n".join(system_parts)

    messages: list[dict] = [{"role": "system", "content": system}]
    for h in (short_term or []):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    result = _call_openai_messages(messages, max_tokens=250)
    if result:
        return result
    return (
        "Can't reach the AI right now. But here's what you do: "
        "open your numbers, find the biggest waste, cut it. That's it."
    )


_MEMORY_UPDATE_PROMPT = """You maintain the long-term memory file for a Tim Grover-style financial coach.

Read the recent conversation and the current memory file. Rewrite the memory file to reflect what you now know.

Rules:
- Keep each section concise — bullet points, specific numbers, no fluff
- Overwrite stale info with fresh observations
- Only record things that are genuinely useful to carry forward
- Total file must stay under 500 words
- Keep the exact markdown structure with the same section headers
- Do not add commentary or explanation — just the updated file content"""


def update_coach_memory(recent_messages: list[dict], current_memory: str) -> None:
    """Compress recent conversation into coach-memory.md. Called every 10 messages."""
    from pathlib import Path
    repo_root = Path(__file__).parent.parent

    conversation = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in recent_messages
    )
    user_msg = (
        f"CURRENT MEMORY FILE:\n{current_memory}\n\n"
        f"RECENT CONVERSATION:\n{conversation}\n\n"
        "Rewrite the memory file with updated insights."
    )
    result = _call_openai(_MEMORY_UPDATE_PROMPT, user_msg, max_tokens=600)
    if result:
        memory_path = repo_root / "vault" / "sessions" / "coach-memory.md"
        memory_path.write_text(result, encoding="utf-8")


def answer_lifeos_question(question: str, structured_data: str = "") -> str:
    """Answer a LifeOS question using vault context and optional live data."""
    from app.vault_context import load_vault_context
    context = load_vault_context()
    if structured_data:
        user_msg = f"Current live data:\n{structured_data}\n\nQuestion: {question}"
    else:
        user_msg = question
    system = f"{_SYSTEM_PROMPT}\n\n# LifeOS Context\n\n{context}"
    result = _call_openai(system, user_msg)
    if result:
        return result
    return (
        "I don't have enough context to answer that. "
        "Try /status for current state or /networth for financial data."
    )


def propose_action(request: str) -> str:
    """Propose an action for user confirmation — does NOT execute anything."""
    from app.vault_context import load_vault_context
    context = load_vault_context()
    system = f"{_ACTION_PROMPT}\n\n# LifeOS Context\n\n{context}"
    result = _call_openai(system, request)
    if result:
        return result
    return (
        f"Action requested: {request}\n\n"
        "I can't generate a specific proposal right now.\n"
        "Describe the task in more detail if needed.\n\n"
        "Reply A to proceed or B to cancel."
    )
