"""CRUD for the user_profiles table via Supabase REST API."""

import logging
import time
from datetime import datetime, timezone

from aisha.config import SUPABASE_URL
from aisha.supabase_http import HEADERS as _HEADERS
from aisha.supabase_http import get_client

log = logging.getLogger(__name__)

_TABLE_URL = f"{SUPABASE_URL}/rest/v1/user_profiles"
_PROFILE_TTL_SECONDS = 60
_CACHE_MISS = object()
_profile_cache: dict[str, tuple[float, dict | None]] = {}


def _cache_get(phone: str):
    cached = _profile_cache.get(phone)
    if cached and (time.monotonic() - cached[0]) < _PROFILE_TTL_SECONDS:
        return cached[1]
    return _CACHE_MISS


def _cache_set(phone: str, profile: dict | None) -> None:
    _profile_cache[phone] = (time.monotonic(), profile)


def invalidate_profile_cache(phone: str) -> None:
    _profile_cache.pop(phone, None)


async def get_profile(phone: str) -> dict | None:
    """Return the user profile dict, or None if not found."""
    cached = _cache_get(phone)
    if cached is not _CACHE_MISS:
        return cached
    client = get_client()
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
    profile = rows[0] if rows else None
    _cache_set(phone, profile)
    return profile


async def upsert_timezone(phone: str, tz: str) -> None:
    """Save or update the user's timezone (IANA name, e.g. 'America/Sao_Paulo')."""
    invalidate_profile_cache(phone)
    client = get_client()
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
    invalidate_profile_cache(phone)
    client = get_client()
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
    invalidate_profile_cache(phone)
    client = get_client()
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
    invalidate_profile_cache(phone)
    client = get_client()
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

    client = get_client()
    await client.post(
        _TABLE_URL,
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
        json={
            "phone": phone,
            "stats": stats,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    _cache_set(phone, {**(profile or {}), "stats": stats})
    log.info(f"Stat incremented (fallback) for {phone}: {key}={stats[key]}")
