"""Cobalt downloader for Cattemis Bot.

Uses a public Cobalt (https://github.com/imputnet/cobalt) API instance as a
free primary downloader for YouTube and Reddit links. Falls back to yt-dlp
(see ``downloaders/ytdlp.py``) when Cobalt returns an error, hits a
rate-limit, or produces an empty response.

API contract (Cobalt v10+ JSON API):
    POST {COBALT_API_URL}/api/json (or /api/json depending on instance)
    Headers: Accept: application/json, Content-Type: application/json
    Body: {"url": "<media url>"}

Response ``status`` values handled here: ``error``, ``rate-limit``,
``redirect``, ``tunnel``, ``stream``, ``success``, ``picker``.
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

COBALT_TIMEOUT: float = 60.0

# Statuses that mean "we got at least one usable media URL"
_OK_STATUSES: frozenset[str] = frozenset({"redirect", "tunnel", "stream", "success"})
# Statuses that mean "give up on Cobalt, let the caller fall back"
_FAIL_STATUSES: frozenset[str] = frozenset({"error", "rate-limit"})


class CobaltError(RuntimeError):
    """Raised when Cobalt fails to produce media (triggers yt-dlp fallback)."""


# ---------------------------------------------------------------------------
# Request helper
# ---------------------------------------------------------------------------


def _api_endpoint() -> str:
    base = settings.cobalt_api_url.rstrip("/")
    return f"{base}/api/json"


async def _request_cobalt(url: str) -> dict:
    """POST *url* to the Cobalt instance and return the parsed JSON payload."""
    endpoint = _api_endpoint()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=COBALT_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(endpoint, json={"url": url}, headers=headers) as resp:
            data = await resp.json(content_type=None)
            if resp.status >= 400 and not isinstance(data, dict):
                resp.raise_for_status()
            return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Media URL extraction
# ---------------------------------------------------------------------------


def _media_urls_from_response(data: dict) -> list[str]:
    """Extract downloadable media URLs from a Cobalt JSON response."""
    status = data.get("status")

    if status == "picker":
        picker = data.get("picker") or []
        urls = [item.get("url") for item in picker if isinstance(item, dict) and item.get("url")]
        return urls[: settings.max_media_items]

    if status in _OK_STATUSES:
        media_url = data.get("url")
        return [media_url] if media_url else []

    return []


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------


async def download_cobalt(url: str) -> DownloadResult:
    """Download media from *url* via the configured Cobalt instance.

    Raises:
        CobaltError: On ``error``/``rate-limit`` status, or when no media
            URLs / files could be produced — callers should catch this and
            fall back to ``download_ytdlp``.
    """
    try:
        data = await _request_cobalt(url)
    except Exception as exc:
        raise CobaltError(f"Cobalt request failed: {exc}") from exc

    status = data.get("status")

    if status in _FAIL_STATUSES:
        text = data.get("text") or data.get("error") or "unknown error"
        raise CobaltError(f"Cobalt returned {status}: {text}")

    media_urls = _media_urls_from_response(data)
    if not media_urls:
        raise CobaltError(f"Cobalt returned no media (status={status!r})")

    caption = None
    filename = data.get("filename")
    if isinstance(filename, str) and filename.strip():
        caption = filename.strip()

    return await _download_files(media_urls, caption)


async def _download_files(media_urls: list[str], caption: str | None) -> DownloadResult:
    """Download *media_urls* to a temp dir and return a ``DownloadResult``."""
    temp_dir = tempfile.mkdtemp(prefix="cobalt_")
    files: list[str] = []
    timeout = aiohttp.ClientTimeout(total=COBALT_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, media_url in enumerate(media_urls[: settings.max_media_items], start=1):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()
                    ct = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    parsed_media = urlparse(media_url)
                    path_ext = Path(parsed_media.path).suffix.lower()
                    ext = path_ext if path_ext in MEDIA_EXTS else guess_ext_from_content_type(ct, fallback=".mp4")
                    file_path = Path(temp_dir) / f"cobalt_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise CobaltError("Не удалось скачать файлы, отданные Cobalt")

        return DownloadResult(files=files, caption=caption, temp_dir=temp_dir)
    except CobaltError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise CobaltError(f"Не удалось скачать файлы, отданные Cobalt: {exc}") from exc
