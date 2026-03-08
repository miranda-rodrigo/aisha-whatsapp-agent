"""In-memory store for scanned PDFs awaiting page selection from the user."""

import time
from dataclasses import dataclass

DOCUMENT_PENDING_TTL = 300  # 5 minutes


@dataclass
class PendingDocument:
    pdf_bytes: bytes
    total_pages: int
    caption: str | None
    timestamp: float


_pending: dict[str, PendingDocument] = {}


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


def get_pending_document(phone: str) -> PendingDocument | None:
    entry = _pending.get(phone)
    if entry is None:
        return None
    if time.monotonic() - entry.timestamp > DOCUMENT_PENDING_TTL:
        _pending.pop(phone, None)
        return None
    return entry


def clear_pending_document(phone: str) -> None:
    _pending.pop(phone, None)
