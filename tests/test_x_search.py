import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("WHATSAPP_TOKEN", "test")
os.environ.setdefault("WHATSAPP_PHONE_ID", "test")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test")

from aisha.skills.x_search import (
    build_x_search_tool,
    normalize_handles,
    search_x,
    validate_date,
)
from aisha.tools import TOOL_DEFINITIONS, ToolContext, execute_tool


def _fake_response(text: str, annotation_urls: list[str] | None = None, citations=None):
    annotations = [SimpleNamespace(url=u) for u in (annotation_urls or [])]
    content = SimpleNamespace(type="output_text", text=text, annotations=annotations)
    message = SimpleNamespace(type="message", content=[content])
    return SimpleNamespace(output=[message], citations=citations or [])


class NormalizeHandlesTests(unittest.TestCase):
    def test_strips_at_and_dupes(self):
        self.assertEqual(
            normalize_handles(["@Nubank", "nubank", "  ElonMusk  "]),
            ["Nubank", "ElonMusk"],
        )

    def test_caps_at_20(self):
        handles = [f"user{i}" for i in range(25)]
        self.assertEqual(len(normalize_handles(handles)), 20)

    def test_empty(self):
        self.assertEqual(normalize_handles(None), [])
        self.assertEqual(normalize_handles(["", "@", 123]), [])


class BuildToolTests(unittest.TestCase):
    def test_allowed_wins_over_excluded(self):
        tool = build_x_search_tool(
            allowed_handles=["nubank"],
            excluded_handles=["spam"],
        )
        self.assertEqual(tool["type"], "x_search")
        self.assertEqual(tool["allowed_x_handles"], ["nubank"])
        self.assertNotIn("excluded_x_handles", tool)

    def test_excluded_only(self):
        tool = build_x_search_tool(excluded_handles=["@spam"])
        self.assertEqual(tool["excluded_x_handles"], ["spam"])

    def test_dates(self):
        tool = build_x_search_tool(from_date="2026-08-01", to_date="2026-08-16")
        self.assertEqual(tool["from_date"], "2026-08-01")
        self.assertEqual(tool["to_date"], "2026-08-16")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            validate_date("16/08/2026", "from_date")
        with self.assertRaises(ValueError):
            build_x_search_tool(from_date="2026/08/16")


class SearchXTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_query(self):
        result = await search_x("   ")
        self.assertIn("error", result)

    async def test_missing_api_key(self):
        with patch.dict(os.environ, {"XAI_API_KEY": ""}, clear=False):
            result = await search_x("Pix")
        self.assertIn("XAI_API_KEY", result["error"])

    async def test_invalid_date_returns_error(self):
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test"}):
            result = await search_x("Pix", from_date="ontem")
        self.assertIn("YYYY-MM-DD", result["error"])

    async def test_success_extracts_summary_and_citations(self):
        fake = _fake_response(
            "O Pix está em alta no X.[[1]](https://x.com/i/status/1)",
            annotation_urls=["https://x.com/i/status/1"],
            citations=["https://x.com/i/status/1", "https://x.com/i/status/2"],
        )
        mock_client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=fake)))
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test"}), patch(
            "aisha.skills.x_search._get_client", return_value=mock_client
        ):
            result = await search_x("Pix", language="português")
        self.assertEqual(result["query"], "Pix")
        self.assertIn("Pix está em alta", result["summary"])
        self.assertEqual(
            result["citations"],
            ["https://x.com/i/status/1", "https://x.com/i/status/2"],
        )
        self.assertIn("WhatsApp", result["note"])
        kwargs = mock_client.responses.create.await_args.kwargs
        self.assertEqual(kwargs["tools"][0]["type"], "x_search")
        self.assertIn("Pix", kwargs["input"])
        self.assertEqual(kwargs["max_tool_calls"], 1)
        self.assertEqual(kwargs["max_output_tokens"], 1024)

    async def test_markdown_citations_extracted(self):
        fake = _fake_response(
            "Texto.[[1]](https://x.com/a/status/1) mais.[[2]](https://x.com/b/status/2)",
            annotation_urls=[],
            citations=[],
        )
        mock_client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(return_value=fake)))
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test"}), patch(
            "aisha.skills.x_search._get_client", return_value=mock_client
        ):
            result = await search_x("Pix")
        self.assertEqual(
            result["citations"],
            ["https://x.com/a/status/1", "https://x.com/b/status/2"],
        )

    async def test_api_failure(self):
        mock_client = SimpleNamespace(
            responses=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("boom")))
        )
        with patch.dict(os.environ, {"XAI_API_KEY": "xai-test"}), patch(
            "aisha.skills.x_search._get_client", return_value=mock_client
        ):
            result = await search_x("Pix")
        self.assertIn("Falha ao consultar o X", result["error"])


class SearchXToolDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_registered(self):
        names = {t.get("name") for t in TOOL_DEFINITIONS if t.get("type") == "function"}
        self.assertIn("search_x", names)

    async def test_execute_tool_missing_query(self):
        ctx = ToolContext(phone="1", scheduler=None, user_tz="UTC", base_url="http://x")
        result = await execute_tool("search_x", "{}", ctx)
        payload = json.loads(result)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
