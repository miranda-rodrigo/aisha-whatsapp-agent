"""WhatsApp adapter; never passes imported content to the general agent."""

import asyncio
import logging
import os
from pathlib import PurePosixPath

from . import store
from .analysis import analyze, analyze_structured
from .ingest import MAX_ZIP_BYTES, ExportError, ingest_zip
from .pdf import render_pdf

log = logging.getLogger(__name__)
_USAGE = "\n\nPor 24 horas, pergunte: sobre a conversa: sua pergunta\nPara receber o PDF novamente: reenviar pdf\nPara apagar: esquecer conversa"


def enabled():
    return os.environ.get("WHATSAPP_EXPORT_ENABLED", "false").lower() == "true"


async def command(sender, text, send, send_file=None):
    stripped = text.strip()
    forget = stripped.casefold() == "esquecer conversa"
    question = stripped.casefold().startswith("sobre a conversa:")
    resend = stripped.casefold() == "reenviar pdf"
    if not forget and not question and not resend:
        return False
    try:
        if forget:  # Deletion remains available with the feature disabled.
            await store.forget(sender)
            await send(sender, "Conversa importada apagada.")
        elif not enabled():
            await send(sender, "A análise de conversas está desativada no momento.")
        elif resend:
            await deliver_pdf(sender, send, send_file)
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


async def document(sender, doc, client, send, processing, send_file=None):
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
        question = doc.get("caption", "").strip()
        if len(question) > 4000:
            raise ExportError("Use uma pergunta de até 4 mil caracteres.")
        title = PurePosixPath(doc.get("filename", "Conversa WhatsApp")).stem[:200]
        await store.save(sender, messages, title=title, question=question)
        saved = True
        await deliver_pdf(sender, send, send_file)
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


async def deliver_pdf(sender, send, send_file):
    record = await store.load_record(sender)
    if record is None:
        await send(sender, "Não há conversa ativa. Envie o ZIP novamente.")
        return
    stage = "análise"
    try:
        analysis = record.get("analysis")
        if analysis is None:
            analysis = await analyze_structured(
                record["messages"], record.get("question", "")
            )
            stage = "armazenamento da análise"
            await store.save_analysis(sender, record, analysis)
        stage = "geração do PDF"
        pdf = await render_pdf(
            record["messages"], analysis, record.get("title", "Conversa WhatsApp")
        )
        stage = "envio do PDF"
        if send_file is None:
            raise RuntimeError("Document delivery unavailable")
        await send_file(sender, pdf, "conversa-analisada.pdf", "application/pdf")
        await send(sender, "PDF da conversa enviado." + _USAGE)
    except Exception as exc:
        log.warning(
            "Export PDF failed at stage=%s error_type=%s", stage, type(exc).__name__
        )
        detail = (
            str(exc) if isinstance(exc, ExportError) else f"Falha na etapa de {stage}."
        )
        await send(
            sender,
            detail + " A conversa continua salva por até 24 horas. Tente: reenviar pdf",
        )
