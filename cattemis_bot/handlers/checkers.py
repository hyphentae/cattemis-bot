"""Checkers (draughts) game handler for Cattemis Bot.

Usage:
    /checkers           — start a game vs bot
    /checkers @user     — challenge another user (text_mention)

Rules (Russian draughts simplified):
- 8×8 board, pieces start on dark squares in rows 1-3 / 6-8.
- Regular pieces move diagonally forward only; kings move any diagonal.
- Captures are mandatory (greedy: must take if possible).
- A piece reaching the last rank is promoted to king (👑).
- Win: opponent has no pieces or no legal moves.

Rendering:
- Board rendered as 8×8 InlineKeyboard.
- Selected piece is highlighted with a border emoji.
- Valid destinations shown with 🔵.
"""

from __future__ import annotations

import random
from copy import deepcopy
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
# Constants
# ---------------------------------------------------------------------------

EMPTY   = "⬜"  # white square (visually empty on dark board)
DARK    = "⬛"  # dark square (unplayable)
W_MAN   = "🔴"  # white / player1 man
W_KING  = "👑"  # white / player1 king
B_MAN   = "🔵"  # black / player2 man  (also used as "dot" for hints — overridden)
B_KING  = "🐞"  # black / player2 king
DOT     = "🟢"  # valid move target
SEL     = "🟡"  # selected piece

P1 = "W"  # human (always)
P2 = "B"  # bot or second player


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

def _is_dark(r: int, c: int) -> bool:
    """Only dark squares (r+c odd) are playable."""
    return (r + c) % 2 == 1


def _initial_board() -> List[List[str]]:
    board = [[""] * 8 for _ in range(8)]
    for r in range(8):
        for c in range(8):
            if not _is_dark(r, c):
                board[r][c] = DARK
            elif r < 3:
                board[r][c] = B_MAN   # P2 starts at top
            elif r > 4:
                board[r][c] = W_MAN   # P1 starts at bottom
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
    if _is_p1(cell):
        return P1
    if _is_p2(cell):
        return P2
    return None


# ---------------------------------------------------------------------------
# Move generation
# ---------------------------------------------------------------------------

def _forward_dirs(piece: str) -> List[Tuple[int, int]]:
    """Diagonal directions a piece can move (not capture) towards."""
    if _is_king(piece):
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    if _is_p1(piece):   # P1 moves up (decreasing row)
        return [(-1, -1), (-1, 1)]
    return [(1, -1), (1, 1)]   # P2 moves down


