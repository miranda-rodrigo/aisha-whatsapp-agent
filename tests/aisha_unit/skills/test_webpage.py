"""Testes unitários da skill de páginas web."""

from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch

from tests.aisha_unit._helpers import async_http_client, http_response

from aisha.skills import webpage


class WebpageParserTests(TestCase):
    def setUp(self):
        webpage._pending.clear()

    def tearDown(self):
        webpage._pending.clear()

    def test_skips_youtube_and_extracts_first_web_url(self):
        text = (
            "Veja https://youtube.com/watch?v=abcdefghijk e "
            "resuma https://example.com/artigo)."
        )

        self.assertEqual(
            webpage.extract_web_url(text), "https://example.com/artigo"
        )
        self.assertEqual(
            webpage.strip_web_url(text),
            "Veja https://youtube.com/watch?v=abcdefghijk e resuma ).",
        )

    def test_returns_original_text_without_eligible_url(self):
        text = "Somente https://youtu.be/abcdefghijk"

        self.assertIsNone(webpage.extract_web_url(text))
        self.assertEqual(webpage.strip_web_url(text), text)

    def test_pending_page_expires(self):
        webpage._pending["5511"] = webpage.PendingPage(
            "https://example.com",
            created_at=datetime.utcnow()
            - timedelta(minutes=webpage._PENDING_TTL_MINUTES + 1),
        )

        self.assertIsNone(webpage.get_pending_page("5511"))
        self.assertNotIn("5511", webpage._pending)


class FetchPageTests(IsolatedAsyncioTestCase):
    async def test_fetches_through_jina_with_expected_contract(self):
        response = http_response(text="# Artigo")
        factory, client = async_http_client(response)

        with patch.object(webpage.httpx, "AsyncClient", factory):
            result = await webpage.fetch_page("https://example.com/a")

        self.assertEqual(result, "# Artigo")
        client.get.assert_awaited_once_with(
            "https://r.jina.ai/https://example.com/a",
            headers={"Accept": "text/markdown", "X-No-Cache": "true"},
            follow_redirects=True,
        )
        response.raise_for_status.assert_called_once()

    async def test_truncates_oversized_content(self):
        response = http_response(text="x" * (webpage._MAX_CHARS + 10))
        factory, _ = async_http_client(response)

        with patch.object(webpage.httpx, "AsyncClient", factory):
            result = await webpage.fetch_page("https://example.com")

        self.assertTrue(result.endswith("[... conteúdo truncado ...]"))
        self.assertEqual(result.count("x"), webpage._MAX_CHARS)
