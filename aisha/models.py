"""Canonical model IDs used across Aisha.

Keep this file as the single source of truth so upgrades stay in one place.
"""

AGENT_MODEL = "gpt-5.6-sol"
FAST_MODEL = "gpt-5.6-luna"
CHAT_MODEL = "gpt-5.6-luna"
REASONING_EFFORT = "none"
# Luna tem ~1M de contexto; ficar abaixo do limiar de preço de long-context (~272k tokens).
CHAT_CHUNK_CHARS = 200_000
XAI_SEARCH_MODEL = "grok-4.6"
DOCUMENT_MODEL = "gpt-5.6-sol"
VISION_OCR_MODEL = "gpt-5.6-sol"
EXTRACT_MODEL = "gpt-5.6-sol"
OPENAI_SERVICE_TIER = "fast"
EMBEDDING_MODEL = "text-embedding-3-small"
WHISPER_MODEL = "whisper-1"
GEMINI_PRIMARY = "gemini-3.6-flash"
GEMINI_FALLBACK = "gemini-2.5-flash"
