"""YouTube video analysis skill using Gemini, with a long-video fallback.

Short videos go to Gemini via YouTube URI. Videos longer than 25 minutes
(or ~80 MB when duration is unknown) are transcribed from captions or
Whisper, then the chat gets a summary and the full text as a downloadable TXT.
"""

import asyncio
import logging
import re
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from aisha.models import GEMINI_FALLBACK, GEMINI_PRIMARY

log = logging.getLogger(__name__)

_MODEL = GEMINI_PRIMARY
_FALLBACK_MODEL = GEMINI_FALLBACK
_client = None

# Spoken video past ~25 min produces a transcript too large for a good WhatsApp
# thread, and Gemini video tokens climb quickly after that. 80 MB is the
# fallback when yt-dlp does not report duration (~3–4 MB/min at 720p).
LONG_VIDEO_SECONDS = 25 * 60
LONG_VIDEO_BYTES = 80 * 1024 * 1024
DOWNLOAD_TTL_MINUTES = 30

_YT_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?(?:[^&\s]*&)*v=|youtu\.be/)([\w-]{11})[^\s]*",
    re.IGNORECASE,
)
_TRANSCRIPT_INTENT_RE = re.compile(
    r"transcrev|transcri|transcript|legend",
    re.IGNORECASE,
)
_TS_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}\s+-->\s+\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}"
)
_TAG_RE = re.compile(r"<[^>]+>")

_DEFAULT_PROMPT = (
    "Analise este vídeo do YouTube em português. "
    "Forneça: (1) resumo conciso do conteúdo, (2) pontos principais, "
    "(3) conclusão ou mensagem central. Seja objetivo e direto."
)

_SUB_LANG_PRIORITY = ("pt-BR", "pt", "pt-PT", "en", "en-US", "en-GB", "en-orig")


def _get_client():
    from google import genai
    from aisha.config import GEMINI_API_KEY

    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY não configurada. Adicione a variável de ambiente no Railway."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


@dataclass
class PendingVideo:
    url: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VideoMeta:
    title: str | None = None
    duration: float | None = None
    filesize: int | None = None


@dataclass
class VideoAnalysis:
    text: str
    download_token: str | None = None
    filename: str | None = None
    download_link: str | None = None
    is_long: bool = False


_pending: dict[str, PendingVideo] = {}
_PENDING_TTL_MINUTES = 10
_pending_transcripts: dict[str, VideoAnalysis] = {}


def extract_youtube_url(text: str) -> str | None:
    """Return the first YouTube URL found in text, or None."""
    m = _YT_PATTERN.search(text)
    return m.group(0) if m else None


def strip_youtube_url(text: str) -> str:
    """Remove the YouTube URL from the text, returning the remainder."""
    return _YT_PATTERN.sub("", text).strip()


def store_pending_video(phone: str, url: str) -> None:
    import asyncio
    from aisha.skills.pending_store import upsert_pending
    _pending[phone] = PendingVideo(url=url)
    try:
        asyncio.get_running_loop().create_task(
            upsert_pending(phone, "youtube", {"url": url}, _PENDING_TTL_MINUTES * 60)
        )
    except RuntimeError:
        pass


def get_pending_video(phone: str) -> PendingVideo | None:
    p = _pending.get(phone)
    if not p:
        return None
    age = datetime.utcnow() - p.created_at
    if age > timedelta(minutes=_PENDING_TTL_MINUTES):
        del _pending[phone]
        return None
    return p


def clear_pending_video(phone: str) -> None:
    import asyncio
    from aisha.skills.pending_store import clear_pending
    _pending.pop(phone, None)
    try:
        asyncio.get_running_loop().create_task(clear_pending(phone, "youtube"))
    except RuntimeError:
        pass


def store_pending_transcript(phone: str, analysis: VideoAnalysis) -> None:
    if analysis.download_token:
        _pending_transcripts[phone] = analysis


def pop_pending_transcript(phone: str) -> VideoAnalysis | None:
    return _pending_transcripts.pop(phone, None)


def is_long_video(duration: float | None, filesize: int | None) -> bool:
    """True when the video should use the summary + TXT delivery path."""
    if duration is not None:
        return duration > LONG_VIDEO_SECONDS
    if filesize is not None:
        return filesize > LONG_VIDEO_BYTES
    return False


def is_transcript_instruction(instruction: str) -> bool:
    return bool(_TRANSCRIPT_INTENT_RE.search(instruction or ""))


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


def _safe_filename(title: str | None) -> str:
    base = (title or "transcricao").strip() or "transcricao"
    base = re.sub(r'[\\/*?:"<>|]', "_", base)
    return f"{base[:80]}.txt"


