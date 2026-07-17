"""Utility sub-package for Cattemis Bot.

Re-exports the most commonly used helpers so callers can do::

    from .utils import tg_call, safe_status_edit
"""

from .media import (
    IMAGE_EXTS,
    VIDEO_EXTS,
    AUDIO_EXTS,
    MEDIA_EXTS,
    MEDIA_CONTENT_TYPES,
    guess_ext_from_content_type,
    send_local_media,
    MAX_FILE_SIZE,
)
from .telegram import tg_call, safe_status_edit, safe_delete_message
from .text import (
    cleanup_llm_text,
    strip_unicode_emoji,
    extract_urls_from_message,
    truncate,
)

__all__ = [
    # media
    "IMAGE_EXTS",
    "VIDEO_EXTS",
    "AUDIO_EXTS",
    "MEDIA_EXTS",
    "MEDIA_CONTENT_TYPES",
    "MAX_FILE_SIZE",
    "guess_ext_from_content_type",
    "send_local_media",
    # telegram
    "tg_call",
    "safe_status_edit",
    "safe_delete_message",
    # text
    "cleanup_llm_text",
    "strip_unicode_emoji",
    "extract_urls_from_message",
    "truncate",
]
