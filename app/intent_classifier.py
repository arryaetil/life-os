"""
Intent classifier for incoming Telegram messages.

Classifies messages into:
  finance_transaction  — clear expense/income with amount (≤6 words)
  lifeos_question      — general question about the LifeOS system
  action_request       — request to build/run/deploy something
  unknown              — unclear; caller should ask for clarification

Note: agent_reply and net_worth_update are handled upstream before this
function is called, so they are not returned here.
"""
import re

_AMOUNT_PAT = re.compile(
    r"(?:^|\s)[+\-]?\d+(?:[.,]\d+)?k?\b",
    re.IGNORECASE,
)

_QUESTION_PATS = [
    re.compile(r"\b(what|how|why|when|where|which|who)\b", re.IGNORECASE),
    re.compile(r"\b(tell me|explain|describe|show me|give me)\b", re.IGNORECASE),
    re.compile(r"\?$"),
]

_COACH_PATS = [
    re.compile(r"\b(am i (doing|on track|okay|good|spending)|coach me|roast me)\b", re.IGNORECASE),
    re.compile(r"\b(analyze|breakdown|review|evaluate)\b.*\b(spend|budget|finance|money|expense)\b", re.IGNORECASE),
    re.compile(r"\b(should i (cut|stop|reduce|buy|get|spend)|can i afford)\b", re.IGNORECASE),
    re.compile(r"\b(too much|overspend|saving enough|on budget|financial(ly)?)\b", re.IGNORECASE),
    re.compile(r"\b(net worth|progress|goal|30k|30\.000)\b", re.IGNORECASE),
]

_ACTION_PATS = [
    re.compile(r"\b(build|create|implement|start|deploy|run|prepare|generate|make)\b", re.IGNORECASE),
    re.compile(r"\b(handoff|commit|push|test|fix|refactor)\b", re.IGNORECASE),
    re.compile(r"\b(portfolio tracker|next module|module 1\.\d)\b", re.IGNORECASE),
]


def classify_intent(text: str) -> str:
    """Classify text into one of: finance_transaction, lifeos_question, action_request, unknown.

    Callers are expected to have already handled agent_reply and net_worth_update upstream.
    """
    stripped = text.strip()

    # Short messages with a clear amount (≤ 6 words) → finance transaction
    if _AMOUNT_PAT.search(stripped) and len(stripped.split()) <= 6:
        return "finance_transaction"

    # Coaching / financial reflection patterns (check before generic question words)
    for pat in _COACH_PATS:
        if pat.search(stripped):
            return "lifeos_question"

    # Question keywords
    for pat in _QUESTION_PATS:
        if pat.search(stripped):
            return "lifeos_question"

    # Action keywords
    for pat in _ACTION_PATS:
        if pat.search(stripped):
            return "action_request"

    return "unknown"
