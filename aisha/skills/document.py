"""Document processing skill: extract text from PDF/DOCX and summarize via LLM."""

import asyncio
import base64
import io
import logging
import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from aisha.config import OPENAI_API_KEY

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_TEXT_CHARS = 100_000  # ~25k tokens — safe for gpt-4.1 128k context

# Heurística: PDFs com menos de 50 caracteres por página são tratados como escaneados
_SCANNED_CHARS_PER_PAGE_THRESHOLD = 50
# Resolução de renderização para visão (DPI). 150 é suficiente para OCR de qualidade.
_PDF_RENDER_DPI = 150

_SUMMARIZE_PROMPT = """\
Você é Aisha, uma assistente pessoal. O usuário enviou um documento e quer que você o analise.

Instruções:
- Se o usuário enviou uma instrução junto com o documento, siga essa instrução.
- Se não há instrução, faça um resumo completo e estruturado do documento.
- Use o idioma do documento.
- Preserve informações-chave: números, datas, nomes, conclusões.
- Use formatação clara com seções e bullet points quando apropriado."""


def _is_scanned_pdf(file_bytes: bytes) -> bool:
    """Return True if the PDF appears to be scanned (image-only, no native text)."""
    import pymupdf

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    total_chars = sum(len(page.get_text()) for page in doc)
    total_pages = max(len(doc), 1)
    chars_per_page = total_chars / total_pages
    log.info(f"PDF text density: {chars_per_page:.1f} chars/page ({total_pages} pages)")
    return chars_per_page < _SCANNED_CHARS_PER_PAGE_THRESHOLD


def _pdf_pages_to_base64_images(file_bytes: bytes) -> list[str]:
    """Render each PDF page as a PNG image and return a list of base64-encoded strings."""
    import pymupdf

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    zoom = _PDF_RENDER_DPI / 72  # pymupdf default is 72 DPI
    matrix = pymupdf.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        png_bytes = pix.tobytes("png")
        images.append(base64.b64encode(png_bytes).decode("utf-8"))
    log.info(f"Rendered {len(images)} PDF page(s) to images at {_PDF_RENDER_DPI} DPI")
    return images


async def _extract_pdf_text_vision(file_bytes: bytes) -> str:
    """Extract text from a scanned PDF by sending each page as an image to gpt-4.1 vision."""
    page_images = await asyncio.to_thread(_pdf_pages_to_base64_images, file_bytes)

    content: list[dict] = [
        {"type": "input_text", "text": "Extraia todo o texto deste documento página por página, preservando a estrutura original (títulos, parágrafos, tabelas, listas). Não faça resumos — transcreva o conteúdo completo."},
    ]
    for i, b64 in enumerate(page_images):
        content.append({"type": "input_text", "text": f"--- Página {i + 1} ---"})
        content.append({"type": "input_image", "image_url": f"data:image/png;base64,{b64}"})

    response = await _client.responses.create(
        model="gpt-4.1",
        input=[{"role": "user", "content": content}],
    )

    text_parts = [
        item.text
        for out in response.output
        if out.type == "message"
        for item in out.content
        if item.type == "output_text"
    ]
    extracted = "\n\n".join(text_parts)
    log.info(f"Vision OCR extracted {len(extracted)} chars from {len(page_images)} page(s)")
    return extracted


def _extract_pdf_text_native(file_bytes: bytes) -> str:
    """Extract text from a native (non-scanned) PDF using pymupdf4llm."""
    import pymupdf4llm

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        return pymupdf4llm.to_markdown(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract PDF text, using vision OCR as fallback for scanned documents."""
    if await asyncio.to_thread(_is_scanned_pdf, file_bytes):
        log.info("PDF detected as scanned — using vision OCR")
        return await _extract_pdf_text_vision(file_bytes)
    log.info("PDF detected as native — using pymupdf4llm")
    return await asyncio.to_thread(_extract_pdf_text_native, file_bytes)


def _extract_docx_text(file_bytes: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts: list[str] = []

    for block in doc.element.body:
        tag = block.tag.split("}")[-1]
        if tag == "p":
            from docx.oxml.ns import qn
            text = "".join(node.text or "" for node in block.iter(qn("w:t")))
            if text.strip():
                parts.append(text)
        elif tag == "tbl":
            from docx.table import Table
            table = Table(block, doc)
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(" | ".join(cells))
            if rows:
                parts.append("\n".join(rows))

    return "\n\n".join(parts)


async def extract_text_async(file_bytes: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        return await _extract_pdf_text(file_bytes)
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return await asyncio.to_thread(_extract_docx_text, file_bytes)
    else:
        raise ValueError(f"Unsupported MIME type: {mime_type}")


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
