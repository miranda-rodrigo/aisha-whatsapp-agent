"""Testes unitários da skill de YouTube."""

from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

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
    async def test_short_video_uses_gemini_uri_path(self):
        with (
            patch.object(youtube, "_probe_video", AsyncMock(return_value=None)),
            patch.object(
                youtube, "_analyze_via_gemini", AsyncMock(return_value="resumo")
            ) as gemini,
        ):
            result = await youtube.analyze_video(
                "https://youtu.be/abcdefghijk", "   "
            )

        self.assertEqual(result.text, "resumo")
        gemini.assert_awaited_once_with("https://youtu.be/abcdefghijk", "   ")

    async def test_transcript_summary_uses_luna(self):
        complete = AsyncMock(return_value="resumo luna")

        with patch("aisha.openai_chat.chat_complete_async", complete):
            result = await youtube._summarize_transcript("fala bruta", "resume")

        self.assertEqual(result, "resumo luna")
        system, user = complete.await_args.args
        self.assertEqual(system, youtube._SUMMARIZE_SYSTEM)
        self.assertIn("resume", user)
        self.assertIn("fala bruta", user)
        complete.assert_awaited_once()
