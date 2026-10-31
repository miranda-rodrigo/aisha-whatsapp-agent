"""Nível 1: transcrição fiel dos áudios, com cache. O texto nunca é reescrito."""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import costs
from .config import STT_FALLBACK, STT_MODEL, load_env

_WORKERS = 10


def _cache_path(out_dir: Path, filename: str) -> Path:
    return out_dir / "cache" / "transcricoes" / (filename + ".json")


def _as_mp3(audio_path: Path, out_dir: Path) -> Path:
    """A API não aceita .opus; converte uma vez para mp3 mono 16 kHz no cache."""
    if audio_path.suffix.lower() in (".mp3", ".wav", ".m4a"):
        return audio_path
    mp3 = out_dir / "cache" / "audio_mp3" / (audio_path.stem + ".mp3")
    if not mp3.exists():
        mp3.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(audio_path),
             "-ac", "1", "-ar", "16000", str(mp3)],
            check=True,
        )
    return mp3


def transcribe_conversation(conv: dict, out_dir: Path, *, limit: int | None = None,
                            model: str = STT_MODEL, language: str = "pt") -> int:
    """Preenche media["transcricao"] nos áudios presentes. Devolve quantos transcreveu."""
    load_env()
    from openai import BadRequestError, NotFoundError, OpenAI
    client = OpenAI()
    export_dir = Path(conv["export_dir"])

    targets = []
    for msg in conv["messages"]:
        for media in msg["media"]:
            if media["kind"] != "audio" or not media["present"]:
                continue
            if media.get("transcricao"):
                continue
            cache = _cache_path(out_dir, media["filename"])
            if cache.exists():
                media["transcricao"] = json.loads(cache.read_text(encoding="utf-8"))["text"]
                continue
            targets.append(media)
    if limit is not None:
        targets = targets[:limit]
    if not targets:
        return 0

    def work(media: dict) -> None:
        used_model = model
        try:
            audio_path = _as_mp3(export_dir / media["path"], out_dir)
            with open(audio_path, "rb") as f:
                try:
                    tx = client.audio.transcriptions.create(
                        model=used_model, file=f, language=language)
                except (BadRequestError, NotFoundError):
                    used_model = STT_FALLBACK
                    f.seek(0)
                    tx = client.audio.transcriptions.create(
                        model=used_model, file=f, language=language)
        except Exception as e:  # rede, chave, formato: registrar e seguir
            media["transcricao_erro"] = f"{type(e).__name__}: {e}"
            print(f"  ERRO {media['filename']}: {e}")
            return
        text = (tx.text or "").strip()
        media["transcricao"] = text
        media.pop("transcricao_erro", None)
        inp, out = costs.usage_tokens(getattr(tx, "usage", None))
        costs.record(out_dir, etapa="nivel1_transcricao", model=used_model,
                     input_tokens=inp, output_tokens=out,
                     audio_seconds=media.get("duration_seconds"),
                     item=media["filename"])
        cache = _cache_path(out_dir, media["filename"])
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"text": text, "model": used_model},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  transcrito: {media['filename']} ({media.get('duration_seconds') or '?'}s)")

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        list(pool.map(work, targets))
    return sum(1 for m in targets if m.get("transcricao"))
