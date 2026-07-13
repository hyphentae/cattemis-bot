"""Tic-tac-toe game handler for Cattemis Bot.

Usage:
    /ttt        — start a new game (solo vs bot, or challenges another user)
    /ttt @user  — challenge a specific user (they must press Accept)

The board is rendered as a 3×3 inline keyboard.
Buttons show ⬜ (empty), ❌ (X), ⭕ (O).
The bot plays as O when in single-player mode.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router()

# ---------------------------------------------------------------------------
# Game state  (in-memory, per chat_id)
# ---------------------------------------------------------------------------

class TicTacToeGame:
    EMPTY = "⬜"
    X = "❌"
    O = "⭕"

    def __init__(self, chat_id: int, player_x_id: int, player_o_id: Optional[int]):
        self.chat_id = chat_id
        self.player_x_id = player_x_id          # always a human
        self.player_o_id = player_o_id           # None  →  bot plays O
        self.board: List[str] = [self.EMPTY] * 9
        self.current: str = self.X               # X goes first
        self.over: bool = False

    @property
    def vs_bot(self) -> bool:
        return self.player_o_id is None

    def current_player_id(self) -> Optional[int]:
        if self.current == self.X:
            return self.player_x_id
        return self.player_o_id  # None when bot's turn

    def make_move(self, idx: int) -> bool:
        """Place current player's mark. Returns True if successful."""
        if self.board[idx] != self.EMPTY or self.over:
            return False
        self.board[idx] = self.current
        self.current = self.O if self.current == self.X else self.X
        return True

    def bot_move(self) -> int:
        """Simple bot: win > block > random."""
        # try to win
        move = self._find_winning_move(self.O)
        if move is not None:
            return move
        # try to block
        move = self._find_winning_move(self.X)
        if move is not None:
            return move
        # prefer center
        if self.board[4] == self.EMPTY:
            return 4
        # random corner / edge
        empties = [i for i, c in enumerate(self.board) if c == self.EMPTY]
        return random.choice(empties)

    def _find_winning_move(self, mark: str) -> Optional[int]:
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for a, b, c in lines:
            cells = [self.board[a], self.board[b], self.board[c]]
            if cells.count(mark) == 2 and cells.count(self.EMPTY) == 1:
                return [a, b, c][cells.index(self.EMPTY)]
        return None

    def check_winner(self) -> Optional[str]:
        """Return winning mark, 'draw', or None."""
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for a, b, c in lines:
            if self.board[a] != self.EMPTY and self.board[a] == self.board[b] == self.board[c]:
                self.over = True
                return self.board[a]
        if self.EMPTY not in self.board:
            self.over = True
            return "draw"
        return None


# chat_id → game
_games: Dict[int, TicTacToeGame] = {}
# chat_id → (challenger_id, challenged_id)
_pending: Dict[int, Tuple[int, int]] = {}


# ---------------------------------------------------------------------------
# Keyboard builder
# ---------------------------------------------------------------------------

def _build_keyboard(game: TicTacToeGame) -> InlineKeyboardMarkup:
    rows = []
    for row in range(3):
        buttons = []
        for col in range(3):
            idx = row * 3 + col
            cell = game.board[idx]
            # disabled-looking button if already taken
            cb = f"ttt:{idx}" if cell == TicTacToeGame.EMPTY and not game.over else "ttt:noop"
            buttons.append(InlineKeyboardButton(text=cell, callback_data=cb))
        rows.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _status_text(game: TicTacToeGame, winner: Optional[str] = None) -> str:
    if winner:
        if winner == "draw":
            return "🤝 Ничья! Никто не победил :3"
        emoji = winner
        if game.vs_bot:
            who = "Ты" if winner == TicTacToeGame.X else "Бот"
            return f"{emoji} {who} победил{'а' if winner == TicTacToeGame.X else ''}! ✨"
        pid = game.player_x_id if winner == TicTacToeGame.X else game.player_o_id
        return f"{emoji} <a href='tg://user?id={pid}'>Игрок</a> победил! ✨"
    # still playing
    turn_mark = game.current
    if game.vs_bot and turn_mark == TicTacToeGame.O:
        return f"Ход бота {turn_mark}..."
    pid = game.current_player_id()
    return f"Ход {turn_mark} — <a href='tg://user?id={pid}'>игрок</a>"


