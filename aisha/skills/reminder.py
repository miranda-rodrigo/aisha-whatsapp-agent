"""Reminder skill for Aisha: create, list, cancel, edit reminders."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

import dateparser
import httpx
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from aisha.config import (
    GRAPH_API_URL,
    OPENAI_API_KEY,
    REMINDER_LEAD_MINUTES,
    USER_TIMEZONE,
    WHATSAPP_TOKEN,
)
from aisha.skills.reminder_store import (
    Reminder,
    cancel_reminder,
    get_reminders,
    mark_sent,
    save_reminder,
    update_job_id,
    update_reminder,
)

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_REMINDER_PATTERNS = [
    r"\blembr[ae]\b",
    r"\blembrete\b",
    r"\blembretes\b",
    r"\bavisa[-\s]?(me)?\b",
    r"\bremind\b",
    r"\bcancela.{0,20}lembrete\b",
    r"\bapaga.{0,20}lembrete\b",
    r"\bedita.{0,20}lembrete\b",
    r"\bmuda.{0,20}lembrete\b",
]


class ReminderExtraction(BaseModel):
    action: Literal["create", "list", "cancel", "edit"]
    message: str | None = Field(None, description="Reminder message, e.g. 'Reuniao com XXX'")
    datetime_raw: str | None = Field(None, description="Raw datetime string, e.g. 'amanha as 10h'")
    reminder_number: int | None = Field(None, description="1-based index from list for cancel/edit")
    new_datetime_raw: str | None = Field(None, description="New datetime string when editing")
    is_recurring: bool = False
    rrule: str | None = Field(None, description="RFC 5545 RRULE, e.g. 'FREQ=WEEKLY;BYDAY=MO'")
    lead_minutes: int = Field(REMINDER_LEAD_MINUTES, description="Minutes of advance notice")


def _build_extract_system() -> str:
    now = _now_local()
    return f"""\
You extract reminder actions from user messages.
Current date/time: {now.strftime('%Y-%m-%d %H:%M')} ({USER_TIMEZONE}).

For 'create': extract the reminder message, datetime expression as written (do NOT translate), \
whether it recurs, and optionally an RRULE for recurrence.
When the user says only a time (e.g. "1830", "18h30", "6:30 PM") without a date, \
assume TODAY if the time is still in the future, or TOMORROW if it already passed.
For 'list': user wants to see their reminders.
For 'cancel': user wants to delete a reminder. Extract reminder_number if they say "lembrete 1" or "#1".
For 'edit': user wants to change a reminder's time. Extract reminder_number and new_datetime_raw.

Keep datetime_raw exactly as the user said it (e.g. "amanha as 10h", "todo dia 5 as 9h").
For recurring patterns, also fill rrule using RFC 5545 (e.g. "FREQ=DAILY", "FREQ=WEEKLY;BYDAY=MO,WE,FR").
lead_minutes defaults to {REMINDER_LEAD_MINUTES} unless the user specifies otherwise."""


def is_reminder_intent(text: str) -> bool:
    """Fast regex check before calling the LLM."""
    for pattern in _REMINDER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _gcal_link(title: str, start_utc: datetime, duration_min: int = 60) -> str:
    """Generate a Google Calendar 'Add event' URL."""
    end_utc = start_utc + timedelta(minutes=duration_min)
    fmt = "%Y%m%dT%H%M%SZ"
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{start_utc.strftime(fmt)}/{end_utc.strftime(fmt)}",
        "ctz": USER_TIMEZONE,
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def _now_local() -> datetime:
    """Return the current time in the user's timezone."""
    import zoneinfo
    return datetime.now(zoneinfo.ZoneInfo(USER_TIMEZONE))


def _parse_dt(raw: str) -> datetime | None:
    """Parse a natural language datetime string to UTC."""
    dt = dateparser.parse(
        raw,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": USER_TIMEZONE,
            "TO_TIMEZONE": "UTC",
            "RELATIVE_BASE": _now_local().replace(tzinfo=None),
        },
    )
    return dt


def _fmt_local(dt_utc: datetime, tz: str = USER_TIMEZONE) -> str:
    """Format a UTC datetime as local time string for display."""
    import zoneinfo
    local = dt_utc.astimezone(zoneinfo.ZoneInfo(tz))
    return local.strftime("%d/%m às %H:%M")


async def _extract(text: str) -> ReminderExtraction:
    """Call gpt-4o-mini with structured output to extract reminder intent."""
    response = await _client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _build_extract_system()},
            {"role": "user", "content": text},
        ],
        response_format=ReminderExtraction,
        temperature=0,
    )
    return response.choices[0].message.parsed


