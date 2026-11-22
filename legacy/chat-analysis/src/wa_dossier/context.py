"""Texto da conversa para dar contexto aos modelos.

Hoje envia a conversa inteira (cabe com folga neste exemplo). Quando houver
chats grandes, esta função passa a devolver janela recente + resumo acumulado.
"""

from __future__ import annotations


def _msg_lines(msg: dict, with_ids: bool) -> list[str]:
    ident = f" ({msg['id']})" if with_ids else ""
    head = f"{msg['date']} {msg['time']} — {msg['sender']}{ident}:"
    lines = [f"{head} {msg['text'] or ''}".rstrip()]
    for media in msg["media"]:
        if media.get("transcricao"):
            lines.append(f"    [áudio {media['filename']}, transcrição fiel]: {media['transcricao']}")
        else:
            lines.append(f"    [{media['kind']}: {media['filename']}]")
    return lines


def conversation_text(conv: dict, *, with_ids: bool = True) -> str:
    lines = []
    for msg in conv["messages"]:
        if not msg["is_system"]:
            lines.extend(_msg_lines(msg, with_ids))
    return "\n".join(lines)


def local_window(conv: dict, msg_id: str, *, before: int = 8, after: int = 4) -> str:
    """Mensagens ao redor de `msg_id`, com a mensagem-alvo marcada por >>>."""
    msgs = [m for m in conv["messages"] if not m["is_system"]]
    idx = next((i for i, m in enumerate(msgs) if m["id"] == msg_id), None)
    if idx is None:
        return ""
    lines = []
    for m in msgs[max(0, idx - before): idx + after + 1]:
        block = _msg_lines(m, True)
        if m["id"] == msg_id:
            block = [">>> " + line for line in block]
        lines.extend(block)
    return "\n".join(lines)
