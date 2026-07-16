import { hasTelegramAuth, telegramAuthHeaders } from './telegram-auth.js?v=20260716-code-only';

const PIECES = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
};

const PIECE_IMAGES = {
  K: '/parabolic/pieces/wk.svg', Q: '/parabolic/pieces/wq.svg', R: '/parabolic/pieces/wr.svg',
  B: '/parabolic/pieces/wb.svg', N: '/parabolic/pieces/wn.svg', P: '/parabolic/pieces/wp.svg',
  k: '/parabolic/pieces/bk.svg', q: '/parabolic/pieces/bq.svg', r: '/parabolic/pieces/br.svg',
  b: '/parabolic/pieces/bb.svg', n: '/parabolic/pieces/bn.svg', p: '/parabolic/pieces/bp.svg',
};

const VALUES = { p: 100, n: 320, b: 335, r: 500, q: 900, k: 20_000 };
const KNIGHT_STEPS = [[-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1]];
const KING_STEPS = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]];
const BISHOP_STEPS = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
const ROOK_STEPS = [[-1, 0], [1, 0], [0, -1], [0, 1]];

function colorOf(piece) {
  if (!piece) return null;
  return piece === piece.toUpperCase() ? 'w' : 'b';
}

function opposite(color) { return color === 'w' ? 'b' : 'w'; }
function inside(row, col) { return row >= 0 && row < 8 && col >= 0 && col < 8; }
function indexOf(row, col) { return row * 8 + col; }

export function createChessState() {
  return {
    board: [
      ...'rnbqkbnr', ...'pppppppp',
      ...Array(32).fill(''),
      ...'PPPPPPPP', ...'RNBQKBNR',
    ],
    turn: 'w',
    castling: { K: true, Q: true, k: true, q: true },
    enPassant: null,
    halfmove: 0,
    fullmove: 1,
  };
}

function slidingMoves(state, from, color, directions, moves) {
  const row = Math.floor(from / 8);
  const col = from % 8;
  for (const [rowStep, colStep] of directions) {
    for (let distance = 1; distance < 8; distance += 1) {
      const nextRow = row + rowStep * distance;
      const nextCol = col + colStep * distance;
      if (!inside(nextRow, nextCol)) break;
      const to = indexOf(nextRow, nextCol);
      const target = state.board[to];
      if (!target) {
        moves.push({ from, to });
        continue;
      }
      if (colorOf(target) !== color) moves.push({ from, to, capture: target });
      break;
    }
  }
}

function pseudoMoves(state, color) {
  const moves = [];
  state.board.forEach((piece, from) => {
    if (colorOf(piece) !== color) return;
    const type = piece.toLowerCase();
    const row = Math.floor(from / 8);
    const col = from % 8;

    if (type === 'p') {
      const direction = color === 'w' ? -1 : 1;
      const startRow = color === 'w' ? 6 : 1;
      const promotionRow = color === 'w' ? 0 : 7;
      const nextRow = row + direction;
      if (inside(nextRow, col) && !state.board[indexOf(nextRow, col)]) {
        const to = indexOf(nextRow, col);
        moves.push({ from, to, promotion: nextRow === promotionRow ? 'q' : null });
        const doubleRow = row + direction * 2;
        if (row === startRow && !state.board[indexOf(doubleRow, col)]) {
          moves.push({ from, to: indexOf(doubleRow, col), doublePawn: true });
        }
      }
      for (const colStep of [-1, 1]) {
        const nextCol = col + colStep;
        if (!inside(nextRow, nextCol)) continue;
        const to = indexOf(nextRow, nextCol);
        const target = state.board[to];
        if (target && colorOf(target) !== color) {
          moves.push({ from, to, capture: target, promotion: nextRow === promotionRow ? 'q' : null });
        } else if (to === state.enPassant) {
          moves.push({ from, to, capture: color === 'w' ? 'p' : 'P', enPassant: true });
        }
      }
      return;
    }

    if (type === 'n' || type === 'k') {
      const steps = type === 'n' ? KNIGHT_STEPS : KING_STEPS;
      for (const [rowStep, colStep] of steps) {
        const nextRow = row + rowStep;
        const nextCol = col + colStep;
        if (!inside(nextRow, nextCol)) continue;
        const to = indexOf(nextRow, nextCol);
        const target = state.board[to];
        if (!target || colorOf(target) !== color) moves.push({ from, to, capture: target || null });
      }
      if (type === 'k') addCastlingMoves(state, color, moves);
      return;
    }

    if (type === 'b') slidingMoves(state, from, color, BISHOP_STEPS, moves);
    if (type === 'r') slidingMoves(state, from, color, ROOK_STEPS, moves);
    if (type === 'q') slidingMoves(state, from, color, [...BISHOP_STEPS, ...ROOK_STEPS], moves);
  });
  return moves;
}

