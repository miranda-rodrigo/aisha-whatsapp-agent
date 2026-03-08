import logging
import logging.handlers
import re
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from fastapi import FastAPI, Query, Request
from sqlalchemy.ext.asyncio import create_async_engine

from aisha.skills.chat import chat, chat_with_document, chat_with_image, chat_with_webpage, classify, wants_new_session
from aisha.config import (
    ALLOWED_NUMBERS,
    DATABASE_PASSWORD,
    GRAPH_API_URL,
    SUPABASE_URL,
    WEBHOOK_VERIFY_TOKEN,
    WHATSAPP_TOKEN,
)
from aisha.skills.document import extract_text_async, is_supported_document, MAX_DOCUMENT_SIZE
from aisha.skills.image_state import clear_pending_image, get_pending_image, store_pending_image
from aisha.skills.refine import refine_transcription
from aisha.skills.reminder import handle_reminder, is_reminder_intent
from aisha.session import delete_session, get_response_id, upsert_session
from aisha.skills.transcribe import transcribe_audio_bytes
from aisha.user_profile import increment_stat
from aisha.skills.youtube import (
    analyze_video,
    clear_pending_video,
    extract_youtube_url,
    get_pending_video,
    store_pending_video,
    strip_youtube_url,
)
from aisha.skills.webpage import (
    clear_pending_page,
    extract_web_url,
    fetch_page,
    get_pending_page,
    store_pending_page,
    strip_web_url,
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
processed_messages: set[str] = set()
MAX_PROCESSED_CACHE = 1000

_project_ref = SUPABASE_URL.replace("https://", "").split(".")[0]
_DB_URL = (
    f"postgresql+asyncpg://postgres.{_project_ref}:{DATABASE_PASSWORD}"
    f"@aws-0-us-west-2.pooler.supabase.com:6543/postgres"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client, scheduler

    http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=60.0,
    )

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
        log.info("WhatsApp agent started")
        yield

    await http_client.aclose()


app = FastAPI(lifespan=lifespan)


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


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Receives incoming message notifications from Meta."""
    body = await request.json()
    log.info("Webhook payload received")

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages")
        if not messages:
            return {"status": "no message"}
        message = messages[0]
    except (KeyError, IndexError):
        return {"status": "no message"}

    msg_id = message.get("id", "")
    if msg_id in processed_messages:
        log.info(f"Duplicate message {msg_id}, skipping")
        return {"status": "duplicate"}
    processed_messages.add(msg_id)
    if len(processed_messages) > MAX_PROCESSED_CACHE:
        processed_messages.clear()

    sender = message.get("from", "")
    msg_type = message.get("type", "")
    log.info(f"Message from {sender}, type={msg_type}, id={msg_id}")

    if sender not in ALLOWED_NUMBERS:
        log.info(f"Ignored: {sender} not in allowed list")
        return {"status": "ignored"}

    if msg_type == "audio":
        await handle_audio(sender, message)
    elif msg_type == "text":
        text = message.get("text", {}).get("body", "")
        await handle_chat(sender, text)
    elif msg_type == "image":
        await handle_image(sender, message)
    elif msg_type == "document":
        await handle_document(sender, message)
    else:
        await send_message(sender, f"Tipo '{msg_type}' ainda não suportado.")

    return {"status": "ok"}


def _contains_aisha(text: str) -> bool:
    return bool(re.search(r"\baisha\b", text, re.IGNORECASE))


def _strip_aisha(text: str) -> str:
    return re.sub(r"\baisha\b[,\s]*", "", text, count=1, flags=re.IGNORECASE).strip()


async def handle_chat(sender: str, text: str):
    """Routes a text message through Aisha chat (or reminder/youtube skill) and sends the response."""
    try:
        # 1. Pending image instruction
        pending_img = get_pending_image(sender)
        if pending_img:
            log.info(f"Pending image found for {sender} — using text as instruction")
            await _process_image_instruction(sender, text, pending_img)
            return

        # 2. Pending YouTube video — user is now sending the instruction
        pending_yt = get_pending_video(sender)
        if pending_yt:
            log.info(f"Pending YouTube for {sender} — processing with instruction: {text[:60]}")
            clear_pending_video(sender)
            await send_message(sender, "⏳ Analisando vídeo...")
            await increment_stat(sender, "youtube")
            reply = await analyze_video(pending_yt.url, text)
            await send_message(sender, reply)
            return

        # 3. Pending webpage — user is now sending the instruction
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
            return

        # 4. YouTube URL in current message
        yt_url = extract_youtube_url(text)
        if yt_url:
            instruction = strip_youtube_url(text)
            if instruction:
                log.info(f"YouTube URL + instruction for {sender}: {yt_url}")
                await send_message(sender, "⏳ Analisando vídeo...")
                await increment_stat(sender, "youtube")
                reply = await analyze_video(yt_url, instruction)
                await send_message(sender, reply)
            else:
                # No instruction — store and ask what to do
                store_pending_video(sender, yt_url)
                log.info(f"YouTube URL stored for {sender}: {yt_url}")
                await send_message(
                    sender,
                    "🎬 Link do YouTube detectado! O que você quer que eu faça com esse vídeo?\n\n"
                    "Exemplos:\n"
                    "• _Faz um resumo_\n"
                    "• _Transcreve o vídeo_\n"
                    "• _Quais são os pontos principais?_\n"
                    "• _Explica os conceitos mencionados_",
                )
            return

        # 5. Web URL in current message
        web_url = extract_web_url(text)
        if web_url:
            instruction = strip_web_url(text)
            if instruction:
                log.info(f"Web URL + instruction for {sender}: {web_url}")
                await send_message(sender, "⏳ Lendo página...")
                await increment_stat(sender, "webpages")
                try:
                    content = await fetch_page(web_url)
                    prev_id = await get_response_id(sender)
                    result = await chat_with_webpage(content, web_url, instruction, prev_id)
                    if result.response_id:
                        await upsert_session(sender, result.response_id)
                    if result.text:
                        await send_message(sender, result.text)
                except Exception as e:
                    log.exception("Webpage processing failed")
                    await send_message(sender, f"Não consegui acessar a página: {e}")
            else:
                # No instruction — store and ask what to do
                store_pending_page(sender, web_url)
                log.info(f"Web URL stored for {sender}: {web_url}")
                await send_message(
                    sender,
                    "🔗 Link detectado! O que você quer que eu faça com essa página?\n\n"
                    "Exemplos:\n"
                    "• _Resume essa notícia_\n"
                    "• _Traduz para inglês_\n"
                    "• _Quais são os pontos principais?_\n"
                    "• _Explica de forma simples_",
                )
            return

        # 7. Classify intent (LLM) — SELF goes straight to chat, skipping skill routers
        complexity = await classify(text)
        log.info(f"Classified as {complexity}: {text[:80]}")

        if complexity != "SELF":
            # 8. Reminder intent (only when not a capability/self question)
            if is_reminder_intent(text):
                log.info(f"Reminder intent detected for {sender}")
                reply = await handle_reminder(sender, text, scheduler)
                if "✅ Lembrete criado" in reply:
                    await increment_stat(sender, "reminders_created")
                await send_message(sender, reply)
                return

        # 9. Chat (SELF / SIMPLE / COMPLEX)
        if wants_new_session(text):
            await delete_session(sender)
            log.info(f"Session reset requested by {sender}")

        prev_id = await get_response_id(sender)
        result = await chat(
            text, previous_response_id=prev_id, phone=sender, complexity=complexity,
        )

        if result.response_id:
            await upsert_session(sender, result.response_id)

        if result.image_bytes:
            await send_image(sender, result.image_bytes)
        if result.text:
            await send_message(sender, result.text)
    except Exception as e:
        log.exception("Chat failed")
        await send_message(sender, f"Erro no chat: {e}")


async def handle_audio(sender: str, message: dict):
    """Downloads audio, transcribes it, and routes to chat or transcription."""
    audio_id = message["audio"]["id"]
    log.info(f"Downloading audio {audio_id}")

    media_resp = await http_client.get(f"https://graph.facebook.com/v22.0/{audio_id}")
    media_resp.raise_for_status()
    media_url = media_resp.json()["url"]

    audio_resp = await http_client.get(media_url)
    audio_resp.raise_for_status()
    audio_bytes = audio_resp.content
    mime_type = message["audio"].get("mime_type", "audio/ogg")

    log.info(f"Audio downloaded: {len(audio_bytes)} bytes, mime={mime_type}")
    await send_message(sender, "⏳ Processando áudio...")
    await increment_stat(sender, "audios")

    try:
        raw_text = await transcribe_audio_bytes(audio_bytes, mime_type)
        log.info(f"Raw transcription: {len(raw_text)} chars")

        pending = get_pending_image(sender)
        if pending:
            log.info(f"Pending image found for {sender} — using audio as instruction")
            await _process_image_instruction(sender, raw_text, pending)
            return

        if _contains_aisha(raw_text):
            log.info("Keyword 'Aisha' detected — routing to chat")
            user_input = _strip_aisha(raw_text)
            result = await chat(user_input, phone=sender)
            if result.image_bytes:
                await send_image(sender, result.image_bytes)
            if result.text:
                await send_message(sender, result.text)
        else:
            log.info("No keyword — routing to transcription refinement")
            refined_text = await refine_transcription(raw_text)
            log.info(f"Refined transcription: {len(refined_text)} chars")
            await send_message(sender, "📝 Transcrição:")
            await send_message(sender, refined_text)
    except Exception as e:
        log.exception("Audio processing failed")
        await send_message(sender, f"Erro ao processar áudio: {e}")


async def handle_image(sender: str, message: dict):
    """Downloads an image from WhatsApp and stores it awaiting user instructions."""
    image_id = message["image"]["id"]
    mime_type = message["image"].get("mime_type", "image/jpeg")
    log.info(f"Downloading image {image_id}")

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
        if caption:
            log.info(f"Image has caption — using as instruction: {caption[:80]}")
            pending = get_pending_image(sender)
            if pending:
                await _process_image_instruction(sender, caption, pending)
            return

        await send_message(sender, "📷 O que você quer que eu faça com esta imagem?")
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

        await send_message(sender, "📄 Processando documento...")
        await increment_stat(sender, "documents")

        document_text = await extract_text_async(doc_bytes, mime_type)
        log.info(f"Text extracted: {len(document_text)} chars from {filename}")

        if not document_text.strip():
            await send_message(
                sender,
                "Não consegui extrair texto deste documento. "
                "Ele pode ser um PDF escaneado (imagem) ou estar protegido.",
            )
            return

        caption = doc.get("caption", "").strip()
        prev_id = await get_response_id(sender)
        result = await chat_with_document(document_text, caption or None, prev_id)

        if result.response_id:
            await upsert_session(sender, result.response_id)

        if result.text:
            await send_message(sender, result.text)

    except Exception as e:
        log.exception("Document processing failed")
        await send_message(sender, f"Erro ao processar documento: {e}")


async def _process_image_instruction(sender: str, instruction: str, pending):
    """Sends the pending image + instruction to the AI and delivers the result."""
    clear_pending_image(sender)
    await send_message(sender, "⏳ Processando imagem...")

    prev_id = await get_response_id(sender)
    result = await chat_with_image(
        instruction,
        pending.image_bytes,
        pending.mime_type,
        previous_response_id=prev_id,
    )

    if result.response_id:
        await upsert_session(sender, result.response_id)

    if result.image_bytes:
        await send_image(sender, result.image_bytes)
    if result.text:
        await send_message(sender, result.text)


async def send_message(to: str, text: str):
    """Sends a text message via WhatsApp Cloud API."""
    resp = await http_client.post(
        f"{GRAPH_API_URL}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        },
    )
    log.info(f"Message sent to {to}: status={resp.status_code}")
    if resp.status_code != 200:
        log.error(f"Send failed: {resp.text}")


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
    log.info(f"Image sent to {to}: status={resp.status_code}")
    if resp.status_code != 200:
        log.error(f"Image send failed: {resp.text}")
