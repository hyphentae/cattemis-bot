"""Twitter/X downloader for Cattemis Bot.

Uses the public FxTwitter API (``api.fxtwitter.com``) to fetch tweet media.
Produces a ``DownloadResult`` with local temp files.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from ..config import settings
from ..utils.media import MEDIA_EXTS, guess_ext_from_content_type
from . import DownloadResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TWITTER_DOMAINS: frozenset[str] = frozenset(
    {
        "x.com",
        "www.x.com",
        "twitter.com",
        "www.twitter.com",
        "mobile.twitter.com",
    }
)

FXTWITTER_BASE_URL: str = "https://api.fxtwitter.com"
FXTWITTER_TIMEOUT: float = 40.0

_MEDIA_URL_KEYS: frozenset[str] = frozenset(
    {"url", "media", "image", "photo", "video", "playback", "source", "src"}
)


# ---------------------------------------------------------------------------
# Domain check
# ---------------------------------------------------------------------------

def is_twitter(url: str) -> bool:
    """Return True if *url* belongs to a Twitter/X domain."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in TWITTER_DOMAINS)


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_twitter_url(url: str) -> tuple[str, str] | None:
    """Extract ``(username, tweet_id)`` from a Twitter/X URL.

    Returns None if the URL cannot be parsed.
    """
    try:
        parts = [p for p in urlparse(url).path.split("/") if p]
    except Exception:
        return None
    if len(parts) >= 3 and parts[1] == "status":
        return parts[0], parts[2]
    return None


# ---------------------------------------------------------------------------
# Media URL extraction
# ---------------------------------------------------------------------------

def _extract_twitter_media_urls(payload: dict) -> list[str]:
    """Recursively walk the FxTwitter media object and collect URLs."""
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k).lower()
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    if any(x in key for x in _MEDIA_URL_KEYS):
                        found.append(v)
                walk(v)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    tweet = payload.get("tweet", payload)
    media = tweet.get("media", {}) if isinstance(tweet, dict) else {}
    walk(media)
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

async def download_twitter_fx(url: str) -> DownloadResult:
    """Download Twitter/X media via FxTwitter API.

    Raises:
        RuntimeError: If URL cannot be parsed or no media is found.
    """
    parsed = parse_twitter_url(url)
    if not parsed:
        raise RuntimeError("Не удалось распарсить ссылку Twitter/X")

    username, tweet_id = parsed
    endpoint = f"{FXTWITTER_BASE_URL}/{username}/status/{tweet_id}"
    timeout = aiohttp.ClientTimeout(total=FXTWITTER_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(endpoint) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

    tweet = data.get("tweet", data)
    caption: str | None = None
    if isinstance(tweet, dict):
        text = tweet.get("text")
        if isinstance(text, str) and text.strip():
            caption = text.strip()

    media_urls = _extract_twitter_media_urls(data)
    if not media_urls:
        raise RuntimeError("FxTwitter не вернул медиа")

    return await _download_files(media_urls, caption, timeout)


async def _download_files(
    media_urls: list[str],
    caption: str | None,
    timeout: aiohttp.ClientTimeout,
) -> DownloadResult:
    """Download *media_urls* to a temp dir and return a ``DownloadResult``."""
    temp_dir = tempfile.mkdtemp(prefix="twitter_fx_")
    files: list[str] = []

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, media_url in enumerate(media_urls[: settings.max_media_items], start=1):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()
                    ct = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    if not (ct.startswith("image/") or ct.startswith("video/") or ct.startswith("audio/")):
                        continue
                    parsed_media = urlparse(media_url)
                    path_ext = Path(parsed_media.path).suffix.lower()
                    ext = path_ext if path_ext in MEDIA_EXTS else guess_ext_from_content_type(ct)
                    file_path = Path(temp_dir) / f"tw_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise RuntimeError("Не удалось скачать файлы из медиа-ссылок FxTwitter")

        return DownloadResult(files=files, caption=caption, temp_dir=temp_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
