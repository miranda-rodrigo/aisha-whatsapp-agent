"""Bounded, in-memory ingestion. Never extract or open media attachments."""
import hashlib
import io
import json
import zipfile
from pathlib import PurePosixPath

from .parser import parse_chat

MAX_ZIP_BYTES = 50 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_CHARS = 100_000
MAX_ENTRIES = 10_000


class ExportError(ValueError):
    """Safe, user-facing export validation error."""


def build_message_ids(messages):
    # Same identity and duplicate suffix algorithm as wa_dossier/dossier.py.
    seen = {}
    result = []
    for msg in messages:
        payload = f"{msg.date}|{msg.time}|{msg.sender}|{msg.text}".encode()
        base = "msg-" + hashlib.sha1(payload).hexdigest()[:12]
        n = seen.get(base, 0)
        seen[base] = n + 1
        result.append(base if n == 0 else f"{base}-{n}")
    return result


def format_conversation(messages: list[dict]) -> str:
    return json.dumps(messages, ensure_ascii=False)


def ingest_zip(data: bytes) -> list[dict]:
    if len(data) > MAX_ZIP_BYTES:
        raise ExportError("O ZIP excede 50 MB. Exporte um período menor.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ExportError("O ZIP contém arquivos demais. Exporte sem mídia.")
            if any(item.flag_bits & 1 for item in entries):
                raise ExportError("ZIP protegido por senha não é aceito.")
            candidates = [item for item in entries if not item.is_dir()
                          and PurePosixPath(item.filename).suffix.lower() == ".txt"
                          and not any(p.startswith((".", "__MACOSX"))
                                      for p in PurePosixPath(item.filename).parts)]
            parsed = []
            total = 0
            for item in candidates:
                total += item.file_size
                if total > MAX_TEXT_BYTES:
                    raise ExportError("O texto descompactado excede 2 MB. Exporte um período menor.")
                with archive.open(item) as stream:
                    raw = stream.read(MAX_TEXT_BYTES + 1)
                if len(raw) > MAX_TEXT_BYTES:
                    raise ExportError("O texto descompactado excede 2 MB.")
                try:
                    result = parse_chat(raw.decode("utf-8-sig"))
                except UnicodeDecodeError:
                    continue
                if result.messages:
                    if result.unparsed_lines:
                        raise ExportError("Há linhas não reconhecidas antes da conversa. Reexporte pelo WhatsApp.")
                    parsed.append(result)
            if not parsed:
                raise ExportError("Nenhuma conversa WhatsApp reconhecida no ZIP (texto UTF-8, iPhone ou Android).")
            if len(parsed) != 1:
                raise ExportError("O ZIP contém mais de uma conversa. Envie uma por vez.")
    except ExportError:
        raise
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError, EOFError) as exc:
        raise ExportError("Não consegui ler o ZIP. Ele pode estar corrompido ou usar compressão incompatível.") from exc
    result = parsed[0]
    messages = [dict(id=mid, date=msg.date, time=msg.time,
                     sender=msg.sender or "[sistema]", text=msg.text)
                for msg, mid in zip(result.messages, build_message_ids(result.messages))]
    if len(format_conversation(messages)) > MAX_CONTEXT_CHARS:
        raise ExportError("A conversa excede 100 mil caracteres formatados. Exporte um período menor; nenhuma parte foi analisada.")
    return messages
