"""Document processing skill: extract text from PDF/DOCX and summarize via LLM."""

import asyncio
import io
import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from config import OPENAI_API_KEY

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TEXT_CHARS = 100_000  # ~25k tokens — safe for gpt-4.1 128k context

_SUMMARIZE_PROMPT = """\
Você é Aisha, uma assistente pessoal. O usuário enviou um documento e quer que você o analise.

Instruções:
- Se o usuário enviou uma instrução junto com o documento, siga essa instrução.
- Se não há instrução, faça um resumo completo e estruturado do documento.
- Use o idioma do documento.
- Preserve informações-chave: números, datas, nomes, conclusões.
- Use formatação clara com seções e bullet points quando apropriado."""


def _extract_pdf_text(file_bytes: bytes) -> str:
    import pymupdf4llm

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        return pymupdf4llm.to_markdown(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _extract_docx_text(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_bytes: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        return _extract_pdf_text(file_bytes)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx_text(file_bytes)
    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")


async def extract_text_async(file_bytes: bytes, mime_type: str) -> str:
    return await asyncio.to_thread(extract_text, file_bytes, mime_type)


async def summarize_document(
    document_text: str,
    user_instruction: str | None = None,
) -> str:
    if len(document_text) > MAX_TEXT_CHARS:
        document_text = document_text[:MAX_TEXT_CHARS] + "\n\n[... documento truncado ...]"

    user_message = f"DOCUMENTO:\n\n{document_text}"
    if user_instruction:
        user_message = f"INSTRUÇÃO DO USUÁRIO: {user_instruction}\n\n{user_message}"

    response = await _client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": _SUMMARIZE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def is_supported_document(mime_type: str) -> bool:
    return mime_type in SUPPORTED_MIME_TYPES
