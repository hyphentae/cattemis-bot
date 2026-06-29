from aiogram.filters import Command
from aiogram.types import Message, ReplyParameters
from aiogram.utils.chat_action import ChatActionSender

from .config import LLM_ENABLED, PERSONA_GOTH, PERSONA_NORMAL
from .media.links import is_allowed_media_link
from .media.processor import process_media_url
from .runtime import bot, dp
from .services.artists import random_artist_link
from .services.gamble import gamble_payload, gamble_plan_text, pick_gamble_outcome
from .services.llm import ask_llm, prepare_llm_text
from .state import get_chat_lock, get_chat_settings, llm_context_key, persona_label, set_chat_persona
from .telegram_utils import (
    answer_praise,
    can_use_say,
    is_bot_mentioned,
    is_praise_for_bot,
    is_reply_to_this_bot,
    moderate_links,
    safe_delete_message,
    tg_call,
)


async def apply_persona_command(message: Message, persona: str) -> None:
    if not await can_use_say(message):
        return

    if not set_chat_persona(message.chat.id, persona):
        await tg_call(message.answer, "Не знаю такой режим. Доступно: normal, goth.")
        return

    if persona == PERSONA_GOTH:
        await tg_call(message.answer, "Гот-режим включён. Каттемис поправил чёрный воротник и слушает ночь.")
    else:
        await tg_call(message.answer, "Обычный режим включён. Каттемис снова мягкий, бодрый и по делу.")


@dp.message(Command("goth", "goth_cattemis"))
async def cmd_goth(message: Message):
    await apply_persona_command(message, PERSONA_GOTH)


@dp.message(Command("normal_cattemis"))
async def cmd_normal(message: Message):
    await apply_persona_command(message, PERSONA_NORMAL)


@dp.message(Command("cattemis_mode"))
async def cmd_cattemis_mode(message: Message):
    if not await can_use_say(message):
        return

    raw_text = (message.text or "").strip()
    payload = raw_text.partition(" ")[2].strip().lower()

    if not payload:
        current = persona_label(get_chat_settings(message.chat.id).persona)
        await tg_call(message.answer, f"Сейчас включён {current}.\nИспользование: /cattemis_mode normal|goth")
        return

    aliases = {
        "normal": PERSONA_NORMAL,
        "обычный": PERSONA_NORMAL,
        "default": PERSONA_NORMAL,
        "goth": PERSONA_GOTH,
        "гот": PERSONA_GOTH,
        "готик": PERSONA_GOTH,
    }
    persona = aliases.get(payload)
    if not persona:
        await tg_call(message.answer, "Не знаю такой режим. Доступно: normal или goth.")
        return

    await apply_persona_command(message, persona)


@dp.message(Command("say_cattemis"))
async def cmd_say(message: Message):
    if not await can_use_say(message):
        return

    raw_text = (message.text or "").strip()
    payload = raw_text.partition(" ")[2].strip()

    if not payload and message.reply_to_message:
        payload = (message.reply_to_message.text or message.reply_to_message.caption or "").strip()

    if not payload:
        await tg_call(message.answer, "Использование: /say_cattemis текст\nИли ответь на сообщение командой /say_cattemis")
        return

    async with get_chat_lock(message.chat.id):
        await tg_call(message.answer, payload)

    await safe_delete_message(message)


@dp.message(Command("gamble", "gamble_cattemis"))
async def cmd_gamble(message: Message):
    raw_text = (message.text or "").strip()
    payload = gamble_payload(raw_text)

    if payload.lower() in {"plan", "план"}:
        await tg_call(message.answer, gamble_plan_text())
        return

    roll, outcome = pick_gamble_outcome()
    wager = payload or "без ставки"
    await tg_call(
        message.answer,
        (
            f"🎲 /gamble\n"
            f"Ставка: {wager}\n"
            f"Бросок: {roll}/100\n"
            f"Исход: {outcome.title} ({outcome.multiplier})\n"
            f"{outcome.text}"
        ),
        reply_parameters=ReplyParameters(message_id=message.message_id),
    )

    if outcome.art_prize:
        link = random_artist_link()
        if not link:
            await tg_call(message.answer, "Призовой арт был в плане, но artists.json пустой.")
            return
        await process_media_url(message, link.url, initial_status_text=f"Скачиваю призовой артик от {link.label}...")


@dp.message(Command("art"))
async def cmd_art(message: Message):
    print(f"[art] command from chat={message.chat.id}")

    link = random_artist_link()
    if not link:
        await tg_call(message.answer, "Хозяин, artists.json пустой или все художники выключены...")
        return

    await process_media_url(message, link.url, initial_status_text=f"Скачиваю артик от {link.label}...")


@dp.message(Command("artist"))
async def cmd_artist(message: Message):
    raw_text = (message.text or "").strip()
    artist_id = raw_text.partition(" ")[2].strip()

    if not artist_id:
        await tg_call(message.answer, "Использование: /artist <id>")
        return

    link = random_artist_link(artist_id)
    if not link:
        await tg_call(message.answer, f"Хозяин, для artist_id='{artist_id}' ничего не найдено.")
        return

    await process_media_url(message, link.url, initial_status_text=f"Скачиваю артик от {link.label}...")


@dp.message()
async def handle_message(message: Message):
    deleted, urls = await moderate_links(message)
    if deleted:
        return

    raw_text = (message.text or message.caption or "").strip()

    if raw_text.startswith("/"):
        return

    if await is_praise_for_bot(message):
        await answer_praise(message)
        return

    if urls:
        allowed_urls = [url for url in urls if is_allowed_media_link(url)]
        if not allowed_urls:
            if message.chat.type == "private":
                await tg_call(message.answer, "Пришли мне ссылку на фото или видео.")
            return

        await process_media_url(message, allowed_urls[0], initial_status_text="Скачиваю...")
        return

    if not raw_text:
        return

    should_use_llm = False
    if LLM_ENABLED:
        if message.chat.type == "private":
            should_use_llm = True
        elif await is_reply_to_this_bot(message) or await is_bot_mentioned(message):
            should_use_llm = True

    if should_use_llm:
        try:
            chat_settings = get_chat_settings(message.chat.id)
            llm_text = await prepare_llm_text(message, raw_text)
            async with ChatActionSender.typing(
                bot=bot,
                chat_id=message.chat.id,
                message_thread_id=message.message_thread_id,
            ):
                reply = await ask_llm(
                    llm_text,
                    user_name=message.from_user.first_name if message.from_user else None,
                    persona=chat_settings.persona,
                    history_key=llm_context_key(message),
                )

            reply = reply.strip()[:4000] or "..."

            await tg_call(
                message.answer,
                reply,
                reply_parameters=ReplyParameters(message_id=message.message_id),
            )
        except Exception as e:
            print(f"[llm] error: {e}")
            await tg_call(
                message.answer,
                "Хозяин... я задумался слишком сильно и не смог ответить TᴖT",
                reply_parameters=ReplyParameters(message_id=message.message_id),
            )
        return

    if message.chat.type == "private":
        await tg_call(message.answer, "Пришли мне ссылку на фото или видео.")
