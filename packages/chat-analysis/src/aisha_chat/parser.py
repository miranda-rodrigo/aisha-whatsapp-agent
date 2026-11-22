"""Parser das exportações de chat do WhatsApp (formatos iPhone e Android).

Formato iPhone (arquivo `_chat.txt`):
    [22/09/2026, 01:11:23] Emanuella Paiva: Olá Rodrigo!
    [29/09/2026, 13:44:05] Emanuella Paiva: ‎<attached: 00000028-PHOTO.jpg>
    Linhas frequentemente começam com U+200E (marca esquerda-direita, invisível).

Formato Android (arquivo `chat.txt` ou similar):
    22/09/2026 01:11 - Emanuella Paiva: Olá Rodrigo!
    29/09/2026 13:44 - Emanuella Paiva: IMG-20260929-WA0001.jpg (file attached)
    29/09/2026 13:45 - Emanuella Paiva: <Media omitted>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Caracteres invisíveis que o WhatsApp injeta nas exportações.
_INVISIBLE = "\u200e\u200f\ufeff"

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


@dataclass
class Message:
    date: str  # como veio no arquivo, ex. "22/09/2026"
    time: str  # como veio no arquivo, ex. "01:11:23" ou "13:44"
    sender: str  # "" para mensagens de sistema
    text: str
    attachments: list[str] = field(default_factory=list)  # nomes de arquivo citados
    omitted_media: list[str] = field(
        default_factory=list
    )  # tipos omitidos ("image", ...)
    line_number: int = 0  # linha onde a mensagem começa (1-based)

    @property
    def is_system(self) -> bool:
        return self.sender == ""


@dataclass
class ParseResult:
    platform: str  # "ios" | "android"
    messages: list[Message]
    unparsed_lines: list[tuple[int, str]]  # linhas que não casaram com nada


# ---------------------------------------------------------------------------
# Expressões regulares
# ---------------------------------------------------------------------------

_DATE = r"(\d{1,2}/\d{1,2}/\d{2,4})"
_TIME = r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap]\.?[Mm]\.?)?)"

# iPhone: "[data, hora] Autor: texto" / sistema: "[data, hora] texto"
IOS_MSG_RE = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s(.*?):\s(.*)$")
IOS_SYS_RE = re.compile(rf"^\[{_DATE},?\s+{_TIME}\]\s(.*)$")

# Android: "data, hora - Autor: texto" / sistema: "data, hora - texto"
AND_MSG_RE = re.compile(rf"^{_DATE},?\s+{_TIME}\s-\s(.*?):\s(.*)$")
AND_SYS_RE = re.compile(rf"^{_DATE},?\s+{_TIME}\s-\s(.*)$")

# Anexo presente no zip.
IOS_ATTACH_RE = re.compile(r"<(?:attached|anexado):\s*(.+?)>")
AND_ATTACH_RE = re.compile(
    r"^(.+?)\s\((?:file attached|arquivo anexado)\)\s*$", re.MULTILINE
)

# Mídia citada mas não incluída na exportação. Mapeia marcador -> tipo.
OMITTED_MARKERS = {
    # iPhone (inglês)
    "image omitted": "image",
    "video omitted": "video",
    "audio omitted": "audio",
    "sticker omitted": "sticker",
    "document omitted": "document",
    "gif omitted": "gif",
    "contact card omitted": "contact",
    # iPhone (português)
    "imagem ocultada": "image",
    "vídeo omitido": "video",
    "vídeo ocultado": "video",
    "áudio ocultado": "audio",
    "áudio omitido": "audio",
    "figurinha omitida": "sticker",
    "documento omitido": "document",
    "documento ocultado": "document",
    "gif omitido": "gif",
    "cartão do contato omitido": "contact",
    # Android
    "<media omitted>": "media",
    "<mídia oculta>": "media",
    "<mídia omitida>": "media",
}

# ---------------------------------------------------------------------------
# Classificação de mídia por extensão
# ---------------------------------------------------------------------------

MEDIA_TYPES = {
    "image": ("jpg", "jpeg", "png", "gif", "webp", "heic"),
    "video": ("mp4", "mov", "mkv", "webm", "3gp"),
    "audio": ("opus", "ogg", "mp3", "wav", "m4a", "aac"),
    "pdf": ("pdf",),
}


def classify_media(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    for kind, exts in MEDIA_TYPES.items():
        if ext in exts:
            return kind
    return "file"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


_INVISIBLE_TABLE = {ord(c): None for c in _INVISIBLE}


def _clean(line: str) -> str:
    return line.strip().strip(_INVISIBLE).strip()


def _drop_invisible(text: str) -> str:
    """Remove caracteres invisíveis em qualquer posição (não só nas bordas)."""
    return text.translate(_INVISIBLE_TABLE)


def detect_platform(lines: list[str]) -> str:
    """Olha as primeiras linhas não vazias e decide o formato."""
    ios = android = 0
    for raw in lines[:200]:
        line = _clean(raw)
        if not line:
            continue
        if IOS_SYS_RE.match(line):
            ios += 1
        elif AND_SYS_RE.match(line):
            android += 1
    return "ios" if ios >= android else "android"


def _extract_media_refs(msg: Message, platform: str) -> None:
    """Preenche attachments e omitted_media a partir do texto da mensagem."""
    text = msg.text
    attach_re = IOS_ATTACH_RE if platform == "ios" else AND_ATTACH_RE
    for m in attach_re.finditer(text):
        msg.attachments.append(_clean(m.group(1)))
    lowered = _clean(text).lower()
    for marker, kind in OMITTED_MARKERS.items():
        if marker in lowered:
            msg.omitted_media.append(kind)


def parse_chat(text: str) -> ParseResult:
    """Converte o conteúdo do chat exportado em mensagens estruturadas."""
    lines = text.splitlines()
    platform = detect_platform(lines)
    msg_re = IOS_MSG_RE if platform == "ios" else AND_MSG_RE
    sys_re = IOS_SYS_RE if platform == "ios" else AND_SYS_RE

    messages: list[Message] = []
    unparsed: list[tuple[int, str]] = []
    current: Message | None = None

    for i, raw in enumerate(lines, start=1):
        line = _clean(raw)

        m = msg_re.match(line)
        if m:
            date, time, sender, body = m.groups()
            current = Message(
                date=date,
                time=time,
                sender=_drop_invisible(sender).strip(),
                text=_drop_invisible(body),
                line_number=i,
            )
            messages.append(current)
            continue

        s = sys_re.match(line)
        if s:
            date, time, body = s.groups()
            current = Message(
                date=date,
                time=time,
                sender="",
                text=_drop_invisible(body),
                line_number=i,
            )
            messages.append(current)
            continue

        # Continuação de mensagem multilinha.
        if current is not None:
            current.text += "\n" + _drop_invisible(raw).strip()
        elif line:
            unparsed.append((i, raw))

    for msg in messages:
        _extract_media_refs(msg, platform)

    return ParseResult(platform=platform, messages=messages, unparsed_lines=unparsed)
