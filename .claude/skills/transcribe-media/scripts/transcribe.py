#!/usr/bin/env python3
"""Transcribe video, audio, URL, or existing transcript text to raw.txt.

Does not import the Aisha package. Missing tools/keys fail with a clear
message so the agent can ask the user before installing anything.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MAX_FILE_SIZE = 24 * 1024 * 1024
CHUNK_DURATION_SECONDS = 600
WHISPER_MODEL = "whisper-1"
SUB_LANG_PRIORITY = ("pt-BR", "pt", "pt-PT", "en", "en-US", "en-GB", "en-orig")

TEXT_EXTS = {".txt", ".srt", ".vtt"}

_TS_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s+-->\s+\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}",
    re.MULTILINE,
)
_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class MissingDependency(RuntimeError):
    """A required binary, package, or env var is missing. Ask before installing."""


def parse_caption_text(raw: str) -> str:
    """Strip VTT/SRT chrome and consecutive duplicate cues."""
    lines_out: list[str] = []
    prev = None
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("WEBVTT", "NOTE", "Kind:", "Language:", "STYLE", "REGION")):
            continue
        if _TS_RE.match(s):
            continue
        if s.isdigit():
            continue
        s = re.sub(r"\s+", " ", _TAG_RE.sub("", s).replace("&nbsp;", " ")).strip()
        if not s or s == prev:
            continue
        lines_out.append(s)
        prev = s
    return "\n".join(lines_out)


def detect_kind(source: str) -> str:
    if _URL_RE.match(source.strip()):
        return "url"
    ext = Path(source).suffix.lower()
    if ext in TEXT_EXTS:
        return "text"
    return "media"


def make_slug(source: str) -> str:
    if _URL_RE.match(source.strip()):
        parsed = urlparse(source)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        ident = video_id or Path(parsed.path).stem or parsed.netloc
    else:
        ident = Path(source).stem
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", ident).strip(".-")[:80]
    return slug or "transcript"


def _require_bin(name: str) -> None:
    if shutil.which(name) is None:
        raise MissingDependency(
            f"'{name}' não está no PATH. Posso instalar se você autorizar — "
            "não vou instalar sozinho."
        )


def _require_openai():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise MissingDependency(
            "Falta OPENAI_API_KEY. Defina a variável; sem ela não transcrevo com Whisper."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise MissingDependency(
            "O pacote Python 'openai' não está instalado. Posso instalar se você autorizar."
        ) from exc
    return OpenAI(api_key=key)


def _require_yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise MissingDependency(
            "O pacote Python 'yt-dlp' não está instalado. Posso instalar se você autorizar."
        ) from exc
    return yt_dlp


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _get_audio_duration(audio_path: Path) -> float | None:
    _require_bin("ffprobe")
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
    )
    raw = result.stdout.strip()
    if not raw or raw.lower() == "n/a":
        return None
    return float(raw)


def _convert_to_mp3(input_path: Path, output_path: Path) -> None:
    _require_bin("ffmpeg")
    _run(
        [
            "ffmpeg",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "4",
            "-y",
            str(output_path),
        ]
    )


def _split_audio(audio_path: Path, chunk_duration: int, tmp_dir: str) -> list[Path]:
    duration = _get_audio_duration(audio_path) or 0.0
    num_chunks = max(1, math.ceil(duration / chunk_duration))
    chunks: list[Path] = []
    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = Path(tmp_dir) / f"chunk_{i:03d}.mp3"
        _run(
            [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-ss",
                str(start),
                "-t",
                str(chunk_duration),
                "-acodec",
                "libmp3lame",
                "-q:a",
                "4",
                "-y",
                str(chunk_path),
            ]
        )
        chunks.append(chunk_path)
    return chunks


def _whisper_result_text(result) -> str:
    if isinstance(result, str):
        return result
    return (getattr(result, "text", None) or str(result)).strip()


def _transcribe_file(client, audio_path: Path, response_format: str = "text") -> str:
    with open(audio_path, "rb") as handle:
        result = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=handle,
            response_format=response_format,
        )
    return _whisper_result_text(result)


def _whisper_path(audio_path: Path) -> tuple[str, str | None, float | None]:
    """Return (plain_text, srt_or_none, duration)."""
    client = _require_openai()
    duration = None
    try:
        duration = _get_audio_duration(audio_path)
    except MissingDependency:
        duration = None

    with tempfile.TemporaryDirectory() as tmp_dir:
        mp3_path = Path(tmp_dir) / "audio.mp3"
        _convert_to_mp3(audio_path, mp3_path)
        size = mp3_path.stat().st_size
        if size <= MAX_FILE_SIZE:
            srt = _transcribe_file(client, mp3_path, "srt")
            text = parse_caption_text(srt) if _looks_like_captions(srt) else srt.strip()
            return text, srt if _looks_like_captions(srt) else None, duration

        chunks = _split_audio(mp3_path, CHUNK_DURATION_SECONDS, tmp_dir)
        results: dict[int, str] = {}

        def _do_chunk(idx: int, chunk_path: Path) -> tuple[int, str]:
            return idx, _transcribe_file(client, chunk_path, "text")

        with ThreadPoolExecutor(max_workers=min(len(chunks), 4)) as executor:
            futures = [executor.submit(_do_chunk, i, c) for i, c in enumerate(chunks)]
            for future in futures:
                idx, text = future.result()
                results[idx] = text

        joined = "\n".join(results[i] for i in range(len(chunks)))
        return joined, None, duration


def _looks_like_captions(text: str) -> bool:
    return bool(_TS_RE.search(text) or text.lstrip().startswith("WEBVTT"))


def _pick_caption_file(files: list[Path]) -> Path:
    names = {f.name.lower(): f for f in files}
    for lang in SUB_LANG_PRIORITY:
        needle = f".{lang.lower()}."
        for name, path in names.items():
            if needle in name:
                return path
    return files[0]


def _try_captions(url: str) -> tuple[str | None, str | None]:
    """Return (plain_text, raw_caption_file_text) or (None, None)."""
    yt_dlp = _require_yt_dlp()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": list(SUB_LANG_PRIORITY),
            "subtitlesformat": "vtt",
            "outtmpl": str(tmp_path / "video"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        vtts = list(tmp_path.glob("*.vtt")) + list(tmp_path.glob("*.srt"))
        if not vtts:
            return None, None
        chosen = _pick_caption_file(vtts)
        raw = chosen.read_text(encoding="utf-8", errors="replace")
        text = parse_caption_text(raw)
        if not text.strip():
            return None, None
        return text, raw


def _download_url_audio(url: str) -> Path:
    yt_dlp = _require_yt_dlp()
    tmp_dir = Path(tempfile.mkdtemp(prefix="transcribe_media_"))
    out_template = str(tmp_dir / "audio.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    downloaded = [p for p in tmp_dir.iterdir() if p.is_file()]
    if not downloaded:
        raise RuntimeError("Download do áudio concluído mas o arquivo não foi encontrado.")
    return downloaded[0]


def _read_text_source(path: Path) -> tuple[str, str | None]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".srt", ".vtt"} or _looks_like_captions(raw):
        return parse_caption_text(raw), raw
    return raw, None


def _write_raw(out_dir: Path, text: str, srt: str | None) -> None:
    raw_path = out_dir / "raw.txt"
    if raw_path.exists():
        return
    raw_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    if srt:
        srt_body = srt if srt.endswith("\n") else srt + "\n"
        (out_dir / "raw.srt").write_text(srt_body, encoding="utf-8")


def transcribe_to_dir(source: str, out_dir: str | Path) -> dict:
    """Transcribe source into out_dir. Never overwrites an existing raw.txt."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "raw.txt"
    kind = detect_kind(source)
    duration: float | None = None
    method: str
    text: str
    srt: str | None = None

    if raw_path.exists():
        existing = {
            "source": source,
            "method": "existing",
            "duration": None,
            "skipped": True,
            "reason": "raw.txt already exists; not overwritten",
        }
        meta_path = out / "meta.json"
        if meta_path.exists():
            try:
                existing = json.loads(meta_path.read_text(encoding="utf-8"))
                existing["skipped"] = True
            except json.JSONDecodeError:
                pass
        return existing

    if kind == "text":
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")
        text, srt = _read_text_source(path)
        method = "text"
    elif kind == "url":
        text_cap, srt_cap = _try_captions(source)
        if text_cap:
            text, srt, method = text_cap, srt_cap, "captions"
        else:
            audio_path = _download_url_audio(source)
            try:
                text, srt, duration = _whisper_path(audio_path)
            finally:
                shutil.rmtree(audio_path.parent, ignore_errors=True)
            method = "whisper"
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")
        text, srt, duration = _whisper_path(path)
        method = "whisper"

    _write_raw(out, text, srt)
    meta = {
        "source": source,
        "method": method,
        "duration": duration,
        "files": sorted(p.name for p in out.iterdir() if p.is_file()),
    }
    (out / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transcreve vídeo, áudio, URL ou .txt/.srt/.vtt para raw.txt"
    )
    parser.add_argument("source", help="Caminho local ou URL")
    parser.add_argument(
        "--out",
        "-o",
        help="Diretório de saída (padrão: transcripts/<slug>)",
    )
    args = parser.parse_args(argv)
    out_dir = args.out or str(Path("transcripts") / make_slug(args.source))
    try:
        meta = transcribe_to_dir(args.source, out_dir)
    except MissingDependency as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"raw: {Path(out_dir) / 'raw.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
