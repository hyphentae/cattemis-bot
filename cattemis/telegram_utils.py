import asyncio
import random
import time

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message

from .config import ADMIN_CACHE_TTL, GROUP_CHAT_TYPES, PRAISE_KEYWORDS, PRAISE_REPLIES
from .media.links import extract_urls_from_message, is_allowed_media_link
from .runtime import bot

_admin_cache: dict[int, tuple[float, set[int]]] = {}
_bot_username_cache: str | None = None
_bot_id_cache: int | None = None


async def tg_call(func, *args, retries: int = 3, **kwargs):
    for attempt in range(retries + 1):
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as e:
            if attempt >= retries:
                raise
            await asyncio.sleep(float(e.retry_after) + 0.5)


async def safe_status_edit(status: Message, text: str) -> None:
    try:
        await tg_call(status.edit_text, text)
    except Exception:
        pass


async def safe_delete_message(message: Message | None):
    if not message:
        return
    try:
        await tg_call(message.delete)
    except Exception:
        pass


async def get_bot_username() -> str:
    global _bot_username_cache
    if _bot_username_cache is None:
        me = await bot.get_me()
        _bot_username_cache = (me.username or "").lower()
    return _bot_username_cache


async def get_bot_id() -> int:
    global _bot_id_cache
    if _bot_id_cache is None:
        me = await bot.get_me()
        _bot_id_cache = me.id
    return _bot_id_cache


def is_praise_text(text: str) -> bool:
    if not text:
        return False
    normalized = " ".join(text.lower().strip().split())
    return any(keyword in normalized for keyword in PRAISE_KEYWORDS)


async def is_reply_to_this_bot(message: Message) -> bool:
    reply = message.reply_to_message
    if not reply or not reply.from_user:
        return False
    return reply.from_user.id == await get_bot_id()


async def is_bot_mentioned(message: Message) -> bool:
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []

    bot_username = await get_bot_username()
    if not bot_username:
        return False

    expected = f"@{bot_username}"

    for entity in entities:
        if str(entity.type) == "mention":
            mention_text = text[entity.offset : entity.offset + entity.length].lower()
            if mention_text == expected:
                return True

    return False


async def is_praise_for_bot(message: Message) -> bool:
    raw_text = (message.text or message.caption or "").strip()
    if not raw_text or not is_praise_text(raw_text):
        return False

    if await is_reply_to_this_bot(message):
        return True

    if await is_bot_mentioned(message):
        return True

    return False


async def answer_praise(message: Message) -> None:
    await tg_call(message.answer, random.choice(PRAISE_REPLIES))


async def get_admin_ids(chat_id: int) -> set[int]:
    now = time.monotonic()
    cached = _admin_cache.get(chat_id)

    if cached:
        ts, ids = cached
        if now - ts < ADMIN_CACHE_TTL:
            return ids

    admins = await bot.get_chat_administrators(chat_id)
    ids = {member.user.id for member in admins}
    _admin_cache[chat_id] = (now, ids)
    return ids


async def is_admin_message(message: Message) -> bool:
    if not message.from_user:
        return False
    if message.chat.type not in GROUP_CHAT_TYPES:
        return False

    admin_ids = await get_admin_ids(message.chat.id)
    return message.from_user.id in admin_ids


async def can_use_say(message: Message) -> bool:
    if message.chat.type == "private":
        return True
    return await is_admin_message(message)


async def moderate_links(message: Message) -> tuple[bool, list[str]]:
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
        except Exception:
            pass
        return True, urls

    return False, urls
