"""Store for scanned PDFs awaiting page selection (memory + Supabase)."""

import asyncio
import base64
import time
from dataclasses import dataclass

from aisha.skills.pending_store import clear_pending, get_pending, upsert_pending

DOCUMENT_PENDING_TTL = 300  # 5 minutes


@dataclass
class PendingDocument:
    pdf_bytes: bytes
    total_pages: int
    caption: str | None
    timestamp: float


_pending: dict[str, PendingDocument] = {}


def _schedule(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        pass


def store_pending_document(
    phone: str,
    pdf_bytes: bytes,
    total_pages: int,
    caption: str | None,
) -> None:
    _pending[phone] = PendingDocument(
        pdf_bytes=pdf_bytes,
        total_pages=total_pages,
        caption=caption,
        timestamp=time.monotonic(),
    )
    _schedule(upsert_pending(
        phone,
        "document",
        {"total_pages": total_pages, "caption": caption},
        DOCUMENT_PENDING_TTL,
        blob_b64=base64.b64encode(pdf_bytes).decode(),
    ))


def get_pending_document(phone: str) -> PendingDocument | None:
    entry = _pending.get(phone)
    if entry is not None:
        if time.monotonic() - entry.timestamp > DOCUMENT_PENDING_TTL:
            _pending.pop(phone, None)
            _schedule(clear_pending(phone, "document"))
            return None
        return entry
    return None


async def get_pending_document_async(phone: str) -> PendingDocument | None:
    entry = get_pending_document(phone)
    if entry:
        return entry
    row = await get_pending(phone, "document")
    if not row or not row.get("blob_b64"):
        return None
    payload = row.get("payload") or {}
    restored = PendingDocument(
        pdf_bytes=base64.b64decode(row["blob_b64"]),
        total_pages=int(payload.get("total_pages") or 0),
        caption=payload.get("caption"),
        timestamp=time.monotonic(),
    )
    _pending[phone] = restored
    return restored


def clear_pending_document(phone: str) -> None:
    _pending.pop(phone, None)
    _schedule(clear_pending(phone, "document"))
