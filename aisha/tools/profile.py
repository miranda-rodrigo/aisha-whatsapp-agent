"""Tool wrappers for user profile management."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_set_personal_context(args: dict, ctx: ToolContext) -> str:
    from aisha.user_profile import get_profile, upsert_context

    context = args.get("context", "")
    if not context:
        return json.dumps({"error": "Contexto pessoal não pode ser vazio."})

    profile = await get_profile(ctx.phone)
    existing = profile.get("personal_context", "") if profile else ""
    new_context = f"{existing}\n{context}" if existing else context

    await upsert_context(ctx.phone, new_context)
    return json.dumps({"status": "saved", "context_length": len(new_context)})


async def tool_set_language(args: dict, ctx: ToolContext) -> str:
    from aisha.user_profile import upsert_language

    language = args.get("language", "")
    if not language:
        return json.dumps({"error": "Idioma não pode ser vazio."})

    await upsert_language(ctx.phone, language)
    return json.dumps({"status": "saved", "language": language})


async def tool_get_my_profile(args: dict, ctx: ToolContext) -> str:
    from aisha.user_profile import get_profile
    from aisha.skills.reminder_store import get_reminders
    from aisha.skills.scheduled_task_store import get_tasks
    from datetime import datetime

    profile = await get_profile(ctx.phone)
    reminders = await get_reminders(ctx.phone)
    tasks = await get_tasks(ctx.phone)

    ctx_text = (profile.get("personal_context") or "nenhum definido") if profile else "nenhum definido"
    lang = (profile.get("language") or "nenhum definido") if profile else "nenhum definido"
    tz = (profile.get("timezone") or ctx.user_tz) if profile else ctx.user_tz
    stats = (profile.get("stats") or {}) if profile else {}

    reminder_list = []
    for r in reminders:
        dt = datetime.fromisoformat(r["scheduled_at"])
        reminder_list.append({
            "message": r["message"],
            "scheduled_at": dt.isoformat(),
            "is_recurring": r.get("is_recurring", False),
        })

    task_list = []
    for t in tasks:
        task_list.append({
            "name": t["name"],
            "cron_expression": t["cron_expression"],
        })

    return json.dumps({
        "personal_context": ctx_text,
        "language": lang,
        "timezone": tz,
        "stats": stats,
        "active_reminders": reminder_list,
        "scheduled_tasks": task_list,
    })
