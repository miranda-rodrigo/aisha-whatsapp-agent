"""Helpers puros para envio de mensagens WhatsApp (testáveis)."""

# Limite da Meta Cloud API para text.body (erro 100 acima disso).
WHATSAPP_TEXT_LIMIT = 4096


def split_whatsapp_text(text: str, limit: int = WHATSAPP_TEXT_LIMIT) -> list[str]:
    """Divide um texto em partes de até `limit` caracteres.

    Prefere quebrar em parágrafos, depois em linhas, depois em espaços,
    para não cortar palavras no meio. Nunca retorna partes vazias.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n\n")
        if cut < limit // 2:
            cut = window.rfind("\n")
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut < limit // 2:
            cut = limit
        chunk = remaining[:cut].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks
