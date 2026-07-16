"""Command handlers for Cattemis Bot.

Registers:
- /help         — show help message
- /ping         — liveness check
- /stats        — runtime statistics
- /reset        — clear per-chat LLM history
- /say_cattemis — repeat text as the bot (admin-only in groups)
"""

import logging
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters

from ..moderation import can_use_say
from ..state import state
from ..utils.telegram import safe_delete_message, tg_call

logger = logging.getLogger(__name__)
router = Router(name="commands")

# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

_HELP_TEXT = (
    "🐾 катемис\n\n"
    "Скачиваю медиа из TikTok, Instagram, X/Twitter, "
    "YouTube, Vimeo и прямых ссылок на фото/видео~ :3\n\n"
    "Команды:\n"
    "/help — показать это сообщение\n"
    "/ping — проверить, жив ли бот\n"
    "/say_cattemis <текст> — повторить текст от имени бота\n"
    "/stats — статистика бота\n"
    "/reset — очистить память диалога\n"
    "/ttt — крестики-нолики\n"
    "/checkers — шашки\n"
    "/games — открыть выбор игр для чата\n\n"
    "Просто отправь ссылку — я попробую скачать~ 💖"
)


# ---------------------------------------------------------------------------
# Uptime formatter
# ---------------------------------------------------------------------------

def _format_uptime(seconds: float) -> str:
    secs = int(seconds)
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    parts = []
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    parts.append(f"{s}с")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Stats formatter
# ---------------------------------------------------------------------------

def format_stats() -> str:
    """Build a pretty /stats reply string from current state."""
    uptime = _format_uptime(time.time() - state.started_at)
    media_total = state.media_total or 1

    success = state.media_total - state.media_errors
    error_rate = (state.media_errors / media_total) * 100

    lines = [
        "🐾 Статистика катемиса~ :3",
        "",
        f"⏱  Uptime          {uptime}",
        f"💬 Чатов           {len(state.unique_chats)}",
        f"✉️  Сообщений       {state.messages_total}",
        f"🔧 Команд          {state.commands_used}",
        "",
        "── Медиа ───────────────────",
        f"📦 Всего           {state.media_total}",
        f"✅ Успешно         {success}",
        f"❌ Ошибок          {state.media_errors}  ({error_rate:.1f}%)",
        "",
        "── По источникам ───────────",
        f"🎵 TikTok          {state.tiktok_downloads}",
        f"📸 Instagram       {state.instagram_downloads}",
        f"🐦 Twitter/X       {state.twitter_downloads}",
        f"🖼️  Прямые ссылки  {state.direct_image_downloads}",
        f"📹 yt-dlp          {state.ytdlp_downloads}",
    ]

    if state.llm_calls or state.llm_errors:
        lines += [
            "",
            "── LLM ────────────────────",
            f"🤖 Вызовов        {state.llm_calls}",
            f"💥 Ошибок         {state.llm_errors}",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    await tg_call(message.answer, _HELP_TEXT)


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    await tg_call(message.answer, "мяу понг~ 🎵🐾")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    await tg_call(
        message.answer,
        format_stats(),
        reply_parameters=ReplyParameters(message_id=message.message_id),
        parse_mode=None,
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    state.clear_history(message.chat.id)
    await tg_call(
        message.answer,
        "Хозяин, я всё забыл~ теперь как новенький :3",
        reply_parameters=ReplyParameters(message_id=message.message_id),
        parse_mode=None,
    )


@router.message(Command("say_cattemis"))
async def cmd_say(message: Message) -> None:
    """Repeat text as the bot (admin-only in groups)."""
    state.inc("commands_used")
    state.track_chat(message.chat.id)

    if not await can_use_say(message):
        return

    raw_text = (message.text or "").strip()
    payload = raw_text.partition(" ")[2].strip()

    if not payload and message.reply_to_message:
        payload = (
            message.reply_to_message.text or message.reply_to_message.caption or ""
        ).strip()

    if not payload:
        await tg_call(
            message.answer,
            "Хозяин... ты ничего не написал после команды :3\n"
            "Использование: /say_cattemis текст\n"
            "Или ответь на сообщение командой /say_cattemis~",
        )
        return

    async with state.get_lock(message.chat.id):
        await tg_call(message.answer, payload)

    await safe_delete_message(message)
