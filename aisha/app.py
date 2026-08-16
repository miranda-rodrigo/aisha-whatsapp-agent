import asyncio
import base64
import hashlib
import hmac
import json
import logging
import logging.handlers
import re
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import create_async_engine

from aisha.skills.chat import chat_with_webpage, classify, classify_pending_response, wants_new_session
from aisha.config import (
    ALLOWED_NUMBERS,
    BASE_URL,
    DATABASE_PASSWORD,
    GRAPH_API_URL,
    SUPABASE_URL,
    WEBHOOK_VERIFY_TOKEN,
    WHATSAPP_APP_SECRET,
    WHATSAPP_TOKEN,
)
from aisha.messaging import split_whatsapp_text, typing_indicator_payload
from aisha.supabase_http import aclose as aclose_supabase_client
from aisha.models import EXTRACT_MODEL
from aisha.routing import (
    contains_aisha as _contains_aisha,
    is_download_intent as _is_download_intent,
    is_retroactive_transcription_request as _is_retroactive_transcription_request,
    is_transcription_request as _is_transcription_request,
    is_trivial_message,
    parse_page_selection as _parse_page_selection,
    strip_aisha as _strip_aisha,
)
from aisha.skills.pending_store import (
    clear_all_pending,
    list_active_pendings,
    upsert_pending,
)
from aisha.skills.document import (
    extract_text_async,
    extract_scanned_pages,
    get_pdf_info,
    is_supported_document,
    MAX_DOCUMENT_SIZE,
    MAX_SCANNED_PAGES,
)
from aisha.skills.document_state import (
    clear_pending_document,
    get_pending_document,
    get_pending_document_async,
    mark_pending_document_meta,
    store_pending_document,
)
from aisha.skills.image_state import (
    clear_pending_image,
    get_pending_image,
    get_pending_image_async,
    mark_pending_image_meta,
    store_pending_image,
)
from aisha.skills.refine import refine_transcription
from aisha.skills.raw_transcription_state import (
    pop_raw_transcription,
    pop_raw_transcription_async,
    store_raw_transcription,
)
from aisha.skills.reminder import handle_reminder
from aisha.skills.scheduled_task import handle_scheduled_task, restore_scheduled_jobs
from aisha.session import delete_session, get_response_id, upsert_session
from aisha.skills.timezone_inference import infer_timezone
from aisha.skills.transcribe import transcribe_audio_bytes
from aisha.user_profile import get_profile, increment_stat, upsert_timezone
from aisha.skills.youtube import (
    VideoAnalysis,
    analyze_video,
    clear_pending_video,
    extract_youtube_url,
    get_pending_video,
    pop_pending_transcript,
    store_pending_video,
    strip_youtube_url,
)
from aisha.skills.video_download import (
    cleanup_expired,
    download_video,
    get_download_entry,
)
from aisha.skills.webpage import (
    clear_pending_page,
    fetch_page,
    get_pending_page,
)

