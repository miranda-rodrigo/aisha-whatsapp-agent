"""In-memory store for images awaiting user instructions."""

import time
from dataclasses import dataclass

IMAGE_PENDING_TTL = 300  # 5 minutes


@dataclass
class PendingImage:
    image_bytes: bytes
    mime_type: str
    timestamp: float


_pending: dict[str, PendingImage] = {}


def store_pending_image(phone: str, image_bytes: bytes, mime_type: str) -> None:
    _pending[phone] = PendingImage(
        image_bytes=image_bytes,
        mime_type=mime_type,
        timestamp=time.monotonic(),
    )


def get_pending_image(phone: str) -> PendingImage | None:
    entry = _pending.get(phone)
    if entry is None:
        return None
    if time.monotonic() - entry.timestamp > IMAGE_PENDING_TTL:
        _pending.pop(phone, None)
        return None
    return entry


def clear_pending_image(phone: str) -> None:
    _pending.pop(phone, None)
