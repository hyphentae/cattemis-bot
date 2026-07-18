"""Reddit image and gallery downloader using Reddit's public JSON output."""

import html
import logging
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import aiohttp

from ..config import settings
from ..utils.media import ANIMATION_EXTS, IMAGE_EXTS, guess_ext_from_content_type
from . import DownloadResult

logger = logging.getLogger(__name__)

REDDIT_DOMAINS: frozenset[str] = frozenset(
    {"reddit.com", "www.reddit.com", "old.reddit.com", "m.reddit.com", "redd.it"}
)
REDDIT_TIMEOUT: float = 40.0
REDDIT_IMAGE_URL_RE = re.compile(
    r"https://i\.redd\.it/[A-Za-z0-9._~!$&'()*+,;=:@%/-]+(?:\?[^\s\"'<>]*)?"
)
REDDIT_PREVIEW_URL_RE = re.compile(r"https://preview\.redd\.it/[^\s\"'<>]+")
REDDIT_PREVIEW_MEDIA_RE = re.compile(
    r"-v\d+-([A-Za-z0-9]+\.(?:jpe?g|png|webp|gif))$",
    re.IGNORECASE,
)
REDDIT_TITLE_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)


class RedditNoImagesError(RuntimeError):
    """Raised when a Reddit post has no directly downloadable images."""


def is_reddit(url: str) -> bool:
    """Return whether *url* belongs to Reddit."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in REDDIT_DOMAINS)


def _json_url(url: str) -> str:
    """Convert a Reddit post, gallery, or short URL to its JSON endpoint."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    parts = [part for part in parsed.path.split("/") if part]

    if host == "redd.it" and parts:
        path = f"/comments/{parts[0]}.json"
    elif len(parts) >= 2 and parts[0] == "gallery":
        path = f"/comments/{parts[1]}.json"
    else:
        path = parsed.path.rstrip("/")
        if not path.endswith(".json"):
            path += ".json"

    return urlunparse(("https", "www.reddit.com", path, "", "raw_json=1", ""))


def _embed_url(url: str) -> str:
    """Return Reddit's public embed page for a post URL."""
    parsed = urlparse(url)
    return urlunparse(("https", "embed.reddit.com", parsed.path, "", "", ""))


async def _fetch_embed_media(
    session: aiohttp.ClientSession,
    url: str,
) -> tuple[list[str], str | None]:
    """Extract original image URLs and title from Reddit's embed page."""
    async with session.get(_embed_url(url)) as response:
        response.raise_for_status()
        raw_page = await response.text()
        page = html.unescape(raw_page)

    title_match = REDDIT_TITLE_RE.search(raw_page)
    title = None
    if title_match:
        title = html.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip()

    if '"type":"video"' in page:
        return [], title

    urls = list(dict.fromkeys(REDDIT_IMAGE_URL_RE.findall(page)))
    if urls:
        return urls, title

    # Gallery embeds expose resized preview URLs rather than i.redd.it URLs.
    # Their filename contains the original media ID, so restore the source URL.
    for preview_url in REDDIT_PREVIEW_URL_RE.findall(page):
        filename = Path(urlparse(preview_url).path).name
        match = REDDIT_PREVIEW_MEDIA_RE.search(filename)
        if match:
            urls.append(f"https://i.redd.it/{match.group(1)}")
    return list(dict.fromkeys(urls)), title


async def _resolve_short_url(session: aiohttp.ClientSession, url: str) -> str:
    """Resolve Reddit's /s/ share links before requesting metadata."""
    parsed = urlparse(url)
    if "/s/" not in parsed.path:
        return url
    async with session.get(url, allow_redirects=True) as response:
        return str(response.url)


def _submission_data(payload: object) -> dict[object, object] | None:
    """Return the submission object from a Reddit listing response."""
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        return None
    listing_data = payload[0].get("data")
    if not isinstance(listing_data, dict):
        return None
    children = listing_data.get("children")
    if not isinstance(children, list) or not children or not isinstance(children[0], dict):
        return None
    submission = children[0].get("data")
    return submission if isinstance(submission, dict) else None


