"""Scheduled task skill: create, list, edit and cancel recurring agent actions.

Unlike reminders (which send a fixed text), scheduled tasks execute an
agent prompt with web_search enabled and send the AI-generated result.
Example: "toda segunda me mande um relatório sobre notícias do Irã".
"""

import logging
import re
import unicodedata
from datetime import timedelta
from difflib import SequenceMatcher
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
    update_task,
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
    r"\b(edita[r]?|edite|modifica[r]?|modifique|altera[r]?|altere|troca[r]?|troque|muda[r]?|mude)\b.{0,40}\b(tarefa|task)\b",
]


class TaskExtraction(BaseModel):
    action: Literal["create", "list", "cancel", "edit"]
    name: str | None = Field(None, description="Short name for the task when creating")
    prompt: str | None = Field(None, description="Full prompt/instruction when creating")
    cron_expression: str | None = Field(None, description="Cron expression when creating")
    cron_readable: str | None = Field(None, description="Human-readable schedule when creating")
    task_number: int | None = Field(None, description="1-based index from list for cancel/edit")
    task_reference_text: str | None = Field(None, description="User text that identifies the task, e.g. 'dos versículos'")
    new_name: str | None = Field(None, description="Updated short name when editing")
    new_prompt: str | None = Field(None, description="Updated instruction/prompt when editing")
    new_cron_expression: str | None = Field(None, description="Updated cron expression when editing")
    new_cron_readable: str | None = Field(None, description="Updated human-readable schedule when editing")


def _build_extract_system(user_tz: str) -> str:
    return f"""\
You extract scheduled task actions from user messages.
Current timezone: {user_tz}.

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
For 'edit': user wants to change an existing scheduled task. Extract:
- task_number when user mentions "tarefa 1"
- task_reference_text when user refers to the task by topic/name, e.g. "dos versículos"
- new_prompt when the requested change alters what should be sent
- new_cron_expression and new_cron_readable when the user changes time/frequency
- new_name only if the new task description clearly implies a better short name

Important:
- Requests like "modifique a tarefa agendada..." or "muda a tarefa dos versículos..."
  are EDIT, not help/self-awareness.
- When editing only the content, keep new_cron_expression null.
- When editing only the schedule, keep new_prompt null.

Examples:
- "toda segunda me mande um relatório com as últimas notícias sobre o Irã"
  → action="create", name="Relatório Irã", prompt="Pesquise as últimas notícias sobre o Irã da última semana. \
Faça um relatório conciso em português com os principais acontecimentos, organizado por tema.", \
cron_expression="0 9 * * 1", cron_readable="toda segunda-feira às 09:00"

- "todo dia às 7h me mande o resumo do mercado financeiro"
  → action="create", name="Resumo mercado", prompt="Pesquise o estado atual do mercado financeiro: \
principais índices (Ibovespa, S&P500, Nasdaq), câmbio (dólar, euro), e destaques do dia. \
Resuma de forma objetiva em português.", \
cron_expression="0 7 * * *", cron_readable="todo dia às 07:00"

- "toda sexta às 18h pesquise as novidades de IA da semana e me mande um resumo"
  → action="create", name="Novidades IA", prompt="Pesquise as principais novidades e lançamentos de \
inteligência artificial da última semana. Inclua novos modelos, ferramentas, papers \
relevantes e notícias do setor. Resuma em português de forma estruturada.", \
cron_expression="0 18 * * 5", cron_readable="toda sexta-feira às 18:00"

- "modifique a tarefa agendada dos versículos para incluir um pequeno texto sobre esses versículos"
  → action="edit", task_reference_text="dos versículos", new_prompt="Acesse bibliaonline.com.br e colete os versículos do dia. Envie os versículos em português de forma clara e concisa. Inclua também um pequeno texto explicando ou refletindo sobre os versículos.", new_cron_expression=null

- "muda a tarefa agendada 1 para todo dia às 10h"
  → action="edit", task_number=1, new_cron_expression="0 10 * * *", new_cron_readable="todo dia às 10:00", new_prompt=null
"""


def is_scheduled_task_intent(text: str) -> bool:
    """Fast regex check before calling the LLM."""
    for pattern in _TASK_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


async def _extract(text: str, user_tz: str) -> TaskExtraction:
    """Call gpt-4o-mini with structured output to extract task intent."""
    response = await _client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _build_extract_system(user_tz)},
            {"role": "user", "content": text},
        ],
        response_format=TaskExtraction,
        temperature=0,
    )
    return response.choices[0].message.parsed


