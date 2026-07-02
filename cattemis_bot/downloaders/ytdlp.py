"""yt-dlp downloader for Cattemis Bot.

Downloads video/audio from YouTube, Vimeo, and any other site supported by
yt-dlp.  The blocking download is run in an executor to avoid blocking the
event loop.  Produces a ``DownloadResult`` with one local temp file.
"""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from . import DownloadResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOUTUBE_DOMAINS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
    }
)

VIMEO_DOMAINS: frozenset[str] = frozenset({"vimeo.com", "www.vimeo.com"})

_YTDLP_FORMAT: str = "bv*[height<=1080]+ba/b[height<=1080]"
_SKIP_SUFFIXES: frozenset[str] = frozenset({".part", ".ytdl", ".temp"})

# ---------------------------------------------------------------------------
# Domain check
# ---------------------------------------------------------------------------

def is_youtube(url: str) -> bool:
    """Return True if *url* belongs to YouTube."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in YOUTUBE_DOMAINS)


def is_vimeo(url: str) -> bool:
    """Return True if *url* belongs to Vimeo."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in VIMEO_DOMAINS)


# ---------------------------------------------------------------------------
# Human-readable error messages
# ---------------------------------------------------------------------------

def human_ytdlp_error(error: Exception) -> str:
    """Convert a yt-dlp exception into a friendly Russian message."""
    text = str(error).lower()

    if "requested format is not available" in text:
        return "Хозяин, нужна другая ссылка. Такое качество не помещается в мой животик (⁠╯⁠︵⁠╰⁠,⁠)."
    if "unsupported url" in text or "not a valid url" in text:
        return "Хозяин, кажется, эта ссылка нерабочая (⁠˘⁠･⁠_⁠･⁠˘⁠)"
    if "private video" in text:
        return "Хозяин, это видео приватное и я не могу его посмотреть (⁠￣⁠ヘ⁠￣⁠;⁠)"
    if "sign in to confirm your age" in text or "age-restricted" in text:
        return "Хозяин, не подумай ничего плохого, но я не могу скачивать видео с ограничениями по возрасту... (⁠；⁠^⁠ω⁠^⁠）"
    if "video unavailable" in text:
        return "Ой, Хозяин, это видео уже недоступно (⁠･⁠o⁠･⁠;⁠)"
    if "http error 403" in text or "forbidden" in text:
        return "Ай, сайт не разрешил скачать видео. :3"
    if "timed out" in text:
        return "Мм, сервер отвечает слишком долго... Попробуй ещё разочек чуть позже, зайка ^^"
    return "Не получилось скачать это видео."


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

async def download_ytdlp(url: str) -> DownloadResult:
    """Download media from *url* using yt-dlp (runs in an executor thread).

    Raises:
        DownloadError: On yt-dlp download failures.
        ExtractorError: On extractor-level failures.
        FileNotFoundError: If no output file is produced.
    """
    temp_dir = tempfile.mkdtemp(prefix="media_bot_")
    outtmpl = str(Path(temp_dir) / "%(id)s.%(ext)s")

    ydl_opts: dict = {
        "outtmpl": outtmpl,
        "format": _YTDLP_FORMAT,
        "noplaylist": True,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    def _run_download() -> DownloadResult:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        files = [
            p for p in Path(temp_dir).iterdir()
            if p.is_file()
            and not p.name.startswith(".")
            and p.suffix.lower() not in _SKIP_SUFFIXES
        ]

        if not files:
            raise FileNotFoundError("Файл после скачивания не найден")

        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        logger.debug("yt-dlp downloaded %s for %s", files[0].name, url)
        return DownloadResult(files=[str(files[0])], caption=None, temp_dir=temp_dir)

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _run_download)
    except (DownloadError, ExtractorError):
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
