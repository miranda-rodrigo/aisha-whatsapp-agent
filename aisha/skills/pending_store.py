"""Persist pending conversation states in Supabase so they survive redeploys."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aisha.config import SUPABASE_URL
from aisha.messaging import pending_list_params
from aisha.supabase_http import HEADERS as _HEADERS
from aisha.supabase_http import get_client

log = logging.getLogger(__name__)

_TABLE_URL = f"{SUPABASE_URL}/rest/v1/pending_states"
_MAX_BLOB_CHARS = 2_000_000


async def upsert_pending(
    phone: str,
    kind: str,
    payload: dict,
    ttl_seconds: int,
    blob_b64: str | None = None,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    body: dict = {
        "phone": phone,
        "kind": kind,
        "payload": payload,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if blob_b64 and len(blob_b64) <= _MAX_BLOB_CHARS:
        body["blob_b64"] = blob_b64
    elif blob_b64:
        log.warning(f"Pending {kind} blob too large to persist for {phone} ({len(blob_b64)} chars)")
    client = get_client()
    resp = await client.post(
        _TABLE_URL,
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
        json=body,
    )
    if resp.status_code not in (200, 201):
        log.warning(f"Failed to persist pending {kind} for {phone}: {resp.status_code} {resp.text[:200]}")
        return
    log.info(f"Pending {kind} persisted for {phone}")


async def list_active_pendings(phone: str) -> list[dict]:
    """Return active pending rows for a phone without downloading blobs."""
    client = get_client()
    resp = await client.get(
        _TABLE_URL,
        headers=_HEADERS,
        params=pending_list_params(phone, datetime.now(timezone.utc).isoformat()),
    )
    if resp.status_code != 200:
        log.warning(f"Failed to list pendings for {phone}: {resp.status_code}")
        return []
    return resp.json()


async def get_pending(phone: str, kind: str) -> dict | None:
    client = get_client()
    resp = await client.get(
        _TABLE_URL,
        headers=_HEADERS,
        params={
            "phone": f"eq.{phone}",
            "kind": f"eq.{kind}",
            "select": "payload,blob_b64,expires_at",
        },
    )
    if resp.status_code != 200:
        return None
    rows = resp.json()
    if not rows:
        return None
    row = rows[0]
    expires = datetime.fromisoformat(row["expires_at"])
    if expires < datetime.now(timezone.utc):
        await clear_pending(phone, kind)
        return None
    return row


async def clear_pending(phone: str, kind: str) -> None:
    client = get_client()
    await client.delete(
        _TABLE_URL,
        headers=_HEADERS,
        params={"phone": f"eq.{phone}", "kind": f"eq.{kind}"},
    )


async def clear_all_pending(phone: str) -> None:
    client = get_client()
    await client.delete(
        _TABLE_URL,
        headers=_HEADERS,
        params={"phone": f"eq.{phone}"},
    )
