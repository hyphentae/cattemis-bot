"""Command handlers for Cattemis Bot.

Registers:
- /help         — show help message
- /donate       — support the bot via Telegram Stars or Ko-fi
- /paysupport   — payment support information
- /ping         — liveness check
- /stats        — runtime statistics
- /reset        — clear per-chat LLM history
"""

import logging
import secrets
import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyParameters,
)

from ..config import settings
from ..state import state
from ..utils.telegram import tg_call

logger = logging.getLogger(__name__)
router = Router(name="commands")

_DONATION_AMOUNTS: tuple[int, ...] = (10, 20, 50, 100, 250, 500)
_DONATION_PAYLOAD_PREFIX = "cattemis_donation"

# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

_HELP_TEXT = (
    "КАТЕМИИИС\n\n"
    "Скачиваю медиа из TikTok, Instagram, X/Twitter, "
    "YouTube и Reddit и не только это~ :3\n\n"
    "Команды:\n"
    "/help — показать это сообщение\n"
    "/donate — поддержать бота звёздами или через Ko-fi\n"
    "/paysupport — помощь с платежами\n"
    "/ping — проверить, жив ли бот\n"
    "/stats — статистика бота\n"
    "/reset — очистить память диалога\n"
    "/ttt — крестики нолики в чате\n"
    "/checkers — шашки в чате\n"
    "/games — открыть выбор игр для чата"
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
        "Статистика :3",
        "",
        f"Uptime          {uptime}",
        f"Чатов           {len(state.unique_chats)}",
        f"Сообщений       {state.messages_total}",
        f"Команд          {state.commands_used}",
        "Медиа:",
        f"Всего           {state.media_total}",
        f"Успешно         {success}",
        f"Ошибок          {state.media_errors}  ({error_rate:.1f}%)",
    ]

    if state.llm_calls or state.llm_errors:
        lines += [
            "",
            "── LLM ────────────────────",
            f"Вызовов        {state.llm_calls}",
            f"Ошибок         {state.llm_errors}",
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


def _donation_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=f"{amount} ⭐", callback_data=f"donate:{amount}")
            for amount in _DONATION_AMOUNTS[start : start + 2]
        ]
        for start in range(0, len(_DONATION_AMOUNTS), 2)
    ]
    if settings.kofi_url.startswith(("https://", "http://")):
        rows.append([InlineKeyboardButton(text="☕ Поддержать через Ko-fi", url=settings.kofi_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("donate"))
async def cmd_donate(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    text = (
        "Хозяин хороший, поддержи мою разработку~ \n\n"
        "Выбери количество Телеграм звезд или Ko-fi:"
    )
    if not settings.kofi_url.startswith(("https://", "http://")):
        text += "\n\nKo-fi пока не настроен владельцем бота."
    await tg_call(message.answer, text, reply_markup=_donation_keyboard())


@router.callback_query(F.data.startswith("donate:"))
async def choose_star_donation(callback: CallbackQuery) -> None:
    try:
        amount = int((callback.data or "").partition(":")[2])
    except ValueError:
        amount = 0

    if amount not in _DONATION_AMOUNTS or not isinstance(callback.message, Message):
        await tg_call(callback.answer, "Некорректная сумма", show_alert=True)
        return

    await tg_call(callback.answer)
    payload = (
        f"{_DONATION_PAYLOAD_PREFIX}:{amount}:{callback.from_user.id}:"
        f"{secrets.token_hex(8)}"
    )
    await tg_call(
        callback.message.answer_invoice,
        title="Поддержать котю :3c",
        description="Добровольная поддержка развития и работы бота",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="Поддержка коти", amount=amount)],
    )


@router.pre_checkout_query(F.invoice_payload.startswith(f"{_DONATION_PAYLOAD_PREFIX}:"))
async def approve_star_donation(query: PreCheckoutQuery) -> None:
    parts = query.invoice_payload.split(":")
    try:
        amount = int(parts[1])
        expected_user_id = int(parts[2])
    except (IndexError, ValueError):
        amount = 0
        expected_user_id = 0

    valid = (
        len(parts) == 4
        and query.currency == "XTR"
        and amount in _DONATION_AMOUNTS
        and query.total_amount == amount
        and query.from_user.id == expected_user_id
    )
    await tg_call(
        query.answer,
        ok=valid,
        error_message=None if valid else "Не удалось проверить платёж. Создай новый через /donate.",
    )


@router.message(F.successful_payment)
async def star_donation_received(message: Message) -> None:
    payment = message.successful_payment
    if not payment or not payment.invoice_payload.startswith(f"{_DONATION_PAYLOAD_PREFIX}:"):
        return
    logger.info(
        "Telegram Stars donation received: user_id=%s amount=%s charge_id=%s",
        message.from_user.id if message.from_user else None,
        payment.total_amount,
        payment.telegram_payment_charge_id,
    )
    await tg_call(
        message.answer,
        f"Спасибо за {payment.total_amount} ⭐, хозяин! "
        "Буду стараться для тебя (⸝⸝> ω <⸝⸝)",
    )


@router.message(Command("paysupport"))
async def cmd_paysupport(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    await tg_call(
        message.answer,
        "Если возникла проблема с оплатой Телеграм звезд, напиши владельцу бота "
        "и приложи время платежа и его сумму. Не отправляй данные карты или пароли.",
    )


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    await tg_call(message.answer, "ПООООООНГ")


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
        "Хозяин, мне сделали лоботомию (｡- .•) ничего не помню...",
        reply_parameters=ReplyParameters(message_id=message.message_id),
        parse_mode=None,
    )
