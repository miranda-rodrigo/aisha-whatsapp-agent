import os
import sys
from dotenv import load_dotenv

load_dotenv(override=False)

REQUIRED = [
    "WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID", "WEBHOOK_VERIFY_TOKEN",
    "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY",
]
missing = [v for v in REQUIRED if v not in os.environ]
if missing:
    print(f"FATAL: Missing env vars: {missing}", file=sys.stderr)
    print(f"Available env vars: {sorted(os.environ.keys())}", file=sys.stderr)
    sys.exit(1)

WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_ID = os.environ["WHATSAPP_PHONE_ID"]
WEBHOOK_VERIFY_TOKEN = os.environ["WEBHOOK_VERIFY_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", "")

ALLOWED_NUMBERS = set(os.environ.get("ALLOWED_NUMBERS", "").split(","))

GRAPH_API_URL = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}"

SESSION_TIMEOUT_MINUTES = 10

USER_TIMEZONE = os.environ.get("USER_TIMEZONE", "America/Sao_Paulo")
REMINDER_LEAD_MINUTES = int(os.environ.get("REMINDER_LEAD_MINUTES", "15"))

# Public base URL of this server (used to build temporary download links).
# Example: https://myserver.com  (no trailing slash)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
