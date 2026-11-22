"""Run the same ingestion, enrichment, analysis and PDF renderer as the bot."""
import argparse
import asyncio
import base64
import json
import os
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from aisha_chat import analysis, enrich, media, pdf
from aisha_chat.ingest import ExportError, MAX_ZIP_BYTES
from .local import LocalAssets, LocalStore


def markdown(messages, result):
    lines = ["# Aisha — conversa", "", "## Análise", ""]
    for claim in result.get("claims", []):
        lines.append(claim["text"] + " [" + ", ".join(claim["ids"]) + "]")
    if not result.get("claims"):
        lines.append("Nenhuma análise de IA produzida nesta execução.")
    for msg in messages:
        lines.extend(["", f"## {msg['id']} — {msg['sender']} — {msg['date']} {msg['time']}", msg["text"]])
        for item in msg.get("media", []):
            lines.append(f"Mídia: {item['name']} ({item['status']})")
            for key, label in [("transcript", "Transcrição automática"), ("description", "Descrição visual automática")]:
                if item.get(key):
                    lines.append(label + ": " + item[key])
    return "\n".join(lines) + "\n"


async def run(source, output, *, ai=False, question="", make_pdf=True):
    source, output = Path(source), Path(output)
    if source.stat().st_size > MAX_ZIP_BYTES:
        raise ExportError("O ZIP excede 50 MB. Exporte um período menor.")
    if ai and not os.environ.get("OPENAI_API_KEY"):
        raise ExportError("Defina OPENAI_API_KEY para executar --ai.")
    with source.open("rb") as stream:
        raw = stream.read(MAX_ZIP_BYTES + 1)
    messages, files = media.prepare(raw)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    directory = output / run_id
    directory.mkdir(parents=True, mode=0o700)
    record = {"version": 3, "revision": uuid.uuid4().hex, "messages": messages,
              "analysis": None, "comments": None, "status": "offline"}
    result = {"claims": [], "offline": not ai}
    summary = {"mode": "ai" if ai else "offline", "run_id": run_id, "errors": []}
    try:
        if ai:
            state, assets = LocalStore(directory), LocalAssets(directory)
            enrich.configure_storage(state, assets)
            await state.update("local", record)
            record = await enrich.run("local", record, files)
            messages = await enrich.hydrated("local", record)
            result = await analysis.analyze_structured(messages, question)
            try:
                result["comments"] = await enrich.comments(messages)
            except Exception as exc:
                result["comments_status"] = "failed"
                summary["errors"].append("comments: " + type(exc).__name__)
        else:
            for message in messages:
                for item in message.get("media", []):
                    if item["kind"] == "image" and item.get("hash") in files:
                        item["image_data"] = base64.b64encode(files[item["hash"]]).decode()
                    if item.get("status") == "pending":
                        item["status"] = "not_processed"
    except Exception as exc:
        summary["errors"].append("processing: " + type(exc).__name__)
        result = {"claims": [], "unavailable": True}
        messages = record["messages"]
    finally:
        files.clear()
    # Preserve recoverable results even when providers or rendering fail.
    def save(name, value):
        directory.joinpath(name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    save("conversation.json", {"schema": 1, "messages": messages, "analysis": result})
    directory.joinpath("conversation.md").write_text(markdown(messages, result), encoding="utf-8")
    directory.joinpath("conversation.html").write_text(pdf.template(messages, result, source.stem), encoding="utf-8")
    if make_pdf:
        try:
            directory.joinpath("conversation.pdf").write_bytes(await pdf.render_pdf(messages, result, source.stem))
        except Exception as exc:
            summary["errors"].append("pdf: " + type(exc).__name__)
    summary.update(messages=len(messages), media_status=dict(Counter(
        item["status"] for msg in messages for item in msg.get("media", [])
    )))
    failed_media = sum(summary["media_status"].get(status, 0) for status in ("failed", "needs_reupload", "invalid"))
    summary["status"] = "partial" if summary["errors"] or failed_media else "complete"
    save("summary.json", summary)
    return directory, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--output", type=Path, default=Path("local/runs"))
    parser.add_argument("--ai", action="store_true", help="Autoriza chamadas reais de IA")
    parser.add_argument("--question", default="")
    parser.add_argument("--env-file", type=Path, help="Arquivo explícito de credenciais de desenvolvimento")
    parser.add_argument("--no-pdf", action="store_true", help="Dispensa Chromium, preservando HTML/Markdown/JSON")
    args = parser.parse_args(argv)
    if args.env_file:
        if not args.ai:
            parser.error("--env-file só é aceito junto com --ai")
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        for key in ["OPENAI_API_KEY", "AISHA_ANALYSIS_MODEL", "AISHA_SERVICE_TIER", "AISHA_VISION_MODEL", "AISHA_TRANSCRIPTION_MODEL"]:
            if values.get(key):
                os.environ.setdefault(key, values[key])
        analysis.configure(model=os.getenv("AISHA_ANALYSIS_MODEL"), service_tier=os.getenv("AISHA_SERVICE_TIER"))
        enrich.VISION_OCR_MODEL = os.getenv("AISHA_VISION_MODEL", enrich.VISION_OCR_MODEL)
        enrich.WHISPER_MODEL = os.getenv("AISHA_TRANSCRIPTION_MODEL", enrich.WHISPER_MODEL)
    try:
        directory, summary = asyncio.run(run(args.zip, args.output, ai=args.ai, question=args.question, make_pdf=not args.no_pdf))
    except (ExportError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(directory.resolve())
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if summary["status"] == "partial" else 0


if __name__ == "__main__":
    raise SystemExit(main())
