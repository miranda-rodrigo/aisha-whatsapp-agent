"""Tool wrappers for the reminder skill."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_create_reminder(args: dict, ctx: ToolContext) -> str:
    from aisha.config import REMINDER_LEAD_MINUTES
    from aisha.skills.reminder_store import Reminder, save_reminder, update_job_id
    from aisha.skills.reminder import _schedule_job, _gcal_link, _fmt_local, _parse_dt_iso

    message = args.get("message", "Lembrete")
    datetime_iso = args.get("datetime_iso")
    is_recurring = args.get("is_recurring", False)
    cron_expression = args.get("cron_expression")
    lead_minutes = args.get("lead_minutes", REMINDER_LEAD_MINUTES)

    if not datetime_iso and not cron_expression:
        return json.dumps({"error": "Preciso de datetime_iso ou cron_expression para criar o lembrete."})

    scheduled_at = None
    if datetime_iso:
        scheduled_at = _parse_dt_iso(datetime_iso, ctx.user_tz)
        if not scheduled_at:
            return json.dumps({"error": f"Não consegui interpretar a data: {datetime_iso}"})

        now_utc = datetime.now(timezone.utc)
        if (scheduled_at - now_utc).total_seconds() / 60 < -60:
            return json.dumps({"error": f"O horário {_fmt_local(scheduled_at, ctx.user_tz)} já passou."})

    rrule = None
    if is_recurring and cron_expression:
        rrule = f"CRON:{cron_expression}"

    if not scheduled_at:
        scheduled_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reminder = Reminder(
        phone=ctx.phone,
        message=message,
        scheduled_at=scheduled_at,
        timezone=ctx.user_tz,
        is_recurring=is_recurring,
        rrule=rrule,
    )

    reminder_id = await save_reminder(reminder)
    job_id = await _schedule_job(
        reminder_id=reminder_id,
        phone=ctx.phone,
        message=message,
        scheduled_at=scheduled_at,
        lead_minutes=lead_minutes,
        is_recurring=is_recurring,
        rrule=rrule,
        scheduler=ctx.scheduler,
    )
    await update_job_id(reminder_id, job_id)

    event_display = _fmt_local(scheduled_at, ctx.user_tz)
    gcal = _gcal_link(message, scheduled_at, ctx.user_tz)

    return json.dumps({
        "status": "created",
        "message": message,
        "datetime_display": event_display,
        "timezone": ctx.user_tz,
        "lead_minutes": lead_minutes,
        "google_calendar_link": gcal,
        "is_recurring": is_recurring,
    })


async def tool_list_reminders(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.reminder_store import get_reminders
    from aisha.skills.reminder import _fmt_local

    rows = await get_reminders(ctx.phone)
    if not rows:
        return json.dumps({"reminders": [], "message": "Nenhum lembrete ativo."})

    reminders = []
    for i, row in enumerate(rows, 1):
        dt_utc = datetime.fromisoformat(row["scheduled_at"])
        reminders.append({
            "number": i,
            "message": row["message"],
            "datetime_display": _fmt_local(dt_utc, row.get("timezone") or ctx.user_tz),
            "is_recurring": row.get("is_recurring", False),
        })

    return json.dumps({"reminders": reminders})


async def tool_cancel_reminder(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.reminder_store import get_reminders, cancel_reminder

    reminder_number = args.get("reminder_number", 1)
    rows = await get_reminders(ctx.phone)

    if not rows:
        return json.dumps({"error": "Nenhum lembrete ativo para cancelar."})

    idx = reminder_number - 1
    if idx < 0 or idx >= len(rows):
        return json.dumps({"error": f"Lembrete #{reminder_number} não encontrado. Total: {len(rows)}."})

    row = rows[idx]
    await cancel_reminder(row["id"])

    if row.get("job_id"):
        try:
            await ctx.scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    return json.dumps({"status": "cancelled", "message": row["message"]})
