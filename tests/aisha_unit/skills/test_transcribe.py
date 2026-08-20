"""Testes unitários da skill de transcrição."""

import sys
from pathlib import Path
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

if "openai" not in sys.modules:
    sys.modules["openai"] = ModuleType("openai")
if not hasattr(sys.modules["openai"], "OpenAI"):
    sys.modules["openai"].OpenAI = MagicMock(return_value=MagicMock())

from aisha.skills import transcribe


class TranscribeCommandTests(TestCase):
    def test_audio_duration_uses_one_ffprobe_call_for_streams_and_duration(self):
        completed = MagicMock(
            stdout='{"format":{"duration":"123.45"},"streams":[{"codec_type":"audio","codec_name":"opus"}]}\n'
        )

        with patch.object(
            transcribe.subprocess, "run", return_value=completed
        ) as run:
            duration = transcribe._get_audio_duration(Path("/tmp/audio.ogg"))

        self.assertEqual(duration, 123.45)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "ffprobe")
        self.assertEqual(command[-1], "/tmp/audio.ogg")
        self.assertIn("format=duration:stream=codec_type,codec_name", command)
        self.assertEqual(run.call_count, 1)
        self.assertTrue(run.call_args.kwargs["check"])

    def test_split_audio_rounds_up_and_builds_ordered_chunks(self):
        with (
            patch.object(transcribe, "_get_audio_duration", return_value=1201),
            patch.object(transcribe.subprocess, "run") as run,
        ):
            chunks = transcribe._split_audio(
                Path("/tmp/audio.mp3"), 600, "/tmp/chunks"
            )

        self.assertEqual(
            chunks,
            [
                Path("/tmp/chunks/chunk_000.mp3"),
                Path("/tmp/chunks/chunk_001.mp3"),
                Path("/tmp/chunks/chunk_002.mp3"),
            ],
        )
        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            [call.args[0][call.args[0].index("-ss") + 1] for call in run.call_args_list],
            ["0", "600", "1200"],
        )

    def test_small_compatible_audio_skips_mp3_recode(self):
        with (
            patch.object(transcribe, "OpenAI") as openai,
            patch.object(transcribe, "_convert_to_mp3") as convert,
            patch.object(
                transcribe, "_transcribe_file", return_value="texto"
            ) as transcribe_file,
            patch.object(transcribe, "_split_audio") as split,
        ):
            result = transcribe._transcribe_sync(b"ogg-bytes", "audio/ogg")

        self.assertEqual(result, "texto")
        openai.assert_called_once_with(api_key=transcribe.OPENAI_API_KEY)
        convert.assert_not_called()
        split.assert_not_called()
        transcribe_file.assert_called_once()
        self.assertEqual(transcribe_file.call_args.args[1].suffix, ".ogg")

    def test_small_mp3_is_transcribed_once_without_recode(self):
        with (
            patch.object(transcribe, "OpenAI") as openai,
            patch.object(transcribe, "_convert_to_mp3") as convert,
            patch.object(
                transcribe, "_transcribe_file", return_value="texto"
            ) as transcribe_file,
            patch.object(transcribe, "_split_audio") as split,
        ):
            result = transcribe._transcribe_sync(b"audio", "audio/mpeg")

        self.assertEqual(result, "texto")
        openai.assert_called_once_with(api_key=transcribe.OPENAI_API_KEY)
        convert.assert_not_called()
        transcribe_file.assert_called_once()
        split.assert_not_called()
        self.assertEqual(transcribe_file.call_args.args[1].suffix, ".mp3")

    def test_oversize_file_is_converted(self):
        def fake_convert(_source, destination):
            destination.write_bytes(b"mp3")

        with (
            patch.object(transcribe, "OpenAI"),
            patch.object(transcribe, "_convert_to_mp3", side_effect=fake_convert) as convert,
            patch.object(transcribe, "_should_send_raw", return_value=False),
            patch.object(
                transcribe, "_transcribe_file", return_value="texto"
            ) as transcribe_file,
            patch.object(transcribe, "_split_audio") as split,
        ):
            result = transcribe._transcribe_sync(b"audio", "audio/ogg")

        self.assertEqual(result, "texto")
        convert.assert_called_once()
        transcribe_file.assert_called_once()
        split.assert_not_called()
        self.assertEqual(transcribe_file.call_args.args[1].suffix, ".mp3")


class TranscribeAsyncTests(IsolatedAsyncioTestCase):
    async def test_async_wrapper_delegates_to_thread(self):
        to_thread = AsyncMock(return_value="transcrição")

        with patch.object(transcribe.asyncio, "to_thread", to_thread):
            result = await transcribe.transcribe_audio_bytes(
                b"bytes", "audio/ogg"
            )

        self.assertEqual(result, "transcrição")
        to_thread.assert_awaited_once_with(
            transcribe._transcribe_sync, b"bytes", "audio/ogg"
        )
