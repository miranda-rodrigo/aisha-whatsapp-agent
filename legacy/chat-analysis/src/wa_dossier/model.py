"""Fonte da verdade da conversa: conversa.json.

Cada nível só acrescenta campos. A pasta exportada não é modificada.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .dossier import build_message_ids
from .extract import extract_export, find_chat_txt, list_media_files
from .parser import AND_ATTACH_RE, IOS_ATTACH_RE, OMITTED_MARKERS, Message, classify_media, parse_chat

SCHEMA = 1
LAYER_KEYS = ("transcricao", "comentario", "transcricao_erro")


def probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return round(float(out), 2) if out else None
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def media_kind(filename: str) -> str:
    if "sticker" in filename.lower():
        return "sticker"
    return classify_media(filename)


def display_text(msg: Message) -> str:
    """Texto da mensagem sem os marcadores de anexo, que a mídia já representa."""
    text = IOS_ATTACH_RE.sub("", msg.text)
    text = AND_ATTACH_RE.sub("", text)
    for marker in OMITTED_MARKERS:
        text = re.sub(re.escape(marker), "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def _pdf_pages(path: Path) -> int | None:
    try:
        import pymupdf
    except ImportError:
        return None
    try:
        doc = pymupdf.open(path)
        pages = doc.page_count
        doc.close()
        return pages
    except Exception:
        return None


def build_conversation(source: Path, objetivo: str = "") -> dict:
    folder = extract_export(source)
    chat_txt = find_chat_txt(folder)
    files = list_media_files(folder, chat_txt)
    by_name = {p.name.lower(): p for p in files}
    result = parse_chat(chat_txt.read_text(encoding="utf-8", errors="replace"))
    ids = build_message_ids(result.messages)

    messages = []
    for msg, mid in zip(result.messages, ids):
        media = []
        for filename in msg.attachments:
            found = by_name.get(filename.lower())
            kind = media_kind(filename)
            item = {
                "filename": filename,
                "kind": kind,
                "present": found is not None,
                "path": None if found is None else str(found.relative_to(folder)),
                "duration_seconds": probe_duration(found) if found and kind in ("audio", "video") else None,
                "pages": _pdf_pages(found) if found and kind == "pdf" else None,
            }
            media.append(item)
        messages.append({
            "id": mid,
            "date": msg.date,
            "time": msg.time,
            "sender": msg.sender,
            "is_system": msg.is_system,
            "text": display_text(msg),
            "media": media,
            "omitted": list(msg.omitted_media),
        })

    return {
        "schema": SCHEMA,
        "chat_name": Path(source).stem,
        "source": str(Path(source).expanduser().resolve()),
        "export_dir": str(folder),
        "platform": result.platform,
        "objetivo": objetivo,
        "nivel": 0,
        "messages": messages,
        "analise": None,
    }


def parse_chat_date(value: str) -> datetime | None:
    """Aceita dd/mm/aa e dd/mm/aaaa, como o WhatsApp escreve nas exportações."""
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def slice_since(conv: dict, since: datetime) -> dict:
    """Cópia da conversa só com mensagens a partir de `since`, inclusive."""
    kept = []
    for msg in conv["messages"]:
        day = parse_chat_date(msg.get("date") or "")
        if day is None or day >= since:
            kept.append(msg)
    out = dict(conv)
    out["messages"] = kept
    out["recorte"] = {
        "desde": since.strftime("%d/%m/%Y"),
        "mensagens_total": len(conv["messages"]),
    }
    return out


def conversation_path(out_dir: Path) -> Path:
    return out_dir / "conversa.json"


def load_conversation(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_conversation(conv: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_layers(fresh: dict, previous: dict | None) -> dict:
    """Copia transcrições, comentários e análise já pagos para a conversa recém-lida."""
    if not previous:
        return fresh
    old_by_id = {m["id"]: m for m in previous.get("messages", [])}
    for msg in fresh["messages"]:
        old = old_by_id.get(msg["id"])
        if not old:
            continue
        old_media = {m.get("filename"): m for m in old.get("media", [])}
        for media in msg["media"]:
            prev = old_media.get(media.get("filename"))
            if not prev:
                continue
            for key in LAYER_KEYS:
                if prev.get(key):
                    media[key] = prev[key]
    if previous.get("analise"):
        fresh["analise"] = previous["analise"]
    fresh["objetivo"] = fresh.get("objetivo") or previous.get("objetivo") or ""
    fresh["nivel"] = previous.get("nivel") or 0
    return fresh


def known_ids(conv: dict) -> set[str]:
    return {m["id"] for m in conv["messages"]}


def validate_analise(analise: dict, ids: set[str]) -> list[str]:
    """Devolve problemas. Rejeita citação inexistente e afirmação sem citação."""
    problems = []
    if not analise:
        return ["análise vazia"]
    for section in ("linha_do_tempo", "valores", "compromissos", "pendencias"):
        for i, item in enumerate(analise.get(section) or []):
            cited = item.get("mensagens") or []
            bad = [mid for mid in cited if mid not in ids]
            if bad:
                problems.append(f"{section}[{i}] cita ids inexistentes: {', '.join(bad)}")
            if not cited:
                problems.append(f"{section}[{i}] não cita nenhuma mensagem")
    return problems


def strip_invalid_citations(analise: dict, ids: set[str]) -> dict:
    """Remove ids inexistentes e descarta afirmações que ficaram sem citação."""
    cleaned = dict(analise)
    for section in ("linha_do_tempo", "valores", "compromissos", "pendencias"):
        kept = []
        for item in analise.get(section) or []:
            cited = [mid for mid in (item.get("mensagens") or []) if mid in ids]
            if cited:
                kept.append({"texto": item.get("texto", ""), "mensagens": cited})
        cleaned[section] = kept
    return cleaned
