"""Bounded attachment ingestion. Only referenced local files are decoded."""

import hashlib
import io
import json
import math
import os
import stat
import subprocess
import tempfile
import time
import warnings
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps

from .ingest import ExportError, ingest_zip
from .parser import AND_ATTACH_RE, IOS_ATTACH_RE, parse_chat

MAX_AUDIO = int(os.getenv("EXPORT_MAX_AUDIO_FILES", "200"))
MAX_SECONDS = int(os.getenv("EXPORT_MAX_AUDIO_SECONDS", "3600"))
MAX_IMAGES = int(os.getenv("EXPORT_MAX_IMAGES", "40"))
MAX_MEDIA_BYTES = 250 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
AUDIO_EXTS = {".opus", ".ogg", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".oga", ".webm"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def enabled():
    return os.getenv("WHATSAPP_EXPORT_MEDIA_ENABLED", "false").lower() == "true"


def safe_name(name):
    p = PurePosixPath(name)
    return (
        bool(name)
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in name
        and "\x00" not in name
        and ":" not in name
    )


def normalize_image(raw):
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise ExportError(
                    "Uma imagem excede 20 megapixels. Reduza a imagem e reexporte."
                )
            if im.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Unsupported image encoding")
            if getattr(im, "n_frames", 1) > 1:
                raise ValueError("Animated image not supported")
            im = ImageOps.exif_transpose(im)
            im.thumbnail((1600, 1600))
            if im.mode in ("RGBA", "LA") or "transparency" in im.info:
                rgba = im.convert("RGBA")
                bg = Image.new("RGB", rgba.size, "white")
                bg.paste(rgba, mask=rgba.getchannel("A"))
                im = bg
            else:
                im = im.convert("RGB")
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=82, optimize=True)
            return out.getvalue()


def probe_audio(raw, suffix):
    with tempfile.TemporaryDirectory(prefix="aisha-media-") as directory:
        path = Path(directory) / ("input" + suffix)
        path.write_bytes(raw)
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            check=True,
            timeout=10,
        )
        value = json.loads(result.stdout)
        seconds = float(value.get("format", {}).get("duration", 0))
        if (
            not math.isfinite(seconds)
            or seconds <= 0
            or not any(s.get("codec_type") == "audio" for s in value.get("streams", []))
        ):
            raise ValueError("Invalid audio duration")
        if any(s.get("codec_type") == "video" for s in value.get("streams", [])):
            raise ValueError("Video is not processed")
        return seconds


def prepare(data):
    """Validate every supported attachment before paid calls. Return metadata + bytes."""
    deadline = time.monotonic() + 120
    messages = ingest_zip(data)
    assets = {}
    counts = {"audio": 0, "image": 0}
    total = 0
    duration = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        by_base = {}
        for entry in entries:
            if not entry.is_dir():
                by_base.setdefault(PurePosixPath(entry.filename).name, []).append(entry)
        for message in messages:
            names = IOS_ATTACH_RE.findall(message["text"]) or AND_ATTACH_RE.findall(
                message["text"]
            )
            message["media"] = []
            parsed = parse_chat(
                f"[{message['date']}, {message['time']}] {message['sender']}: {message['text']}"
            )
            if not names and parsed.messages:
                for kind in parsed.messages[0].omitted_media:
                    item = {
                        "kind": kind,
                        "name": "Mídia omitida na exportação",
                        "status": "missing",
                    }
                    if kind in counts:
                        counts[kind] += 1
                        item["number"] = counts[kind]
                    message["media"].append(item)
            for name in names:
                if time.monotonic() > deadline:
                    raise ExportError(
                        "A validação das mídias excedeu dois minutos. Exporte um período menor."
                    )
                name = name.strip().strip("\u200e\u200f")
                if not safe_name(name):
                    raise ExportError(
                        "Referência de arquivo insegura no ZIP. Reexporte a conversa."
                    )
                suffix = PurePosixPath(name).suffix.lower()
                kind = (
                    "audio"
                    if suffix in AUDIO_EXTS
                    else "image"
                    if suffix in IMAGE_EXTS
                    else "document"
                )
                item = {"name": name, "kind": kind, "status": "not_processed"}
                message["media"].append(item)
                if kind == "document":
                    continue
                counts[kind] += 1
                item["number"] = counts[kind]
                if counts["audio"] > MAX_AUDIO or counts["image"] > MAX_IMAGES:
                    raise ExportError(
                        "A exportação excede 200 áudios ou 40 imagens. Envie um período menor."
                    )
                matches = by_base.get(PurePosixPath(name).name, [])
                if len(matches) > 1:
                    raise ExportError("Há arquivos de mídia com nomes ambíguos no ZIP.")
                if not matches:
                    item["status"] = "missing"
                    continue
                entry = matches[0]
                if not safe_name(entry.filename) or stat.S_ISLNK(
                    entry.external_attr >> 16
                ):
                    raise ExportError("Arquivo de mídia inseguro no ZIP.")
                total += entry.file_size
                if total > MAX_MEDIA_BYTES or (
                    kind == "image" and entry.file_size > MAX_IMAGE_BYTES
                ):
                    raise ExportError(
                        "Mídias excedem 250 MiB no total ou 10 MiB por imagem. Reduza a exportação."
                    )
                try:
                    with archive.open(entry) as stream:
                        raw = stream.read(min(entry.file_size, MAX_MEDIA_BYTES) + 1)
                    if len(raw) != entry.file_size:
                        raise ValueError("Invalid archive size")
                    digest = hashlib.sha256(raw).hexdigest()
                    item["hash"] = digest
                    item["suffix"] = suffix
                    if kind == "audio":
                        item["seconds"] = probe_audio(raw, suffix)
                        duration += item["seconds"]
                        if duration > MAX_SECONDS:
                            raise ExportError(
                                "Os áudios excedem 60 minutos. Exporte um período menor; nenhuma mídia foi enviada à IA."
                            )
                        assets[digest] = raw
                    else:
                        assets[digest] = normalize_image(raw)
                    item["status"] = "pending"
                except ExportError:
                    raise
                except Exception:
                    item["status"] = "invalid"
    return messages, assets
