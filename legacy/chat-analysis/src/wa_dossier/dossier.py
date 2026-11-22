"""Geração do dossiê em Markdown (v0: linha do tempo sem IA)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .extract import extract_export, find_chat_txt, list_media_files
from .inventory import build_inventory, format_inventory
from .parser import Message, classify_media, parse_chat


def message_id(msg: Message) -> str:
    """Id estável por mensagem, usável como citação (ex.: msg-1a2b3c4d5e6f)."""
    payload = f"{msg.date}|{msg.time}|{msg.sender}|{msg.text}".encode("utf-8")
    return "msg-" + hashlib.sha1(payload).hexdigest()[:12]


def build_message_ids(messages: list[Message]) -> list[str]:
    """Ids únicos: mensagens idênticas ganham sufixo numérico."""
    seen: dict[str, int] = {}
    ids = []
    for msg in messages:
        base = message_id(msg)
        n = seen.get(base, 0)
        seen[base] = n + 1
        ids.append(base if n == 0 else f"{base}-{n}")
    return ids


def _media_placeholder(msg: Message, present_names: set[str]) -> list[str]:
    """Linhas de placeholder para mídias citadas na mensagem."""
    lines = []
    for att in msg.attachments:
        kind = classify_media(att)
        status = "presente" if att.lower() in present_names else "AUSENTE do zip"
        lines.append(f"  - [mídia {kind}: `{att}` — {status}]")
    for kind in msg.omitted_media:
        lines.append(f"  - [mídia {kind} omitida da exportação]")
    return lines


def generate_dossier(source: Path, output_root: Path) -> Path:
    """Gera output/<chat>/conversa.md e devolve o caminho."""
    folder = extract_export(source)
    chat_txt = find_chat_txt(folder)
    media_files = list_media_files(folder, chat_txt)
    present_names = {p.name.lower() for p in media_files}

    result = parse_chat(chat_txt.read_text(encoding="utf-8", errors="replace"))
    ids = build_message_ids(result.messages)
    inv = build_inventory(source)

    chat_name = Path(source).stem
    out_dir = output_root / chat_name
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Conversa: {chat_name}",
        "",
        "## Inventário",
        "",
        "```",
        format_inventory(inv),
        "```",
        "",
        "## Linha do tempo",
        "",
        "Cada mensagem tem um id estável (`msg-...`) para citação.",
        "",
    ]

    current_date = None
    for msg, mid in zip(result.messages, ids):
        if msg.date != current_date:
            current_date = msg.date
            lines += [f"### {current_date}", ""]
        sender = msg.sender if not msg.is_system else "[sistema]"
        text = msg.text.replace("\n", "\n  ")
        lines.append(f"- `{mid}` **{msg.time} — {sender}:** {text}")
        lines += _media_placeholder(msg, present_names)
    lines.append("")

    out_path = out_dir / "conversa.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
