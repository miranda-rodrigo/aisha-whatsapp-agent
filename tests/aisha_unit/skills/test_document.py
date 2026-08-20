"""Testes unitários da skill de documentos."""

import sys
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import namespace

if "openai" not in sys.modules:
    sys.modules["openai"] = ModuleType("openai")
if not hasattr(sys.modules["openai"], "AsyncOpenAI"):
    sys.modules["openai"].AsyncOpenAI = MagicMock(return_value=MagicMock())

from aisha.skills import document


class DocumentContractTests(TestCase):
    def test_supported_mime_types_are_explicit(self):
        self.assertTrue(document.is_supported_document("application/pdf"))
        self.assertTrue(
            document.is_supported_document(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        )
        self.assertFalse(document.is_supported_document("text/plain"))


class DocumentExtractionTests(IsolatedAsyncioTestCase):
    async def test_extract_text_routes_pdf_and_docx(self):
        pdf = AsyncMock(return_value="pdf")
        to_thread = AsyncMock(return_value="docx")

        with (
            patch.object(document, "_extract_pdf_text", pdf),
            patch.object(document.asyncio, "to_thread", to_thread),
        ):
            self.assertEqual(
                await document.extract_text_async(b"pdf", "application/pdf"),
                "pdf",
            )
            self.assertEqual(
                await document.extract_text_async(
                    b"docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
                "docx",
            )

        pdf.assert_awaited_once_with(b"pdf", None)
        to_thread.assert_awaited_once_with(document._extract_docx_text, b"docx")

    async def test_extract_text_rejects_unknown_mime(self):
        with self.assertRaisesRegex(ValueError, "Unsupported MIME type"):
            await document.extract_text_async(b"x", "text/plain")

    async def test_native_pdf_uses_native_extractor(self):
        async def fake_to_thread(function, *args):
            if function is document.get_pdf_info:
                return False, 8
            self.assertIs(function, document._extract_pdf_text_native)
            return "texto nativo"

        with (
            patch.object(document.asyncio, "to_thread", side_effect=fake_to_thread),
            patch.object(document, "extract_scanned_pages", AsyncMock()) as ocr,
        ):
            result = await document._extract_pdf_text(b"pdf")

        self.assertEqual(result, "texto nativo")
        ocr.assert_not_awaited()

    async def test_scanned_pdf_limits_pages_sent_to_ocr(self):
        to_thread = AsyncMock(return_value=(True, 20))
        ocr = AsyncMock(return_value="texto OCR")

        with (
            patch.object(document.asyncio, "to_thread", to_thread),
            patch.object(document, "extract_scanned_pages", ocr),
        ):
            result = await document._extract_pdf_text(b"pdf")

        self.assertEqual(result, "texto OCR")
        ocr.assert_awaited_once_with(
            b"pdf", list(range(document.MAX_SCANNED_PAGES))
        )

    async def test_scanned_ocr_builds_page_markers_and_collects_text(self):
        response = namespace(
            output=[
                namespace(
                    type="message",
                    content=[
                        namespace(type="output_text", text="Página um"),
                        namespace(type="other", text="ignorar"),
                    ],
                ),
                namespace(type="other", content=[]),
                namespace(
                    type="message",
                    content=[namespace(type="output_text", text="Página dois")],
                ),
            ]
        )
        create = AsyncMock(return_value=response)
        fake_client = namespace(responses=namespace(create=create))

        with (
            patch.object(
                document.asyncio,
                "to_thread",
                AsyncMock(return_value=["base64-a", "base64-b"]),
            ),
            patch.object(document, "_client", fake_client),
        ):
            result = await document.extract_scanned_pages(b"pdf", [0, 2])

        self.assertEqual(result, "Página um\n\nPágina dois")
        content = create.await_args.kwargs["input"][0]["content"]
        self.assertIn({"type": "input_text", "text": "--- Página 1 ---"}, content)
        self.assertIn({"type": "input_text", "text": "--- Página 3 ---"}, content)
        self.assertIn(
            {"type": "input_image", "image_url": "data:image/png;base64,base64-b"},
            content,
        )


class DocumentSummaryTests(IsolatedAsyncioTestCase):
    async def test_summary_includes_instruction_and_truncation_marker(self):
        response = namespace(
            choices=[namespace(message=namespace(content="  resultado  "))]
        )
        create = AsyncMock(return_value=response)
        fake_client = namespace(chat=namespace(completions=namespace(create=create)))

        with patch.object(document, "_client", fake_client):
            result = await document.summarize_document(
                "x" * (document.MAX_TEXT_CHARS + 10),
                "Liste riscos",
            )

        self.assertEqual(result, "resultado")
        kwargs = create.await_args.kwargs
        self.assertEqual(kwargs["model"], document.DOCUMENT_MODEL)
        self.assertEqual(kwargs["model"], "gpt-5.6-sol")
        self.assertEqual(kwargs["service_tier"], "fast")
        self.assertEqual(kwargs["temperature"], 0.3)
        user_message = kwargs["messages"][1]["content"]
        self.assertTrue(user_message.startswith("INSTRUÇÃO DO USUÁRIO: Liste riscos"))
        self.assertIn("[... documento truncado ...]", user_message)
        self.assertEqual(user_message.count("x"), document.MAX_TEXT_CHARS)
