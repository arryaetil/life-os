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
