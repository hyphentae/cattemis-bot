"""Instagram downloader for Cattemis Bot.

Uses the Apify ``elis~instagram-downloader-api`` actor (or any actor
configured via ``settings.apify_instagram_actor``) to download media from
Instagram posts/reels.  Produces a ``DownloadResult`` with local temp files.
"""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from ..config import settings
from ..utils.media import IMAGE_EXTS, MEDIA_EXTS, VIDEO_EXTS, guess_ext_from_content_type
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
MediaLink = tuple[str, str | None]
_PREVIEW_HASH_SIZE = 16
_PREVIEW_HASH_DISTANCE = 24


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

def _extract_media_urls(obj: object) -> list[MediaLink]:
    """Collect media URLs from an unexpected actor response shape."""
    found: list[MediaLink] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k).lower()
                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    if not any(bad in key for bad in _SKIP_KEYS):
                        if any(ok in key for ok in _GOOD_KEYS):
                            found.append((v, None))
                walk(v)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)
    return list(dict.fromkeys(found))


def _extract_actor_media(item: dict[object, object]) -> list[MediaLink]:
    """Extract result URLs in actor order without trusting its media types."""
    result = item.get("result")
    if not isinstance(result, list):
        return []

    media: list[MediaLink] = []
    for entry in result:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        media.append((url, None))
    return media


async def _media_fingerprint(path: str) -> tuple[tuple[int, int], int] | None:
    """Return media dimensions and an average hash of its first frame."""
    try:
        probe = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        probe_stdout, _ = await probe.communicate()
        width_text, height_text = probe_stdout.decode().strip().split(",", maxsplit=1)

        frame = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-vf",
            f"scale={_PREVIEW_HASH_SIZE}:{_PREVIEW_HASH_SIZE},format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        pixels, _ = await frame.communicate()
        expected_pixels = _PREVIEW_HASH_SIZE * _PREVIEW_HASH_SIZE
        if probe.returncode or frame.returncode or len(pixels) != expected_pixels:
            return None

        mean = sum(pixels) / len(pixels)
        average_hash = 0
        for pixel in pixels:
            average_hash = (average_hash << 1) | int(pixel >= mean)
        return (int(width_text), int(height_text)), average_hash
    except (OSError, ValueError):
        return None


async def _remove_video_previews(files: list[str]) -> list[str]:
    """Remove still images that duplicate the first frame of a video."""
    image_paths = [path for path in files if Path(path).suffix.lower() in IMAGE_EXTS]
    video_paths = [path for path in files if Path(path).suffix.lower() in VIDEO_EXTS]
    if not image_paths or not video_paths:
        return files

    paths = [*image_paths, *video_paths]
    fingerprints = dict(
        zip(paths, await asyncio.gather(*(_media_fingerprint(path) for path in paths)))
    )
    video_fingerprints = [
        fingerprints[path] for path in video_paths if fingerprints[path]
    ]
    previews: set[str] = set()
    for path in image_paths:
        image_fingerprint = fingerprints[path]
        if not image_fingerprint:
            continue
        image_size, image_hash = image_fingerprint
        for video_size, video_hash in video_fingerprints:
            if image_size != video_size:
                continue
            if (image_hash ^ video_hash).bit_count() <= _PREVIEW_HASH_DISTANCE:
                previews.add(path)
                break

    if previews:
        logger.info("[instagram] removed %d video preview image(s)", len(previews))
    return [path for path in files if path not in previews]


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
    media_urls: list[MediaLink] = []

    for item in data:
        if isinstance(item, dict):
            if not caption:
                for key in _CAPTION_KEYS:
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        caption = value.strip()
                        break
            resolved_media = _extract_actor_media(item)
            media_urls.extend(resolved_media or _extract_media_urls(item))

    dedup_urls = list(dict.fromkeys(media_urls))
    if not dedup_urls:
        raise RuntimeError("Apify не вернул прямые ссылки на медиа")

    source_path = urlparse(url).path.lower()
    skip_images = "/reel/" in source_path or "/tv/" in source_path
    return await _download_files(dedup_urls, caption, timeout, skip_images=skip_images)


async def _download_files(
    media_urls: list[MediaLink],
    caption: str | None,
    timeout: aiohttp.ClientTimeout,
    *,
    skip_images: bool = False,
) -> DownloadResult:
    """Download *media_urls* to a temp dir and return a ``DownloadResult``."""
    temp_dir = tempfile.mkdtemp(prefix="apify_ig_")
    files: list[str] = []

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, (media_url, expected_type) in enumerate(
                media_urls[: settings.max_media_items], start=1
            ):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()
                    ct = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    parsed = urlparse(media_url)
                    path_ext = Path(parsed.path).suffix.lower()
                    fallback_ext = ".mp4" if ct.startswith("video/") else ".jpg"
                    ext = (
                        path_ext
                        if path_ext in MEDIA_EXTS
                        else guess_ext_from_content_type(ct, fallback=fallback_ext)
                    )
                    is_media_content_type = ct.startswith(("image/", "video/", "audio/"))
                    is_error_content_type = ct.startswith("text/") or ct in {
                        "application/json",
                        "application/xml",
                    }
                    is_skipped_preview = skip_images and ct.startswith("image/")
                    if is_skipped_preview or is_error_content_type or (
                        not is_media_content_type
                        and path_ext not in MEDIA_EXTS
                        and expected_type is None
                    ):
                        logger.warning(
                            "[instagram] skipped non-media response: host=%s content_type=%s",
                            parsed.netloc,
                            ct or "missing",
                        )
                        continue
                    file_path = Path(temp_dir) / f"ig_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise RuntimeError("Не удалось скачать медиафайлы из ссылок Apify")

        files = await _remove_video_previews(files)

        return DownloadResult(files=files, caption=caption, temp_dir=temp_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
