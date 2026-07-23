"""Telegram HTML5 Game launch handlers."""

from urllib.parse import quote

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineQuery, InlineQueryResultGame, Message
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import settings
from ..game_auth import create_game_auth_token
from ..state import state
from ..tunnel import current_tunnel_url

router = Router(name="games")

GAMES = (
    ("tictactoe", "крестики-нолики"),
    ("minesweeper", "сапёр"),
    ("sudoku", "судоку"),
    ("canvas", "общий холст"),
    ("chess", "шахматы"),
    ("parabolic_chess", "parabolic chess"),
    ("checkers", "шашки"),
)
GAME_SHORT_NAMES = frozenset(short_name for short_name, _ in GAMES)


@router.message(Command("games"))
async def cmd_games(message: Message) -> None:
    """Open a compact inline picker for the registered games."""
    state.inc("commands_used")
    state.track_chat(message.chat.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=title,
            switch_inline_query_current_chat=short_name,
        )]
        for short_name, title in GAMES
    ])
    await message.answer(
        "выбери игру",
        reply_markup=keyboard,
    )


@router.inline_query()
async def inline_games(query: InlineQuery) -> None:
    """Offer all matching game cards in inline mode."""
    search = query.query.strip().lower()
    games = [
        (short_name, title)
        for short_name, title in GAMES
        if not search or search in short_name or search in title.lower()
    ]
    await query.answer(
        results=[
            InlineQueryResultGame(
                id=f"cattemis-{short_name}",
                game_short_name=short_name,
            )
            for short_name, _ in games
        ],
        cache_time=0,
        is_personal=True,
    )


@router.callback_query(F.game_short_name.in_(GAME_SHORT_NAMES))
async def launch_game(query: CallbackQuery) -> None:
    """Return the current tunnel URL with a signed player identity."""
    url = current_tunnel_url()
    if not url:
        await query.answer(
            "игровой домик пока не открылся... попробуй ещё раз, хозяин T_T",
            show_alert=True,
        )
        return

    token = create_game_auth_token(
        query.from_user,
        settings.bot_token,
        query.chat_instance or "",
    )
    short_name = query.game_short_name or ""
    launch_url = (
        f"{url.rstrip('/')}/#game={quote(short_name, safe='')}"
        f"&game_auth={quote(token, safe='')}"
    )
    await query.answer(url=launch_url, cache_time=0)
