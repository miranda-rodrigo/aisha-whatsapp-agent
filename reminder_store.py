"""CRUD for the reminders table via Supabase REST API."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx

from config import SUPABASE_KEY, SUPABASE_URL

log = logging.getLogger(__name__)

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
_TABLE_URL = f"{SUPABASE_URL}/rest/v1/reminders"


@dataclass
class Reminder:
    phone: str
    message: str
    scheduled_at: datetime
    timezone: str
    is_recurring: bool = False
    rrule: str | None = None
    job_id: str | None = None
    id: str | None = None
    status: str = "pending"


async def save_reminder(reminder: Reminder) -> str:
    """Insert a new reminder, return its UUID."""
    payload = {
        "phone": reminder.phone,
        "message": reminder.message,
        "scheduled_at": reminder.scheduled_at.isoformat(),
        "timezone": reminder.timezone,
        "is_recurring": reminder.is_recurring,
        "status": "pending",
    }
    if reminder.rrule:
        payload["rrule"] = reminder.rrule
    if reminder.job_id:
        payload["job_id"] = reminder.job_id

    async with httpx.AsyncClient() as client:
        resp = await client.post(_TABLE_URL, headers=_HEADERS, json=payload)
        resp.raise_for_status()
        row = resp.json()[0]

    log.info(f"Reminder saved: id={row['id']}")
    return row["id"]


async def update_job_id(reminder_id: str, job_id: str) -> None:
    """Set job_id after APScheduler assigns it."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{reminder_id}"},
            json={"job_id": job_id},
        )


async def get_reminders(phone: str, status: str = "pending") -> list[dict]:
    """Return active reminders for a phone number, ordered by scheduled_at."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _TABLE_URL,
            headers=_HEADERS,
            params={
                "phone": f"eq.{phone}",
                "status": f"eq.{status}",
                "order": "scheduled_at.asc",
                "select": "id,message,scheduled_at,timezone,is_recurring,rrule,job_id",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def cancel_reminder(reminder_id: str) -> None:
    """Mark reminder as cancelled and return its job_id."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            _TABLE_URL,
            headers={**_HEADERS, "Prefer": "return=representation"},
            params={"id": f"eq.{reminder_id}"},
            json={"status": "cancelled"},
        )
        resp.raise_for_status()
    log.info(f"Reminder cancelled: id={reminder_id}")


async def mark_sent(reminder_id: str) -> None:
    """Mark reminder as sent after delivery."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{reminder_id}"},
            json={"status": "sent"},
        )
    log.info(f"Reminder marked sent: id={reminder_id}")


async def update_reminder(reminder_id: str, scheduled_at: datetime, rrule: str | None = None) -> None:
    """Update scheduled_at (and optionally rrule) of an existing reminder."""
    payload: dict = {"scheduled_at": scheduled_at.isoformat(), "status": "pending"}
    if rrule is not None:
        payload["rrule"] = rrule
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{reminder_id}"},
            json=payload,
        )
    log.info(f"Reminder updated: id={reminder_id}")
