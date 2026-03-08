"""Scheduled task skill: create, list, cancel recurring agent actions.

Unlike reminders (which send a fixed text), scheduled tasks execute an
agent prompt with web_search enabled and send the AI-generated result.
Example: "toda segunda me mande um relatório sobre notícias do Irã".
"""

import logging
import re
from datetime import timedelta
from typing import Literal

import httpx
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from aisha.config import (
    GRAPH_API_URL,
    OPENAI_API_KEY,
    USER_TIMEZONE,
    WHATSAPP_TOKEN,
)
from aisha.skills.scheduled_task_store import (
    ScheduledTask,
    deactivate_task,
    get_tasks,
    save_task,
    update_job_id,
)

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

_TASK_PATTERNS = [
    r"\btoda\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo|semana)\b.*\b(mand[ae]|envi[ae]|faz|gera|pesquis[ae]|busca|relatório|report)\b",
    r"\b(mand[ae]|envi[ae]).*\btod[oa]s?\s+(os\s+dias?|as?\s+(segunda|terça|quarta|quinta|sexta|sábado|domingo))\b",
    r"\b(diariamente|semanalmente|mensalmente)\b.*\b(mand[ae]|envi[ae]|faz|gera)\b",
    r"\btodo\s+dia\b.*\b(mand[ae]|envi[ae]|faz|gera|pesquis[ae]|busca)\b",
    r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|day|week|month)\b",
    r"\b(agenda|schedul)\w*\b.*\b(task|tarefa|ação)\b",
    r"\bcancela.{0,20}(tarefa|task)\s*(agendad|programad|recorrent)\w*\b",
    r"\b(lista|quais).{0,20}(tarefas|tasks)\s*(agendad|programad|recorrent)\w*\b",
]


class TaskExtraction(BaseModel):
    action: Literal["create", "list", "cancel"]
    name: str | None = Field(None, description="Short name for the task, e.g. 'Relatório Irã'")
    prompt: str | None = Field(None, description="The full prompt/instruction the agent should execute each time")
    cron_expression: str | None = Field(None, description="Standard cron expression (5 fields: min hour dom month dow)")
    cron_readable: str | None = Field(None, description="Human-readable schedule, e.g. 'toda segunda às 9h'")
    task_number: int | None = Field(None, description="1-based index from list for cancel")


def _build_extract_system() -> str:
    return f"""\
You extract scheduled task actions from user messages.
Current timezone: {USER_TIMEZONE}.

For 'create': extract:
- name: a short descriptive name (max 50 chars) for the task
- prompt: the full instruction the AI agent should execute each time. \
Include all context the user gave (topic, format, language, etc.). \
The prompt should be self-contained — it will run without conversation history.
- cron_expression: a standard 5-field cron expression (minute hour day-of-month month day-of-week). \
Use reasonable defaults: if user says "toda segunda" without time, default to 09:00. \
If user says "todo dia" without time, default to 08:00.
- cron_readable: human-readable version of the schedule in Portuguese.

For 'list': user wants to see their active scheduled tasks.
For 'cancel': user wants to remove a scheduled task. Extract task_number if mentioned.

Examples:
- "toda segunda me mande um relatório com as últimas notícias sobre o Irã"
  → name="Relatório Irã", prompt="Pesquise as últimas notícias sobre o Irã da última semana. \
Faça um relatório conciso em português com os principais acontecimentos, organizado por tema.", \
cron_expression="0 9 * * 1", cron_readable="toda segunda-feira às 09:00"

- "todo dia às 7h me mande o resumo do mercado financeiro"
  → name="Resumo mercado", prompt="Pesquise o estado atual do mercado financeiro: \
principais índices (Ibovespa, S&P500, Nasdaq), câmbio (dólar, euro), e destaques do dia. \
Resuma de forma objetiva em português.", \
cron_expression="0 7 * * *", cron_readable="todo dia às 07:00"

- "toda sexta às 18h pesquise as novidades de IA da semana e me mande um resumo"
  → name="Novidades IA", prompt="Pesquise as principais novidades e lançamentos de \
inteligência artificial da última semana. Inclua novos modelos, ferramentas, papers \
relevantes e notícias do setor. Resuma em português de forma estruturada.", \
cron_expression="0 18 * * 5", cron_readable="toda sexta-feira às 18:00"
"""


def is_scheduled_task_intent(text: str) -> bool:
    """Fast regex check before calling the LLM."""
    for pattern in _TASK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


async def _extract(text: str) -> TaskExtraction:
    """Call gpt-4o-mini with structured output to extract task intent."""
    response = await _client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _build_extract_system()},
            {"role": "user", "content": text},
        ],
        response_format=TaskExtraction,
        temperature=0,
    )
    return response.choices[0].message.parsed


def _parse_cron(expression: str) -> CronTrigger:
    """Parse a 5-field cron expression into an APScheduler CronTrigger."""
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 cron fields, got {len(parts)}: {expression}")
    return CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=USER_TIMEZONE,
    )


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


