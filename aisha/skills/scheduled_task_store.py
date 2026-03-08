"""CRUD for the scheduled_tasks table via Supabase REST API."""

import logging
from dataclasses import dataclass

import httpx

from aisha.config import SUPABASE_KEY, SUPABASE_URL

log = logging.getLogger(__name__)

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
_TABLE_URL = f"{SUPABASE_URL}/rest/v1/scheduled_tasks"


@dataclass
class ScheduledTask:
    phone: str
    name: str
    prompt: str
    cron_expression: str
    timezone: str
    job_id: str | None = None
    id: str | None = None
    active: bool = True


async def save_task(task: ScheduledTask) -> str:
    """Insert a new scheduled task, return its UUID."""
    payload = {
        "phone": task.phone,
        "name": task.name,
        "prompt": task.prompt,
        "cron_expression": task.cron_expression,
        "timezone": task.timezone,
        "active": True,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(_TABLE_URL, headers=_HEADERS, json=payload)
        resp.raise_for_status()
        row = resp.json()[0]
    log.info(f"Scheduled task saved: id={row['id']} name={task.name}")
    return row["id"]


async def update_job_id(task_id: str, job_id: str) -> None:
    """Set job_id after APScheduler assigns it."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{task_id}"},
            json={"job_id": job_id},
        )


async def get_tasks(phone: str) -> list[dict]:
    """Return active scheduled tasks for a phone number."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _TABLE_URL,
            headers=_HEADERS,
            params={
                "phone": f"eq.{phone}",
                "active": "eq.true",
                "order": "created_at.asc",
                "select": "id,name,prompt,cron_expression,timezone,job_id",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_all_active_tasks() -> list[dict]:
    """Return ALL active scheduled tasks (for restoring jobs on startup)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _TABLE_URL,
            headers=_HEADERS,
            params={
                "active": "eq.true",
                "select": "id,phone,name,prompt,cron_expression,timezone,job_id",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def deactivate_task(task_id: str) -> None:
    """Mark a scheduled task as inactive (soft delete)."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{task_id}"},
            json={"active": False},
        )
    log.info(f"Scheduled task deactivated: id={task_id}")


async def update_task(task_id: str, **fields) -> None:
    """Update arbitrary fields on a scheduled task."""
    async with httpx.AsyncClient() as client:
        await client.patch(
            _TABLE_URL,
            headers=_HEADERS,
            params={"id": f"eq.{task_id}"},
            json=fields,
        )
    log.info(f"Scheduled task updated: id={task_id} fields={list(fields.keys())}")