def _best_filesize(info: dict) -> int | None:
    for key in ("filesize", "filesize_approx"):
        value = info.get(key)
        if value:
            return int(value)
    sizes: list[int] = []
    for fmt in info.get("formats") or []:
        value = fmt.get("filesize") or fmt.get("filesize_approx")
        if value:
            sizes.append(int(value))
    return max(sizes) if sizes else None


def _meta_from_info(info: dict) -> VideoMeta:
    duration = info.get("duration")
    return VideoMeta(
        title=info.get("title"),
        duration=float(duration) if duration is not None else None,
        filesize=_best_filesize(info),
    )


def _extract_info(url: str) -> dict:
    import yt_dlp

    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "best[height<=720]/best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


def _download_captions_sync(url: str) -> str | None:
    import yt_dlp

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": list(_SUB_LANG_PRIORITY),
            "subtitlesformat": "vtt",
            "outtmpl": str(tmp_path / "video"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)
        vtts = list(tmp_path.glob("*.vtt"))
        if not vtts:
            return None
        chosen = _pick_caption_file(vtts)
        text = parse_caption_text(chosen.read_text(encoding="utf-8", errors="replace"))
        return text or None


def _pick_caption_file(files: list[Path]) -> Path:
    names = {f.name.lower(): f for f in files}
    for lang in _SUB_LANG_PRIORITY:
        needle = f".{lang.lower()}."
        for name, path in names.items():
            if needle in name:
                return path
    return files[0]


