"""Telegram API helpers for Cattemis Bot.

Provides thin wrappers around aiogram calls that handle rate-limiting
(``TelegramRetryAfter``) and silently swallow non-fatal errors.
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Default number of retry attempts for tg_call
_DEFAULT_TG_RETRIES: int = 3


async def tg_call(
    func: Callable[..., Coroutine[Any, Any, Any]],
    /,
    *args: Any,
    retries: int = _DEFAULT_TG_RETRIES,
    **kwargs: Any,
) -> Any:
    """Call an aiogram coroutine function, retrying on ``TelegramRetryAfter``.

    Args:
        func: The aiogram async callable to invoke.
        *args: Positional arguments forwarded to *func*.
        retries: Maximum number of retry attempts (default 3).
        **kwargs: Keyword arguments forwarded to *func*.

    Returns:
        Whatever *func* returns.

    Raises:
        TelegramRetryAfter: If all retries are exhausted.
        Any other exception raised by *func*.
    """
    for attempt in range(retries + 1):
        try:
            return await func(*args, **kwargs)
        except TelegramRetryAfter as exc:
            if attempt >= retries:
                raise
            wait = float(exc.retry_after) + 0.5
            logger.warning("Telegram rate-limit hit, sleeping %.1f s (attempt %d)", wait, attempt + 1)
            await asyncio.sleep(wait)


async def safe_status_edit(status: Message, text: str) -> None:
    """Edit *status* message text, ignoring all errors silently."""
    try:
        await tg_call(status.edit_text, text)
    except Exception as exc:
        logger.debug("safe_status_edit swallowed: %s", exc)


async def safe_delete_message(message: Message | None) -> None:
    """Delete *message*, ignoring errors (e.g. already deleted)."""
    if not message:
        return
    try:
        await tg_call(message.delete)
    except Exception as exc:
        logger.debug("safe_delete_message swallowed: %s", exc)
