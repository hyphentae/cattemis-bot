"""Text processing utilities for Cattemis Bot."""

import re
from urllib.parse import urlparse

from aiogram.types import Message

# ---------------------------------------------------------------------------
# Emoji stripping
# ---------------------------------------------------------------------------

PROTOCOL_MARKER_RE = re.compile(
    r"<\|(?:/?(?:channel|message|analysis|final|thought|commentary|end|start))\|>"
    r"|<channel\|>"
    r"|\b(?:thought|analysis|commentary|final)\s*(?=<\|?channel\|>)",
    flags=re.IGNORECASE,
)


def strip_protocol_markers(text: str) -> str:
    """Remove leaked model channel markers without altering user-facing text."""
    return PROTOCOL_MARKER_RE.sub("", text)


def repair_truncated_kaomoji(text: str) -> str:
    """Restore a missing closing ``<`` on supported truncated kaomoji."""
    if text.endswith((">///", ">w")):
        return text + "<"
    return text


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------

def _normalize_possible_url(url: str) -> str:
    """Prepend ``https://`` to *url* if it lacks a scheme."""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_urls_from_message(message: Message) -> list[str]:
    """Return a deduplicated list of URLs found in *message* entities.

    Handles both ``url`` and ``text_link`` entity types.
    """
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    urls: list[str] = []

    for entity in entities:
        entity_type = str(entity.type)

        if entity_type == "url":
            raw = text[entity.offset : entity.offset + entity.length]
            raw = _normalize_possible_url(raw)
            if raw:
                urls.append(raw)

        elif entity_type == "text_link" and entity.url:
            raw = _normalize_possible_url(entity.url)
            if raw:
                urls.append(raw)

    return list(dict.fromkeys(urls))


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

def truncate(text: str, max_len: int = 1024) -> str | None:
    """Return *text* stripped and capped at *max_len* characters, or None if empty."""
    if not text:
        return None
    return text.strip()[:max_len] or None