def _download_audio_sync(url: str) -> tuple[bytes, str]:
    import yt_dlp

    tmp_dir = Path(tempfile.gettempdir()) / "aisha_downloads"
    tmp_dir.mkdir(exist_ok=True)
    token = secrets.token_urlsafe(8)
    out_template = str(tmp_dir / f"{token}.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)
    downloaded = list(tmp_dir.glob(f"{token}.*"))
    if not downloaded:
        raise RuntimeError("Download do áudio concluído mas o arquivo não foi encontrado.")
    path = downloaded[0]
    try:
        return path.read_bytes(), _mime_for_ext(path.suffix)
    finally:
        path.unlink(missing_ok=True)


def _mime_for_ext(suffix: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".opus": "audio/ogg",
        ".webm": "audio/webm",
    }.get(suffix.lower(), "audio/mpeg")


def _is_token_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "token count exceeds" in text or "maximum number of tokens" in text


async def _probe_video(url: str) -> VideoMeta | None:
    try:
        info = await asyncio.to_thread(_extract_info, url)
    except ImportError:
        log.warning("yt-dlp not installed — cannot probe video duration")
        return None
    except Exception:
        log.warning("Failed to probe YouTube metadata", exc_info=True)
        return None
    meta = _meta_from_info(info)
    log.info(
        f"YouTube probe: title={meta.title!r} duration={meta.duration} "
        f"filesize={meta.filesize}"
    )
    return meta


async def _fetch_transcript(url: str) -> str:
    try:
        captions = await asyncio.to_thread(_download_captions_sync, url)
    except ImportError:
        captions = None
    except Exception:
        log.warning("Caption download failed", exc_info=True)
        captions = None
    if captions:
        log.info(f"Using YouTube captions ({len(captions)} chars)")
        return captions

    log.info("No captions — falling back to Whisper on downloaded audio")
    from aisha.skills.transcribe import transcribe_audio_bytes

    audio_bytes, mime = await asyncio.to_thread(_download_audio_sync, url)
    return await transcribe_audio_bytes(audio_bytes, mime)


async def _generate_text(prompt: str) -> str:
    async def _generate(model: str) -> str:
        response = await _get_client().aio.models.generate_content(
            model=model,
            contents=prompt,
        )
        return (response.text or "").strip()

    try:
        return await _generate(_MODEL)
    except Exception as primary_exc:
        log.warning(f"Primary text model {_MODEL} failed ({primary_exc}); trying {_FALLBACK_MODEL}")
        return await _generate(_FALLBACK_MODEL)


async def _summarize_transcript(transcript: str, instruction: str) -> str:
    if is_transcript_instruction(instruction) or not instruction.strip():
        task = _DEFAULT_PROMPT
    else:
        task = instruction.strip()
    prompt = (
        f"{task}\n\n"
        "Use a transcrição abaixo como fonte. Não invente trechos que não estejam nela.\n\n"
        f"TRANSCRIÇÃO:\n{transcript}"
    )
    return await _generate_text(prompt)


def format_long_video_reply(
    analysis_text: str,
    filename: str,
    download_link: str,
    duration: float | None,
) -> str:
    mins = int(duration // 60) if duration else None
    dur = f" ({mins} min)" if mins else ""
    return (
        f"{analysis_text}\n\n"
        f"📄 A transcrição completa{dur} está no arquivo *{filename}*.\n"
        f"🔗 Link de download (expira em {DOWNLOAD_TTL_MINUTES} min):\n{download_link}"
    )


def _with_download(analysis_text: str, transcript: str, title: str | None, duration: float | None) -> VideoAnalysis:
    from aisha.config import BASE_URL
    from aisha.skills.video_download import register_text_download

    token, filename = register_text_download(transcript, _safe_filename(title))
    link = f"{BASE_URL}/download/{token}"
    return VideoAnalysis(
        text=format_long_video_reply(analysis_text, filename, link, duration),
        download_token=token,
        filename=filename,
        download_link=link,
        is_long=True,
    )


async def _analyze_via_transcript(url: str, instruction: str, meta: VideoMeta | None) -> VideoAnalysis:
    transcript = await _fetch_transcript(url)
    if not transcript.strip():
        return VideoAnalysis(
            text="Não consegui obter a transcrição desse vídeo (sem legendas e o áudio falhou)."
        )
    summary = await _summarize_transcript(transcript, instruction)
    return _with_download(
        summary,
        transcript,
        meta.title if meta else None,
        meta.duration if meta else None,
    )


async def _analyze_via_gemini(url: str, instruction: str) -> str:
    from google.genai import types

    prompt = instruction.strip() if instruction.strip() else _DEFAULT_PROMPT
    log.info(f"Analyzing YouTube video via Gemini: {url} | prompt: {prompt[:80]}")

    async def _generate(model: str) -> str:
        response = await _get_client().aio.models.generate_content(
            model=model,
            contents=[
                types.Part.from_uri(file_uri=url, mime_type="video/mp4"),
                prompt,
            ],
        )
        return response.text

    try:
        return await _generate(_MODEL)
    except Exception as primary_exc:
        if _is_token_limit_error(primary_exc):
            raise
        log.warning(f"Primary YouTube model {_MODEL} failed ({primary_exc}); trying {_FALLBACK_MODEL}")
        return await _generate(_FALLBACK_MODEL)


async def analyze_video(url: str, instruction: str) -> VideoAnalysis:
    """Analyze a YouTube video. Long videos get a summary plus a TXT download."""
    from google.genai.errors import ClientError  # local import — optional in unit tests

    meta = await _probe_video(url)
    long_video = is_long_video(
        meta.duration if meta else None,
        meta.filesize if meta else None,
    )
    if long_video:
        log.info(
            f"Long video detected (duration={meta.duration if meta else None}, "
            f"filesize={meta.filesize if meta else None}) — summary + TXT"
        )
        try:
            return await _analyze_via_transcript(url, instruction, meta)
        except Exception:
            log.exception("Long-video transcript path failed")
            return VideoAnalysis(
                text=(
                    "Esse vídeo é longo e não consegui gerar a transcrição agora. "
                    "Tente de novo em alguns minutos."
                )
            )

    try:
        try:
            text = await _analyze_via_gemini(url, instruction)
            return VideoAnalysis(text=text)
        except Exception as primary_exc:
            if _is_token_limit_error(primary_exc):
                log.warning(f"Gemini token limit for {url} — falling back to transcript path")
                try:
                    return await _analyze_via_transcript(url, instruction, meta)
                except Exception:
                    log.exception("Transcript fallback after Gemini token limit failed")
                    return VideoAnalysis(text=(
                        "Esse vídeo é longo e não consegui gerar a transcrição agora. "
                        "Tente de novo em alguns minutos."
                    ))
            raise
    except ClientError as e:
        if e.code == 403:
            log.warning(f"Gemini 403 for {url} — live stream or restricted video")
            return VideoAnalysis(text=(
                "Não consegui acessar esse vídeo. Isso geralmente acontece com:\n\n"
                "• *Lives ao vivo* — só funciona após o vídeo ser publicado\n"
                "• Vídeos com *restrição de idade* ou *região*\n"
                "• Vídeos *privados* ou *não listados*\n\n"
                "Tente novamente depois que a live terminar e o vídeo estiver disponível."
            ))
        if e.code == 400:
            log.warning(f"Gemini 400 for {url}: {e}")
            if _is_token_limit_error(e):
                try:
                    return await _analyze_via_transcript(url, instruction, meta)
                except Exception:
                    log.exception("Transcript fallback after Gemini 400 failed")
                    return VideoAnalysis(text=(
                        "Esse vídeo é longo e não consegui gerar a transcrição agora. "
                        "Tente de novo em alguns minutos."
                    ))
            return VideoAnalysis(text=(
                "Não consegui processar esse vídeo. "
                "Verifique se o link é válido e o vídeo está disponível publicamente."
            ))
        raise
