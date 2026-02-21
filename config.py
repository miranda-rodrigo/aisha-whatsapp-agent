import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
WHATSAPP_PHONE_ID = os.environ["WHATSAPP_PHONE_ID"]
WEBHOOK_VERIFY_TOKEN = os.environ["WEBHOOK_VERIFY_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

ALLOWED_NUMBERS = set(os.environ.get("ALLOWED_NUMBERS", "").split(","))

GRAPH_API_URL = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}"
