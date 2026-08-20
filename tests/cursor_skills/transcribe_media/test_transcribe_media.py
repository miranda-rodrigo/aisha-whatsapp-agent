"""Testes da skill transcribe-media (scripts, sem Whisper de verdade)."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO_ROOT / ".cursor" / "skills" / "transcribe-media" / "scripts"
_CLAUDE_SCRIPTS = _REPO_ROOT / ".claude" / "skills" / "transcribe-media" / "scripts"


def _load(name: str):
    path = _SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"transcribe_media_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Sibling imports (cleanup -> transcribe) resolve against the scripts dir.
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    spec.loader.exec_module(module)
    return module


transcribe = _load("transcribe")
cleanup = _load("cleanup")


SAMPLE_VTT = """WEBVTT
Kind: captions
Language: pt

00:00:00.000 --> 00:00:02.000
olá
olá mundo

00:00:02.000 --> 00:00:04.000
olá mundo
"""

SAMPLE_SRT = """1
00:00:01,000 --> 00:00:02,000
<c>hello</c> &nbsp;world
"""


class CaptionParseTests(unittest.TestCase):
    def test_strips_vtt_chrome_and_duplicates(self):
        self.assertEqual(transcribe.parse_caption_text(SAMPLE_VTT), "olá\nolá mundo")

    def test_strips_html_tags_and_srt_index(self):
        self.assertEqual(transcribe.parse_caption_text(SAMPLE_SRT), "hello world")


class TextSourceTests(unittest.TestCase):
    def test_txt_is_copied_to_raw_without_whisper(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "notes.txt"
            src.write_text("hello from txt\n", encoding="utf-8")
            out = Path(tmp) / "out"
            with patch.object(transcribe, "_whisper_path") as whisper:
                meta = transcribe.transcribe_to_dir(str(src), out)

            whisper.assert_not_called()
            self.assertEqual(meta["method"], "text")
            self.assertEqual((out / "raw.txt").read_text(encoding="utf-8"), "hello from txt\n")
            saved = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["method"], "text")
            self.assertIn("raw.txt", saved["files"])

    def test_srt_becomes_paragraphs_and_keeps_raw_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "talk.srt"
            src.write_text(SAMPLE_SRT, encoding="utf-8")
            out = Path(tmp) / "out"
            meta = transcribe.transcribe_to_dir(str(src), out)

            self.assertEqual(meta["method"], "text")
            self.assertEqual((out / "raw.txt").read_text(encoding="utf-8"), "hello world\n")
            self.assertTrue((out / "raw.srt").exists())
            self.assertIn("00:00:01,000", (out / "raw.srt").read_text(encoding="utf-8"))

    def test_existing_raw_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "notes.txt"
            src.write_text("second\n", encoding="utf-8")
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "raw.txt").write_text("first\n", encoding="utf-8")

            meta = transcribe.transcribe_to_dir(str(src), out)

            self.assertTrue(meta.get("skipped"))
            self.assertEqual((out / "raw.txt").read_text(encoding="utf-8"), "first\n")


class UrlFallbackTests(unittest.TestCase):
    def test_url_without_captions_falls_back_to_whisper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            audio_dir = Path(tmp) / "download"
            audio_dir.mkdir()
            audio = audio_dir / "audio.m4a"
            audio.write_bytes(b"fake")

            with (
                patch.object(transcribe, "_try_captions", return_value=(None, None)),
                patch.object(transcribe, "_download_url_audio", return_value=audio) as download,
                patch.object(
                    transcribe, "_whisper_path", return_value=("fala bruta", None, 12.0)
                ) as whisper,
            ):
                meta = transcribe.transcribe_to_dir(
                    "https://youtu.be/abcdefghijk", out
                )

            download.assert_called_once()
            whisper.assert_called_once_with(audio)
            self.assertEqual(meta["method"], "whisper")
            self.assertEqual(meta["duration"], 12.0)
            self.assertEqual((out / "raw.txt").read_text(encoding="utf-8"), "fala bruta\n")

    def test_url_with_captions_skips_whisper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            with (
                patch.object(
                    transcribe,
                    "_try_captions",
                    return_value=("olá mundo", SAMPLE_VTT),
                ),
                patch.object(transcribe, "_whisper_path") as whisper,
                patch.object(transcribe, "_download_url_audio") as download,
            ):
                meta = transcribe.transcribe_to_dir("https://youtu.be/abcdefghijk", out)

            whisper.assert_not_called()
            download.assert_not_called()
            self.assertEqual(meta["method"], "captions")
            self.assertEqual((out / "raw.txt").read_text(encoding="utf-8"), "olá mundo\n")
            self.assertTrue((out / "raw.srt").exists())


class CleanupTests(unittest.TestCase):
    def test_cleanup_does_not_alter_raw_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.txt"
            raw.write_text("uh hello world hmm\n", encoding="utf-8")
            original = raw.read_bytes()
            dest = Path(tmp) / "cleaned.txt"

            result = cleanup.cleanup_file(raw, dest)

            self.assertEqual(raw.read_bytes(), original)
            self.assertTrue(dest.exists())
            self.assertNotIn("uh", result.split())
            self.assertNotIn("hmm", result.split())
            self.assertIn("hello", result)

    def test_keeps_portuguese_content_words_and_article_um(self):
        text = "então tipo né um gato um,"
        cleaned = cleanup.cleanup_text(text)
        self.assertIn("então", cleaned)
        self.assertIn("tipo", cleaned)
        self.assertIn("né", cleaned)
        self.assertIn("um gato", cleaned)
        self.assertNotRegex(cleaned, r"\bum,")

    def test_srt_input_becomes_paragraphs(self):
        cleaned = cleanup.cleanup_text(SAMPLE_SRT)
        self.assertEqual(cleaned.strip(), "hello world")


class SkillCopyTests(unittest.TestCase):
    def test_claude_copy_has_the_same_scripts(self):
        for rel in (
            "scripts/transcribe.py",
            "scripts/cleanup.py",
            "SKILL.md",
            "references/refine-prompt.md",
        ):
            cursor = (_REPO_ROOT / ".cursor" / "skills" / "transcribe-media" / rel).read_text(
                encoding="utf-8"
            )
            claude = (_REPO_ROOT / ".claude" / "skills" / "transcribe-media" / rel).read_text(
                encoding="utf-8"
            )
            self.assertEqual(cursor, claude, f"{rel} diverged between Cursor and Claude copies")
