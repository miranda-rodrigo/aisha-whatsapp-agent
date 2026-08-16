"""Testes unitários da skill de refinamento."""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from tests.aisha_unit._helpers import namespace

from aisha.skills import refine


class RefineTests(IsolatedAsyncioTestCase):
    def tearDown(self):
        refine._client = None

    async def test_generate_sends_stable_prompt_and_strips_response(self):
        generate = AsyncMock(return_value=namespace(text="  texto refinado \n"))
        client = namespace(aio=namespace(models=namespace(generate_content=generate)))

        with patch.object(refine, "_get_client", return_value=client):
            result = await refine._generate("modelo", "fala bruta")

        self.assertEqual(result, "texto refinado")
        kwargs = generate.await_args.kwargs
        self.assertEqual(kwargs["model"], "modelo")
        self.assertEqual(kwargs["contents"], "fala bruta")
        self.assertEqual(kwargs["config"].system_instruction, refine._SYSTEM_PROMPT)
        self.assertEqual(kwargs["config"].temperature, 0.3)

    async def test_retries_with_fallback_only_for_503(self):
        class FakeServerError(Exception):
            def __init__(self, code):
                self.code = code

        generate = AsyncMock(
            side_effect=[FakeServerError(503), "texto recuperado"]
        )

        with (
            patch.object(refine, "ServerError", FakeServerError),
            patch.object(refine, "_generate", generate),
        ):
            result = await refine.refine_transcription("fala")

        self.assertEqual(result, "texto recuperado")
        self.assertEqual(
            [call.args for call in generate.await_args_list],
            [
                (refine._PRIMARY_MODEL, "fala"),
                (refine._FALLBACK_MODEL, "fala"),
            ],
        )

    async def test_propagates_non_503_error_without_fallback(self):
        class FakeServerError(Exception):
            def __init__(self, code):
                self.code = code

        generate = AsyncMock(side_effect=FakeServerError(500))

        with (
            patch.object(refine, "ServerError", FakeServerError),
            patch.object(refine, "_generate", generate),
        ):
            with self.assertRaises(FakeServerError):
                await refine.refine_transcription("fala")

        generate.assert_awaited_once_with(refine._PRIMARY_MODEL, "fala")