async def _send_whatsapp(phone: str, message: str) -> None:
    """Send a WhatsApp message from within the scheduler job."""
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=30.0,
    ) as client:
        await client.post(
            f"{GRAPH_API_URL}/messages",
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": message},
            },
        )


async def _fire_reminder(phone: str, reminder_id: str, message: str) -> None:
    """Called by APScheduler when a reminder fires."""
    log.info(f"Firing reminder {reminder_id} for {phone}")
    await _send_whatsapp(phone, f"⏰ Lembrete: {message}")
    await mark_sent(reminder_id)


async def _schedule_job(
    reminder_id: str,
    phone: str,
    message: str,
    scheduled_at: datetime,
    lead_minutes: int,
    is_recurring: bool,
    rrule: str | None,
    scheduler: AsyncScheduler,
) -> str:
    """Schedule the reminder job and return the APScheduler schedule_id."""
    fire_at = scheduled_at - timedelta(minutes=lead_minutes)

    if is_recurring and rrule:
        trigger = _rrule_to_trigger(rrule, fire_at)
    else:
        trigger = DateTrigger(run_time=fire_at)

    schedule_id = await scheduler.add_schedule(
        _fire_reminder,
        trigger,
        id=reminder_id,
        kwargs={"phone": phone, "reminder_id": reminder_id, "message": message},
        misfire_grace_time=timedelta(seconds=120),
    )
    return str(schedule_id)


def _rrule_to_trigger(rrule: str, first_fire: datetime) -> CronTrigger:
    """Convert a simple RRULE string to an APScheduler CronTrigger."""
    parts = {k: v for k, v in (p.split("=") for p in rrule.split(";") if "=" in p)}
    freq = parts.get("FREQ", "DAILY")
    byday = parts.get("BYDAY", "")
    bymonthday = parts.get("BYMONTHDAY", "")

    day_map = {"MO": "mon", "TU": "tue", "WE": "wed", "TH": "thu",
               "FR": "fri", "SA": "sat", "SU": "sun"}

    kwargs: dict = {
        "hour": first_fire.hour,
        "minute": first_fire.minute,
        "timezone": "UTC",
    }

    if freq == "DAILY":
        kwargs["day"] = "*"
    elif freq == "WEEKLY" and byday:
        days = ",".join(day_map.get(d.strip(), "*") for d in byday.split(","))
        kwargs["day_of_week"] = days
    elif freq == "MONTHLY" and bymonthday:
        kwargs["day"] = bymonthday

    return CronTrigger(**kwargs)


async def handle_reminder(phone: str, text: str, scheduler: AsyncScheduler) -> str:
    """Main entry point: parse, act, and return a reply message."""
    extraction = await _extract(text)
    action = extraction.action

    if action == "list":
        return await _handle_list(phone)

    if action == "cancel":
        return await _handle_cancel(phone, extraction, scheduler)

    if action == "edit":
        return await _handle_edit(phone, extraction, scheduler)

    # action == "create"
    return await _handle_create(phone, extraction, scheduler)


