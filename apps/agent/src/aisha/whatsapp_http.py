"""Shared httpx client for WhatsApp Cloud API calls made outside the webhook path.

Scheduler jobs (reminders and scheduled tasks) used to open a fresh
AsyncClient — and therefore a fresh TCP+TLS handshake — on every fire.
Reusing one client keeps the connection warm.
"""

from __future__ import annotations

import httpx

from aisha.config import WHATSAPP_TOKEN

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
            timeout=30.0,
        )
    return _client


async def aclose() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