def _extract_image_urls(submission: dict[object, object]) -> list[str]:
    """Extract ordered image URLs from a single-image post or gallery."""
    urls: list[str] = []
    gallery_data = submission.get("gallery_data")
    media_metadata = submission.get("media_metadata")
    if isinstance(gallery_data, dict) and isinstance(media_metadata, dict):
        items = gallery_data.get("items")
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                media_id = item.get("media_id")
                metadata = media_metadata.get(media_id)
                if not isinstance(metadata, dict):
                    continue
                source = metadata.get("s")
                mime = str(metadata.get("m", "")).lower()
                image_url = source.get("u") if isinstance(source, dict) else None
                if isinstance(image_url, str):
                    path_ext = Path(urlparse(image_url).path).suffix.lower()
                    if mime.startswith("image/") or path_ext in IMAGE_EXTS:
                        urls.append(html.unescape(image_url))
        if urls:
            return list(dict.fromkeys(urls))

    destination = submission.get("url_overridden_by_dest") or submission.get("url")
    if isinstance(destination, str):
        path_ext = Path(urlparse(destination).path).suffix.lower()
        if submission.get("post_hint") == "image" or path_ext in IMAGE_EXTS:
            urls.append(html.unescape(destination))

    if not urls:
        crossposts = submission.get("crosspost_parent_list")
        if isinstance(crossposts, list) and crossposts and isinstance(crossposts[0], dict):
            return _extract_image_urls(crossposts[0])
    return list(dict.fromkeys(urls))


async def download_reddit_images(url: str) -> DownloadResult:
    """Download an image or ordered gallery from a Reddit post."""
    timeout = aiohttp.ClientTimeout(total=REDDIT_TIMEOUT)
    headers = {"User-Agent": settings.reddit_user_agent}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        resolved_url = await _resolve_short_url(session, url)
        json_url = _json_url(resolved_url)
        submission = None
        image_urls: list[str] = []
        embed_title: str | None = None
        async with session.get(json_url) as response:
            if response.status == 403 and settings.reddit_client_id:
                payload = await _fetch_oauth_payload(session, json_url)
            elif response.status in {403, 429}:
                payload = None
                image_urls, embed_title = await _fetch_embed_media(session, resolved_url)
            else:
                response.raise_for_status()
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    payload = None
                    image_urls, embed_title = await _fetch_embed_media(session, resolved_url)

        if payload is not None:
            submission = _submission_data(payload)
            if submission:
                image_urls = _extract_image_urls(submission)
        if not image_urls:
            raise RedditNoImagesError("В Reddit-посте нет изображений")

        temp_dir = tempfile.mkdtemp(prefix="reddit_img_")
        files: list[str] = []
        try:
            for index, image_url in enumerate(
                image_urls[: settings.max_media_items], start=1
            ):
                async with session.get(image_url) as response:
                    response.raise_for_status()
                    content_type = (
                        response.headers.get("Content-Type") or ""
                    ).split(";")[0].lower()
                    path_ext = Path(urlparse(image_url).path).suffix.lower()
                    supported_exts = IMAGE_EXTS | ANIMATION_EXTS
                    if not content_type.startswith("image/") and path_ext not in supported_exts:
                        continue
                    ext = (
                        path_ext
                        if path_ext in supported_exts
                        else guess_ext_from_content_type(content_type, ".jpg")
                    )
                    file_path = Path(temp_dir) / f"reddit_{index}{ext}"
                    file_path.write_bytes(await response.read())
                    files.append(str(file_path))

            if not files:
                raise RedditNoImagesError("Не удалось скачать изображения Reddit")

            title = submission.get("title") if submission else embed_title
            caption = title.strip() if isinstance(title, str) and title.strip() else None
            return DownloadResult(files=files, caption=caption, temp_dir=temp_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise


async def _fetch_oauth_payload(
    session: aiohttp.ClientSession,
    json_url: str,
) -> object:
    """Fetch a Reddit listing through OAuth client credentials."""
    auth = aiohttp.BasicAuth(
        settings.reddit_client_id,
        settings.reddit_client_secret,
    )
    async with session.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        auth=auth,
    ) as response:
        response.raise_for_status()
        token_data = await response.json(content_type=None)

    access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise RedditNoImagesError("Reddit OAuth не вернул access_token")

    parsed = urlparse(json_url)
    oauth_url = urlunparse(
        ("https", "oauth.reddit.com", parsed.path, "", parsed.query, "")
    )
    async with session.get(
        oauth_url,
        headers={"Authorization": f"Bearer {access_token}"},
    ) as response:
        response.raise_for_status()
        return await response.json(content_type=None)
