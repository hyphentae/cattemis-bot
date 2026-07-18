"""Link-moderation logic for Cattemis Bot.

In group chats, non-admin messages that contain links to non-media hosts are
deleted automatically.  Admin messages are always allowed through.

Public API:
- ``moderate_links(message)`` — delete if necessary, return ``(deleted, urls)``.
- ``is_admin_message(message)`` — check whether the message author is an admin.
- ``can_use_say(message)`` — check whether the author may use /say_cattemis.
"""

import logging
import time
from urllib.parse import urlparse

from aiogram.types import Message

from .config import settings
from .state import state
from .utils.text import extract_urls_from_message

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GROUP_CHAT_TYPES: frozenset[str] = frozenset({"group", "supergroup"})

# These domains + any direct media file extension are allowed in groups
from .downloaders.tiktok import TIKTOK_DOMAINS
from .downloaders.instagram import INSTAGRAM_DOMAINS
from .downloaders.reddit import REDDIT_DOMAINS
from .downloaders.twitter import TWITTER_DOMAINS
from .downloaders.ytdlp import YOUTUBE_DOMAINS, VIMEO_DOMAINS
from .utils.media import MEDIA_EXTS

_ALLOWED_MEDIA_HOSTS: frozenset[str] = (
    TIKTOK_DOMAINS
    | INSTAGRAM_DOMAINS
    | TWITTER_DOMAINS
    | YOUTUBE_DOMAINS
    | VIMEO_DOMAINS
    | REDDIT_DOMAINS
)


# ---------------------------------------------------------------------------
# URL classification
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _host_matches(host: str, allowed: frozenset[str]) -> bool:
    host = (host or "").lower()
    return any(host == item or host.endswith("." + item) for item in allowed)


def is_allowed_media_link(url: str) -> bool:
    """Return True if *url* points to an allowed media source."""
    url = _normalize_url(url)
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    if _host_matches(host, _ALLOWED_MEDIA_HOSTS):
        return True
    if any(path.endswith(ext) for ext in MEDIA_EXTS):
        return True
    return False


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------

async def _get_admin_ids(chat_id: int) -> set[int]:
    """Return the set of admin user-IDs for *chat_id*, using a TTL cache."""
    # Import bot lazily to avoid circular imports at module load time
    from .main import bot  # noqa: PLC0415

    now = time.monotonic()
    cached = state.admin_cache.get(chat_id)
    if cached:
        ts, ids = cached
        if now - ts < settings.admin_cache_ttl:
            return ids

    admins = await bot.get_chat_administrators(chat_id)
    ids = {member.user.id for member in admins}
    state.admin_cache[chat_id] = (now, ids)
    logger.debug("Admin cache refreshed for chat_id=%s (%d admins)", chat_id, len(ids))
    return ids


async def is_admin_message(message: Message) -> bool:
    """Return True if the message author is a chat admin."""
    if not message.from_user:
        return False
    if message.chat.type not in GROUP_CHAT_TYPES:
        return False
    admin_ids = await _get_admin_ids(message.chat.id)
    return message.from_user.id in admin_ids


async def can_use_say(message: Message) -> bool:
    """Return True if the message author may use /say_cattemis."""
    if message.chat.type == "private":
        return True
    return await is_admin_message(message)


# ---------------------------------------------------------------------------
# Moderation entry point
# ---------------------------------------------------------------------------

async def moderate_links(message: Message) -> tuple[bool, list[str]]:
    """Moderate a message in a group chat.

    If the message contains any non-media links and the author is not an admin,
    the message is deleted.

    Returns:
        A tuple ``(deleted, urls)`` where *deleted* is True if the message was
        removed, and *urls* is the list of URLs found in the message.
    """
    urls = extract_urls_from_message(message)
    if not urls:
        return False, []

    if message.chat.type not in GROUP_CHAT_TYPES:
        return False, urls

    if await is_admin_message(message):
        return False, urls

    has_bad_links = any(not is_allowed_media_link(url) for url in urls)
    if has_bad_links:
        try:
            await message.delete()
            logger.info("Deleted message with forbidden links from user %s in chat %s",
                        message.from_user and message.from_user.id, message.chat.id)
        except Exception as exc:
            logger.warning("Could not delete message: %s", exc)
        return True, urls

    return False, urls
