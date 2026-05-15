import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_WEBHOOK_SECRET: str = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./lifeos.db")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
WEEKLY_BUDGET: float = float(os.environ.get("WEEKLY_BUDGET", "90"))
WEBHOOK_BASE_URL: str = os.environ.get("WEBHOOK_BASE_URL", "")
LOCAL_POLLING: bool = os.environ.get("LOCAL_POLLING", "false").lower() == "true"
