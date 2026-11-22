"""Compatibility import for the shared chat-analysis package."""
import sys
from aisha_chat import media as _shared
sys.modules[__name__] = _shared
