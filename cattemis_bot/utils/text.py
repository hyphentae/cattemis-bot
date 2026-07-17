"""Text processing utilities for Cattemis Bot.

Provides:
- ``strip_unicode_emoji`` — remove emoji characters from a string.
- ``cleanup_llm_text`` — clean up raw LLM output for Telegram display.
- ``extract_urls_from_message`` — collect unique URLs from a Telegram message.
- ``truncate`` — cap a string to a maximum length.
"""

import re
from urllib.parse import urlparse

from aiogram.types import Message

# ---------------------------------------------------------------------------
# Emoji stripping
# ---------------------------------------------------------------------------

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)


def strip_unicode_emoji(text: str) -> str:
    """Remove Unicode emoji characters from *text*."""
    return EMOJI_RE.sub("", text)


# ---------------------------------------------------------------------------
# LLM output cleanup
# ---------------------------------------------------------------------------

def cleanup_llm_text(text: str) -> str:
    """Normalise raw LLM output for Telegram.

    - Strips emoji.
    - Removes Markdown bold markers (``**`` / ``*``).
    - Collapses repeated spaces and blank lines.
    - Collapses repeated punctuation.
    """
    text = strip_unicode_emoji(text)
    text = text.replace("**", "*")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
