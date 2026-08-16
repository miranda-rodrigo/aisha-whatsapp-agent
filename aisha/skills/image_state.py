"""Store for images awaiting user instructions (memory + Supabase)."""

import asyncio
import base64
import time
from dataclasses import dataclass

from aisha.skills.pending_store import clear_pending, get_pending, upsert_pending

IMAGE_PENDING_TTL = 300  # 5 minutes


@dataclass
class PendingImage:
    image_bytes: bytes
    mime_type: str
    timestamp: float


_pending: dict[str, PendingImage] = {}


def _schedule(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def store_pending_image(phone: str, image_bytes: bytes, mime_type: str) -> None:
    _pending[phone] = PendingImage(
        image_bytes=image_bytes,
        mime_type=mime_type,
        timestamp=time.monotonic(),
    )
    _schedule(upsert_pending(
        phone,
        "image",
        {"mime_type": mime_type},
        IMAGE_PENDING_TTL,
        blob_b64=base64.b64encode(image_bytes).decode(),
    ))


def get_pending_image(phone: str) -> PendingImage | None:
    entry = _pending.get(phone)
    if entry is not None:
        if time.monotonic() - entry.timestamp > IMAGE_PENDING_TTL:
            _pending.pop(phone, None)
            _schedule(clear_pending(phone, "image"))
            return None
        return entry
    return None


async def get_pending_image_async(phone: str) -> PendingImage | None:
    entry = get_pending_image(phone)
    if entry:
        return entry
    row = await get_pending(phone, "image")
    if not row or not row.get("blob_b64"):
        return None
    image_bytes = base64.b64decode(row["blob_b64"])
    mime_type = (row.get("payload") or {}).get("mime_type", "image/jpeg")
    restored = PendingImage(image_bytes=image_bytes, mime_type=mime_type, timestamp=time.monotonic())
    _pending[phone] = restored
    return restored


def clear_pending_image(phone: str) -> None:
    _pending.pop(phone, None)
    _schedule(clear_pending(phone, "image"))