async def _handle_create(
    phone: str, ex: ReminderExtraction, scheduler: AsyncScheduler
) -> str:
    if not ex.datetime_raw:
        return "Por favor, diga quando quer ser lembrado. Ex: 'me lembra da reunião amanhã às 10h'."

    scheduled_at = _parse_dt(ex.datetime_raw)
    if not scheduled_at:
        return f"Não consegui entender o horário '{ex.datetime_raw}'. Tente ser mais específico, ex: 'amanhã às 10h'."

    now_utc = datetime.now(timezone.utc)
    diff_minutes = (scheduled_at - now_utc).total_seconds() / 60

    if diff_minutes < -60:
        local_display = _fmt_local(scheduled_at)
        return (
            f"O horário {local_display} já passou. Você quis dizer amanhã no mesmo horário?\n\n"
            f"Se sim, diga: 'me lembra amanhã às {_fmt_local(scheduled_at).split(' às ')[1]}'"
        )

    if diff_minutes < 0:
        local_display = _fmt_local(scheduled_at)
        return (
            f"O horário {local_display} acabou de passar (há {abs(int(diff_minutes))} minutos). "
            f"Quer que eu crie para amanhã no mesmo horário?"
        )

    if diff_minutes < ex.lead_minutes:
        local_display = _fmt_local(scheduled_at)
        return (
            f"O lembrete para {local_display} é daqui a menos de {ex.lead_minutes} minutos — "
            f"não daria tempo de avisar com antecedência. Quer que eu crie mesmo assim? "
            f"O aviso será enviado imediatamente."
        )

    message = ex.message or ex.datetime_raw
    reminder = Reminder(
        phone=phone,
        message=message,
        scheduled_at=scheduled_at,
        timezone=USER_TIMEZONE,
        is_recurring=ex.is_recurring,
        rrule=ex.rrule,
    )

    reminder_id = await save_reminder(reminder)

    job_id = await _schedule_job(
        reminder_id=reminder_id,
        phone=phone,
        message=message,
        scheduled_at=scheduled_at,
        lead_minutes=ex.lead_minutes,
        is_recurring=ex.is_recurring,
        rrule=ex.rrule,
        scheduler=scheduler,
    )
    await update_job_id(reminder_id, job_id)

    fire_display = _fmt_local(scheduled_at - timedelta(minutes=ex.lead_minutes))
    event_display = _fmt_local(scheduled_at)
    gcal = _gcal_link(message, scheduled_at)

    recurrence_line = ""
    if ex.is_recurring and ex.rrule:
        recurrence_line = f"\n🔁 Recorrente ({ex.rrule})"

    return (
        f"✅ Lembrete criado!\n"
        f"📌 {message}\n"
        f"📅 {event_display} ({USER_TIMEZONE}){recurrence_line}\n"
        f"⏰ Aviso: {ex.lead_minutes} min antes (às {fire_display.split(' às ')[1]})\n\n"
        f"🗓️ Adicionar ao Google Calendar:\n{gcal}"
    )


async def _handle_list(phone: str) -> str:
    rows = await get_reminders(phone)
    if not rows:
        return "Você não tem lembretes ativos."

    lines = ["📋 Seus lembretes:"]
    for i, row in enumerate(rows, 1):
        dt_utc = datetime.fromisoformat(row["scheduled_at"])
        display = _fmt_local(dt_utc, row.get("timezone", USER_TIMEZONE))
        recur = " 🔁" if row.get("is_recurring") else ""
        lines.append(f"{i}. {row['message']} — {display}{recur}")

    lines.append("\nPara cancelar: 'cancela o lembrete 1'")
    return "\n".join(lines)


async def _handle_cancel(
    phone: str, ex: ReminderExtraction, scheduler: AsyncScheduler
) -> str:
    rows = await get_reminders(phone)
    if not rows:
        return "Você não tem lembretes ativos para cancelar."

    idx = (ex.reminder_number or 1) - 1
    if idx < 0 or idx >= len(rows):
        return f"Lembrete #{idx + 1} não encontrado. Você tem {len(rows)} lembrete(s) ativo(s)."

    row = rows[idx]
    await cancel_reminder(row["id"])

    # Remove job from scheduler if it exists
    if row.get("job_id"):
        try:
            await scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    return f"✅ Lembrete cancelado: '{row['message']}'"


async def _handle_edit(
    phone: str, ex: ReminderExtraction, scheduler: AsyncScheduler
) -> str:
    rows = await get_reminders(phone)
    if not rows:
        return "Você não tem lembretes ativos para editar."

    idx = (ex.reminder_number or 1) - 1
    if idx < 0 or idx >= len(rows):
        return f"Lembrete #{idx + 1} não encontrado."

    row = rows[idx]
    raw = ex.new_datetime_raw or ex.datetime_raw
    if not raw:
        return "Por favor, diga o novo horário. Ex: 'muda o lembrete 1 para as 11h'."

    new_dt = _parse_dt(raw)
    if not new_dt:
        return f"Não consegui entender '{raw}'. Tente novamente."

    if new_dt <= datetime.now(timezone.utc):
        return "Esse horário já passou. Por favor, escolha um horário futuro."

    # Cancel old job
    if row.get("job_id"):
        try:
            await scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    await update_reminder(row["id"], new_dt, ex.rrule)

    new_job_id = await _schedule_job(
        reminder_id=row["id"],
        phone=phone,
        message=row["message"],
        scheduled_at=new_dt,
        lead_minutes=REMINDER_LEAD_MINUTES,
        is_recurring=row.get("is_recurring", False),
        rrule=ex.rrule or row.get("rrule"),
        scheduler=scheduler,
    )
    await update_job_id(row["id"], new_job_id)

    display = _fmt_local(new_dt)
    return f"✅ Lembrete atualizado!\n📌 {row['message']}\n📅 {display}"