def _all_dirs() -> List[Tuple[int, int]]:
    return [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def _get_captures(
    board: List[List[str]],
    r: int, c: int,
    player: str,
) -> List[Tuple[int, int, int, int]]:
    """
    Returns list of (from_r, from_c, to_r, to_c) single-step captures
    available for piece at (r,c).
    """
    piece = board[r][c]
    enemy = P2 if player == P1 else P1
    results = []
    for dr, dc in _all_dirs():
        mr, mc = r + dr, c + dc      # middle (enemy)
        lr, lc = r + 2*dr, c + 2*dc  # landing
        if not (0 <= mr < 8 and 0 <= lc < 8 and 0 <= lr < 8 and 0 <= mc < 8):
            continue
        if _owner(board[mr][mc]) == enemy and board[lr][lc] == EMPTY:
            results.append((r, c, lr, lc))
    return results


def _get_moves(
    board: List[List[str]],
    r: int, c: int,
    player: str,
) -> List[Tuple[int, int, int, int]]:
    """Non-capture moves for piece at (r,c)."""
    piece = board[r][c]
    results = []
    for dr, dc in _forward_dirs(piece):
        nr, nc = r + dr, c + dc
        if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == EMPTY:
            results.append((r, c, nr, nc))
    return results


def _all_captures_for_player(
    board: List[List[str]], player: str
) -> List[Tuple[int, int, int, int]]:
    caps = []
    for r in range(8):
        for c in range(8):
            if _owner(board[r][c]) == player:
                caps.extend(_get_captures(board, r, c, player))
    return caps


def _all_moves_for_player(
    board: List[List[str]], player: str
) -> List[Tuple[int, int, int, int]]:
    """All legal moves (captures mandatory)."""
    caps = _all_captures_for_player(board, player)
    if caps:
        return caps
    moves = []
    for r in range(8):
        for c in range(8):
            if _owner(board[r][c]) == player:
                moves.extend(_get_moves(board, r, c, player))
    return moves


# ---------------------------------------------------------------------------
# Apply move
# ---------------------------------------------------------------------------

def _apply_move(
    board: List[List[str]],
    fr: int, fc: int,
    tr: int, tc: int,
) -> List[List[str]]:
    """Return new board after moving (fr,fc)->(tr,tc). Handles capture & promotion."""
    b = deepcopy(board)
    piece = b[fr][fc]
    b[tr][tc] = piece
    b[fr][fc] = EMPTY

    # Capture: remove jumped piece
    if abs(tr - fr) == 2:
        mr, mc = (fr + tr) // 2, (fc + tc) // 2
        b[mr][mc] = EMPTY

    # Promotion
    if piece == W_MAN and tr == 0:
        b[tr][tc] = W_KING
    elif piece == B_MAN and tr == 7:
        b[tr][tc] = B_KING

    return b


# ---------------------------------------------------------------------------
# Bot AI (simple greedy + random)
# ---------------------------------------------------------------------------

def _bot_move(
    board: List[List[str]],
) -> Optional[Tuple[int, int, int, int]]:
    moves = _all_moves_for_player(board, P2)
    if not moves:
        return None
    # Prefer captures; among those prefer multi-captures (greedy)
    caps = _all_captures_for_player(board, P2)
    if caps:
        # Pick capture that results in the board with fewest P1 pieces
        best = min(
            caps,
            key=lambda m: sum(
                1 for r in range(8) for c in range(8)
                if _is_p1(_apply_move(board, *m)[r][c])
            ),
        )
        return best
    return random.choice(moves)


# ---------------------------------------------------------------------------
# Win check
# ---------------------------------------------------------------------------

def _check_winner(board: List[List[str]]) -> Optional[str]:
    has_p1 = any(_is_p1(board[r][c]) for r in range(8) for c in range(8))
    has_p2 = any(_is_p2(board[r][c]) for r in range(8) for c in range(8))
    if not has_p1:
        return P2
    if not has_p2:
        return P1
    if not _all_moves_for_player(board, P1):
        return P2
    if not _all_moves_for_player(board, P2):
        return P1
    return None


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class CheckersGame:
    def __init__(self, chat_id: int, player1_id: int, player2_id: Optional[int]):
        self.chat_id = chat_id
        self.player1_id = player1_id   # P1 = W, moves first
        self.player2_id = player2_id   # None → bot
        self.board = _initial_board()
        self.current = P1
        self.selected: Optional[Tuple[int, int]] = None
        self.over = False
        self.winner: Optional[str] = None

    @property
    def vs_bot(self) -> bool:
        return self.player2_id is None

    def current_human_id(self) -> Optional[int]:
        if self.current == P1:
            return self.player1_id
        return self.player2_id

    def valid_targets(self) -> List[Tuple[int, int]]:
        """Destination squares for currently selected piece."""
        if self.selected is None:
            return []
        fr, fc = self.selected
        all_moves = _all_moves_for_player(self.board, self.current)
        return [(tr, tc) for (r, c, tr, tc) in all_moves if r == fr and c == fc]


# chat_id → game
_games: Dict[int, CheckersGame] = {}
# chat_id → (challenger_id, challenged_id)
_pending: Dict[int, Tuple[int, int]] = {}


# ---------------------------------------------------------------------------
# Keyboard renderer
# ---------------------------------------------------------------------------

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
                return "🔴 Ты победил! ✨"
            return f"🔴 <a href='tg://user?id={game.player1_id}'>Игрок 1</a> победил! ✨"
        if game.winner == P2:
            if game.vs_bot:
                return "🔵 Бот победил... попробуй ещё! :3"
            return f"🔵 <a href='tg://user?id={game.player2_id}'>Игрок 2</a> победил! ✨"
        return "🤝 Ничья!"

    p_mark = "🔴" if game.current == P1 else "🔵"
    if game.vs_bot and game.current == P2:
        return f"Ход бота {p_mark}..."
    pid = game.current_human_id()
    return f"Ход {p_mark} — <a href='tg://user?id={pid}'>игрок</a>"


# ---------------------------------------------------------------------------
# /checkers command
# ---------------------------------------------------------------------------

@router.message(Command("checkers"))
async def cmd_checkers(message: Message) -> None:
    chat_id = message.chat.id
    caller_id = message.from_user.id

    # Challenge via text_mention
    challenged_user = None
    for ent in (message.entities or []):
        if ent.type == "text_mention" and ent.user and ent.user.id != caller_id:
            challenged_user = ent.user
            break

    if challenged_user:
        _pending[chat_id] = (caller_id, challenged_user.id)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Принять вызов!",
                callback_data=f"chk_accept:{challenged_user.id}",
            )
        ]])
        await message.reply(
            f"<a href='tg://user?id={caller_id}'>Игрок</a> вызывает "
            f"<a href='tg://user?id={challenged_user.id}'>{challenged_user.first_name}</a> "
            f"на шашки! 🔴🔵\nНажми кнопку чтобы принять :3",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return

    # Solo vs bot
    game = CheckersGame(chat_id=chat_id, player1_id=caller_id, player2_id=None)
    _games[chat_id] = game
    await message.reply(
        "🔴🔵 Шашки!\n"
        "Ты играешь за 🔴 (ходишь вверх), бот за 🔵\n"
        "Нажми на свою шашку, затем на зелёную точку — ход :3",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Accept challenge
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("chk_accept:"))
async def cb_chk_accept(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    expected_id = int(call.data.split(":")[1])

    if call.from_user.id != expected_id:
        await call.answer("Этот вызов не для тебя! :3", show_alert=True)
        return
    if chat_id not in _pending:
        await call.answer("Вызов устарел.", show_alert=True)
        return

    challenger_id, challenged_id = _pending.pop(chat_id)
    game = CheckersGame(chat_id=chat_id, player1_id=challenger_id, player2_id=challenged_id)
    _games[chat_id] = game
    await call.message.edit_text(
        f"🔴🔵 Игра началась!\n"
        f"<a href='tg://user?id={challenger_id}'>🔴 Игрок 1</a> vs "
        f"<a href='tg://user?id={challenged_id}'>🔵 Игрок 2</a>\n"
        f"Ход 🔴",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )
    await call.answer()


# ---------------------------------------------------------------------------
# Select piece
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("chk:sel:"))
async def cb_chk_select(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    game = _games.get(chat_id)
    if not game or game.over:
        await call.answer()
        return

    # Only the current human player can select
    if game.current_human_id() != call.from_user.id:
        await call.answer("Не твой ход! :3", show_alert=True)
        return

    _, r_s, c_s = call.data.split(":")[1:]
    r, c = int(r_s), int(c_s)

    # Check piece has valid moves
    all_moves = _all_moves_for_player(game.board, game.current)
    piece_moves = [(tr, tc) for (fr, fc, tr, tc) in all_moves if fr == r and fc == c]
    if not piece_moves:
        await call.answer("У этой шашки нет ходов!", show_alert=True)
        return

    game.selected = (r, c)
    await call.message.edit_reply_markup(reply_markup=_build_keyboard(game))
    await call.answer()


# ---------------------------------------------------------------------------
# Make move
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("chk:move:"))
async def cb_chk_move(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    game = _games.get(chat_id)
    if not game or game.over or game.selected is None:
        await call.answer()
        return

    if game.current_human_id() != call.from_user.id:
        await call.answer("Не твой ход! :3", show_alert=True)
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
        await call.message.edit_text(
            f"🔴🔵 Шашки\n{_status(game)}",
            reply_markup=_build_keyboard(game),
            parse_mode="HTML",
        )
        await call.answer()
        return

    # Check for mandatory chain capture
    chain_caps = _get_captures(game.board, tr, tc, game.current)
    all_caps = _all_captures_for_player(game.board, game.current)
    if chain_caps and abs(tr - fr) == 2:  # was a capture, chain possible
        game.selected = (tr, tc)
        await call.message.edit_text(
            f"🔴🔵 Шашки\nПродолжай бить! 🔴" if game.current == P1 else
            f"🔴🔵 Шашки\nПродолжай бить! 🔵",
            reply_markup=_build_keyboard(game),
            parse_mode="HTML",
        )
        await call.answer()
        return

    # Switch turn
    game.current = P2 if game.current == P1 else P1

    # Bot turn
    if game.vs_bot and game.current == P2:
        await call.message.edit_text(
            f"🔴🔵 Шашки\n{_status(game)}",
            reply_markup=_build_keyboard(game),
            parse_mode="HTML",
        )
        await call.answer()
        await _do_bot_turn(call.message, game, chat_id)
        return

    await call.message.edit_text(
        f"🔴🔵 Шашки\n{_status(game)}",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )
    await call.answer()


async def _do_bot_turn(msg, game: CheckersGame, chat_id: int) -> None:
    """Execute bot move(s), including chain captures."""
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
            await msg.edit_text(
                f"🔴🔵 Шашки\n{_status(game)}",
                reply_markup=_build_keyboard(game),
                parse_mode="HTML",
            )
            return

        # Chain capture?
        if abs(tr - fr) == 2 and _get_captures(game.board, tr, tc, P2):
            continue
        break

    game.current = P1
    await msg.edit_text(
        f"🔴🔵 Шашки\n{_status(game)}",
        reply_markup=_build_keyboard(game),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Noop
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "chk:noop")
async def cb_chk_noop(call: CallbackQuery) -> None:
    await call.answer()