function addCastlingMoves(state, color, moves) {
  const row = color === 'w' ? 7 : 0;
  const kingFrom = indexOf(row, 4);
  const enemy = opposite(color);
  if (isSquareAttacked(state.board, kingFrom, enemy)) return;

  const kingSide = color === 'w' ? 'K' : 'k';
  if (state.castling[kingSide]
    && state.board[indexOf(row, 7)].toLowerCase() === 'r'
    && colorOf(state.board[indexOf(row, 7)]) === color
    && !state.board[indexOf(row, 5)]
    && !state.board[indexOf(row, 6)]
    && !isSquareAttacked(state.board, indexOf(row, 5), enemy)
    && !isSquareAttacked(state.board, indexOf(row, 6), enemy)) {
    moves.push({ from: kingFrom, to: indexOf(row, 6), castle: 'king' });
  }

  const queenSide = color === 'w' ? 'Q' : 'q';
  if (state.castling[queenSide]
    && state.board[indexOf(row, 0)].toLowerCase() === 'r'
    && colorOf(state.board[indexOf(row, 0)]) === color
    && !state.board[indexOf(row, 1)]
    && !state.board[indexOf(row, 2)]
    && !state.board[indexOf(row, 3)]
    && !isSquareAttacked(state.board, indexOf(row, 3), enemy)
    && !isSquareAttacked(state.board, indexOf(row, 2), enemy)) {
    moves.push({ from: kingFrom, to: indexOf(row, 2), castle: 'queen' });
  }
}

function isSquareAttacked(board, target, byColor) {
  const row = Math.floor(target / 8);
  const col = target % 8;
  const pawnSourceRow = row + (byColor === 'w' ? 1 : -1);
  for (const colStep of [-1, 1]) {
    const sourceCol = col + colStep;
    if (inside(pawnSourceRow, sourceCol)) {
      const piece = board[indexOf(pawnSourceRow, sourceCol)];
      if (piece && colorOf(piece) === byColor && piece.toLowerCase() === 'p') return true;
    }
  }

  for (const [rowStep, colStep] of KNIGHT_STEPS) {
    const sourceRow = row + rowStep;
    const sourceCol = col + colStep;
    if (inside(sourceRow, sourceCol)) {
      const piece = board[indexOf(sourceRow, sourceCol)];
      if (piece && colorOf(piece) === byColor && piece.toLowerCase() === 'n') return true;
    }
  }

  for (const [rowStep, colStep] of KING_STEPS) {
    const sourceRow = row + rowStep;
    const sourceCol = col + colStep;
    if (inside(sourceRow, sourceCol)) {
      const piece = board[indexOf(sourceRow, sourceCol)];
      if (piece && colorOf(piece) === byColor && piece.toLowerCase() === 'k') return true;
    }
  }

  const rayAttacked = (directions, types) => directions.some(([rowStep, colStep]) => {
    for (let distance = 1; distance < 8; distance += 1) {
      const sourceRow = row + rowStep * distance;
      const sourceCol = col + colStep * distance;
      if (!inside(sourceRow, sourceCol)) return false;
      const piece = board[indexOf(sourceRow, sourceCol)];
      if (!piece) continue;
      return colorOf(piece) === byColor && types.includes(piece.toLowerCase());
    }
    return false;
  });

  return rayAttacked(BISHOP_STEPS, ['b', 'q']) || rayAttacked(ROOK_STEPS, ['r', 'q']);
}