# ---------------------------------------------------------------------------
# /ttt command
# ---------------------------------------------------------------------------

@router.message(Command("ttt"))
async def cmd_ttt(message: Message) -> None:
    chat_id = message.chat.id
    caller_id = message.from_user.id

    # Challenge another user?
    if message.entities and len(message.entities) > 1:
        # parse @mention from text
        for ent in message.entities:
            if ent.type == "mention":
                # Can't get user id from @mention in public without resolving;
                # use text_mention entity instead (works when user clicked)
                pass
        # text_mention gives us the User object
        challenged_user = None
        for ent in message.entities:
            if ent.type == "text_mention" and ent.user:
                challenged_user = ent.user
                break
        if challenged_user and challenged_user.id != caller_id:
            _pending[chat_id] = (caller_id, challenged_user.id)
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="✅ Принять вызов!",
                    callback_data=f"ttt_accept:{challenged_user.id}"
                )
            ]])
            await message.reply(
                f"<a href='tg://user?id={caller_id}'>Игрок</a> вызывает "
                f"<a href='tg://user?id={challenged_user.id}'>{challenged_user.first_name}</a> "
                f"на крестики-нолики! ❌⭕\n"
                f"Нажми кнопку ниже чтобы принять :3",
                parse_mode="HTML",
                reply_markup=kb,
            )
            return

    # Solo game vs bot
    game = TicTacToeGame(chat_id=chat_id, player_x_id=caller_id, player_o_id=None)
    _games[chat_id] = game
    await message.reply(
        f"❌⭕ Крестики-нолики!\n"
        f"Ты играешь за ❌, бот за ⭕\n"
        f"Ход ❌ — твой ход!",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Accept challenge callback
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("ttt_accept:"))
async def cb_accept(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    expected_user_id = int(call.data.split(":")[1])

    if call.from_user.id != expected_user_id:
        await call.answer("Этот вызов не для тебя! :3", show_alert=True)
        return

    if chat_id not in _pending:
        await call.answer("Вызов устарел.", show_alert=True)
        return

    challenger_id, challenged_id = _pending.pop(chat_id)
    game = TicTacToeGame(
        chat_id=chat_id,
        player_x_id=challenger_id,
        player_o_id=challenged_id,
    )
    _games[chat_id] = game
    await call.message.edit_text(
        f"❌⭕ Игра началась!\n"
        f"<a href='tg://user?id={challenger_id}'>Игрок X ❌</a> vs "
        f"<a href='tg://user?id={challenged_id}'>Игрок O ⭕</a>\n"
        f"Ход ❌",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Board click callback
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("ttt:"))
async def cb_move(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    payload = call.data.split(":")[1]

    if payload == "noop":
        await call.answer()
        return

    idx = int(payload)
    game = _games.get(chat_id)

    if game is None:
        await call.answer("Нет активной игры. Начни /ttt :3", show_alert=True)
        return

    if game.over:
        await call.answer("Игра уже закончена!", show_alert=True)
        return

    # Check it's this user's turn
    expected = game.current_player_id()
    if expected is not None and call.from_user.id != expected:
        await call.answer("Не твой ход! :3", show_alert=True)
        return

    if not game.make_move(idx):
        await call.answer("Клетка занята!", show_alert=True)
        return

    winner = game.check_winner()
    status = _status_text(game, winner)

    if winner:
        _games.pop(chat_id, None)
        await call.message.edit_text(
            f"❌⭕ Крестики-нолики\n{status}",
            reply_markup=_build_keyboard(game),
            parse_mode="HTML",
        )
        await call.answer()
        return

    # Bot's turn?
    if game.vs_bot and game.current == TicTacToeGame.O:
        bot_idx = game.bot_move()
        game.make_move(bot_idx)
        winner = game.check_winner()
        status = _status_text(game, winner)
        if winner:
            _games.pop(chat_id, None)

    await call.message.edit_text(
        f"❌⭕ Крестики-нолики\n{status}",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )
    await call.answer()