_log_handlers: list[logging.Handler] = [logging.StreamHandler()]
_log_dir = Path(__file__).parents[1] / "logs"
if _log_dir.exists():
    _log_handlers.append(
        logging.handlers.RotatingFileHandler(
            _log_dir / "aisha.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_log_handlers,
)
log = logging.getLogger(__name__)

http_client: httpx.AsyncClient
scheduler: AsyncScheduler
_background_tasks: set[asyncio.Task] = set()
LONG_TRANSCRIPTION_WORD_LIMIT = 500
TRANSCRIPTION_PREVIEW_WORDS = 60


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _verify_signature(raw_body: bytes, header: str | None) -> bool:
    if not WHATSAPP_APP_SECRET:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(
        WHATSAPP_APP_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(header[7:], expected)

# --- Deduplication with TTL (Layer 5) ---
_processed_messages: OrderedDict[str, float] = OrderedDict()
_DEDUP_TTL_SECONDS = 300

def _is_duplicate(msg_id: str) -> bool:
    now = time.time()
    while _processed_messages:
        oldest_id, oldest_time = next(iter(_processed_messages.items()))
        if now - oldest_time > _DEDUP_TTL_SECONDS:
            _processed_messages.pop(oldest_id)
        else:
            break
    if msg_id in _processed_messages:
        return True
    _processed_messages[msg_id] = now
    return False

# --- Temporal echo detection (Layer 4) ---
_last_reply_time: dict[str, float] = {}

# --- Processing lock per user (Layer 6) ---
_processing: set[str] = set()  # phones currently being processed by the agent

_project_ref = SUPABASE_URL.replace("https://", "").split(".")[0]
_DB_URL = (
    f"postgresql+asyncpg://postgres.{_project_ref}:{DATABASE_PASSWORD}"
    f"@aws-0-us-west-2.pooler.supabase.com:6543/postgres"
)


_LAST_REPLY_TTL_SECONDS = 60  # só precisamos de ~5s para echo detection; 60s é folga segura

async def _periodic_download_cleanup():
    """Background task: remove expired temporary video files and stale echo-detection entries every 15 minutes."""
    while True:
        await asyncio.sleep(15 * 60)
        removed = cleanup_expired()
        if removed:
            log.info(f"Cleaned up {removed} expired download(s)")
        cutoff = time.time() - _LAST_REPLY_TTL_SECONDS
        stale = [k for k, v in _last_reply_time.items() if v < cutoff]
        for k in stale:
            del _last_reply_time[k]
        if stale:
            log.info(f"Cleaned up {len(stale)} stale echo-detection entr{'y' if len(stale) == 1 else 'ies'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client, scheduler

    http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=60.0,
    )

    cleanup_task = asyncio.create_task(_periodic_download_cleanup())

    engine = create_async_engine(
        _DB_URL,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    data_store = SQLAlchemyDataStore(engine)
    async with AsyncScheduler(data_store=data_store) as sched:
        scheduler = sched
        await sched.start_in_background()
        log.info("APScheduler started")

        async def _restore_jobs():
            try:
                restored = await restore_scheduled_jobs(sched)
                log.info(f"Restored {restored} scheduled task(s)")
            except Exception:
                log.exception("Failed to restore scheduled jobs")

        _spawn(_restore_jobs())
        log.info("WhatsApp agent started")
        yield

    cleanup_task.cancel()
    await http_client.aclose()
    await aclose_supabase_client()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """Liveness probe for Railway / keep-alive. Does not wait on the scheduler."""
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta sends a GET to verify the webhook on setup."""
    if hub_mode == "subscribe" and hub_verify_token == WEBHOOK_VERIFY_TOKEN:
        log.info("Webhook verified")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    log.warning("Webhook verification failed: bad token")
    return {"error": "invalid verify token"}, 403


@app.get("/download/{token}")
async def serve_download(token: str):
    """Serves a temporary video file previously downloaded by the video_download skill."""
    entry = get_download_entry(token)
    if not entry:
        raise HTTPException(status_code=404, detail="Link expirado ou não encontrado.")
    if not entry.filepath.exists():
        raise HTTPException(status_code=410, detail="Arquivo não está mais disponível.")
    return FileResponse(
        path=entry.filepath,
        filename=entry.filename,
        media_type=entry.media_type or "application/octet-stream",
    )


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receives incoming message notifications from Meta. ACKs immediately."""
    raw = await request.body()
    if not _verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        log.warning("Webhook signature verification failed")
        raise HTTPException(status_code=403, detail="invalid signature")

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "invalid json"}

    log.info("Webhook payload received")
    _spawn(_process_webhook(body))
    return {"status": "ok"}


async def _process_webhook(body: dict) -> None:
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")
        if not messages:
            return
        message = messages[0]
    except (KeyError, IndexError):
        return

    contacts = value.get("contacts")
    if not contacts:
        log.warning(
            f"Webhook without contacts field — possible phantom: "
            f"{json.dumps(body, ensure_ascii=False)[:500]}"
        )

    metadata = value.get("metadata", {})
    bot_phone = metadata.get("display_phone_number", "").replace("+", "")
    sender = message.get("from", "")
    if sender and bot_phone and sender == bot_phone:
        log.info(f"Ignoring own message echo from bot number {sender}")
        return

    msg_id = message.get("id", "")
    if _is_duplicate(msg_id):
        log.info(f"Duplicate message {msg_id}, skipping")
        return

    msg_type = message.get("type", "")
    text_preview = ""
    if msg_type == "text":
        text_preview = message.get("text", {}).get("body", "")
    log.info(
        f"Message from {sender}, type={msg_type}, id={msg_id}, "
        f"text={text_preview[:100]!r}"
    )

    last_reply = _last_reply_time.get(sender, 0)
    gap = time.time() - last_reply
    if last_reply and gap < 5.0:
        log.warning(
            f"Message from {sender} arrived {gap:.1f}s after bot reply "
            f"— possible echo: {text_preview[:80]!r}"
        )

    if sender not in ALLOWED_NUMBERS:
        log.info(f"Ignored: {sender} not in allowed list")
        return

    _spawn(send_typing(msg_id))

    try:
        if msg_type == "audio":
            await handle_audio(sender, message)
        elif msg_type == "text":
            text = message.get("text", {}).get("body", "")
            await handle_chat(sender, text, msg_id)
        elif msg_type == "image":
            await handle_image(sender, message)
        elif msg_type == "document":
            await handle_document(sender, message)
        else:
            await send_message(sender, f"Tipo '{msg_type}' ainda não suportado.")
    except Exception:
        log.exception(f"Failed to process {msg_type} from {sender}")
        try:
            await send_message(sender, "Erro ao processar sua mensagem. Tente de novo.")
        except Exception:
            log.exception("Failed to send error message")


# phone -> original reminder text awaiting timezone confirmation
_pending_timezone: dict[str, str] = {}

_TZ_RESOLVE_SYSTEM = """\
Extract the IANA timezone identifier from a city or country name.
Return ONLY the IANA timezone string (e.g. "America/Sao_Paulo", "Europe/Lisbon").
If you cannot determine it, return the string "unknown".
Do not include any explanation."""


async def _resolve_tz_from_text(text: str) -> str | None:
    """Ask the LLM to resolve a city/country name to an IANA timezone. Returns None if unresolvable."""
    from openai import AsyncOpenAI
    from aisha.config import OPENAI_API_KEY
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model=EXTRACT_MODEL,
        messages=[
            {"role": "system", "content": _TZ_RESOLVE_SYSTEM},
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=30,
    )
    result = resp.choices[0].message.content.strip()
    return None if result.lower() == "unknown" else result


async def get_or_ask_timezone(
    sender: str, reminder_text: str
) -> str | None:
    """Return the user's timezone if known, otherwise ask and return None.

    Lookup order:
    1. Supabase profile (already confirmed/saved)
    2. Infer from phone number DDD/DDI (saves automatically if confident)
    3. Ask the user — stores reminder_text in _pending_timezone so we can retry after answer
    """
    from aisha.config import USER_TIMEZONE

    profile = await get_profile(sender)
    if profile and profile.get("timezone"):
        return profile["timezone"]

    inferred = infer_timezone(sender)
    if inferred:
        await upsert_timezone(sender, inferred)
        log.info(f"Timezone inferred for {sender}: {inferred}")
        return inferred

    # Cannot determine — ask the user and park the reminder text
    _pending_timezone[sender] = reminder_text
    _spawn(upsert_pending(sender, "timezone", {"reminder_text": reminder_text}, 600))
    return None


def _tz_question_message(inferred: str | None = None) -> str:
    if inferred:
        return (
            f"📍 Para criar lembretes com o horário certo, preciso saber onde você está.\n\n"
            f"Detectei que você pode estar em *{inferred}* — está correto?\n"
            f"Se sim, diga \"sim\". Se não, me diga sua cidade ou país."
        )
    return (
        "📍 Para criar lembretes com o horário certo, preciso saber onde você está.\n\n"
        "Me diz sua cidade ou país (ex: \"São Paulo\", \"Lisboa\", \"New York\")."
    )


def _get_pending_description(sender: str) -> str | None:
    """Return a human-readable description of the active pending state, or None."""
    if sender in _pending_timezone:
        return "Aguardando o fuso horário do usuário (cidade ou país)"
    if get_pending_document(sender):
        return "Aguardando seleção de páginas do PDF escaneado"
    if get_pending_image(sender):
        return "Aguardando instrução sobre a imagem enviada"
    pending_yt = get_pending_video(sender)
    if pending_yt:
        return f"Aguardando instrução sobre o vídeo do YouTube: {pending_yt.url}"
    pending_page = get_pending_page(sender)
    if pending_page:
        return f"Aguardando instrução sobre a página web: {pending_page.url}"
    return None


def _clear_all_pendings(sender: str) -> None:
    """Remove every pending state for a sender."""
    _pending_timezone.pop(sender, None)
    clear_pending_image(sender)
    clear_pending_video(sender)
    clear_pending_page(sender)
    clear_pending_document(sender)
    _spawn(clear_all_pending(sender))


async def _execute_pending(sender: str, text: str) -> bool:
    """Execute the active pending action with the user's reply. Returns True if handled."""
    # Timezone confirmation
    if sender in _pending_timezone:
        original_text = _pending_timezone.pop(sender)
        tz = await _resolve_tz_from_text(text)
        if tz:
            await upsert_timezone(sender, tz)
            log.info(f"Timezone confirmed for {sender}: {tz}")
            original_intent = await classify(original_text)
            if original_intent == "SCHEDULED_TASK":
                reply = await handle_scheduled_task(sender, original_text, scheduler, tz)
                if "✅ Tarefa agendada criada" in reply:
                    await increment_stat(sender, "scheduled_tasks_created")
            else:
                reply = await handle_reminder(sender, original_text, scheduler, tz)
                if "✅ Lembrete criado" in reply:
                    await increment_stat(sender, "reminders_created")
            await send_message(sender, reply)
        else:
            await send_message(
                sender,
                "Não consegui identificar o fuso horário. "
                "Pode me dizer sua cidade ou país? Ex: \"São Paulo\", \"Lisboa\", \"New York\"."
            )
            _pending_timezone[sender] = original_text
        return True

    # Scanned document — page selection
    pending_doc = await get_pending_document_async(sender)
    if pending_doc:
        log.info(f"Pending scanned PDF for {sender} — parsing page selection: {text[:60]}")
        await _process_document_pages(sender, text, pending_doc)
        return True

    # Image instruction
    pending_img = await get_pending_image_async(sender)
    if pending_img:
        log.info(f"Pending image for {sender} — using text as instruction")
        await _process_image_instruction(sender, text, pending_img)
        return True

    # YouTube video instruction
    pending_yt = get_pending_video(sender)
    if pending_yt:
        log.info(f"Pending YouTube for {sender} — instruction: {text[:60]}")
        clear_pending_video(sender)
        if _is_download_intent(text):
            await send_message(sender, "⏳ Baixando vídeo...")
            try:
                token, filename = await download_video(pending_yt.url)
                link = f"{BASE_URL}/download/{token}"
                await send_message(
                    sender,
                    f"✅ *{filename}*\n\n"
                    f"🔗 Link de download (expira em 30 min):\n{link}",
                )
                await increment_stat(sender, "video_downloads")
            except Exception as exc:
                log.exception("Video download failed")
                await send_message(sender, f"Não consegui baixar o vídeo: {exc}")
        else:
            await send_message(sender, "⏳ Analisando vídeo...")
            await increment_stat(sender, "youtube")
            analysis = await analyze_video(pending_yt.url, text)
            await _deliver_video_analysis(sender, analysis)
        return True

    # Webpage instruction
    pending_page = get_pending_page(sender)
    if pending_page:
        log.info(f"Pending webpage for {sender} — processing with instruction: {text[:60]}")
        clear_pending_page(sender)
        await send_message(sender, "⏳ Lendo página...")
        await increment_stat(sender, "webpages")
        try:
            content = await fetch_page(pending_page.url)
            prev_id = await get_response_id(sender)
            result = await chat_with_webpage(content, pending_page.url, text, prev_id)
            if result.response_id:
                await upsert_session(sender, result.response_id)
            if result.text:
                await send_message(sender, result.text)
        except Exception as e:
            log.exception("Webpage processing failed")
            await send_message(sender, f"Não consegui acessar a página: {e}")
        return True

    return False


async def _hydrate_pendings(sender: str) -> None:
    """Restore pending metadata from Supabase after a redeploy.

    One request, no blobs. Image/PDF bytes are fetched only when the
    pending action actually runs.
    """
    if (
        sender in _pending_timezone
        or get_pending_image(sender)
        or get_pending_document(sender)
        or get_pending_video(sender)
        or get_pending_page(sender)
    ):
        return

    rows = await list_active_pendings(sender)
    for row in rows:
        kind = row.get("kind")
        payload = row.get("payload") or {}
        if kind == "timezone":
            original = payload.get("reminder_text")
            if original:
                _pending_timezone[sender] = original
        elif kind == "image":
            mark_pending_image_meta(sender, payload.get("mime_type", "image/jpeg"))
        elif kind == "document":
            mark_pending_document_meta(sender, payload)
        elif kind == "youtube":
            url = payload.get("url")
            if url:
                from aisha.skills.youtube import store_pending_video
                store_pending_video(sender, url, persist=False)
        elif kind == "webpage":
            url = payload.get("url")
            if url:
                from aisha.skills.webpage import store_pending_page
                store_pending_page(sender, url, persist=False)


async def handle_chat(sender: str, text: str, msg_id: str = ""):
    """Routes a text message through pending states or the agentic loop."""
    from aisha.agent import run_agent, run_fast_path

    if sender in _processing:
        log.info(f"User {sender} sent message while agent is busy — replying with wait message")
        await send_message(
            sender,
            "⏳ Ainda estou processando sua mensagem anterior. Aguarde um momento, por favor!",
        )
        return

    _processing.add(sender)
    try:
        if _is_retroactive_transcription_request(text):
            raw = await pop_raw_transcription_async(sender)
            if raw:
                log.info(f"Retroactive transcription request for {sender}")
                await _send_refined_transcription(sender, raw)
                return

        youtube_url = extract_youtube_url(text)
        if youtube_url:
            instruction = strip_youtube_url(text).strip("\\ \n\t")
            if not instruction:
                store_pending_video(sender, youtube_url)
                await send_message(
                    sender,
                    "O que você quer que eu faça com esse vídeo? "
                    "Posso transcrever, resumir ou listar os pontos principais.",
                )
                return

            clear_pending_video(sender)
            await send_message(sender, "⏳ Analisando vídeo...")
            await increment_stat(sender, "youtube")
            analysis = await analyze_video(youtube_url, instruction)
            await _deliver_video_analysis(sender, analysis)
            return

        ack_task = asyncio.create_task(send_message(sender, "⏳ Processando..."))
        try:
            await _hydrate_pendings(sender)
        finally:
            try:
                await ack_task
            except Exception:
                log.warning("Failed to send processing ack", exc_info=True)
        pending_desc = _get_pending_description(sender)
        if pending_desc:
            decision = await classify_pending_response(text, pending_desc)
            log.info(f"Pending triage for {sender}: {decision} (pending={pending_desc[:60]})")
            if decision == "CANCEL":
                _clear_all_pendings(sender)
                await send_message(
                    sender,
                    "Sem problema! Pode ignorar a mensagem anterior.\n\n"
                    "Se precisar de algo, é só falar.",
                )
                return
            if decision == "NEW_INTENT":
                _clear_all_pendings(sender)
            elif decision == "CONTINUE":
                if await _execute_pending(sender, text):
                    return

        if wants_new_session(text):
            await delete_session(sender)
            log.info(f"Session reset requested by {sender}")

        if msg_id:
            _spawn(send_typing(msg_id))
        prev_id = await get_response_id(sender)

        if is_trivial_message(text):
            result = await run_fast_path(text, previous_response_id=prev_id, phone=sender)
        else:
            result = await run_agent(
                user_input=text,
                previous_response_id=prev_id,
                phone=sender,
                scheduler=scheduler,
            )

        await _deliver_agent_result(sender, result)

    except Exception as e:
        log.exception("Agentic chat failed")
        await send_message(sender, f"Erro no chat: {e}")
    finally:
        _processing.discard(sender)


async def _send_refined_transcription(sender: str, raw_text: str) -> None:
    refined_text = await refine_transcription(raw_text)
    words = refined_text.split()
    word_count = len(words)
    log.info(
        f"Refined transcription: {len(refined_text)} chars, {word_count} words"
    )

    if word_count > LONG_TRANSCRIPTION_WORD_LIMIT:
        preview = " ".join(words[:TRANSCRIPTION_PREVIEW_WORDS])
        if word_count > TRANSCRIPTION_PREVIEW_WORDS:
            preview += "…"
        await send_message(
            sender,
            f"📝 Transcrição longa ({word_count} palavras).\n\n"
            f"*Prévia:* {preview}\n\n"
            "A transcrição completa está no arquivo .txt abaixo.",
        )
        await send_text_document(
            sender,
            refined_text,
            filename="transcricao-aisha.txt",
            caption="Transcrição completa",
        )
        return

    await send_message(sender, "📝 Transcrição:")
    await send_message(sender, refined_text)


async def handle_audio(sender: str, message: dict):
    """Downloads audio, transcribes it, and routes to chat or transcription.

    Routing rules:
    1. Pending image → use audio as instruction (unchanged).
    2. Explicit transcription request ("Aisha, transcreva...") → refine and return.
    3. New session (no active context) AND no 'Aisha' keyword → user wants a transcript.
    4. Active session AND no 'Aisha' keyword → route to chat (person is talking TO Aisha).
    5. 'Aisha' keyword present but not a transcription request → strip name and chat.
    """
    audio_id = message["audio"]["id"]
    log.info(f"Downloading audio {audio_id}")
    await send_message(sender, "⏳ Processando áudio...")

    media_resp = await http_client.get(f"https://graph.facebook.com/v22.0/{audio_id}")
    media_resp.raise_for_status()
    media_url = media_resp.json()["url"]

    audio_resp = await http_client.get(media_url)
    audio_resp.raise_for_status()
    audio_bytes = audio_resp.content
    mime_type = message["audio"].get("mime_type", "audio/ogg")

    log.info(f"Audio downloaded: {len(audio_bytes)} bytes, mime={mime_type}")
    await increment_stat(sender, "audios")

    try:
        raw_text = await transcribe_audio_bytes(audio_bytes, mime_type)
        log.info(f"Raw transcription: {len(raw_text)} chars")

        # Rule 1: pending image — use audio as instruction
        pending = await get_pending_image_async(sender)
        if pending:
            log.info(f"Pending image found for {sender} — using audio as instruction")
            await _process_image_instruction(sender, raw_text, pending)
            return

        # Rule 2: explicit transcription request ("Aisha, transcreva ...")
        if _is_transcription_request(raw_text):
            log.info("Explicit transcription request detected — refining")
            user_text = re.sub(
                r"\baisha\b.{0,40}\bTranscreva\b[,\s]*",
                "",
                raw_text,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            ).strip()
            store_raw_transcription(sender, user_text)
            await _send_refined_transcription(sender, user_text)
            return

        has_aisha = _contains_aisha(raw_text)

        # Rule 3: new session AND no 'Aisha' → person wants a transcript
        prev_id = await get_response_id(sender)
        is_new_session = prev_id is None

        if is_new_session and not has_aisha:
            log.info("New session, no Aisha keyword — routing to transcription refinement")
            store_raw_transcription(sender, raw_text)
            await _send_refined_transcription(sender, raw_text)
            return

        # Rule 4 & 5: active session OR has 'Aisha' → chat
        user_input = _strip_aisha(raw_text) if has_aisha else raw_text
        log.info(f"Routing to chat (new_session={is_new_session}, has_aisha={has_aisha})")
        store_raw_transcription(sender, raw_text)

        from aisha.agent import run_agent
        _processing.add(sender)
        try:
            result = await run_agent(
                user_input=user_input,
                previous_response_id=prev_id,
                phone=sender,
                scheduler=scheduler,
            )
        finally:
            _processing.discard(sender)

        await _deliver_agent_result(sender, result)
    except Exception as e:
        log.exception("Audio processing failed")
        await send_message(sender, f"Erro ao processar áudio: {e}")


async def handle_image(sender: str, message: dict):
    """Downloads an image from WhatsApp and stores it awaiting user instructions."""
    image_id = message["image"]["id"]
    mime_type = message["image"].get("mime_type", "image/jpeg")
    log.info(f"Downloading image {image_id}")
    await send_message(sender, "⏳ Processando imagem...")

    try:
        media_resp = await http_client.get(
            f"https://graph.facebook.com/v22.0/{image_id}"
        )
        media_resp.raise_for_status()
        media_url = media_resp.json()["url"]

        image_resp = await http_client.get(media_url)
        image_resp.raise_for_status()
        image_bytes = image_resp.content

        log.info(f"Image downloaded: {len(image_bytes)} bytes, mime={mime_type}")

        max_size = 50 * 1024 * 1024  # 50 MB (GPT-image-1.5 limit)
        if len(image_bytes) > max_size:
            await send_message(
                sender,
                "A imagem é muito grande (máx. 50 MB). Envie uma imagem menor.",
            )
            return

        store_pending_image(sender, image_bytes, mime_type)
        await increment_stat(sender, "images")

        caption = message["image"].get("caption", "").strip()
        instruction = caption or (
            "O usuário enviou esta imagem sem instrução. "
            "Pergunte o que deseja fazer com ela."
        )
        pending = get_pending_image(sender)
        if pending:
            await _process_image_instruction(sender, instruction, pending, ack=False)
    except Exception as e:
        log.exception("Image handling failed")
        await send_message(sender, f"Erro ao processar imagem: {e}")


async def handle_document(sender: str, message: dict):
    """Downloads a document from WhatsApp, extracts text, and summarizes it."""
    doc = message["document"]
    doc_id = doc["id"]
    mime_type = doc.get("mime_type", "")
    filename = doc.get("filename", "document")
    log.info(f"Document received: {filename} ({mime_type}), id={doc_id}")

    try:
        if not is_supported_document(mime_type):
            await send_message(
                sender,
                f"Formato não suportado: _{filename}_\n\n"
                "Formatos aceitos: *PDF* e *Word (.docx)*",
            )
            return

        await send_message(sender, "📄 Processando documento...")

        media_resp = await http_client.get(
            f"https://graph.facebook.com/v22.0/{doc_id}"
        )
        media_resp.raise_for_status()
        media_url = media_resp.json()["url"]

        doc_resp = await http_client.get(media_url)
        doc_resp.raise_for_status()
        doc_bytes = doc_resp.content

        log.info(f"Document downloaded: {len(doc_bytes)} bytes")

        if len(doc_bytes) > MAX_DOCUMENT_SIZE:
            await send_message(
                sender,
                "O documento é muito grande (máx. 50 MB). Envie um arquivo menor.",
            )
            return

        await increment_stat(sender, "documents")

        # For scanned PDFs over the page limit, ask which pages the user wants
        if mime_type == "application/pdf":
            is_scanned, total_pages = await asyncio.to_thread(get_pdf_info, doc_bytes)
            if is_scanned and total_pages > MAX_SCANNED_PAGES:
                caption = doc.get("caption", "").strip()
                store_pending_document(sender, doc_bytes, total_pages, caption or None)
                await send_message(
                    sender,
                    f"📄 Este PDF escaneado tem *{total_pages} páginas*.\n\n"
                    f"O limite por análise é de *{MAX_SCANNED_PAGES} páginas*.\n\n"
                    f"Quais páginas você quer analisar?\n"
                    f"Exemplos: _\"páginas 1 a 5\"_, _\"página 3\"_, _\"páginas 2, 4 e 7\"_",
                )
                return

        document_text = await extract_text_async(doc_bytes, mime_type)
        log.info(f"Text extracted: {len(document_text)} chars from {filename}")

        if not document_text.strip():
            await send_message(
                sender,
                "Não consegui extrair texto deste documento. "
                "Ele pode estar protegido por senha ou corrompido.",
            )
            return

        caption = doc.get("caption", "").strip()
        await _run_document_agent(sender, document_text, caption or None)

    except Exception as e:
        log.exception("Document processing failed")
        await send_message(sender, f"Erro ao processar documento: {e}")


async def _deliver_agent_result(sender: str, result) -> None:
    if result.response_id:
        await upsert_session(sender, result.response_id)
    if result.image_bytes:
        await send_image(sender, result.image_bytes)
    if result.text:
        await send_message(sender, result.text)
    if getattr(result, "tools_called", None):
        for tool_name in result.tools_called:
            await increment_stat(sender, f"tool_{tool_name}")
        if "analyze_youtube_video" in result.tools_called:
            pending = pop_pending_transcript(sender)
            if pending:
                await _send_analysis_document(sender, pending)


async def _deliver_video_analysis(sender: str, analysis: VideoAnalysis) -> None:
    await send_message(sender, analysis.text)
    await _send_analysis_document(sender, analysis)


async def _send_analysis_document(sender: str, analysis: VideoAnalysis) -> None:
    if not analysis.download_token:
        return
    entry = get_download_entry(analysis.download_token)
    if not entry or not entry.filepath.exists():
        return
    try:
        await send_document(
            sender,
            entry.filepath.read_bytes(),
            entry.filename,
            entry.media_type or "text/plain",
        )
    except Exception:
        log.exception("Failed to send transcript as WhatsApp document")


async def _run_document_agent(sender: str, document_text: str, instruction: str | None) -> None:
    from aisha.agent import run_agent

    user_message = f"DOCUMENTO:\n\n{document_text}"
    if instruction:
        user_message = f"INSTRUÇÃO: {instruction}\n\n{user_message}"
    prev_id = await get_response_id(sender)
    result = await run_agent(
        user_input=user_message,
        previous_response_id=prev_id,
        phone=sender,
        scheduler=scheduler,
    )
    await _deliver_agent_result(sender, result)


async def _process_document_pages(sender: str, text: str, pending):
    """Parse the user's page selection, run vision OCR and send the result."""
    clear_pending_document(sender)

    page_indices = _parse_page_selection(text, pending.total_pages)
    if not page_indices:
        await send_message(
            sender,
            "Não entendi quais páginas você quer. "
            "Me diga assim: _\"páginas 1 a 5\"_, _\"página 3\"_ ou _\"páginas 2, 4 e 7\"_.",
        )
        store_pending_document(sender, pending.pdf_bytes, pending.total_pages, pending.caption)
        return

    page_display = ", ".join(str(i + 1) for i in page_indices)
    await send_message(sender, f"📄 Processando páginas {page_display}...")

    document_text = await extract_scanned_pages(pending.pdf_bytes, page_indices)
    if not document_text.strip():
        await send_message(sender, "Não consegui extrair texto dessas páginas.")
        return

    await _run_document_agent(sender, document_text, pending.caption)


async def _process_image_instruction(sender: str, instruction: str, pending, ack: bool = True):
    """Sends the pending image + instruction to the agent and delivers the result."""
    from aisha.agent import run_agent

    clear_pending_image(sender)
    if ack:
        await send_message(sender, "⏳ Processando imagem...")

    b64 = base64.b64encode(pending.image_bytes).decode()
    multimodal_input = [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": f"data:{pending.mime_type};base64,{b64}",
                },
                {"type": "input_text", "text": instruction},
            ],
        }
    ]
    prev_id = await get_response_id(sender)
    result = await run_agent(
        user_input=multimodal_input,
        previous_response_id=prev_id,
        phone=sender,
        scheduler=scheduler,
    )
    await _deliver_agent_result(sender, result)


