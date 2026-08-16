"""Shared httpx client for Supabase REST calls.

Creating a new AsyncClient per request forces a fresh TCP+TLS handshake.
Reusing one client keeps the connection warm across session/profile/pending
lookups on the message hot path.
"""

from __future__ import annotations

import httpx

from aisha.config import SUPABASE_KEY, SUPABASE_URL

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=20.0)
    return _client


async def aclose() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
