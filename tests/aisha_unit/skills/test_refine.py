"""Testes unitários da skill de refinamento."""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from aisha.skills import refine


class RefineTests(IsolatedAsyncioTestCase):
    async def test_sends_whole_transcript_in_one_luna_call(self):
        mapper = AsyncMock(return_value=["texto refinado"])

        with patch.object(refine, "map_chat_chunks_async", mapper):
            result = await refine.refine_transcription("fala bruta")

        self.assertEqual(result, "texto refinado")
        system, chunks, user_fn = mapper.await_args.args
        self.assertEqual(system, refine._SYSTEM_PROMPT)
        self.assertEqual(chunks, ["fala bruta"])
        self.assertEqual(user_fn(0, "fala bruta", 1), "fala bruta")
        self.assertEqual(refine.refine_model_id(), "gpt-5.6-luna")

    async def test_parallel_chunks_keep_original_order(self):
        mapper = AsyncMock(return_value=["um", "dois"])

        with (
            patch.object(refine, "chunk_text", return_value=["a" * 10, "b" * 10]),
            patch.object(refine, "map_chat_chunks_async", mapper),
        ):
            result = await refine.refine_transcription("ignored")

        self.assertEqual(result, "um\n\ndois")
        user_fn = mapper.await_args.args[2]
        self.assertIn("Parte 1 de 2", user_fn(0, "aaa", 2))
        self.assertIn("Parte 2 de 2", user_fn(1, "bbb", 2))

    async def test_empty_raw_fails_explicitly(self):
        with self.assertRaises(RuntimeError) as ctx:
            await refine.refine_transcription("   ")
        self.assertIn("vazio", str(ctx.exception))
