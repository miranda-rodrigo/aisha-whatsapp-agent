"""Stores raw audio transcriptions briefly so the user can request a transcript after the fact."""

import time
from dataclasses import dataclass, field

_TTL_SECONDS = 5 * 60  # 5 minutes


@dataclass
class _Entry:
    raw_text: str
    ts: float = field(default_factory=time.time)


_store: dict[str, _Entry] = {}


def store_raw_transcription(phone: str, raw_text: str) -> None:
    _store[phone] = _Entry(raw_text=raw_text)
    _evict()


def get_raw_transcription(phone: str) -> str | None:
    _evict()
    entry = _store.get(phone)
    return entry.raw_text if entry else None


def pop_raw_transcription(phone: str) -> str | None:
    """Returns and removes the stored transcription."""
    _evict()
    entry = _store.pop(phone, None)
    return entry.raw_text if entry else None


def _evict() -> None:
    cutoff = time.time() - _TTL_SECONDS
    stale = [k for k, v in _store.items() if v.ts < cutoff]
    for k in stale:
        del _store[k]
