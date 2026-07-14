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
        return "Хозяин, нужна другая ссылка... такое качество не помещается в мой животик :<"
    if "unsupported url" in text or "not a valid url" in text:
        return "хозяин кажется эта ссылка нерабочая -.-'"
    if "private video" in text:
        return "хозяин это видео приватное и я не могу его посмотреть (¬_¬)"
    if "sign in to confirm your age" in text or "age-restricted" in text:
        return "хозяин не подумай ничего плохого... но видео с возрастным ограничением я скачать не могу >///<"
    if "video unavailable"