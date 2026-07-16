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
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in YOUTUBE_DOMAINS)


def is_vimeo(url: str) -> bool:
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
    text = str(error).lower()
    if "requested format is not available" in text:
        return "Хозяин, нужна другая ссылка... такое качество не помещается в мой животик :3"
    if "unsupported url" in text or "not a valid url" in text:
        return "хозяин кажется эта ссылка нерабочая (¬_¬)"
    if "private video" in text:
        return "хозяин это видео приватное и я не могу его посмотреть T_T"
    if "sign in to confirm your age" in text or "age-restricted" in text:
        return "хозяин не подумай ничего плохого... но видео с возрастным ограничением я скачать не могу >///< "
    if "video unavailable" in text:
        return "хозяин... это видео недоступно или удалено... T_T"
    if "timed out" in text or "timeout" in text:
        return "хозяин... сервер отвечает слишком долго... попробуйте ещё разочек~ ;3"
    if "no space left" in text:
        return "хозяин... у меня закончилось место на диске... T_T"
    return "хозяин... не удалось скачать... п-попробуйте ещё раз пожалуйста... T_T"


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

def _download_sync(url: str, tmpdir: str) -> Path:
    """Synchronous yt-dlp download into *tmpdir*. Returns the output file path."""
    ydl_opts = {
        "format": _YTDLP_FORMAT,
        "outtmpl": str(Path(tmpdir) / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = (info or {}).get("title", "") if info else ""

    files = [
        p for p in Path(tmpdir).iterdir()
        if p.is_file() and p.suffix.lower() not in _SKIP_SUFFIXES
    ]
    if not files:
        raise DownloadError("yt-dlp did not produce any output file")

    return files[0], title


async def download_ytdlp(url: str) -> DownloadResult:
    """Async wrapper: download *url* with yt-dlp and return a DownloadResult."""
    tmpdir = tempfile.mkdtemp(prefix="cattemis_ytdlp_")
    try:
        loop = asyncio.get_running_loop()
        file_path, title = await loop.run_in_executor(None, _download_sync, url, tmpdir)
        return DownloadResult(files=[str(file_path)], caption=title, temp_dir=tmpdir)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
