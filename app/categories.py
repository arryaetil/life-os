import logging
import re
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
        "lidl", "albert", "aldi", "jumbo", "restaurant", "eten", "brood",
    ],
    "Social": [
        "date", "drinks", "party", "cinema", "friends", "bar", "club",
        "concert", "festival", "tickets", "borrel",
    ],
    "Transport": [
        "fuel", "train", "bus", "uber", "parking", "taxi", "metro",
        "tram", "benzine", "trein",
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

KNOWN_CATEGORIES = frozenset({
    "Food", "Transport", "Social", "Health", "Education",
    "Project", "Clothing", "Income", "Investment", "Transfer",
    "Impulse", "Other",
})

_CATEGORY_SYNONYMS: dict[str, str] = {
    "Eating": "Food", "Meals": "Food", "Restaurant": "Food",
    "Groceries": "Food", "Grocery": "Food", "Dining": "Food",
    "Car": "Transport", "Gas": "Transport", "Fuel": "Transport",
    "Travel": "Transport", "Petrol": "Transport",
    "Entertainment": "Social", "Nightlife": "Social",
    "Fitness": "Health", "Medical": "Health",
    "Books": "Education", "Learning": "Education", "Course": "Education",
    "Shopping": "Clothing", "Fashion": "Clothing",
    "Tech": "Project", "Software": "Project", "Tools": "Project",
    "Technology": "Project",
}

_MAX_DYNAMIC_WORDS = 3
_LOW_CONFIDENCE_THRESHOLD = 0.7


def normalize_category(category: str) -> str:
    """Normalize an AI-suggested category. Maps synonyms to canonical names.

    Unknown categories pass through title-cased (dynamic category creation).
    """
    if not category or not category.strip():
        return "Other"
    cat = re.sub(r"[^A-Za-z0-9 &/-]+", " ", category)
    cat = re.sub(r"\s+", " ", cat).strip().title()
    if not cat:
        return "Other"
    return _CATEGORY_SYNONYMS.get(cat, cat)


_log = logging.getLogger(__name__)


def get_stored_categories() -> set[str]:
    """Return categories already persisted on transactions."""
    try:
        from app import database
        return {
            normalize_category(str(t.get("category", "")))
            for t in database.get_all_transactions()
            if t.get("category") and t.get("notes") != "[UNDONE]"
        } - {"Other"}
    except Exception as exc:
        _log.debug("Could not load stored categories: %s", exc)
        return set()


def get_available_categories() -> list[str]:
    categories = KNOWN_CATEGORIES | get_stored_categories()
    return sorted(categories - {"Other"}) + ["Other"]


def is_existing_category(category: str) -> bool:
    return normalize_category(category) in set(get_available_categories())


def is_clean_dynamic_category(category: str) -> bool:
    cat = normalize_category(category)
    if cat in KNOWN_CATEGORIES:
        return True
    words = cat.replace("&", " ").replace("/", " ").replace("-", " ").split()
    return 1 <= len(words) <= _MAX_DYNAMIC_WORDS and all(len(word) >= 2 for word in words)


def needs_category_clarification(parsed: dict, category: str) -> bool:
    """Ask before accepting a low-confidence new category."""
    try:
        confidence = float(parsed.get("confidence", 1.0))
    except (TypeError, ValueError):
        confidence = 1.0
    return (
        confidence < _LOW_CONFIDENCE_THRESHOLD
        and normalize_category(category) not in set(get_available_categories())
    )


def build_category_clarification_question(description: str, category: str) -> str:
    available = ", ".join(get_available_categories())
    return (
        f"Should '{description}' be categorized as {category}, or one of: "
        f"{available}?"
    )


def _keyword_match(description: str) -> str | None:
    desc_lower = description.lower()
    for category, keywords in KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None

def _ai_categorize(description: str) -> str:
    categories = ", ".join(get_available_categories())
    prompt = (
        "You are a personal finance categorizer.\n"
        f"Existing categories: {categories}\n\n"
        "Prefer an existing category when it fits well. Only suggest a new "
        "category when it is clearly useful and not a duplicate. Keep any new "
        "category short and clean. Avoid duplicates like Food/Eating/Meals.\n\n"
        f'Description: "{description}"\n'
        "Reply with the category name only. No explanation."
    )

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
        raw = _ai_categorize(description)
        category = normalize_category(raw)
        if not is_clean_dynamic_category(category):
            return "Other"
        return category
    except Exception as exc:
        _log.warning("AI categorization failed for %r: %s", description, exc)
        return "Other"
