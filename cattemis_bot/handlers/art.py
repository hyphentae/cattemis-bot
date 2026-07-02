"""Art / artist command handlers for Cattemis Bot.

Registers:
- /art (alias /gamble_cattemis) — send a random artwork.
- /artist <id>                  — send a random artwork by a specific artist.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..artists import random_artist_link
from ..state import state
from ..utils.telegram import tg_call

logger = logging.getLogger(__name__)
router = Router(name="art")


@router.message(Command("gamble_cattemis"))
@router.message(Command("art"))
async def cmd_art(message: Message) -> None:
    """Send a random artwork from the configured artists list."""
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    logger.debug("[art] command from chat=%s", message.chat.id)

    link = random_artist_link(state.artists)
    if not link:
        await tg_call(
            message.answer,
            "Хозяин, artists.json пустой или все художники выключены...",
        )
        return

    from .media import process_media_url  # avoid circular at module level

    await process_media_url(
        message,
        link.url,
        initial_status_text=f"Скачиваю артик от {link.label}...",
    )


@router.message(Command("artist"))
async def cmd_artist(message: Message) -> None:
    """Send a random artwork by the specified artist ID."""
    state.inc("commands_used")
    state.track_chat(message.chat.id)

    raw_text = (message.text or "").strip()
    artist_id = raw_text.partition(" ")[2].strip()

    if not artist_id:
        await tg_call(message.answer, "Использование: /artist <id>")
        return

    link = random_artist_link(state.artists, artist_id)
    if not link:
        await tg_call(
            message.answer,
            f"Хозяин, для artist_id='{artist_id}' ничего не найдено.",
        )
        return

    from .media import process_media_url

    await process_media_url(
        message,
        link.url,
        initial_status_text=f"Скачиваю артик от {link.label}...",
    )
