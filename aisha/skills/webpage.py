"""Webpage reading skill using Jina Reader (r.jina.ai).

Fetches any public URL as clean markdown and sends the content to the LLM
for summarization, translation, Q&A, or any user-defined instruction.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import httpx

log = logging.getLogger(__name__)

_JINA_BASE = "https://r.jina.ai/"
_MAX_CHARS = 80_000  # ~20k tokens — enough for most articles
_PENDING_TTL_MINUTES = 10

_URL_PATTERN = re.compile(
    r"https?://[^\s]+",
    re.IGNORECASE,
)

# In-memory state: phone -> PendingPage
@dataclass
class PendingPage:
    url: str
    created_at: datetime = field(default_factory=datetime.utcnow)


_pending: dict[str, PendingPage] = {}


def extract_web_url(text: str) -> str | None:
    """Return the first non-YouTube HTTP(S) URL found in text, or None."""
    for m in _URL_PATTERN.finditer(text):
        url = m.group(0).rstrip(".,;)")
        if not _is_youtube(url):
            return url
    return None


def strip_web_url(text: str) -> str:
    """Remove the first non-YouTube URL from text, returning the remainder."""
    for m in _URL_PATTERN.finditer(text):
        url = m.group(0).rstrip(".,;)")
        if not _is_youtube(url):
            return (text[: m.start()] + text[m.start() + len(url) :]).strip()
    return text


def _is_youtube(url: str) -> bool:
    return bool(re.search(r"youtube\.com|youtu\.be", url, re.IGNORECASE))


def store_pending_page(phone: str, url: str) -> None:
    _pending[phone] = PendingPage(url=url)


def get_pending_page(phone: str) -> PendingPage | None:
    p = _pending.get(phone)
    if not p:
        return None
    age = datetime.utcnow() - p.created_at
    if age > timedelta(minutes=_PENDING_TTL_MINUTES):
        del _pending[phone]
        return None
    return p


def clear_pending_page(phone: str) -> None:
    _pending.pop(phone, None)


async def fetch_page(url: str) -> str:
    """Fetch a URL via Jina Reader and return clean markdown content."""
    jina_url = f"{_JINA_BASE}{url}"
    log.info(f"Fetching via Jina: {jina_url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            jina_url,
            headers={"Accept": "text/markdown", "X-No-Cache": "true"},
            follow_redirects=True,
        )
        resp.raise_for_status()

    content = resp.text
    if len(content) > _MAX_CHARS:
        content = content[:_MAX_CHARS] + "\n\n[... conteúdo truncado ...]"

    log.info(f"Jina returned {len(content)} chars for {url}")
    return content
