"""WhatsApp adapter; never passes imported content to the general agent."""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import assets, enrich, media, store
from .analysis import analyze, analyze_structured
from .ingest import MAX_ZIP_BYTES, ExportError, ingest_zip
from .pdf import render_pdf

log = logging.getLogger(__name__)
_media_job = asyncio.Lock()
_active_jobs = {}
_USAGE = "\n\nAté 1 hora após o recebimento do ZIP, pergunte: sobre a conversa: sua pergunta\nPara receber o PDF novamente: reenviar pdf\nPara apagar: esquecer conversa"


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
            task = _active_jobs.get(sender)
            if task and task is not asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            await store.forget_with_assets(sender)
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
            record = await store.load_record(sender)
            if record is None:
                await send(
                    sender,
                    "Não há conversa ativa; ela pode ter expirado. Envie o ZIP novamente.",
                )
            else:
                async with asyncio.timeout(120):
                    answer = await analyze(record["messages"], prompt)
                if not await store.current(sender, record):
                    raise ExportError("A conversa foi apagada, substituída ou expirou.")
                await send(sender, answer)
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
    if not media.enabled() or not is_export(doc) or not enabled():
        return await _document(sender, doc, client, send, processing, send_file)
    if _media_job.locked():
        await send(
            sender,
            "Estou processando outra exportação com mídia. Tente novamente em alguns minutos.",
        )
        return True
    async with _media_job:
        _active_jobs[sender] = asyncio.current_task()
        try:
            async with asyncio.timeout(15 * 60):
                return await _document(sender, doc, client, send, processing, send_file)
        except TimeoutError:
            await send(
                sender,
                "O processamento excedeu 15 minutos. Resultados já salvos continuam disponíveis com reenviar pdf; para tentar os áudios pendentes, reenvie o ZIP.",
            )
            return True
        finally:
            _active_jobs.pop(sender, None)


async def _document(sender, doc, client, send, processing, send_file=None):
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
    received_at = datetime.now(timezone.utc)
    data = bytearray()
    files = {}
    try:
        await send(
            sender,
            "Lendo a exportação. Vou processar textos, áudios e imagens disponíveis; documentos serão apenas identificados."
            if media.enabled()
            else "Lendo a exportação; nesta versão analiso somente mensagens de texto.",
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
        files = {}
        if media.enabled():
            messages, files = await prepare_media(bytes(data))
        else:
            messages = await asyncio.to_thread(ingest_zip, bytes(data))
        question = doc.get("caption", "").strip()
        if len(question) > 4000:
            raise ExportError("Use uma pergunta de até 4 mil caracteres.")
        fingerprint = enrich.fingerprint(bytes(data), question)
        data.clear()
        title = PurePosixPath(doc.get("filename", "Conversa WhatsApp")).stem[:200]
        if media.enabled():
            record = await enrich.begin(
                sender,
                messages,
                fingerprint,
                title,
                question,
                received_at=received_at,
            )
            saved = True
            await send(
                sender,
                "Exportação validada. Processando mídias; isso pode levar alguns minutos.",
            )
            await enrich.run(sender, record, files)
        else:
            await store.save(
                sender,
                messages,
                title=title,
                question=question,
                received_at=received_at,
            )
        saved = True
        await deliver_pdf(sender, send, send_file)
    except ExportError as exc:
        await send(sender, str(exc) + (_USAGE if saved else ""))
    except Exception as exc:
        errors = getattr(exc, "exceptions", (exc,))
        log.warning(
            "Export processing failed saved=%s errors=%s",
            saved,
            [
                (
                    type(e).__name__,
                    getattr(getattr(e, "response", None), "status_code", None),
                )
                for e in errors
            ],
        )
        await send(
            sender,
            ("A conversa foi salva, mas a análise falhou." + _USAGE)
            if saved
            else "Não consegui processar o ZIP. Tente reenviar.",
        )
    finally:
        files.clear()
        data.clear()
        processing.discard(sender)
    return True


async def deliver_pdf(sender, send, send_file):
    record = await store.load_record(sender)
    if record is None:
        await send(sender, "Não há conversa ativa. Envie o ZIP novamente.")
        return
    stage = "análise"
    enriched = record.get("version") == 3
    if enriched and (
        record.get("status") == "context_exceeded"
        or len(
            json.dumps(enrich.source_messages(record["messages"]), ensure_ascii=False)
        )
        > enrich.MAX_CONTEXT
    ):
        await send(
            sender,
            "O conteúdo enriquecido excedeu 200 mil caracteres. Exporte um período menor.",
        )
        return
    try:
        if enriched and record.get("comments") is None:
            try:
                async with asyncio.timeout(120):
                    record["comments"] = await enrich.comments(record["messages"])
                record["comments_status"] = "ready"
            except Exception:
                record["comments"] = []
                record["comments_status"] = "failed"
            await store.update(sender, record)
        analysis = record.get("analysis")
        if analysis is None or (enriched and analysis.get("unavailable")):
            try:
                async with asyncio.timeout(120):
                    analysis = await analyze_structured(
                        record["messages"], record.get("question", "")
                    )
            except Exception:
                if not enriched:
                    raise
                analysis = {"claims": [], "unavailable": True}
            if enriched:
                analysis["comments"] = record.get("comments", [])
                analysis["comments_status"] = record.get("comments_status", "failed")
            stage = "armazenamento da análise"
            await store.save_analysis(sender, record, analysis)
        stage = "geração do PDF"
        messages = (
            await enrich.hydrated(sender, record) if enriched else record["messages"]
        )
        pdf = await render_pdf(
            messages, analysis, record.get("title", "Conversa WhatsApp")
        )
        if not await store.current(sender, record):
            raise ExportError(
                "A conversa foi apagada, substituída ou expirou; o envio foi cancelado."
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
            detail
            + " A conversa fica disponível somente até 1 hora após o recebimento do ZIP. Tente: reenviar pdf",
        )


async def cleanup_media():
    """Startup + periodic cleanup, independent of feature flag for safe rollback."""
    while True:
        for cleanup in (store.cleanup_expired, assets.cleanup):
            try:
                await cleanup()
            except Exception as exc:
                log.warning(
                    "Export cleanup failed component=%s error_type=%s",
                    cleanup.__name__,
                    type(exc).__name__,
                )
        await asyncio.sleep(60)


def cleanup_temp_files():
    """Single-process startup only: remove orphaned export conversion files."""
    for pattern in ("aisha-audio-*", "aisha-media-*"):
        for path in Path(tempfile.gettempdir()).glob(pattern):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)


async def prepare_media(data):
    """Await validator cleanup even when its caller is cancelled."""
    task = asyncio.create_task(asyncio.to_thread(media.prepare, data))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            _, files = await task
            files.clear()
        except Exception:
            pass
        raise