function kingInCheck(state, color) {
  const king = color === 'w' ? 'K' : 'k';
  const square = state.board.indexOf(king);
  return square === -1 || isSquareAttacked(state.board, square, opposite(color));
}

export function applyChessMove(state, move) {
  const board = [...state.board];
  const castling = { ...state.castling };
  const piece = board[move.from];
  const color = colorOf(piece);
  const type = piece.toLowerCase();
  const captured = board[move.to];
  board[move.from] = '';
  board[move.to] = move.promotion ? (color === 'w' ? 'Q' : 'q') : piece;

  if (move.enPassant) {
    const direction = color === 'w' ? -1 : 1;
    board[move.to - direction * 8] = '';
  }
  if (move.castle === 'king') {
    const row = color === 'w' ? 7 : 0;
    board[indexOf(row, 5)] = board[indexOf(row, 7)];
    board[indexOf(row, 7)] = '';
  } else if (move.castle === 'queen') {
    const row = color === 'w' ? 7 : 0;
    board[indexOf(row, 3)] = board[indexOf(row, 0)];
    board[indexOf(row, 0)] = '';
  }

  if (type === 'k') {
    castling[color === 'w' ? 'K' : 'k'] = false;
    castling[color === 'w' ? 'Q' : 'q'] = false;
  }
  if (move.from === 63 || move.to === 63) castling.K = false;
  if (move.from === 56 || move.to === 56) castling.Q = false;
  if (move.from === 7 || move.to === 7) castling.k = false;
  if (move.from === 0 || move.to === 0) castling.q = false;

  const next = {
    board,
    turn: opposite(color),
    castling,
    enPassant: move.doublePawn ? (move.from + move.to) / 2 : null,
    halfmove: type === 'p' || captured || move.enPassant ? 0 : state.halfmove + 1,
    fullmove: state.fullmove + (color === 'b' ? 1 : 0),
  };
  return next;
}

export function legalChessMoves(state) {
  const color = state.turn;
  return pseudoMoves(state, color).filter((move) => !kingInCheck(applyChessMove(state, move), color));
}

function gameResult(state, moves = legalChessMoves(state)) {
  if (moves.length === 0) {
    return kingInCheck(state, state.turn)
      ? { type: 'checkmate', winner: opposite(state.turn) }
      : { type: 'draw' };
  }
  const material = state.board.filter((piece) => piece && piece.toLowerCase() !== 'k');
  if (material.length === 0 || (material.length === 1 && ['b', 'n'].includes(material[0].toLowerCase()))) {
    return { type: 'draw' };
  }
  if (state.halfmove >= 100) return { type: 'draw' };
  return null;
}

function evaluate(state) {
  let score = 0;
  state.board.forEach((piece, square) => {
    if (!piece) return;
    const row = Math.floor(square / 8);
    const col = square % 8;
    const centre = 7 - Math.abs(3.5 - row) - Math.abs(3.5 - col);
    const value = VALUES[piece.toLowerCase()] + centre * (piece.toLowerCase() === 'p' ? 3 : 5);
    score += colorOf(piece) === 'b' ? value : -value;
  });
  return score;
}

function orderedMoves(moves) {
  return [...moves].sort((left, right) => {
    const score = (move) => (move.capture ? VALUES[move.capture.toLowerCase()] : 0) + (move.promotion ? 800 : 0);
    return score(right) - score(left);
  });
}

