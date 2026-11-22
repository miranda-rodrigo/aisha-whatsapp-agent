"""Compatibility import for the shared chat-analysis package."""
import sys
from aisha_chat import analysis as _shared
from aisha.config import OPENAI_API_KEY
from aisha.models import DOCUMENT_MODEL, OPENAI_SERVICE_TIER
_shared.configure(api_key=OPENAI_API_KEY, model=DOCUMENT_MODEL, service_tier=OPENAI_SERVICE_TIER)
sys.modules[__name__] = _shared
