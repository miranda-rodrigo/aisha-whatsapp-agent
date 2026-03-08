import logging
import re
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query, Request

from chat import chat
from config import (
    ALLOWED_NUMBERS,
    GRAPH_API_URL,
    WEBHOOK_VERIFY_TOKEN,
    WHATSAPP_TOKEN,
)
from refine import refine_transcription
from transcribe import transcribe_audio_bytes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

http_client: httpx.AsyncClient
processed_messages: set[str] = set()
MAX_PROCESSED_CACHE = 1000


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        timeout=60.0,
    )
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
    else:
        await send_message(sender, f"Tipo '{msg_type}' ainda não suportado.")

    return {"status": "ok"}


def _contains_aisha(text: str) -> bool:
    return bool(re.search(r"\baisha\b", text, re.IGNORECASE))


def _strip_aisha(text: str) -> str:
    return re.sub(r"\baisha\b[,\s]*", "", text, count=1, flags=re.IGNORECASE).strip()


async def handle_chat(sender: str, text: str):
    """Routes a text message through Aisha chat and sends the response."""
    try:
        result = await chat(text)
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

    try:
        raw_text = await transcribe_audio_bytes(audio_bytes, mime_type)
        log.info(f"Raw transcription: {len(raw_text)} chars")

        if _contains_aisha(raw_text):
            log.info("Keyword 'Aisha' detected — routing to chat")
            user_input = _strip_aisha(raw_text)
            result = await chat(user_input)
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