async def _execute_task(phone: str, task_id: str, name: str, prompt: str) -> None:
    """Called by APScheduler: runs the prompt through the agent and sends the result."""
    log.info(f"Executing scheduled task '{name}' (id={task_id}) for {phone}")
    try:
        response = await _client.responses.create(
            model="gpt-5.4",
            instructions=(
                "Você é Aisha, uma assistente pessoal. Execute a tarefa abaixo e "
                "retorne o resultado de forma clara, organizada e em português. "
                "Use a busca web para obter informações atualizadas."
            ),
            input=prompt,
            tools=[{"type": "web_search"}],
        )

        text_parts = [
            content.text
            for item in response.output
            if item.type == "message"
            for content in item.content
            if content.type == "output_text"
        ]
        result_text = "\n".join(text_parts) if text_parts else "Não consegui gerar o relatório desta vez."

        await _send_whatsapp(phone, f"📋 *{name}*\n\n{result_text}")
        log.info(f"Scheduled task '{name}' executed successfully for {phone}")

    except Exception as e:
        log.exception(f"Scheduled task '{name}' failed for {phone}")
        await _send_whatsapp(phone, f"⚠️ A tarefa agendada *{name}* falhou: {e}")


async def _schedule_job(
    task_id: str,
    phone: str,
    name: str,
    prompt: str,
    cron_expression: str,
    scheduler: AsyncScheduler,
) -> str:
    """Schedule the task job and return the APScheduler schedule_id."""
    trigger = _parse_cron(cron_expression)

    schedule_id = await scheduler.add_schedule(
        _execute_task,
        trigger,
        id=task_id,
        kwargs={
            "phone": phone,
            "task_id": task_id,
            "name": name,
            "prompt": prompt,
        },
        misfire_grace_time=timedelta(seconds=300),
    )
    return str(schedule_id)


async def handle_scheduled_task(phone: str, text: str, scheduler: AsyncScheduler) -> str:
    """Main entry point: parse, act, and return a reply message."""
    extraction = await _extract(text)
    action = extraction.action

    if action == "list":
        return await _handle_list(phone)

    if action == "cancel":
        return await _handle_cancel(phone, extraction, scheduler)

    return await _handle_create(phone, extraction, scheduler)


async def _handle_create(
    phone: str, ex: TaskExtraction, scheduler: AsyncScheduler
) -> str:
    if not ex.cron_expression or not ex.prompt:
        return (
            "Não entendi a tarefa. Tente algo como:\n"
            "• _toda segunda me mande um relatório sobre notícias de tecnologia_\n"
            "• _todo dia às 8h me mande o resumo do mercado financeiro_"
        )

    name = ex.name or "Tarefa agendada"
    try:
        _parse_cron(ex.cron_expression)
    except ValueError:
        return f"Não consegui interpretar o agendamento '{ex.cron_readable}'. Tente ser mais específico."

    task = ScheduledTask(
        phone=phone,
        name=name,
        prompt=ex.prompt,
        cron_expression=ex.cron_expression,
        timezone=USER_TIMEZONE,
    )

    task_id = await save_task(task)

    job_id = await _schedule_job(
        task_id=task_id,
        phone=phone,
        name=name,
        prompt=ex.prompt,
        cron_expression=ex.cron_expression,
        scheduler=scheduler,
    )
    await update_job_id(task_id, job_id)

    schedule_display = ex.cron_readable or ex.cron_expression
    return (
        f"✅ Tarefa agendada criada!\n"
        f"📌 *{name}*\n"
        f"🕐 {schedule_display}\n"
        f"📝 _{ex.prompt[:120]}{'...' if len(ex.prompt) > 120 else ''}_\n\n"
        f"Cada vez que disparar, vou executar essa tarefa com busca na web e te enviar o resultado."
    )


async def _handle_list(phone: str) -> str:
    rows = await get_tasks(phone)
    if not rows:
        return (
            "Você não tem tarefas agendadas ativas.\n\n"
            "Para criar, diga algo como:\n"
            "• _toda segunda me mande um relatório sobre notícias de tecnologia_"
        )

    lines = ["📋 *Suas tarefas agendadas:*\n"]
    for i, row in enumerate(rows, 1):
        lines.append(
            f"{i}. *{row['name']}*\n"
            f"   🕐 `{row['cron_expression']}`\n"
            f"   📝 _{row['prompt'][:80]}{'...' if len(row['prompt']) > 80 else ''}_"
        )

    lines.append("\nPara cancelar: _cancela a tarefa agendada 1_")
    return "\n".join(lines)


async def _handle_cancel(
    phone: str, ex: TaskExtraction, scheduler: AsyncScheduler
) -> str:
    rows = await get_tasks(phone)
    if not rows:
        return "Você não tem tarefas agendadas ativas para cancelar."

    idx = (ex.task_number or 1) - 1
    if idx < 0 or idx >= len(rows):
        return f"Tarefa #{idx + 1} não encontrada. Você tem {len(rows)} tarefa(s) ativa(s)."

    row = rows[idx]
    await deactivate_task(row["id"])

    if row.get("job_id"):
        try:
            await scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    return f"✅ Tarefa agendada cancelada: *{row['name']}*"


async def restore_scheduled_jobs(scheduler: AsyncScheduler) -> int:
    """Restore all active scheduled task jobs on startup. Returns count of restored jobs."""
    from aisha.skills.scheduled_task_store import get_all_active_tasks

    tasks = await get_all_active_tasks()
    restored = 0

    for task in tasks:
        try:
            job_id = await _schedule_job(
                task_id=task["id"],
                phone=task["phone"],
                name=task["name"],
                prompt=task["prompt"],
                cron_expression=task["cron_expression"],
                scheduler=scheduler,
            )
            if task.get("job_id") != job_id:
                await update_job_id(task["id"], job_id)
            restored += 1
        except Exception:
            log.exception(f"Failed to restore scheduled task {task['id']}: {task['name']}")

    log.info(f"Restored {restored}/{len(tasks)} scheduled task jobs")
    return restored
