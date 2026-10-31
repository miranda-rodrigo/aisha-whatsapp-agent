"""Texto da conversa para dar contexto aos modelos.

Hoje envia a conversa inteira (cabe com folga neste exemplo). Quando houver
chats grandes, esta função passa a devolver janela recente + resumo acumulado.
"""

from __future__ import annotations


def conversation_text(conv: dict, *, with_ids: bool = True) -> str:
    lines = []
    for msg in conv["messages"]:
        if msg["is_system"]:
            continue
        ident = f" ({msg['id']})" if with_ids else ""
        head = f"{msg['date']} {msg['time']} — {msg['sender']}{ident}:"
        body = msg["text"] or ""
        lines.append(f"{head} {body}".rstrip())
        for media in msg["media"]:
            if media.get("transcricao"):
                lines.append(f"    [áudio {media['filename']}, transcrição fiel]: {media['transcricao']}")
            else:
                lines.append(f"    [{media['kind']}: {media['filename']}]")
    return "\n".join(lines)
