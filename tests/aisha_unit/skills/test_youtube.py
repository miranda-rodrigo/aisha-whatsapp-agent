"""Testes unitários da skill de YouTube."""

from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from tests.aisha_unit._helpers import namespace

from aisha.skills import youtube


class YoutubeParserTests(TestCase):
    def setUp(self):
        youtube._pending.clear()

    def tearDown(self):
        youtube._pending.clear()

    def test_extracts_first_supported_url_and_strips_it(self):
        text = "Analise https://youtu.be/abcdefghijk?t=30 com foco no final"

        self.assertEqual(
            youtube.extract_youtube_url(text),
            "https://youtu.be/abcdefghijk?t=30",
        )
        self.assertEqual(
            youtube.strip_youtube_url(text),
            "Analise  com foco no final",
        )

    def test_rejects_invalid_video_id(self):
        self.assertIsNone(youtube.extract_youtube_url("https://youtu.be/curto"))

    def test_pending_video_expires(self):
        youtube._pending["5511"] = youtube.PendingVideo(
            "https://youtu.be/abcdefghijk",
            created_at=datetime.utcnow()
            - timedelta(minutes=youtube._PENDING_TTL_MINUTES + 1),
        )

        self.assertIsNone(youtube.get_pending_video("5511"))
        self.assertNotIn("5511", youtube._pending)


class YoutubeAnalysisTests(IsolatedAsyncioTestCase):
    async def test_falls_back_and_uses_default_prompt(self):
        generate = AsyncMock(
            side_effect=[RuntimeError("primary unavailable"), namespace(text="resumo")]
        )
        client = namespace(aio=namespace(models=namespace(generate_content=generate)))
        part = MagicMock()

        with (
            patch.object(youtube, "_get_client", return_value=client),
            patch.object(youtube.types.Part, "from_uri", return_value=part) as from_uri,
        ):
            result = await youtube.analyze_video(
                "https://youtu.be/abcdefghijk", "   "
            )

        self.assertEqual(result, "resumo")
        self.assertEqual(
            [call.kwargs["model"] for call in generate.await_args_list],
            [youtube._MODEL, youtube._FALLBACK_MODEL],
        )
        self.assertEqual(
            generate.await_args_list[0].kwargs["contents"],
            [part, youtube._DEFAULT_PROMPT],
        )
        from_uri.assert_called_with(
            file_uri="https://youtu.be/abcdefghijk", mime_type="video/mp4"
        )
