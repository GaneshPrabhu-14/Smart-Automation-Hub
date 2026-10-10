"""Central configuration. Secrets come from .env (never commit it)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
TASKS_FILE = OUTPUT_DIR / "tasks.json"
DRAFTS_FILE = OUTPUT_DIR / "drafts.json"

# --- LLM (Groq / xAI via an OpenAI-compatible API) ---
LLM_API_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")
               or os.getenv("LLM_API_KEY") or "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.x.ai/v1")
MODEL = os.getenv("LLM_MODEL", "grok-4")
MAX_STEPS = 8
LLM_RATE_LIMIT_RETRY_SECONDS = 30

# --- Token-budget controls ---
MAX_EMAILS = 10
DEFAULT_EMAILS = int(os.getenv("DEFAULT_EMAILS", "5"))
EMAIL_BODY_CHARS = int(os.getenv("EMAIL_BODY_CHARS", "400"))
MAX_TOOL_RESULT_CHARS = 3500

if not 1 <= DEFAULT_EMAILS <= MAX_EMAILS:
    raise ValueError(f"DEFAULT_EMAILS must be between 1 and {MAX_EMAILS}")
if EMAIL_BODY_CHARS < 1:
    raise ValueError("EMAIL_BODY_CHARS must be a positive integer")

# --- Email ---
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "").strip()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
EMAIL_LIVE = bool(EMAIL_ADDRESS and EMAIL_PASSWORD)
ALLOW_AGENT_SEND = os.getenv("ALLOW_AGENT_SEND", "false").lower() == "true"

OUTPUT_DIR.mkdir(exist_ok=True)
