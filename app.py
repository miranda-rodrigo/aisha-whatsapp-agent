import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Query, Request

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
        await send_message(sender, f"Recebi sua mensagem: {text}")
    else:
        await send_message(sender, f"Tipo '{msg_type}' ainda não suportado.")

    return {"status": "ok"}


async def handle_audio(sender: str, message: dict):
    """Downloads audio from Meta, transcribes it, and sends back the text."""
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
    await send_message(sender, "⏳ Transcrevendo...")

    try:
        raw_text = await transcribe_audio_bytes(audio_bytes, mime_type)
        log.info(f"Raw transcription: {len(raw_text)} chars")
        refined_text = await refine_transcription(raw_text)
        log.info(f"Refined transcription: {len(refined_text)} chars")
        reply = f"📝 Transcrição:\n\n{refined_text}"
    except Exception as e:
        log.exception("Transcription failed")
        reply = f"Erro na transcrição: {e}"

    await send_message(sender, reply)


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