def _parse_cron(expression: str, user_tz: str) -> CronTrigger:
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
        timezone=user_tz,
    )


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _resolve_task_reference(rows: list[dict], ex: TaskExtraction) -> tuple[dict | None, str | None]:
    if not rows:
        return None, "Você não tem tarefas agendadas ativas para editar."

    if ex.task_number is not None:
        idx = ex.task_number - 1
        if idx < 0 or idx >= len(rows):
            return None, f"Tarefa #{idx + 1} não encontrada. Você tem {len(rows)} tarefa(s) ativa(s)."
        return rows[idx], None

    reference = _normalize_text(ex.task_reference_text or "")
    if not reference:
        if len(rows) == 1:
            return rows[0], None
        task_list = "\n".join(f"{i}. *{row['name']}*" for i, row in enumerate(rows, 1))
        return None, (
            "Qual tarefa agendada você quer editar?\n\n"
            f"{task_list}\n\n"
            "Você pode dizer, por exemplo: _edita a tarefa agendada 1_"
        )

    ref_tokens = {token for token in reference.split() if len(token) > 2}
    scored_rows: list[tuple[float, dict]] = []
    for row in rows:
        haystack = _normalize_text(f"{row['name']} {row['prompt']}")
        ratio = SequenceMatcher(None, reference, haystack).ratio()
        token_hits = sum(1 for token in ref_tokens if token in haystack)
        token_score = token_hits / max(len(ref_tokens), 1)
        substring_bonus = 0.25 if reference and reference in haystack else 0.0
        scored_rows.append((max(ratio, token_score) + substring_bonus, row))

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    best_score, best_row = scored_rows[0]
    second_score = scored_rows[1][0] if len(scored_rows) > 1 else 0.0

    if best_score < 0.35 or (second_score and best_score - second_score < 0.12):
        task_list = "\n".join(f"{i}. *{row['name']}*" for i, row in enumerate(rows, 1))
        return None, (
            "Encontrei mais de uma tarefa possível ou não consegui identificar com segurança.\n\n"
            f"{task_list}\n\n"
            "Me diga o número da tarefa, por exemplo: _edita a tarefa agendada 1_"
        )

    return best_row, None


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
    user_tz: str,
) -> str:
    """Schedule the task job and return the APScheduler schedule_id."""
    trigger = _parse_cron(cron_expression, user_tz)

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


async def handle_scheduled_task(phone: str, text: str, scheduler: AsyncScheduler, user_tz: str) -> str:
    """Main entry point: parse, act, and return a reply message."""
    extraction = await _extract(text, user_tz)
    action = extraction.action

    if action == "list":
        return await _handle_list(phone)

    if action == "cancel":
        return await _handle_cancel(phone, extraction, scheduler)

    if action == "edit":
        return await _handle_edit(phone, extraction, scheduler, user_tz)

    return await _handle_create(phone, extraction, scheduler, user_tz)


async def _handle_create(
    phone: str, ex: TaskExtraction, scheduler: AsyncScheduler, user_tz: str
) -> str:
    if not ex.cron_expression or not ex.prompt:
        return (
            "Não entendi a tarefa. Tente algo como:\n"
            "• _toda segunda me mande um relatório sobre notícias de tecnologia_\n"
            "• _todo dia às 8h me mande o resumo do mercado financeiro_"
        )

    name = ex.name or "Tarefa agendada"
    try:
        _parse_cron(ex.cron_expression, user_tz)
    except ValueError:
        return f"Não consegui interpretar o agendamento '{ex.cron_readable}'. Tente ser mais específico."

    task = ScheduledTask(
        phone=phone,
        name=name,
        prompt=ex.prompt,
        cron_expression=ex.cron_expression,
        timezone=user_tz,
    )

    task_id = await save_task(task)

    job_id = await _schedule_job(
        task_id=task_id,
        phone=phone,
        name=name,
        prompt=ex.prompt,
        cron_expression=ex.cron_expression,
        scheduler=scheduler,
        user_tz=user_tz,
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
    lines.append("Para editar: _edita a tarefa agendada 1 para todo dia às 10h_")
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


async def _handle_edit(
    phone: str, ex: TaskExtraction, scheduler: AsyncScheduler, user_tz: str
) -> str:
    rows = await get_tasks(phone)
    row, error = _resolve_task_reference(rows, ex)
    if error:
        return error
    assert row is not None

    new_name = ex.new_name or row["name"]
    new_prompt = ex.new_prompt or row["prompt"]
    new_cron_expression = ex.new_cron_expression or row["cron_expression"]
    effective_tz = row.get("timezone") or user_tz

    changed_fields: dict[str, str] = {}
    if new_name != row["name"]:
        changed_fields["name"] = new_name
    if new_prompt != row["prompt"]:
        changed_fields["prompt"] = new_prompt
    if new_cron_expression != row["cron_expression"]:
        try:
            _parse_cron(new_cron_expression, effective_tz)
        except ValueError:
            schedule_label = ex.new_cron_readable or new_cron_expression
            return f"Não consegui interpretar o novo agendamento '{schedule_label}'. Tente ser mais específico."
        changed_fields["cron_expression"] = new_cron_expression

    if not changed_fields:
        return (
            "Não identifiquei o que você quer mudar nessa tarefa.\n\n"
            "Você pode alterar o conteúdo, o horário ou ambos. Exemplo:\n"
            "• _edita a tarefa agendada 1 para incluir uma breve reflexão_\n"
            "• _muda a tarefa agendada 1 para todo dia às 10h_"
        )

    if row.get("job_id"):
        try:
            await scheduler.remove_schedule(row["job_id"])
        except Exception:
            pass

    await update_task(row["id"], **changed_fields)

    job_id = await _schedule_job(
        task_id=row["id"],
        phone=phone,
        name=new_name,
        prompt=new_prompt,
        cron_expression=new_cron_expression,
        scheduler=scheduler,
        user_tz=effective_tz,
    )
    await update_job_id(row["id"], job_id)

    schedule_display = ex.new_cron_readable or new_cron_expression
    return (
        f"✅ Tarefa agendada atualizada!\n"
        f"📌 *{new_name}*\n"
        f"🕐 {schedule_display}\n"
        f"📝 _{new_prompt[:120]}{'...' if len(new_prompt) > 120 else ''}_"
    )


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
                user_tz=task.get("timezone") or USER_TIMEZONE,
            )
            if task.get("job_id") != job_id:
                await update_job_id(task["id"], job_id)
            restored += 1
        except Exception:
            log.exception(f"Failed to restore scheduled task {task['id']}: {task['name']}")

    log.info(f"Restored {restored}/{len(tasks)} scheduled task jobs")
    return restored
