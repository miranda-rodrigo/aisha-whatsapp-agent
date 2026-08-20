"""Testes do helper de chat (Luna, reasoning none, chunks grandes)."""

from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import namespace

from aisha import openai_chat
from aisha.models import CHAT_CHUNK_CHARS, CHAT_MODEL, REASONING_EFFORT


class ChatContractTests(TestCase):
    def test_chat_model_is_luna_with_reasoning_none(self):
        self.assertEqual(CHAT_MODEL, "gpt-5.6-luna")
        self.assertEqual(REASONING_EFFORT, "none")
        self.assertEqual(openai_chat.CHAT_MODEL, "gpt-5.6-luna")

    def test_chat_chunks_stay_under_long_context_surcharge(self):
        self.assertGreaterEqual(CHAT_CHUNK_CHARS, 100_000)
        self.assertLess(CHAT_CHUNK_CHARS, 1_000_000)
        self.assertEqual(CHAT_CHUNK_CHARS, 200_000)

    def test_typical_transcript_fits_in_one_chunk(self):
        text = "fala " * 10_000
        self.assertEqual(len(openai_chat.chunk_text(text)), 1)

    def test_huge_text_splits_near_paragraph_breaks(self):
        block = ("parágrafo.\n\n" * 20_000)
        chunks = openai_chat.chunk_text(block)
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(max(len(c) for c in chunks), CHAT_CHUNK_CHARS)


class ChatCompleteTests(TestCase):
    def test_prefers_responses_api_without_temperature(self):
        response = namespace(output_text="  editado  ", output=None)
        client = MagicMock()
        client.responses.create.return_value = response

        with patch.object(openai_chat, "openai_client", return_value=client):
            text = openai_chat.chat_complete("sys", "user", temperature=0.2)

        self.assertEqual(text, "editado")
        kwargs = client.responses.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-5.6-luna")
        self.assertEqual(kwargs["instructions"], "sys")
        self.assertEqual(kwargs["input"], "user")
        self.assertEqual(kwargs["reasoning"], {"effort": "none"})
        self.assertNotIn("temperature", kwargs)
        client.chat.completions.create.assert_not_called()

    def test_falls_back_to_chat_completions_when_responses_missing(self):
        choice = namespace(message=namespace(content="via completions"))

        class LegacyClient:
            chat = MagicMock()

        client = LegacyClient()
        client.chat.completions.create.return_value = namespace(choices=[choice])

        with patch.object(openai_chat, "openai_client", return_value=client):
            text = openai_chat.chat_complete("sys", "user")

        self.assertEqual(text, "via completions")
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-5.6-luna")
        self.assertEqual(kwargs["reasoning_effort"], "none")
        self.assertNotIn("temperature", kwargs)


class ChatCompleteAsyncTests(IsolatedAsyncioTestCase):
    async def test_async_uses_reasoning_none(self):
        response = namespace(output_text="ok", output=None)
        client = MagicMock()
        client.responses.create = AsyncMock(return_value=response)

        with patch.object(openai_chat, "async_openai_client", return_value=client):
            text = await openai_chat.chat_complete_async("sys", "user")

        self.assertEqual(text, "ok")
        self.assertEqual(
            client.responses.create.await_args.kwargs["reasoning"],
            {"effort": "none"},
        )
