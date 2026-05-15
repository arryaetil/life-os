from app import config

# Imported at module level so tests can patch them cleanly.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore

KEYWORDS: dict[str, list[str]] = {
    "Food": [
        "lunch", "dinner", "coffee", "kebab", "snack", "groceries", "pizza",
        "burger", "sushi", "sandwich", "supermarket", "takeaway", "bread",
        "ah", "lidl", "albert", "aldi", "jumbo", "restaurant", "eten", "brood",
    ],
    "Social": [
        "date", "drinks", "party", "cinema", "friends", "bar", "club",
        "concert", "festival", "tickets", "borrel",
    ],
    "Transport": [
        "fuel", "train", "bus", "uber", "parking", "taxi", "metro",
        "tram", "ns", "ov", "benzine", "trein",
    ],
    "Project": [
        "api", "domain", "hosting", "software", "tool", "credits",
        "subscription", "server", "claude", "openai", "railway",
    ],
    "Health": [
        "gym", "supplement", "doctor", "medicine", "pharmacy", "dentist",
        "sport", "fitness", "apotheek",
    ],
    "Clothing": [
        "clothes", "shoes", "jacket", "shirt", "pants", "zara",
        "h&m", "nike", "adidas", "kleding",
    ],
    "Education": [
        "book", "course", "udemy", "school", "university", "coursera",
        "boek", "cursus",
    ],
    "Impulse": ["impulse", "random", "unnecessary"],
    "Income": [
        "salary", "duo", "uncle", "refund", "gift", "freelance",
        "loon", "salaris", "oom",
    ],
    "Investment": ["etf", "stock", "crypto", "degiro", "investing"],
    "Transfer": ["savings", "portfolio", "transfer", "spaarrekening"],
}

_AI_PROMPT = (
    "You are a personal finance categorizer. Given this expense description, "
    "return exactly one category from this list:\n"
    "Food, Social, Transport, Project, Health, Clothing, Education, Impulse, "
    "Income, Investment, Transfer, Other\n\n"
    'Description: "{description}"\n'
    "Reply with the category name only. No explanation."
)

def _keyword_match(description: str) -> str | None:
    desc_lower = description.lower()
    for category, keywords in KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None

def _ai_categorize(description: str) -> str:
    prompt = _AI_PROMPT.format(description=description)

    if config.OPENAI_API_KEY and OpenAI is not None:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
        )
        return response.choices[0].message.content.strip()

    if config.ANTHROPIC_API_KEY and Anthropic is not None:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    return "Other"

def get_category(description: str) -> str:
    matched = _keyword_match(description)
    if matched:
        return matched
    try:
        return _ai_categorize(description)
    except Exception:
        return "Other"
