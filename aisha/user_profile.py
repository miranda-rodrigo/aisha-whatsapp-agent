"""CRUD for the user_profiles table via Supabase REST API."""

import logging
from datetime import datetime, timezone

import httpx

from aisha.config import SUPABASE_KEY, SUPABASE_URL

log = logging.getLogger(__name__)

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
_TABLE_URL = f"{SUPABASE_URL}/rest/v1/user_profiles"


async def get_profile(phone: str) -> dict | None:
    """Return the user profile dict, or None if not found."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _TABLE_URL,
            headers=_HEADERS,
            params={
                "phone": f"eq.{phone}",
                "select": "personal_context,language,timezone,stats,updated_at",
            },
        )
        resp.raise_for_status()
        rows = resp.json()
    return rows[0] if rows else None


async def upsert_timezone(phone: str, tz: str) -> None:
    """Save or update the user's timezone (IANA name, e.g. 'America/Sao_Paulo')."""
    async with httpx.AsyncClient() as client:
        await client.post(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "timezone": tz,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    log.info(f"Timezone set for {phone}: {tz}")


async def upsert_context(phone: str, context: str) -> None:
    """Save or update the user's personal context."""
    async with httpx.AsyncClient() as client:
        await client.post(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "personal_context": context,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    log.info(f"Context saved for {phone} ({len(context)} chars)")


async def upsert_language(phone: str, language: str) -> None:
    """Save or update the user's preferred language."""
    async with httpx.AsyncClient() as client:
        await client.post(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "language": language,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    log.info(f"Language set for {phone}: {language}")


async def increment_stat(phone: str, key: str) -> None:
    """Increment a usage counter in the stats JSONB field atomically via Supabase RPC."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/increment_stat",
            headers=_HEADERS,
            json={"p_phone": phone, "p_key": key},
        )
    if resp.status_code not in (200, 204):
        log.warning(f"increment_stat RPC failed ({resp.status_code}), falling back to GET+POST")
        await _increment_stat_fallback(phone, key)
    else:
        log.info(f"Stat incremented for {phone}: {key}")


async def _increment_stat_fallback(phone: str, key: str) -> None:
    """Fallback: GET + POST (non-atomic). Used only if RPC is unavailable."""
    profile = await get_profile(phone)
    stats = profile.get("stats", {}) if profile else {}
    stats[key] = stats.get(key, 0) + 1

    async with httpx.AsyncClient() as client:
        await client.post(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "stats": stats,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    log.info(f"Stat incremented (fallback) for {phone}: {key}={stats[key]}")