function alphaBeta(state, depth, alpha, beta) {
  const moves = legalChessMoves(state);
  const result = gameResult(state, moves);
  if (result?.type === 'checkmate') return result.winner === 'b' ? 100_000 + depth : -100_000 - depth;
  if (result || depth === 0) return result ? 0 : evaluate(state);

  if (state.turn === 'b') {
    let best = -Infinity;
    for (const move of orderedMoves(moves)) {
      best = Math.max(best, alphaBeta(applyChessMove(state, move), depth - 1, alpha, beta));
      alpha = Math.max(alpha, best);
      if (beta <= alpha) break;
    }
    return best;
  }

  let best = Infinity;
  for (const move of orderedMoves(moves)) {
    best = Math.min(best, alphaBeta(applyChessMove(state, move), depth - 1, alpha, beta));
    beta = Math.min(beta, best);
    if (beta <= alpha) break;
  }
  return best;
}

export function chooseChessMove(state, depth = 3) {
  const moves = orderedMoves(legalChessMoves(state));
  if (!moves.length) return null;
  let bestMove = moves[0];
  let bestScore = -Infinity;
  for (const move of moves) {
    const score = alphaBeta(applyChessMove(state, move), depth - 1, -Infinity, Infinity);
    if (score > bestScore) {
      bestScore = score;
      bestMove = move;
    }
  }
  return bestMove;
}

function squareName(square) {
  return `${'abcdefgh'[square % 8]}${8 - Math.floor(square / 8)}`;
}

