from urllib.parse import urlparse

from aiogram.types import Message

from ..config import (
    ALLOWED_MEDIA_HOSTS,
    IMAGE_EXTS,
    INSTAGRAM_DOMAINS,
    MEDIA_CONTENT_TYPES,
    MEDIA_EXTS,
    TIKTOK_DOMAINS,
    TWITTER_DOMAINS,
)


def normalize_possible_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def host_matches(host: str, allowed_hosts: set[str]) -> bool:
    host = (host or "").lower()
    return any(host == item or host.endswith("." + item) for item in allowed_hosts)


def is_tiktok(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return host_matches(host, TIKTOK_DOMAINS)


def is_instagram(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return host_matches(host, INSTAGRAM_DOMAINS)


def is_twitter(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return host_matches(host, TWITTER_DOMAINS)


def is_direct_image(url: str) -> bool:
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return False
    return any(path.endswith(ext) for ext in IMAGE_EXTS)


def is_allowed_media_link(url: str) -> bool:
    url = normalize_possible_url(url)

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    if host_matches(host, ALLOWED_MEDIA_HOSTS):
        return True

    if any(path.endswith(ext) for ext in MEDIA_EXTS):
        return True

    return False


def guess_ext_from_content_type(content_type: str | None, fallback: str = ".jpg") -> str:
    if not content_type:
        return fallback
    content_type = content_type.split(";")[0].strip().lower()
    return MEDIA_CONTENT_TYPES.get(content_type, fallback)


def extract_urls_from_message(message: Message) -> list[str]:
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    urls = []

    for entity in entities:
        entity_type = str(entity.type)

        if entity_type == "url":
            raw = text[entity.offset : entity.offset + entity.length]
            raw = normalize_possible_url(raw)
            if raw:
                urls.append(raw)

        elif entity_type == "text_link" and entity.url:
            raw = normalize_possible_url(entity.url)
            if raw:
                urls.append(raw)

    dedup = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            dedup.append(url)

    return dedup
