"""Checkers (draughts) game handler for Cattemis Bot.

Usage:
    /checkers           — start a game vs bot
    /checkers @user     — challenge another user (text_mention)
"""

from __future__ import annotations

import asyncio
import logging
import random
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logger = logging.getLogger(__name__)
router = Router()

EMPTY   = "⬜"
DARK    = "⬛"
W_MAN   = "🔴"
W_KING  = "👑"
B_MAN   = "🔵"
B_KING  = "🐞"
DOT     = "🟢"
SEL     = "🟡"

P1 = "W"
P2 = "B"

# Minimum seconds between edit_text calls to avoid flood control
_EDIT_COOLDOWN = 1.5


def _is_dark(r: int, c: int) -> bool:
    return (r + c) % 2 == 1


def _initial_board() -> List[List[str]]:
    board = [[""] * 8 for _ in range(8)]
    for r in range(8):
        for c in range(8):
            if not _is_dark(r, c):
                board[r][c] = DARK
            elif r < 3:
                board[r][c] = B_MAN
            elif r > 4:
                board[r][c] = W_MAN
            else:
                board[r][c] = EMPTY
    return board


def _is_p1(cell: str) -> bool:
    return cell in (W_MAN, W_KING)


def _is_p2(cell: str) -> bool:
    return cell in (B_MAN, B_KING)


def _is_king(cell: str) -> bool:
    return cell in (W_KING, B_KING)


def _owner(cell: str) -> Optional[str]:
    if _is_p1(cell): return P1
    if _is_p2(cell): return P2
    return None


def _forward_dirs(piece: str) -> List[Tuple[int, int]]:
    if _is_king(piece):
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    if _is_p1(piece):
        return [(-1, -1), (-1, 1)]
    return [(1, -1), (1, 1)]


