"""Video download skill using yt-dlp.

Downloads videos from YouTube, X/Twitter, and 1000+ other sites.
Instead of sending the file directly via WhatsApp (16 MB limit),
generates a temporary download link that expires after TTL_MINUTES.
"""

import asyncio
import logging
import re
import secrets
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

_TTL_MINUTES = 30
_MAX_HEIGHT = 720  # cap resolution to keep files reasonably small

# Regex patterns for supported platforms
_YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?.*v=|youtu\.be/)[\w-]+",
    re.IGNORECASE,
)
_TWITTER_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+",
    re.IGNORECASE,
)

# Temporary storage: token -> DownloadEntry
@dataclass
class DownloadEntry:
    filepath: Path
    filename: str
    created_at: datetime = field(default_factory=datetime.utcnow)


_downloads: dict[str, DownloadEntry] = {}


def extract_video_url(text: str) -> str | None:
    """Return the first YouTube or X/Twitter URL found in text, or None."""
    for pattern in (_YOUTUBE_PATTERN, _TWITTER_PATTERN):
        m = pattern.search(text)
        if m:
            return m.group(0).rstrip(".,;)")
    return None


def strip_video_url(text: str) -> str:
    """Remove the first video URL from text, returning the remainder."""
    for pattern in (_YOUTUBE_PATTERN, _TWITTER_PATTERN):
        m = pattern.search(text)
        if m:
            url = m.group(0).rstrip(".,;)")
            return (text[: m.start()] + text[m.start() + len(url) :]).strip()
    return text


def get_download_entry(token: str) -> DownloadEntry | None:
    """Return entry if it exists and hasn't expired."""
    entry = _downloads.get(token)
    if not entry:
        return None
    if datetime.utcnow() - entry.created_at > timedelta(minutes=_TTL_MINUTES):
        _expire_entry(token)
        return None
    return entry


def _expire_entry(token: str) -> None:
    entry = _downloads.pop(token, None)
    if entry and entry.filepath.exists():
        try:
            entry.filepath.unlink()
            log.info(f"Deleted expired temp file: {entry.filepath}")
        except OSError as exc:
            log.warning(f"Could not delete {entry.filepath}: {exc}")


def cleanup_expired() -> int:
    """Remove all expired entries. Returns count of removed entries."""
    expired = [
        token
        for token, entry in list(_downloads.items())
        if datetime.utcnow() - entry.created_at > timedelta(minutes=_TTL_MINUTES)
    ]
    for token in expired:
        _expire_entry(token)
    return len(expired)


async def download_video(url: str) -> tuple[str, str]:
    """Download a video and register a temporary download token.

    Returns (token, filename).
    Raises RuntimeError if download fails.
    """
    tmp_dir = Path(tempfile.gettempdir()) / "aisha_downloads"
    tmp_dir.mkdir(exist_ok=True)

    token = secrets.token_urlsafe(16)
    out_template = str(tmp_dir / f"{token}.%(ext)s")

    ydl_opts = {
        "format": f"best[height<={_MAX_HEIGHT}][ext=mp4]/best[height<={_MAX_HEIGHT}]/best",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        import yt_dlp  # local import — optional dependency

        info: dict = await asyncio.to_thread(_run_download, ydl_opts, url)
    except ImportError:
        raise RuntimeError("yt-dlp não está instalado no servidor.")

    # Find the file yt-dlp created (extension varies)
    downloaded = list(tmp_dir.glob(f"{token}.*"))
    if not downloaded:
        raise RuntimeError("Download concluído mas o arquivo não foi encontrado.")

    filepath = downloaded[0]
    filename = info.get("title", "video") + filepath.suffix
    # Sanitize filename for use in Content-Disposition
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)

    _downloads[token] = DownloadEntry(filepath=filepath, filename=filename)
    log.info(f"Video downloaded: {filepath} ({filepath.stat().st_size} bytes), token={token}")
    return token, filename


def _run_download(ydl_opts: dict, url: str) -> dict:
    """Blocking helper: runs yt-dlp in a thread via asyncio.to_thread."""
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info or {}
