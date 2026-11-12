"""Durable per-sender conversation. Fail closed on storage failures."""

from datetime import datetime, timedelta, timezone

from aisha.config import SUPABASE_URL
from aisha.supabase_http import HEADERS, get_client
from .ingest import ExportError

KIND = "wa_export"
TTL_SECONDS = 86400
_URL = f"{SUPABASE_URL}/rest/v1/pending_states"


def _params(phone):
    return {"phone": f"eq.{phone}", "kind": f"eq.{KIND}"}


async def save(phone: str, messages: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    try:
        response = await get_client().post(
            _URL,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "kind": KIND,
                "payload": {"version": 1, "messages": messages},
                "blob_b64": None,
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=TTL_SECONDS)).isoformat(),
            },
        )
        response.raise_for_status()
    except Exception as exc:
        raise ExportError(
            "Não consegui salvar a conversa. Tente reenviar; não confirmei a substituição da anterior."
        ) from exc


async def forget(phone: str) -> None:
    try:
        response = await get_client().delete(
            _URL, headers=HEADERS, params=_params(phone)
        )
        response.raise_for_status()
    except Exception as exc:
        raise ExportError(
            "Não consegui apagar a conversa. Tente novamente; a exclusão não foi confirmada."
        ) from exc


async def load(phone: str) -> list[dict] | None:
    try:
        response = await get_client().get(
            _URL,
            headers=HEADERS,
            params={**_params(phone), "select": "payload,expires_at"},
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return None
        row = rows[0]
        if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            await forget(phone)
            return None
        payload = row["payload"]
        if payload.get("version") != 1 or not isinstance(payload.get("messages"), list):
            raise ValueError("Unsupported stored conversation")
        return payload["messages"]
    except ExportError:
        raise
    except Exception as exc:
        raise ExportError(
            "Não consegui recuperar a conversa salva. Tente novamente."
        ) from exc
