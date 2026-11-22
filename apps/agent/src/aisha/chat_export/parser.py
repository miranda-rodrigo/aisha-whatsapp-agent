"""Compatibility import for the shared chat-analysis package."""
import sys
from aisha_chat import parser as _shared
sys.modules[__name__] = _shared
