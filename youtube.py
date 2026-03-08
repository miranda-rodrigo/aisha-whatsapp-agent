"""YouTube video analysis skill using Gemini 2.5 Flash."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from google import genai
from google.genai import types

from config import GEMINI_API_KEY

log = logging.getLogger(__name__)

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_YT_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?(?:[^&\s]*&)*v=|youtu\.be/)([\w-]{11})[^\s]*",
    re.IGNORECASE,
)

_DEFAULT_PROMPT = (
    "Analise este vídeo do YouTube em português. "
    "Forneça: (1) resumo conciso do conteúdo, (2) pontos principais, "
    "(3) conclusão ou mensagem central. Seja objetivo e direto."
)

# In-memory state: phone -> PendingVideo
@dataclass
class PendingVideo:
    url: str
    created_at: datetime = field(default_factory=datetime.utcnow)

_pending: dict[str, PendingVideo] = {}
_PENDING_TTL_MINUTES = 10


def extract_youtube_url(text: str) -> str | None:
    """Return the first YouTube URL found in text, or None."""
    m = _YT_PATTERN.search(text)
    return m.group(0) if m else None


def strip_youtube_url(text: str) -> str:
    """Remove the YouTube URL from the text, returning the remainder."""
    return _YT_PATTERN.sub("", text).strip()


def store_pending_video(phone: str, url: str) -> None:
    _pending[phone] = PendingVideo(url=url)


def get_pending_video(phone: str) -> PendingVideo | None:
    p = _pending.get(phone)
    if not p:
        return None
    age = datetime.utcnow() - p.created_at
    if age > timedelta(minutes=_PENDING_TTL_MINUTES):
        del _pending[phone]
        return None
    return p


def clear_pending_video(phone: str) -> None:
    _pending.pop(phone, None)


async def analyze_video(url: str, instruction: str) -> str:
    """Send the YouTube URL + instruction to Gemini and return the text response."""
    prompt = instruction.strip() if instruction.strip() else _DEFAULT_PROMPT

    log.info(f"Analyzing YouTube video: {url} | prompt: {prompt[:80]}")

    response = await _client.aio.models.generate_content(
        model=_MODEL,
        contents=[
            types.Part.from_uri(file_uri=url, mime_type="video/mp4"),
            prompt,
        ],
    )
    return response.text
