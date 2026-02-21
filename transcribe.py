"""Audio transcription using OpenAI Whisper API."""

import asyncio
import math
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

from config import OPENAI_API_KEY

MAX_FILE_SIZE = 24 * 1024 * 1024  # 24 MB safety margin for Whisper's 25 MB limit
CHUNK_DURATION_SECONDS = 600  # 10 minutes per chunk

MIME_TO_EXT = {
    "audio/ogg": ".ogg",
    "audio/ogg; codecs=opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
}


def _get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _convert_to_mp3(input_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-i", str(input_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "4",
            "-y",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def _split_audio(audio_path: Path, chunk_duration: int, tmp_dir: str) -> list[Path]:
    duration = _get_audio_duration(audio_path)
    num_chunks = math.ceil(duration / chunk_duration)
    chunks = []

    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = Path(tmp_dir) / f"chunk_{i:03d}.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-i", str(audio_path),
                "-ss", str(start),
                "-t", str(chunk_duration),
                "-acodec", "libmp3lame",
                "-q:a", "4",
                "-y",
                str(chunk_path),
            ],
            check=True,
            capture_output=True,
        )
        chunks.append(chunk_path)

    return chunks


def _transcribe_file(client: OpenAI, audio_path: Path) -> str:
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return transcription.text


def _transcribe_sync(audio_bytes: bytes, mime_type: str) -> str:
    """Synchronous transcription pipeline: convert, chunk if needed, transcribe."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    ext = MIME_TO_EXT.get(mime_type, ".ogg")

    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_path = Path(tmp_dir) / f"input{ext}"
        raw_path.write_bytes(audio_bytes)

        mp3_path = Path(tmp_dir) / "audio.mp3"
        _convert_to_mp3(raw_path, mp3_path)

        file_size = mp3_path.stat().st_size

        if file_size <= MAX_FILE_SIZE:
            return _transcribe_file(client, mp3_path)

        chunks = _split_audio(mp3_path, CHUNK_DURATION_SECONDS, tmp_dir)
        total = len(chunks)
        results: dict[int, str] = {}

        def _do_chunk(idx: int, chunk_path: Path) -> tuple[int, str]:
            return idx, _transcribe_file(client, chunk_path)

        with ThreadPoolExecutor(max_workers=min(total, 4)) as executor:
            futures = [executor.submit(_do_chunk, i, c) for i, c in enumerate(chunks)]
            for f in futures:
                idx, text = f.result()
                results[idx] = text

        return "\n".join(results[i] for i in range(total))


async def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str) -> str:
    """Async wrapper — runs transcription in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(_transcribe_sync, audio_bytes, mime_type)
