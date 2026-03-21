"""Tool wrappers for the scheduled task skill."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aisha.tools import ToolContext

log = logging.getLogger(__name__)


async def tool_create_scheduled_task(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.scheduled_task_store import ScheduledTask, save_task, update_job_id
    from aisha.skills.scheduled_task import _schedule_job, _parse_cron

    name = args.get("name", "Tarefa agendada")
    prompt = args.get("prompt")
    cron_expression = args.get("cron_expression")

    if not prompt or not cron_expression:
        return json.dumps({"error": "Preciso de prompt e cron_expression para criar a tarefa."})

    try:
        _parse_cron(cron_expression, ctx.user_tz)
    except ValueError:
        return json.dumps({"error": f"Cron expression inválida: {cron_expression}"})

    task = ScheduledTask(
        phone=ctx.phone,
        name=name,
        prompt=prompt,
        cron_expression=cron_expression,
        timezone=ctx.user_tz,
    )

    task_id = await save_task(task)
    job_id = await _schedule_job(
        task_id=task_id,
        phone=ctx.phone,
        name=name,
        prompt=prompt,
        cron_expression=cron_expression,
        scheduler=ctx.scheduler,
        user_tz=ctx.user_tz,
    )
    await update_job_id(task_id, job_id)

    return json.dumps({
        "status": "created",
        "name": name,
        "cron_expression": cron_expression,
        "prompt_preview": prompt[:120],
    })


async def tool_list_scheduled_tasks(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.scheduled_task_store import get_tasks

    rows = await get_tasks(ctx.phone)
    if not rows:
        return json.dumps({"tasks": [], "message": "Nenhuma tarefa agendada ativa."})

    tasks = []
    for i, row in enumerate(rows, 1):
        tasks.append({
            "number": i,
            "name": row["name"],
            "cron_expression": row["cron_expression"],
            "prompt_preview": row["prompt"][:80],
        })

    return json.dumps({"tasks": tasks})


async def tool_cancel_scheduled_task(args: dict, ctx: ToolContext) -> str:
    from aisha.skills.scheduled_task_store import get_tasks, deactivate_task

    task_number = args.get("task_number", 1)
    rows = await get_tasks(ctx.phone)

    if not rows:
        return json.dumps({"error": "Nenhuma tarefa agendada ativa para cancelar."})

    idx = task_number - 1
    if idx < 0 or idx >= len(rows):
        return json.dumps({"error": f"Tarefa #{task_number} não encontrada. Total: {len(rows)}."})

    row = rows[idx]
    await deactivate_task(row["id"])

    if row.get("job_id"):
        try:
            await ctx.scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    return json.dumps({"status": "cancelled", "name": row["name"]})
