"""Compatibility import for the shared chat-analysis package."""
import sys
from aisha_chat import enrich as _shared
from . import analysis, assets, store
from aisha.models import VISION_OCR_MODEL, WHISPER_MODEL
_shared.VISION_OCR_MODEL = VISION_OCR_MODEL
_shared.WHISPER_MODEL = WHISPER_MODEL
_shared.configure_storage(store, assets)
sys.modules[__name__] = _shared
