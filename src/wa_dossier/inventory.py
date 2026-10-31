"""Inventário da exportação: o que veio, o que falta, quem fala."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .extract import extract_export, find_chat_txt, list_media_files
from .parser import ParseResult, classify_media, parse_chat


def build_inventory(source: Path) -> dict:
    folder = extract_export(source)
    chat_txt = find_chat_txt(folder)
    media_files = list_media_files(folder, chat_txt)
    result = parse_chat(chat_txt.read_text(encoding="utf-8", errors="replace"))

    user_msgs = [m for m in result.messages if not m.is_system]
    senders = Counter(m.sender for m in user_msgs)

    present_names = {p.name.lower() for p in media_files}
    attached_refs = [a for m in result.messages for a in m.attachments]
    attached_missing = [a for a in attached_refs if a.lower() not in present_names]
    omitted = Counter(kind for m in result.messages for kind in m.omitted_media)

    media_by_type = Counter(classify_media(p.name) for p in media_files)
    media_bytes = sum(p.stat().st_size for p in media_files)

    dates = [m.date for m in result.messages if m.date]

    return {
        "source": str(source),
        "chat_txt": str(chat_txt),
        "platform": result.platform,
        "total_messages": len(result.messages),
        "user_messages": len(user_msgs),
        "system_messages": len(result.messages) - len(user_msgs),
        "senders": dict(senders.most_common()),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "media_files_present": len(media_files),
        "media_by_type": dict(media_by_type),
        "media_total_bytes": media_bytes,
        "attachments_referenced": len(attached_refs),
        "attachments_missing": attached_missing,
        "omitted_media_by_type": dict(omitted),
        "unparsed_lines": result.unparsed_lines,
    }


def format_inventory(inv: dict) -> str:
    lines = [
        f"Exportação : {inv['source']}",
        f"Plataforma : {inv['platform']}",
        f"Período    : {inv['first_date']} a {inv['last_date']}",
        f"Mensagens  : {inv['total_messages']} "
        f"({inv['user_messages']} de usuários, {inv['system_messages']} de sistema)",
        "",
        "Por autor:",
    ]
    for sender, count in inv["senders"].items():
        lines.append(f"  {count:>6}  {sender}")

    mb = inv["media_total_bytes"] / 1_000_000
    lines += ["", f"Mídias presentes no zip: {inv['media_files_present']} ({mb:.1f} MB)"]
    for kind, count in sorted(inv["media_by_type"].items()):
        lines.append(f"  {count:>6}  {kind}")

    lines += [
        "",
        f"Anexos citados no texto : {inv['attachments_referenced']}",
        f"  dos quais ausentes    : {len(inv['attachments_missing'])}",
        f"Mídias omitidas na exportação (citadas sem arquivo):",
    ]
    if inv["omitted_media_by_type"]:
        for kind, count in sorted(inv["omitted_media_by_type"].items()):
            lines.append(f"  {count:>6}  {kind}")
    else:
        lines.append("  nenhuma")

    unparsed = inv["unparsed_lines"]
    lines += ["", f"Linhas não interpretadas: {len(unparsed)}"]
    for lineno, content in unparsed[:10]:
        lines.append(f"  linha {lineno}: {content[:80]!r}")
    if len(unparsed) > 10:
        lines.append(f"  ... e mais {len(unparsed) - 10}")

    return "\n".join(lines)
