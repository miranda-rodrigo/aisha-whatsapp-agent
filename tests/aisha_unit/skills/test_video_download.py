"""Testes unitários da skill de download de vídeos."""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import MagicMock, patch

from aisha.skills import video_download


class VideoDownloadParserTests(TestCase):
    def test_extracts_youtube_before_twitter(self):
        text = (
            "https://x.com/user/status/123 e "
            "https://youtu.be/abcdefghijk"
        )

        self.assertEqual(
            video_download.extract_video_url(text),
            "https://youtu.be/abcdefghijk",
        )

    def test_strips_twitter_url_and_trailing_punctuation(self):
        text = "Baixe https://x.com/user/status/12345, por favor"

        self.assertEqual(
            video_download.strip_video_url(text), "Baixe , por favor"
        )


class DownloadRegistryTests(TestCase):
    def setUp(self):
        video_download._downloads.clear()

    def tearDown(self):
        video_download._downloads.clear()

    def test_expired_entry_is_removed_and_file_deleted(self):
        path = MagicMock()
        path.exists.return_value = True
        video_download._downloads["old"] = video_download.DownloadEntry(
            filepath=path,
            filename="old.mp4",
            created_at=datetime.utcnow()
            - timedelta(minutes=video_download._TTL_MINUTES + 1),
        )

        self.assertIsNone(video_download.get_download_entry("old"))
        path.unlink.assert_called_once()
        self.assertNotIn("old", video_download._downloads)

    def test_cleanup_only_removes_expired_entries(self):
        now = datetime.utcnow()
        video_download._downloads["old"] = video_download.DownloadEntry(
            MagicMock(exists=MagicMock(return_value=False)),
            "old.mp4",
            now - timedelta(minutes=31),
        )
        video_download._downloads["new"] = video_download.DownloadEntry(
            MagicMock(), "new.mp4", now
        )

        self.assertEqual(video_download.cleanup_expired(), 1)
        self.assertEqual(set(video_download._downloads), {"new"})


class DownloadVideoTests(IsolatedAsyncioTestCase):
    async def test_registers_download_and_sanitizes_filename_without_yt_dlp(self):
        fake_yt_dlp = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            expected_dir = Path(tmp) / "aisha_downloads"

            async def fake_to_thread(function, options, url):
                self.assertIs(function, video_download._run_download)
                self.assertEqual(url, "https://example.com/video")
                self.assertTrue(options["noplaylist"])
                (expected_dir / "fixed.mp4").write_bytes(b"video")
                return {"title": 'Título: "inválido"'}

            with (
                patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}),
                patch.object(video_download.tempfile, "gettempdir", return_value=tmp),
                patch.object(
                    video_download.secrets, "token_urlsafe", return_value="fixed"
                ),
                patch.object(
                    video_download.asyncio,
                    "to_thread",
                    side_effect=fake_to_thread,
                ),
            ):
                token, filename = await video_download.download_video(
                    "https://example.com/video"
                )

        self.assertEqual((token, filename), ("fixed", "Título_ _inválido_.mp4"))
        self.assertEqual(
            video_download._downloads["fixed"].filename,
            "Título_ _inválido_.mp4",
        )
