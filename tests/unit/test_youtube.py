import os
import unittest

os.environ.setdefault("WHATSAPP_TOKEN", "test")
os.environ.setdefault("WHATSAPP_PHONE_ID", "test")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test")
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test")
os.environ.setdefault("BASE_URL", "https://aisha.example")

from aisha.skills.video_download import get_download_entry, register_text_download
from aisha.skills.youtube import (
    LONG_VIDEO_BYTES,
    LONG_VIDEO_SECONDS,
    VideoAnalysis,
    _best_filesize,
    _safe_filename,
    format_long_video_reply,
    is_long_video,
    is_transcript_instruction,
    parse_caption_text,
    pop_pending_transcript,
    should_deliver_as_file,
    store_pending_transcript,
    wants_transcript_file,
)


class LongVideoThresholdTests(unittest.TestCase):
    def test_under_25_min_without_large_file_is_not_long(self):
        self.assertFalse(is_long_video(24 * 60, None))
        self.assertFalse(is_long_video(24 * 60, LONG_VIDEO_BYTES))

    def test_exactly_25_min_is_long(self):
        self.assertTrue(is_long_video(25 * 60, None))
        self.assertTrue(is_long_video(25 * 60 + 1, None))

    def test_filesize_triggers_even_when_duration_is_known(self):
        self.assertTrue(is_long_video(10 * 60, LONG_VIDEO_BYTES + 1))
        self.assertTrue(is_long_video(25 * 60, 180 * 1024 * 1024))

    def test_filesize_when_duration_missing(self):
        self.assertFalse(is_long_video(None, LONG_VIDEO_BYTES))
        self.assertTrue(is_long_video(None, LONG_VIDEO_BYTES + 1))

    def test_unknown_metadata_is_not_long(self):
        self.assertFalse(is_long_video(None, None))

    def test_threshold_constants(self):
        self.assertEqual(LONG_VIDEO_SECONDS, 25 * 60)
        self.assertEqual(LONG_VIDEO_BYTES, 80 * 1024 * 1024)

    def test_max_filesize_across_formats(self):
        info = {
            "filesize": 50 * 1024 * 1024,
            "formats": [
                {"filesize": 50 * 1024 * 1024},
                {"filesize_approx": 180 * 1024 * 1024},
            ],
        }
        self.assertEqual(_best_filesize(info), 180 * 1024 * 1024)


class CaptionParseTests(unittest.TestCase):
    def test_strips_vtt_chrome_and_duplicates(self):
        raw = """WEBVTT
Kind: captions
Language: pt

00:00:00.000 --> 00:00:02.000
olá
olá mundo

00:00:02.000 --> 00:00:04.000
olá mundo
"""
        self.assertEqual(parse_caption_text(raw), "olá\nolá mundo")

    def test_strips_html_tags_and_srt_index(self):
        raw = """1
00:00:01,000 --> 00:00:02,000
<c>hello</c> &nbsp;world
"""
        self.assertEqual(parse_caption_text(raw), "hello world")


class TranscriptInstructionTests(unittest.TestCase):
    def test_detects_transcription_intent(self):
        self.assertTrue(is_transcript_instruction("transcreve esse vídeo"))
        self.assertTrue(is_transcript_instruction("manda a transcrição"))
        self.assertFalse(is_transcript_instruction("faz um post no LinkedIn"))
        self.assertFalse(is_transcript_instruction(""))

    def test_explicit_txt_request(self):
        msg = "transcrever... o video é longo, resuma e mande um txt com a transcricao completa"
        self.assertTrue(wants_transcript_file(msg))
        self.assertTrue(should_deliver_as_file(msg, 24 * 60, None))
        self.assertTrue(wants_transcript_file("manda a transcrição completa"))
        self.assertFalse(wants_transcript_file("faz um post no LinkedIn"))

    def test_user_case_25min_180mb(self):
        self.assertTrue(is_long_video(25 * 60, 180 * 1024 * 1024))
        self.assertTrue(should_deliver_as_file("transcreve", 25 * 60, 180 * 1024 * 1024))


class TextDownloadTests(unittest.TestCase):
    def test_register_text_download_roundtrip(self):
        token, filename = register_text_download("texto da transcrição", "Aula / parte 1")
        self.assertTrue(filename.endswith(".txt"))
        self.assertNotIn("/", filename)
        entry = get_download_entry(token)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.media_type, "text/plain")
        self.assertEqual(entry.filepath.read_text(encoding="utf-8"), "texto da transcrição")

    def test_safe_filename_truncates_and_sanitizes(self):
        name = _safe_filename('a' * 120 + ':"?')
        self.assertTrue(name.endswith(".txt"))
        self.assertLessEqual(len(name), 84)
        self.assertNotIn(":", name)

    def test_long_reply_includes_summary_duration_and_link(self):
        text = format_long_video_reply(
            "Resumo curto",
            "Palestra.txt",
            "https://aisha.example/download/abc",
            40 * 60,
        )
        self.assertIn("Resumo curto", text)
        self.assertIn("40 min", text)
        self.assertIn("Palestra.txt", text)
        self.assertIn("https://aisha.example/download/abc", text)

    def test_pending_transcript_store(self):
        analysis = VideoAnalysis(text="x", download_token="tok")
        store_pending_transcript("5511", analysis)
        self.assertEqual(pop_pending_transcript("5511").download_token, "tok")
        self.assertIsNone(pop_pending_transcript("5511"))

    def test_pending_without_token_is_ignored(self):
        store_pending_transcript("5511", VideoAnalysis(text="só texto"))
        self.assertIsNone(pop_pending_transcript("5511"))


if __name__ == "__main__":
    unittest.main()
