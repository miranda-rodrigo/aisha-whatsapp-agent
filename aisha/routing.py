"""Pure routing helpers — no I/O, no env, safe to unit-test."""

import re

DOWNLOAD_KEYWORDS = re.compile(
    r"\b(baixa|baixe|baixar|download|salva|salve|salvar|me manda|manda|pega)\b",
    re.IGNORECASE,
)

WANTS_TRANSCRIPTION_RE = re.compile(
    r"(só\s+quer(ia|o)|quero\s+só|só\s+precis(ava|o)|era\s+só|só\s+era|"
    r"não\s+precis(a|o)\s+responder|s[oó]\s+a?\s*transcri[çc][aã]o|"
    r"transcrev(e|a)\s+(isso|a[íi]|o\s+áudio)|manda\s+(a\s+)?transcri[çc][aã]o)",
    re.IGNORECASE,
)

NEW_SESSION_PATTERNS = [
    r"\bnova conversa\b",
    r"\bnovo assunto\b",
    r"\bmudar de assunto\b",
    r"\breseta\b",
    r"\breset\b",
    r"\bvamos falar sobre outra coisa\b",
]

TRIVIAL_RE = re.compile(
    r"^(oi+|ol[áa]|hey|hi|hello|e a[ií]|eae|opa|fala|"
    r"obrigad[oa]s?|thanks|valeu|tmj|"
    r"ok+|beleza|blz|certo|show|"
    r"tudo bem\??|td bem\??|"
    r"bom dia|boa tarde|boa noite)"
    r"[\s!.?]*$",
    re.IGNORECASE,
)

MAX_SCANNED_PAGES = 5


def contains_aisha(text: str) -> bool:
    return bool(re.search(r"\baisha\b", text, re.IGNORECASE))


def strip_aisha(text: str) -> str:
    return re.sub(r"\baisha\b[,\s]*", "", text, count=1, flags=re.IGNORECASE).strip()


def is_download_intent(text: str) -> bool:
    return bool(DOWNLOAD_KEYWORDS.search(text))


def is_retroactive_transcription_request(text: str) -> bool:
    return bool(WANTS_TRANSCRIPTION_RE.search(text))


def is_transcription_request(text: str) -> bool:
    """True if the raw transcription explicitly asks Aisha to transcribe."""
    return bool(re.search(
        r"\baisha\b.{0,40}\bTranscreva\b",
        text,
        re.IGNORECASE | re.DOTALL,
    ))


def wants_new_session(text: str) -> bool:
    for pattern in NEW_SESSION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def is_trivial_message(text: str) -> bool:
    """True for greetings/thanks that do not need tools or the full agent loop."""
    return bool(TRIVIAL_RE.match(text.strip()))


def parse_page_selection(text: str, total_pages: int) -> list[int] | None:
    """Parse page selection text into 0-based indices. None if nothing parsed."""
    text_lower = text.lower()
    indices: set[int] = set()

    range_match = re.search(r"(\d+)\s+a\s+(\d+)", text_lower)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        indices.update(range(start - 1, end))

    for m in re.finditer(r"\d+", text_lower):
        n = int(m.group())
        if 1 <= n <= total_pages:
            indices.add(n - 1)

    if not indices:
        return None

    valid = sorted(i for i in indices if 0 <= i < total_pages)
    return valid[:MAX_SCANNED_PAGES]
