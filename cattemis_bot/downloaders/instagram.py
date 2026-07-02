"""Instagram downloader for Cattemis Bot.

Uses the Apify ``elis~instagram-downloader-api`` actor (or any actor
configured via ``settings.apify_instagram_actor``) to download media from
Instagram posts/reels.  Produces a ``DownloadResult`` with local temp files.
"""

import logging
import tempfile
import shutil
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

INSTAGRAM_DOMAINS: frozenset[str] = frozenset(
    {
        "instagram.com",
        "www.instagram.com",
        "m.instagram.com",
    }
)

APIFY_ENDPOINT_TPL: str = (
    "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
)
APIFY_TIMEOUT: float = 90.0

_CAPTION_KEYS: tuple[str, ...] = ("caption", "title", "text")
_SKIP_KEYS: frozenset[str] = frozenset(
    {"thumbnail", "thumb", "avatar", "profile", "icon", "logo", "permalink", "shortcode", "posturl", "pageurl"}
)
_GOOD_KEYS: frozenset[str] = frozenset(
    {"video", "image", "photo", "display", "download", "src", "media", "url", "play"}
)


# ---------------------------------------------------------------------------
# Domain check
# ---------------------------------------------------------------------------

def is_instagram(url: str) -> bool:
    """Return True if *url* belongs to an Instagram domain."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in INSTAGRAM_DOMAINS)


# ---------------------------------------------------------------------------
# Media URL extraction helper
# ---------------------------------------------------------------------------

def _extract_media_urls(obj: object) -> list[str]:
    """Recursively walk *obj* and collect candidate media URLs."""
    found: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k).lower()
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    if not any(bad in key for bad in _SKIP_KEYS):
                        if any(ok in key for ok in _GOOD_KEYS):
                            found.append(v)
                walk(v)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)
    return list(dict.fromkeys(found))


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

async def download_instagram_apify(url: str) -> DownloadResult:
    """Download Instagram media via Apify actor.

    Raises:
        RuntimeError: On API errors, missing token, or failed downloads.
    """
    if not settings.apify_token:
        raise RuntimeError("APIFY_TOKEN не задан")

    endpoint = APIFY_ENDPOINT_TPL.format(actor=settings.apify_instagram_actor)
    headers = {
        "Authorization": f"Bearer {settings.apify_token}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=APIFY_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(endpoint, json={"url": [url]}, headers=headers) as resp:
            raw_text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Apify HTTP {resp.status}: {raw_text[:300]}")
            try:
                data = await resp.json(content_type=None)
            except Exception as exc:
                raise RuntimeError("Apify вернул не JSON") from exc

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        raise RuntimeError("Apify не вернул результатов")

    caption: str | None = None
    media_urls: list[str] = []

    for item in data:
        if isinstance(item, dict):
            if not caption:
                for key in _CAPTION_KEYS:
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        caption = value.strip()
                        break
            media_urls.extend(_extract_media_urls(item))

    dedup_urls = list(dict.fromkeys(media_urls))
    if not dedup_urls:
        raise RuntimeError("Apify не вернул прямые ссылки на медиа")

    return await _download_files(dedup_urls, caption, timeout)


async def _download_files(
    media_urls: list[str],
    caption: str | None,
    timeout: aiohttp.ClientTimeout,
) -> DownloadResult:
    """Download *media_urls* to a temp dir and return a ``DownloadResult``."""
    temp_dir = tempfile.mkdtemp(prefix="apify_ig_")
    files: list[str] = []

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, media_url in enumerate(media_urls[: settings.max_media_items], start=1):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()
                    ct = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    if not (ct.startswith("image/") or ct.startswith("video/") or ct.startswith("audio/")):
                        continue
                    parsed = urlparse(media_url)
                    path_ext = Path(parsed.path).suffix.lower()
                    ext = path_ext if path_ext in MEDIA_EXTS else guess_ext_from_content_type(ct)
                    file_path = Path(temp_dir) / f"ig_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise RuntimeError("Не удалось скачать медиафайлы из ссылок Apify")

        return DownloadResult(files=files, caption=caption, temp_dir=temp_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
