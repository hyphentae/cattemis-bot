import asyncio
import shutil
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
import yt_dlp

from ..config import (
    APIFY_INSTAGRAM_ACTOR,
    APIFY_TOKEN,
    IMAGE_EXTS,
    MEDIA_EXTS,
    TIKWM_API,
)
from .links import guess_ext_from_content_type

_api_lock = asyncio.Lock()
_last_api_call: float = 0.0


async def rate_limit_free_api() -> None:
    global _last_api_call
    async with _api_lock:
        now = time.monotonic()
        diff = now - _last_api_call
        if diff < 1.1:
            await asyncio.sleep(1.1 - diff)
        _last_api_call = time.monotonic()


async def download_tiktok(url: str) -> dict:
    await rate_limit_free_api()

    timeout = aiohttp.ClientTimeout(total=40)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    }

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.post(TIKWM_API, data={"url": url, "hd": 1}) as resp:
            resp.raise_for_status()
            payload = await resp.json(content_type=None)

    if payload.get("code") != 0 or not payload.get("data"):
        raise RuntimeError(payload.get("msg") or "TikWM не вернул данные")

    return payload["data"]


def extract_media_urls(obj) -> list[str]:
    found = []
    skip_keys = {
        "thumbnail",
        "thumb",
        "avatar",
        "profile",
        "icon",
        "logo",
        "permalink",
        "shortcode",
        "posturl",
        "pageurl",
    }
    good_keys = {
        "video",
        "image",
        "photo",
        "display",
        "download",
        "src",
        "media",
        "url",
        "play",
    }

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k).lower()

                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    if any(bad in key for bad in skip_keys):
                        pass
                    elif any(ok in key for ok in good_keys):
                        found.append(v)

                walk(v)

        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)

    dedup = []
    seen = set()
    for url in found:
        if url not in seen:
            seen.add(url)
            dedup.append(url)

    return dedup


async def download_instagram_apify(url: str) -> dict:
    if not APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN не задан")

    endpoint = f"https://api.apify.com/v2/acts/{APIFY_INSTAGRAM_ACTOR}/run-sync-get-dataset-items"
    payload = {"url": [url]}
    headers = {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=90)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(endpoint, json=payload, headers=headers) as resp:
            raw_text = await resp.text()

            if resp.status >= 400:
                raise RuntimeError(f"Apify HTTP {resp.status}: {raw_text[:300]}")

            try:
                data = await resp.json(content_type=None)
            except Exception:
                raise RuntimeError("Apify вернул не JSON")

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list) or not data:
        raise RuntimeError("Apify не вернул результатов")

    caption = None
    media_urls = []

    for item in data:
        if isinstance(item, dict):
            if not caption:
                for key in ("caption", "title", "text"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        caption = value.strip()
                        break

            media_urls.extend(extract_media_urls(item))

    dedup_urls = []
    seen = set()
    for media_url in media_urls:
        if media_url not in seen:
            seen.add(media_url)
            dedup_urls.append(media_url)

    if not dedup_urls:
        raise RuntimeError("Apify не вернул прямые ссылки на медиа")

    temp_dir = tempfile.mkdtemp(prefix="apify_ig_")
    files = []

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, media_url in enumerate(dedup_urls[:10], start=1):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()

                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    if not (
                        content_type.startswith("image/")
                        or content_type.startswith("video/")
                        or content_type.startswith("audio/")
                    ):
                        continue

                    parsed = urlparse(media_url)
                    path_ext = Path(parsed.path).suffix.lower()
                    ext = path_ext if path_ext in MEDIA_EXTS else guess_ext_from_content_type(content_type)

                    file_path = Path(temp_dir) / f"ig_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise RuntimeError("Не удалось скачать медиафайлы из ссылок Apify")

        return {
            "temp_dir": temp_dir,
            "files": files,
            "caption": caption,
        }
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def parse_twitter_url(url: str) -> tuple[str, str] | None:
    try:
        parts = [p for p in urlparse(url).path.split("/") if p]
    except Exception:
        return None

    if len(parts) >= 3 and parts[1] == "status":
        return parts[0], parts[2]

    return None


def extract_twitter_media_urls(payload) -> list[str]:
    found = []

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                key = str(k).lower()

                if isinstance(v, str) and v.startswith(("http://", "https://")):
                    if any(x in key for x in ["url", "media", "image", "photo", "video", "playback", "source", "src"]):
                        found.append(v)

                walk(v)

        elif isinstance(value, list):
            for item in value:
                walk(item)

    tweet = payload.get("tweet", payload)
    media = tweet.get("media", {}) if isinstance(tweet, dict) else {}
    walk(media)

    result = []
    seen = set()
    for url in found:
        if url not in seen:
            seen.add(url)
            result.append(url)

    return result


async def download_twitter_fx(url: str) -> dict:
    parsed = parse_twitter_url(url)
    if not parsed:
        raise RuntimeError("Не удалось распарсить ссылку Twitter/X")

    username, tweet_id = parsed
    endpoint = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"
    timeout = aiohttp.ClientTimeout(total=40)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(endpoint) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

    tweet = data.get("tweet", data)
    caption = None
    if isinstance(tweet, dict):
        text = tweet.get("text")
        if isinstance(text, str) and text.strip():
            caption = text.strip()

    media_urls = extract_twitter_media_urls(data)
    if not media_urls:
        raise RuntimeError("FxTwitter не вернул медиа")

    temp_dir = tempfile.mkdtemp(prefix="twitter_fx_")
    files = []

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i, media_url in enumerate(media_urls[:10], start=1):
                async with session.get(media_url) as resp:
                    resp.raise_for_status()

                    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].lower()
                    if not (
                        content_type.startswith("image/")
                        or content_type.startswith("video/")
                        or content_type.startswith("audio/")
                    ):
                        continue

                    parsed_media = urlparse(media_url)
                    path_ext = Path(parsed_media.path).suffix.lower()
                    ext = path_ext if path_ext in MEDIA_EXTS else guess_ext_from_content_type(content_type)

                    file_path = Path(temp_dir) / f"tw_{i}{ext}"
                    file_path.write_bytes(await resp.read())
                    files.append(str(file_path))

        if not files:
            raise RuntimeError("Не удалось скачать файлы из медиа-ссылок FxTwitter")

        return {
            "temp_dir": temp_dir,
            "files": files,
            "caption": caption,
        }
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


async def download_direct_image(url: str) -> dict:
    temp_dir = tempfile.mkdtemp(prefix="img_bot_")
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    timeout = aiohttp.ClientTimeout(total=40)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type")
                ext = path_ext if path_ext in IMAGE_EXTS else guess_ext_from_content_type(content_type, ".jpg")
                file_path = Path(temp_dir) / f"image{ext}"
                file_path.write_bytes(await resp.read())

        return {"temp_dir": temp_dir, "files": [str(file_path)], "caption": None}
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


async def download_ytdlp(url: str) -> dict:
    temp_dir = tempfile.mkdtemp(prefix="media_bot_")
    outtmpl = str(Path(temp_dir) / "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "noplaylist": True,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        files = []
        for p in Path(temp_dir).iterdir():
            if not p.is_file():
                continue
            if p.name.startswith("."):
                continue
            if p.suffix.lower() in {".part", ".ytdl", ".temp"}:
                continue
            files.append(p)

        if not files:
            raise FileNotFoundError("Файл после скачивания не найден")

        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return {
            "temp_dir": temp_dir,
            "files": [str(files[0])],
            "caption": None,
        }

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _download)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