async def send_typing(message_id: str) -> None:
    """Marks the inbound message as read and shows the WhatsApp typing indicator."""
    if not message_id:
        return
    try:
        resp = await http_client.post(
            f"{GRAPH_API_URL}/messages",
            json=typing_indicator_payload(message_id),
        )
        log.info(f"Typing indicator sent: status={resp.status_code}")
        if resp.status_code != 200:
            log.warning(f"Typing indicator failed: {resp.text[:200]}")
    except Exception:
        log.warning("Failed to send typing indicator", exc_info=True)


async def send_message(to: str, text: str):
    """Sends a text message via WhatsApp Cloud API, dividindo se passar de 4096 chars."""
    for chunk in split_whatsapp_text(text):
        resp = await http_client.post(
            f"{GRAPH_API_URL}/messages",
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": chunk},
            },
        )
        _last_reply_time[to] = time.time()
        log.info(f"Message sent to {to}: status={resp.status_code}")
        if resp.status_code != 200:
            log.error(f"Send failed: {resp.text}")


async def send_document(to: str, file_bytes: bytes, filename: str, mime_type: str = "text/plain"):
    """Uploads a document to Meta and sends it via WhatsApp Cloud API."""
    upload_resp = await http_client.post(
        f"{GRAPH_API_URL}/media",
        data={"messaging_product": "whatsapp", "type": mime_type},
        files={"file": (filename, file_bytes, mime_type)},
    )
    upload_resp.raise_for_status()
    media_id = upload_resp.json()["id"]
    log.info(f"Document uploaded: media_id={media_id} filename={filename}")

    resp = await http_client.post(
        f"{GRAPH_API_URL}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"id": media_id, "filename": filename},
        },
    )
    _last_reply_time[to] = time.time()
    log.info(f"Document sent to {to}: status={resp.status_code}")
    if resp.status_code != 200:
        log.error(f"Document send failed: {resp.text}")


