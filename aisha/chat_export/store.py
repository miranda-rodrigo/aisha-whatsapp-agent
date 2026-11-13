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


async def save(
    phone: str,
    messages: list[dict],
    *,
    title: str = "Conversa WhatsApp",
    question: str = "",
) -> None:
    now = datetime.now(timezone.utc)
    try:
        response = await get_client().post(
            _URL,
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={
                "phone": phone,
                "kind": KIND,
                "payload": {
                    "version": 2,
                    "messages": messages,
                    "title": title,
                    "question": question,
                    "analysis": None,
                },
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


async def load_record(phone: str) -> dict | None:
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
        if payload.get("version") not in (1, 2) or not isinstance(
            payload.get("messages"), list
        ):
            raise ValueError("Unsupported stored conversation")
        return {**payload, "expires_at": row["expires_at"]}
    except ExportError:
        raise
    except Exception as exc:
        raise ExportError(
            "Não consegui recuperar a conversa salva. Tente novamente."
        ) from exc


async def load(phone: str) -> list[dict] | None:
    record = await load_record(phone)
    return record["messages"] if record else None


async def save_analysis(phone: str, record: dict, analysis: dict) -> None:
    """Keep original expiration and avoid overwriting a newer upload."""
    payload = {k: v for k, v in record.items() if k != "expires_at"}
    payload.update(version=2, analysis=analysis)
    try:
        response = await get_client().patch(
            _URL,
            headers=HEADERS,
            params={**_params(phone), "expires_at": "eq." + record["expires_at"]},
            json={"payload": payload},
        )
        response.raise_for_status()
        if not response.json():
            raise ValueError("Conversation replaced or expired")
    except Exception as exc:
        raise ExportError(
            "Não consegui salvar a análise para reenvio. Tente novamente."
        ) from exc