export function initChess({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-chess'),
    lobbyBack: document.getElementById('chess-lobby-back'),
    playBot: document.getElementById('play-chess-bot'),
    create: document.getElementById('create-chess-room'),
    findPublic: document.getElementById('find-chess-public'),
    joinForm: document.getElementById('join-chess-form'),
    codeInput: document.getElementById('chess-room-code'),
    lobbyMessage: document.getElementById('chess-lobby-message'),
    leave: document.getElementById('leave-chess'),
    fresh: document.getElementById('new-chess'),
    copyCode: document.getElementById('copy-chess-room-code'),
    activeCode: document.getElementById('active-chess-room-code'),
    matchTitle: document.getElementById('chess-match-title'),
    board: document.getElementById('chess-board'),
    status: document.getElementById('chess-status'),
  };
  let mode = 'bot';
  let state = createChessState();
  let room = null;
  let selected = null;
  let legal = [];
  let thinking = false;
  let finished = false;
  let pending = false;
  let animating = false;
  let lastMove = null;
  let botTimer = null;
  let pollTimer = null;

  elements.open.addEventListener('click', openLobby);
  elements.lobbyBack.addEventListener('click', () => showScreen('menu'));
  elements.playBot.addEventListener('click', startBotGame);
  elements.create.addEventListener('click', createRoom);
  elements.findPublic.addEventListener('click', findPublicGame);
  elements.joinForm.addEventListener('submit', joinRoom);
  elements.leave.addEventListener('click', leaveGame);
  elements.fresh.addEventListener('click', newBotGame);
  elements.copyCode.addEventListener('click', copyRoomCode);
  elements.codeInput.addEventListener('input', () => {
    elements.codeInput.value = elements.codeInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  });

  function openLobby() {
    clearMessage();
    if (!hasTelegramAuth(telegram)) showMessage('онлайн-комнаты работают только внутри Telegram :3');
    showScreen('chess-lobby');
  }

  function startBotGame() {
    mode = 'bot';
    room = null;
    elements.copyCode.hidden = true;
    elements.matchTitle.hidden = false;
    elements.matchTitle.textContent = 'партия с катемисом';
    elements.fresh.hidden = false;
    newBotGame();
    showScreen('chess');
  }

  function newBotGame() {
    if (mode !== 'bot') return;
    cancelBot();
    state = createChessState();
    selected = null;
    legal = legalChessMoves(state);
    thinking = false;
    finished = false;
    lastMove = null;
    setStatus('твой ход, хозяин... белые начинают :3');
    render();
  }

  async function createRoom() {
    if (pending) return;
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/chess/create', { method: 'POST' });
      openOnlineGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function findPublicGame() {
    if (pending) return;
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/chess/public', { method: 'POST' });
      openOnlineGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function joinRoom(event) {
    event.preventDefault();
    if (pending) return;
    const code = elements.codeInput.value.trim().toUpperCase();
    if (code.length !== 6) {
      showMessage('нужен кодик из шести символов :3');
      return;
    }
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/chess/join', { method: 'POST', body: JSON.stringify({ code }) });
      openOnlineGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function joinByCode(code) {
    room = await api('/api/chess/join', { method: 'POST', body: JSON.stringify({ code }) });
    openOnlineGame();
  }

  function openOnlineGame() {
    mode = 'online';
    selected = null;
    thinking = false;
    finished = room.status === 'finished';
    lastMove = room.last_move ?? null;
    elements.copyCode.hidden = room.public;
    elements.matchTitle.hidden = !room.public;
    elements.matchTitle.textContent = 'публичная партия';
    elements.activeCode.textContent = room.code;
    elements.fresh.hidden = true;
    setPending(false);
    showScreen('chess');
    renderOnlineStatus();
    render();
    startPolling();
    telegram?.HapticFeedback?.notificationOccurred('success');
  }

  function leaveGame() {
    cancelBot();
    stopPolling();
    room = null;
    selected = null;
    showScreen('chess-lobby');
  }

  function cancelBot() {
    if (botTimer !== null) window.clearTimeout(botTimer);
    botTimer = null;
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(refreshRoom, 1000);
  }

  function stopPolling() {
    if (pollTimer !== null) window.clearInterval(pollTimer);
    pollTimer = null;
  }

  async function refreshRoom() {
    if (mode !== 'online' || !room || pending || animating || document.hidden) return;
    try {
      const next = await api(`/api/chess/state?code=${encodeURIComponent(room.code)}`);
      if (next.version !== room.version) {
        await animateChessMove(next.last_move, true);
        room = next;
        lastMove = next.last_move ?? null;
        selected = null;
        finished = room.status === 'finished';
        renderOnlineStatus();
        render();
        telegram?.HapticFeedback?.selectionChanged();
      }
      if (room.status === 'finished') stopPolling();
    } catch (error) {
      setStatus(`ой, хозяин... ${error.message}`, 'lose');
    }
  }

  function currentBoard() { return mode === 'online' ? room.board : state.board; }
  function currentMoves() { return mode === 'online' ? room.moves : legal; }
  function currentTurn() { return mode === 'online' ? room.turn : state.turn; }

  function render() {
    elements.board.replaceChildren();
    elements.board.classList.toggle('bot-thinking', thinking);
    elements.board.classList.toggle('game-finished', finished);
    elements.status.classList.toggle('thinking', thinking);
    const board = currentBoard();
    const moves = currentMoves();
    const targets = new Set(selected === null ? [] : moves.filter((move) => move.from === selected).map((move) => move.to));
    const reversed = mode === 'online' && room.you === 'b';
    const indexes = Array.from({ length: 8 }, (_, index) => reversed ? 7 - index : index);

    for (const row of indexes) {
      for (const col of indexes) {
        const square = row * 8 + col;
        const piece = board[square];
        const cell = document.createElement('button');
        cell.type = 'button';
        cell.className = `chess-square ${(row + col) % 2 ? 'dark' : 'light'}`;
        cell.setAttribute('role', 'gridcell');
        cell.setAttribute('aria-label', `${squareName(square)}${piece ? `: ${PIECES[piece]}` : ': пусто'}`);
        cell.dataset.square = String(square);
        if (lastMove?.from === square) cell.classList.add('last-from');
        if (lastMove?.to === square) cell.classList.add('last-to');
        if (square === selected) cell.classList.add('selected');
        if (targets.has(square)) cell.classList.add(board[square] ? 'capture' : 'target');
        if (piece) {
          const figure = document.createElement('img');
          figure.className = `chess-piece ${colorOf(piece) === 'w' ? 'white' : 'black'}`;
          figure.src = PIECE_IMAGES[piece];
          figure.alt = '';
          figure.draggable = false;
          cell.appendChild(figure);
        }
        const playerColor = mode === 'online' ? room.you : 'w';
        const canPlay = !thinking && !finished && !pending && !animating && currentTurn() === playerColor;
        const canSelect = canPlay && colorOf(piece) === playerColor && moves.some((move) => move.from === square);
        const canMove = canPlay && targets.has(square);
        cell.disabled = !(canSelect || canMove);
        cell.setAttribute('aria-disabled', String(cell.disabled));
        cell.addEventListener('click', () => handleSquare(square, canSelect, canMove));
        elements.board.appendChild(cell);
      }
    }
  }

  async function handleSquare(square, canSelect, canMove) {
    if (animating) return;
    if (canSelect) {
      selected = square;
      telegram?.HapticFeedback?.selectionChanged();
      render();
      return;
    }
    if (!canMove || selected === null) return;
    if (mode === 'online') {
      makeOnlineMove(selected, square);
      return;
    }
    const move = legal.find((candidate) => candidate.from === selected && candidate.to === square);
    selected = null;
    await animateChessMove(move);
    state = applyChessMove(state, move);
    lastMove = move;
    legal = legalChessMoves(state);
    telegram?.HapticFeedback?.impactOccurred('medium');
    if (finishBotGame()) return;
    thinking = true;
    setStatus(kingInCheck(state, 'b') ? 'шах катемису... хозяин, ну ты даёшь owo' : 'катемис думает... двигаю ушками :3');
    render();
    botTimer = window.setTimeout(botMove, 320);
  }

  async function makeOnlineMove(from, to) {
    pending = true;
    selected = null;
    setStatus('отправляю ход лапкой...');
    render();
    try {
      const next = await api('/api/chess/move', { method: 'POST', body: JSON.stringify({ code: room.code, from, to }) });
      await animateChessMove(next.last_move);
      room = next;
      lastMove = next.last_move ?? { from, to };
      finished = room.status === 'finished';
      renderOnlineStatus();
      telegram?.HapticFeedback?.impactOccurred('medium');
    } catch (error) {
      setStatus(`ой, хозяин... ${error.message}`, 'lose');
    } finally {
      pending = false;
      render();
    }
  }

  async function botMove() {
    botTimer = null;
    const move = chooseChessMove(state);
    if (move) {
      await animateChessMove(move, true);
      state = applyChessMove(state, move);
      lastMove = move;
    }
    thinking = false;
    legal = legalChessMoves(state);
    if (finishBotGame()) return;
    setStatus(kingInCheck(state, 'w') ? 'шах, хозяин... осторожнее с королём :3' : 'твой ход, хозяин');
    render();
  }

  async function animateChessMove(move, accented = false) {
    if (!move || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const board = currentBoard();
    const piece = board[move.from];
    if (!piece) return;

    animating = true;
    elements.board.setAttribute('aria-busy', 'true');
    elements.board.querySelectorAll('.chess-square').forEach((cell) => {
      cell.disabled = true;
      cell.setAttribute('aria-disabled', 'true');
    });
    try {
      const animations = [animateChessPiece(move.from, move.to, accented)];
      const captureSquare = (move.enPassant || move.en_passant)
        ? move.to + (colorOf(piece) === 'w' ? 8 : -8)
        : move.to;
      const captured = findChessSquare(captureSquare)?.querySelector('.chess-piece');
      if (captured) {
        animations.push(captured.animate([
          { opacity: 1, transform: 'scale(1) rotate(0)' },
          { opacity: 0, transform: 'scale(.35) rotate(10deg)' },
        ], { duration: 280, easing: 'ease-in', fill: 'forwards' }).finished.catch(() => {}));
      }
      if (move.castle) {
        const row = Math.floor(move.from / 8);
        const rookFrom = row * 8 + (move.castle === 'king' ? 7 : 0);
        const rookTo = row * 8 + (move.castle === 'king' ? 5 : 3);
        animations.push(animateChessPiece(rookFrom, rookTo, accented));
      }
      await Promise.all(animations);
    } finally {
      animating = false;
      elements.board.removeAttribute('aria-busy');
    }
  }

  async function animateChessPiece(from, to, accented) {
    const fromSquare = findChessSquare(from);
    const toSquare = findChessSquare(to);
    const figure = fromSquare?.querySelector('.chess-piece');
    if (!fromSquare || !toSquare || !figure) return;

    const boardRect = elements.board.getBoundingClientRect();
    const figureRect = figure.getBoundingClientRect();
    const targetRect = toSquare.getBoundingClientRect();
    const moving = figure.cloneNode(true);
    moving.classList.add('chess-piece-moving');
    if (accented) moving.classList.add('accented');
    Object.assign(moving.style, {
      left: `${figureRect.left - boardRect.left - elements.board.clientLeft}px`,
      top: `${figureRect.top - boardRect.top - elements.board.clientTop}px`,
      width: `${figureRect.width}px`,
      height: `${figureRect.height}px`,
    });
    elements.board.appendChild(moving);
    figure.style.opacity = '0';
    const targetX = targetRect.left + (targetRect.width - figureRect.width) / 2 - figureRect.left;
    const targetY = targetRect.top + (targetRect.height - figureRect.height) / 2 - figureRect.top;
    const animation = moving.animate([
      { transform: 'translate3d(0, 0, 0)' },
      { transform: `translate3d(${targetX}px, ${targetY}px, 0)` },
    ], {
      duration: accented ? 390 : 310,
      easing: 'cubic-bezier(.4, 0, .2, 1)',
      fill: 'forwards',
    });
    await animation.finished.catch(() => {});
    moving.remove();
  }

  function findChessSquare(square) {
    return elements.board.querySelector(`[data-square="${square}"]`);
  }

  function finishBotGame() {
    const result = gameResult(state, legal);
    if (!result) return false;
    finished = true;
    thinking = false;
    if (result.type === 'draw') {
      setStatus('ничья, хозяин... наши короли устали owo', 'draw');
      telegram?.HapticFeedback?.notificationOccurred('warning');
    } else if (result.winner === 'w') {
      setStatus('мат! хозяин победил... я впечатлён :3', 'win');
      telegram?.HapticFeedback?.notificationOccurred('success');
    } else {
      setStatus('мат, хозяин... кошкомальчик победил >:3', 'lose');
      telegram?.HapticFeedback?.notificationOccurred('error');
    }
    render();
    return true;
  }

  function renderOnlineStatus() {
    if (room.status === 'waiting') {
      setStatus(room.public
        ? 'ищу соперника в публичном лобби, хозяин... :3'
        : 'хозяин, отправь кодик другу — белые уже готовы :3');
    } else if (room.status === 'finished') {
      if (room.winner === 'draw') setStatus('ничья... короли договорились, хозяин owo', 'draw');
      else if (room.winner === room.you) setStatus('мат! хозяин победил :3', 'win');
      else setStatus('мат... друг оказался хитрее T_T', 'lose');
      stopPolling();
    } else if (room.turn === room.you) {
      setStatus('твой ход, хозяин :3');
    } else {
      setStatus('ждём ход друга, хозяин...');
    }
  }

  async function copyRoomCode() {
    if (!room?.code) return;
    try {
      await navigator.clipboard.writeText(room.code);
      setStatus('кодик скопирован, хозяин :3');
    } catch {
      setStatus(`кодик комнаты: ${room.code}`);
    }
  }

  async function api(path, options = {}) {
    if (!hasTelegramAuth(telegram)) throw new Error('открой игру внутри Telegram, хозяин :3');
    const response = await fetch(path, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...telegramAuthHeaders(telegram), ...options.headers },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'сервер молчит... попробуй ещё раз T_T');
    return payload;
  }

  function setPending(value) {
    pending = value;
    elements.create.disabled = value;
    elements.findPublic.disabled = value;
    elements.joinForm.querySelector('button').disabled = value;
  }
  function showMessage(message) { elements.lobbyMessage.textContent = `хозяин, ${message}`; }
  function clearMessage() { elements.lobbyMessage.textContent = ''; }
  function setStatus(text, style = '') {
    elements.status.textContent = text;
    elements.status.className = `status-bar${style ? ` ${style}` : ''}`;
  }
  return { joinByCode };
}
