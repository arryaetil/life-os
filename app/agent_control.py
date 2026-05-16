"""Agent-control reply detection for the Telegram bot."""

_AGENT_REPLY_TOKENS = frozenset({
    "a", "b", "c", "d",
    "yes", "no",
    "done",
    "approve", "approved",
    "reject",
    "continue",
    "stop",
})


def is_agent_reply(text: str) -> bool:
    """Return True if text is a recognized agent-control reply token.

    Matches exactly (after stripping whitespace and lowercasing).
    Partial matches like 'A great idea' return False.
    """
    return text.strip().lower() in _AGENT_REPLY_TOKENS
