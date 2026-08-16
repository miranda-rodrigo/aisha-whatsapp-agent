"""Stores raw audio transcriptions briefly so the user can request a transcript after the fact."""

import asyncio
import time
from dataclasses import dataclass, field

from aisha.skills.pending_store import clear_pending, get_pending, upsert_pending

_TTL_SECONDS = 5 * 60  # 5 minutes


@dataclass
class _Entry:
    raw_text: str
    ts: float = field(default_factory=time.time)


_store: dict[str, _Entry] = {}


def _schedule(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def store_raw_transcription(phone: str, raw_text: str) -> None:
    _store[phone] = _Entry(raw_text=raw_text)
    _evict()
    _schedule(upsert_pending(phone, "transcription", {"raw_text": raw_text}, _TTL_SECONDS))


def get_raw_transcription(phone: str) -> str | None:
    _evict()
    entry = _store.get(phone)
    return entry.raw_text if entry else None


async def get_raw_transcription_async(phone: str) -> str | None:
    text = get_raw_transcription(phone)
    if text:
        return text
    row = await get_pending(phone, "transcription")
    if not row:
        return None
    raw = (row.get("payload") or {}).get("raw_text")
    if raw:
        _store[phone] = _Entry(raw_text=raw)
    return raw


def pop_raw_transcription(phone: str) -> str | None:
    """Returns and removes the stored transcription."""
    _evict()
    entry = _store.pop(phone, None)
    _schedule(clear_pending(phone, "transcription"))
    return entry.raw_text if entry else None


async def pop_raw_transcription_async(phone: str) -> str | None:
    text = pop_raw_transcription(phone)
    if text:
        return text
    row = await get_pending(phone, "transcription")
    if not row:
        return None
    await clear_pending(phone, "transcription")
    return (row.get("payload") or {}).get("raw_text")


def _evict() -> None:
    cutoff = time.time() - _TTL_SECONDS
    stale = [k for k, v in _store.items() if v.ts < cutoff]
    for k in stale:
        del _store[k]
        _schedule(clear_pending(k, "transcription"))