def _all_dirs() -> List[Tuple[int, int]]:
    return [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _get_captures(board, r, c, player):
    piece = board[r][c]
    enemy = P2 if player == P1 else P1
    results = []
    for dr, dc in _all_dirs():
        mr, mc = r + dr, c + dc
        lr, lc = r + 2*dr, c + 2*dc
        if not (0 <= mr < 8 and 0 <= mc < 8 and 0 <= lr < 8 and 0 <= lc < 8):
            continue
        if _owner(board[mr][mc]) == enemy and board[lr][lc] == EMPTY:
            results.append((r, c, lr, lc))
    return results


def _get_moves(board, r, c, player):
    piece = board[r][c]
    results = []
    for dr, dc in _forward_dirs(piece):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == EMPTY:
            results.append((r, c, nr, nc))
    return results


def _all_captures_for_player(board, player):
    caps = []
    for r in range(8):
        for c in range(8):
            if _owner(board[r][c]) == player:
                caps.extend(_get_captures(board, r, c, player))
    return caps


def _all_moves_for_player(board, player):
    caps = _all_captures_for_player(board, player)
    if caps:
        return caps
    moves = []
    for r in range(8):
        for c in range(8):
            if _owner(board[r][c]) == player:
                moves.extend(_get_moves(board, r, c, player))
    return moves


def _apply_move(board, fr, fc, tr, tc):
    b = deepcopy(board)
    piece = b[fr][fc]
    b[tr][tc] = piece
    b[fr][fc] = EMPTY
    if abs(tr - fr) == 2:
        b[(fr + tr) // 2][(fc + tc) // 2] = EMPTY
    if piece == W_MAN and tr == 0:
        b[tr][tc] = W_KING
    elif piece == B_MAN and tr == 7:
        b[tr][tc] = B_KING
    return b


def _bot_move(board):
    moves = _all_moves_for_player(board, P2)
    if not moves:
        return None
    caps = _all_captures_for_player(board, P2)
    if caps:
        return min(
            caps,
            key=lambda m: sum(
                1 for r in range(8) for c in range(8)
                if _is_p1(_apply_move(board, *m)[r][c])
            ),
        )
    return random.choice(moves)


def _check_winner(board):
    has_p1 = any(_is_p1(board[r][c]) for r in range(8) for c in range(8))
    has_p2 = any(_is_p2(board[r][c]) for r in range(8) for c in range(8))
    if not has_p1: return P2
    if not has_p2: return P1
    if not _all_moves_for_player(board, P1): return P2
    if not _all_moves_for_player(board, P2): return P1
    return None


async def _safe_edit(msg: Message, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """edit_text with RetryAfter handling and TelegramBadRequest suppression."""
    try:
        await msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except TelegramRetryAfter as e:
        await asyncio.sleep(float(e.retry_after) + 0.5)
        try:
            await msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except (TelegramRetryAfter, TelegramBadRequest) as inner:
            logger.warning("[checkers] edit_text failed after retry: %s", inner)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.warning("[checkers] edit_text bad request: %s", e)


class CheckersGame:
    def __init__(self, chat_id, player1_id, player2_id):
        self.chat_id = chat_id
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.board = _initial_board()
        self.current = P1
        self.selected = None
        self.over = False
        self.winner = None

    @property
    def vs_bot(self):
        return self.player2_id is None

    def current_human_id(self):
        if self.current == P1:
            return self.player1_id
        return self.player2_id

    def valid_targets(self):
        if self.selected is None:
            return []
        fr, fc = self.selected
        all_moves = _all_moves_for_player(self.board, self.current)
        return [(tr, tc) for (r, c, tr, tc) in all_moves if r == fr and c == fc]


_games: Dict[int, CheckersGame] = {}
_pending: Dict[int, Tuple[int, int]] = {}


def _build_keyboard(game: CheckersGame) -> InlineKeyboardMarkup:
    targets = set(game.valid_targets())
    sel = game.selected
    rows = []
    for r in range(8):
        row_btns = []
        for c in range(8):
            cell = game.board[r][c]
            is_sel = sel == (r, c)
            is_target = (r, c) in targets
            if is_sel:
                display = SEL
            elif is_target:
                display = DOT
            else:
                display = cell
            if game.over:
                cb = "chk:noop"
            elif is_target:
                cb = f"chk:move:{r}:{c}"
            elif not _is_dark(r, c):
                cb = "chk:noop"
            elif _owner(cell) == game.current and not game.over:
                cb = f"chk:sel:{r}:{c}"
            else:
                cb = "chk:noop"
            row_btns.append(InlineKeyboardButton(text=display, callback_data=cb))
        rows.append(row_btns)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _status(game: CheckersGame) -> str:
    if game.over:
        if game.winner == P1:
            if game.vs_bot:
                return "Хозяин ты победил! хехе~ >:3"
            return f"🔴 <a href='tg://user?id={game.player1_id}'>хозяин</a> победил! хехе~ >:3"
        if game.winner == P2:
            if game.vs_bot:
                return "Хозяин я победил! хехе (¬_¬) один раз >w<"
            return f"🔵 <a href='tg://user?id={game.player2_id}'>игрок 2</a> победил! хехе~ >:3"
        return "ничья... вы оба молодцы :3"
    p_mark = "🔴" if game.current == P1 else "🔵"
    if game.vs_bot and game.current == P2:
        return f"хозяин я думаю... {p_mark} :3"
    pid = game.current_human_id()
    return f"ход {p_mark} — <a href='tg://user?id={pid}'>хозяин</a>~"


@router.message(Command("checkers"))
async def cmd_checkers(message: Message) -> None:
    chat_id = message.chat.id
    caller_id = message.from_user.id
    challenged_user = None
    for ent in (message.entities or []):
        if ent.type == "text_mention" and ent.user and ent.user.id != caller_id:
            challenged_user = ent.user
            break
    if challenged_user:
        _pending[chat_id] = (caller_id, challenged_user.id)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ принять вызов~ 💖",
                callback_data=f"chk_accept:{challenged_user.id}",
            )
        ]])
        await message.reply(
            f"<a href='tg://user?id={caller_id}'>хозяин</a> вызывает "
            f"<a href='tg://user?id={challenged_user.id}'>{challenged_user.first_name}</a> "
            f"на шашки! 🔴🔵 прими вызов если не страшно :3",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return
    game = CheckersGame(chat_id=chat_id, player1_id=caller_id, player2_id=None)
    _games[chat_id] = game
    await message.reply(
        "🔴🔵 шашки!\n"
        "хозяин ты за 🔴 (ходишь вверх), я за 🔵\n"
        "нажми на свою шашку, затем на зёленую точку — ход~ :3",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("chk_accept:"))
async def cb_chk_accept(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    expected_id = int(call.data.split(":")[1])
    if call.from_user.id != expected_id:
        await call.answer("этот вызов не для тебя~ :3", show_alert=True)
        return
    if chat_id not in _pending:
        await call.answer("вызов уже устарел... :3", show_alert=True)
        return
    challenger_id, challenged_id = _pending.pop(chat_id)
    game = CheckersGame(chat_id=chat_id, player1_id=challenger_id, player2_id=challenged_id)
    _games[chat_id] = game
    await _safe_edit(
        call.message,
        f"🔴🔵 игра началась! хехе~\n"
        f"<a href='tg://user?id={challenger_id}'>🔴 хозяин 1</a> vs "
        f"<a href='tg://user?id={challenged_id}'>🔵 хозяин 2</a>\n"
        f"ход 🔴~",
        _build_keyboard(game),
    )
    await call.answer()


@router.callback_query(F.data.startswith("chk:sel:"))
async def cb_chk_select(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    game = _games.get(chat_id)
    if not game or game.over:
        await call.answer()
        return
    if game.current_human_id() != call.from_user.id:
        await call.answer("не твой ход хозяин~ :3", show_alert=True)
        return
    _, r_s, c_s = call.data.split(":")[1:]
    r, c = int(r_s), int(c_s)
    all_moves = _all_moves_for_player(game.board, game.current)
    piece_moves = [(tr, tc) for (fr, fc, tr, tc) in all_moves if fr == r and fc == c]
    if not piece_moves:
        await call.answer("у этой шашки нет ходов~ выбери другую :3", show_alert=True)
        return
    game.selected = (r, c)
    try:
        await call.message.edit_reply_markup(reply_markup=_build_keyboard(game))
    except (TelegramRetryAfter, TelegramBadRequest):
        pass
    await call.answer()


@router.callback_query(F.data.startswith("chk:move:"))
async def cb_chk_move(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    game = _games.get(chat_id)
    if not game or game.over or game.selected is None:
        await call.answer()
        return
    if game.current_human_id() != call.from_user.id:
        await call.answer("не твой ход хозяин~ :3", show_alert=True)
        return
    parts = call.data.split(":")
    tr, tc = int(parts[2]), int(parts[3])
    fr, fc = game.selected
    game.board = _apply_move(game.board, fr, fc, tr, tc)
    game.selected = None
    winner = _check_winner(game.board)
    if winner:
        game.over = True
        game.winner = winner
        _games.pop(chat_id, None)
        await _safe_edit(call.message, f"🔴🔵 шашки\n{_status(game)}", _build_keyboard(game))
        await call.answer()
        return
    chain_caps = _get_captures(game.board, tr, tc, game.current)
    if chain_caps and abs(tr - fr) == 2:
        game.selected = (tr, tc)
        await _safe_edit(
            call.message,
            f"🔴🔵 шашки\nхозяин, ещё можно бить! продолжай~ 🔴",
            _build_keyboard(game),
        )
        await call.answer()
        return
    game.current = P2 if game.current == P1 else P1
    if game.vs_bot and game.current == P2:
        await _safe_edit(call.message, f"🔴🔵 шашки\n{_status(game)}", _build_keyboard(game))
        await call.answer()
        await _do_bot_turn(call.message, game, chat_id)
        return
    await _safe_edit(call.message, f"🔴🔵 шашки\n{_status(game)}", _build_keyboard(game))
    await call.answer()


async def _do_bot_turn(msg: Message, game: CheckersGame, chat_id: int) -> None:
    """Execute bot's turn(s) with rate-limit-safe edit_text calls."""
    while True:
        move = _bot_move(game.board)
        if move is None:
            break
        fr, fc, tr, tc = move
        game.board = _apply_move(game.board, fr, fc, tr, tc)
        winner = _check_winner(game.board)
        if winner:
            game.over = True
            game.winner = winner
            _games.pop(chat_id, None)
            await asyncio.sleep(_EDIT_COOLDOWN)
            await _safe_edit(msg, f"🔴🔵 шашки\n{_status(game)}", _build_keyboard(game))
            return
        if abs(tr - fr) == 2 and _get_captures(game.board, tr, tc, P2):
            # chain capture — apply next capture without extra edit
            continue
        break
    game.current = P1
    await asyncio.sleep(_EDIT_COOLDOWN)
    await _safe_edit(msg, f"🔴🔵 шашки\n{_status(game)}", _build_keyboard(game))


@router.callback_query(F.data == "chk:noop")
async def cb_chk_noop(call: CallbackQuery) -> None:
    await call.answer()