async def send_image(to: str, image_bytes: bytes, caption: str = ""):
    """Uploads an image to Meta and sends it via WhatsApp Cloud API."""
    upload_resp = await http_client.post(
        f"{GRAPH_API_URL}/media",
        data={"messaging_product": "whatsapp", "type": "image/png"},
        files={"file": ("image.png", image_bytes, "image/png")},
    )
    upload_resp.raise_for_status()
    media_id = upload_resp.json()["id"]
    log.info(f"Image uploaded: media_id={media_id}")

    payload: dict = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"id": media_id},
    }
    if caption:
        payload["image"]["caption"] = caption

    resp = await http_client.post(f"{GRAPH_API_URL}/messages", json=payload)
    _last_reply_time[to] = time.time()
    log.info(f"Image sent to {to}: status={resp.status_code}")
    if resp.status_code != 200:
        log.error(f"Image send failed: {resp.text}")


async def send_text_document(
    to: str,
    text: str,
    filename: str = "transcricao.txt",
    caption: str = "",
):
    """Uploads UTF-8 text and sends it as a WhatsApp document."""
    text_bytes = text.encode("utf-8")
    upload_resp = await http_client.post(
        f"{GRAPH_API_URL}/media",
        data={"messaging_product": "whatsapp", "type": "text/plain"},
        files={"file": (filename, text_bytes, "text/plain")},
    )
    upload_resp.raise_for_status()
    media_id = upload_resp.json()["id"]
    log.info(f"Text document uploaded: media_id={media_id}, bytes={len(text_bytes)}")

    document: dict = {"id": media_id, "filename": filename}
    if caption:
        document["caption"] = caption
    resp = await http_client.post(
        f"{GRAPH_API_URL}/messages",
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": document,
        },
    )
    _last_reply_time[to] = time.time()
    log.info(f"Text document sent to {to}: status={resp.status_code}")
    if resp.status_code != 200:
        log.error(f"Text document send failed: {resp.text}")
