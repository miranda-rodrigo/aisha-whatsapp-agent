"""WhatsApp adapter; never passes imported content to the general agent."""

import asyncio
import logging
import os

from .analysis import analyze
from .ingest import ExportError, MAX_ZIP_BYTES, ingest_zip
from . import store

log = logging.getLogger(__name__)
_USAGE = "\n\nPor 24 horas, pergunte: sobre a conversa: sua pergunta\nPara apagar: esquecer conversa"


def enabled():
    return os.environ.get("WHATSAPP_EXPORT_ENABLED", "false").lower() == "true"


async def command(sender, text, send):
    stripped = text.strip()
    forget = stripped.casefold() == "esquecer conversa"
    question = stripped.casefold().startswith("sobre a conversa:")
    if not forget and not question:
        return False
    try:
        if forget:  # Deletion remains available with the feature disabled.
            await store.forget(sender)
            await send(sender, "Conversa importada apagada.")
        elif not enabled():
            await send(sender, "A análise de conversas está desativada no momento.")
        else:
            prompt = stripped.split(":", 1)[1].strip()
            if not prompt:
                await send(
                    sender, "Escreva sua pergunta depois de “sobre a conversa:”."
                )
                return True
            messages = await store.load(sender)
            if messages is None:
                await send(
                    sender,
                    "Não há conversa ativa; ela pode ter expirado. Envie o ZIP novamente.",
                )
            else:
                await send(sender, await analyze(messages, prompt))
    except ExportError as exc:
        await send(sender, str(exc))
    except Exception:
        log.warning("Export follow-up failed")
        await send(sender, "Não consegui concluir a análise. Tente novamente.")
    return True


def is_export(doc):
    filename = doc.get("filename", "")
    return filename.lower().endswith(".zip") or doc.get("mime_type") in {
        "application/zip",
        "application/x-zip-compressed",
    }


async def document(sender, doc, client, send, processing):
    if not is_export(doc):
        return False
    if not enabled():
        await send(sender, "A análise de conversas está desativada no momento.")
        return True
    if sender in processing:
        await send(
            sender, "Ainda estou processando sua mensagem anterior. Aguarde um momento."
        )
        return True
    processing.add(sender)
    saved = False
    try:
        await send(
            sender,
            "Lendo a exportação; nesta versão analiso somente mensagens de texto.",
        )
        response = await client.get(f"https://graph.facebook.com/v22.0/{doc['id']}")
        response.raise_for_status()
        metadata = response.json()
        if int(metadata.get("file_size") or 0) > MAX_ZIP_BYTES:
            raise ExportError("O ZIP excede 50 MB. Exporte um período menor.")
        data = bytearray()
        async with client.stream("GET", metadata["url"]) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_ZIP_BYTES:
                    raise ExportError("O ZIP excede 50 MB. Exporte um período menor.")
        messages = await asyncio.to_thread(ingest_zip, bytes(data))
        await store.save(sender, messages)
        saved = True
        result = await analyze(messages, doc.get("caption", "").strip())
        await send(sender, result + _USAGE)
    except ExportError as exc:
        await send(sender, str(exc) + (_USAGE if saved else ""))
    except Exception:
        log.warning("Export processing failed (saved=%s)", saved)
        await send(
            sender,
            ("A conversa foi salva, mas a análise falhou." + _USAGE)
            if saved
            else "Não consegui processar o ZIP. Tente reenviar.",
        )
    finally:
        processing.discard(sender)
    return True
