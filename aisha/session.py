"""Session management via Supabase REST API (uses httpx, no extra deps)."""

import logging
from datetime import datetime, timezone

import httpx

from aisha.config import SESSION_TIMEOUT_MINUTES, SUPABASE_KEY, SUPABASE_URL

log = logging.getLogger(__name__)

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
_TABLE_URL = f"{SUPABASE_URL}/rest/v1/sessions"


async def get_response_id(phone: str) -> str | None:
    """Return the active session's response_id, or None if expired/missing."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _TABLE_URL,
            headers=_HEADERS,
            params={"phone": f"eq.{phone}", "select": "response_id,last_active"},
        )
        rows = resp.json()

    if not rows:
        return None

    row = rows[0]
    last_active = datetime.fromisoformat(row["last_active"])
    age_minutes = (datetime.now(timezone.utc) - last_active).total_seconds() / 60

    if age_minutes > SESSION_TIMEOUT_MINUTES:
        log.info(f"Session expired for {phone} (idle {age_minutes:.0f}min)")
        await delete_session(phone)
        return None

    return row["response_id"]


async def upsert_session(phone: str, response_id: str) -> None:
    """Create or update the session for a phone number."""
    async with httpx.AsyncClient() as client:
        await client.post(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "response_id": response_id,
                "last_active": datetime.now(timezone.utc).isoformat(),
            },
        )
    log.info(f"Session upserted for {phone}")


async def delete_session(phone: str) -> None:
    """Remove a session (used on expiry or explicit reset)."""
    async with httpx.AsyncClient() as client:
        await client.delete(
            _TABLE_URL,
            headers=_HEADERS,
            params={"phone": f"eq.{phone}"},
        )
    log.info(f"Session deleted for {phone}")
