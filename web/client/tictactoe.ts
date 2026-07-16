import { hasTelegramAuth, telegramAuthHeaders } from './telegram-auth.ts';

const WINNING_LINES = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8],
  [0, 3, 6], [1, 4, 7], [2, 5, 8],
  [0, 4, 8], [2, 4, 6],
];

const MARKS = {
  X: '<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-x"/></svg>',
  O: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="7.75"/></svg>',
};

const PHRASES = {
  turn: [
    'твой ход, хозяин :3',
    'ходи, хозяин... я внимательно смотрю owo',
    'покажи свой лучший ход, хозяин :3',
  ],
  thinking: [
    'катемис думает... ушки дымятся owo',
    'секундочку, хозяин... считаю на лапках :3',
    'мой кошачий гений сейчас проснётся, мяу',
  ],
  playerWin: [
    'хозяин победил... я точно не поддавался >:3',
    'вау, хозяин... ты прижал мои ушки T_T',
  ],
  botWin: [
    'я победил, мяу :3',
    'хе-хе, я снова победил >:3',
    'не грусти, хозяин... можешь погладить победителя owo',
  ],
  draw: [
    'ничья, хозяин... ещё раз? owo',
    'мы слишком хорошо знаем друг друга, хозяин :3',
  ],
};

function phrase(group) {
  return group[Math.floor(Math.random() * group.length)];
}

function checkWinner(currentBoard) {
  for (const [a, b, c] of WINNING_LINES) {
    if (currentBoard[a] && currentBoard[a] === currentBoard[b] && currentBoard[a] === currentBoard[c]) {
      return { winner: currentBoard[a], line: [a, b, c] };
    }
  }
  return currentBoard.every(Boolean) ? { winner: 'draw' } : null;
}

function minimax(currentBoard, maximizing, depth, alpha, beta, cache) {
  const result = checkWinner(currentBoard);
  if (result?.winner === 'O') return 10 - depth;
  if (result?.winner === 'X') return depth - 10;
  if (result?.winner === 'draw') return 0;

  const cacheKey = `${currentBoard.map((mark) => mark ?? '-').join('')}:${maximizing}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);

  let bestScore = maximizing ? -Infinity : Infinity;
  let fullySearched = true;
  for (let index = 0; index < currentBoard.length; index += 1) {
    if (currentBoard[index]) continue;
    currentBoard[index] = maximizing ? 'O' : 'X';
    const score = minimax(currentBoard, !maximizing, depth + 1, alpha, beta, cache);
    currentBoard[index] = null;

    if (maximizing) {
      bestScore = Math.max(bestScore, score);
      alpha = Math.max(alpha, bestScore);
    } else {
      bestScore = Math.min(bestScore, score);
      beta = Math.min(beta, bestScore);
    }
    if (beta <= alpha) {
      fullySearched = false;
      break;
    }
  }

  if (fullySearched) cache.set(cacheKey, bestScore);
  return bestScore;
}

export function findBestTicTacToeMove(currentBoard) {
  let bestScore = -Infinity;
  let move = -1;
  const cache = new Map();

  currentBoard.forEach((mark, index) => {
    if (mark) return;
    currentBoard[index] = 'O';
    const score = minimax(currentBoard, false, 1, -Infinity, Infinity, cache);
    currentBoard[index] = null;
    if (score > bestScore) {
      bestScore = score;
      move = index;
    }
  });
  return move;
}

export function initTicTacToe({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-ttt'),
    back: document.getElementById('back-menu'),
    restart: document.getElementById('restart-ttt'),
    board: document.getElementById('ttt-board'),
    status: document.getElementById('ttt-status'),
    scoreYou: document.getElementById('score-you'),
    scoreBot: document.getElementById('score-bot'),
    scoreDraw: document.getElementById('score-draw'),
    lobbyBack: document.getElementById('ttt-lobby-back'), playBot: document.getElementById('play-ttt-bot'),
    findPublic: document.getElementById('find-ttt-public'), create: document.getElementById('create-ttt-room'),
    joinForm: document.getElementById('join-ttt-form'), codeInput: document.getElementById('ttt-room-code'),
    lobbyMessage: document.getElementById('ttt-lobby-message'),
    onlineMeta: document.getElementById('ttt-online-meta'), copyCode: document.getElementById('copy-ttt-room-code'),
    activeCode: document.getElementById('active-ttt-code'), scoreRow: document.getElementById('ttt-score-row'),
  };

  let board = [];
  let gameOver = false;
  let botThinking = false;
  let botTimer = null;
  let mode = 'bot';
  let room = null;
  let pollTimer = null;
  let pending = false;
  const scores = { you: 0, bot: 0, draw: 0 };

  elements.open.addEventListener('click', () => {
    showScreen('ttt-lobby');
  });
  elements.lobbyBack.addEventListener('click', () => showScreen('menu'));
  elements.playBot.addEventListener('click', () => {
    mode = 'bot';
    room = null;
    elements.onlineMeta.hidden = true;
    elements.scoreRow.hidden = false;
    elements.restart.hidden = false;
    restartGame();
    showScreen('ttt');
  });
  elements.findPublic.addEventListener('click', () => enterOnline('/api/tictactoe/public'));
  elements.create.addEventListener('click', () => enterOnline('/api/tictactoe/create'));
  elements.joinForm.addEventListener('submit', (event) => { event.preventDefault(); joinByCode((elements.codeInput as HTMLInputElement).value.toUpperCase()); });
  elements.copyCode.addEventListener('click', async () => {
    if (!room?.code) return;
    try {
      await navigator.clipboard.writeText(room.code);
      setStatus('код комнаты скопирован, хозяин :3');
    } catch {
      setStatus(`код комнаты: ${room.code}`);
    }
  });
  elements.back.addEventListener('click', leaveGame);
  elements.restart.addEventListener('click', restartGame);

  function leaveGame() {
    cancelBotMove();
    stopPolling();
    botThinking = false;
    showScreen('ttt-lobby');
  }

  function restartGame() {
    cancelBotMove();
    board = Array(9).fill(null);
    gameOver = false;
    botThinking = false;
    setStatus(phrase(PHRASES.turn));
    renderBoard();
  }

  function cancelBotMove() {
    if (botTimer !== null) window.clearTimeout(botTimer);
    botTimer = null;
  }

  function renderBoard() {
    elements.board.replaceChildren();
    const visibleBoard = mode === 'online' ? room.board.map((mark) => mark.toUpperCase() || null) : board;
    visibleBoard.forEach((mark, index) => {
      const cell = document.createElement('button');
      cell.type = 'button';
      cell.className = `cell${mark ? ` ${mark.toLowerCase()}` : ''}`;
      cell.setAttribute('role', 'gridcell');
      cell.setAttribute('aria-label', mark ? `Клетка ${index + 1}: ${mark}` : `Клетка ${index + 1}: пусто`);
      cell.disabled = Boolean(mark) || gameOver || botThinking || (mode === 'online' && (room.status !== 'active' || room.turn !== room.you));
      cell.setAttribute('aria-disabled', String(cell.disabled));
      if (mark) cell.innerHTML = MARKS[mark];
      cell.addEventListener('click', () => mode === 'online' ? onlineMove(index) : playerMove(index));
      elements.board.appendChild(cell);
    });
  }

  async function enterOnline(path, body?) {
    if (pending || !hasTelegramAuth(telegram)) return;
    pending = true;
    try {
      room = await api(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
      mode = 'online';
      gameOver = room.status === 'finished';
      elements.restart.hidden = true;
      elements.onlineMeta.hidden = false;
      elements.scoreRow.hidden = true;
      elements.activeCode.textContent = room.code;
      showScreen('ttt'); renderOnline(); startPolling();
    } catch (error) { elements.lobbyMessage.textContent = error.message; }
    finally { pending = false; }
  }

  async function joinByCode(code) { await enterOnline('/api/tictactoe/join', { code }); }

  async function onlineMove(index) {
    if (pending) return; pending = true;
    try { room = await api('/api/tictactoe/move', { method: 'POST', body: JSON.stringify({ code: room.code, index }) }); renderOnline(); }
    catch (error) { setStatus(error.message); }
    finally { pending = false; }
  }

  function renderOnline() {
    gameOver = room.status === 'finished';
    elements.activeCode.textContent = room.code;
    if (room.status === 'waiting') setStatus('ждём второго игрока, хозяин...');
    else if (room.status === 'finished') setStatus(room.winner === 'draw' ? 'ничья!' : room.winner === room.you ? 'хозяин победил!' : 'соперник победил');
    else setStatus(room.turn === room.you ? 'твой ход, хозяин' : 'ход соперника...');
    renderBoard();
  }

  function startPolling() { stopPolling(); pollTimer = window.setInterval(refreshOnline, 900); }
  function stopPolling() { if (pollTimer) window.clearInterval(pollTimer); pollTimer = null; }
  async function refreshOnline() { if (!room || pending || document.hidden) return; try { const next = await api(`/api/tictactoe/state?code=${room.code}`); if (next.version !== room.version) { room = next; renderOnline(); } } catch {} }
  async function api(path, options = {}) { const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...telegramAuthHeaders(telegram) } }); const payload = await response.json().catch(() => ({})); if (!response.ok) throw new Error(payload.error || 'сервер молчит...'); return payload; }

  function setStatus(text, state = '') {
    elements.status.textContent = text;
    elements.status.className = `status-bar${state ? ` ${state}` : ''}`;
  }

  function playerMove(index) {
    if (gameOver || botThinking || board[index]) return;

    telegram?.HapticFeedback?.selectionChanged();
    board[index] = 'X';

    const result = checkWinner(board);
    if (result) return endGame(result);

    botThinking = true;
    renderBoard();
    setStatus(phrase(PHRASES.thinking));
    botTimer = window.setTimeout(botMove, 350);
  }

  function botMove() {
    botTimer = null;
    const move = findBestTicTacToeMove(board);
    if (move !== -1) board[move] = 'O';
    botThinking = false;

    const result = checkWinner(board);
    if (result) return endGame(result);
    renderBoard();
    setStatus(phrase(PHRASES.turn));
  }

  function endGame(result) {
    gameOver = true;
    renderBoard();
    const outcome = result.winner === 'X' ? 'success' : result.winner === 'O' ? 'error' : 'warning';
    telegram?.HapticFeedback?.notificationOccurred(outcome);

    if (result.winner === 'X') {
      scores.you += 1;
      setStatus(phrase(PHRASES.playerWin), 'win');
      bumpScore(elements.scoreYou);
    } else if (result.winner === 'O') {
      scores.bot += 1;
      setStatus(phrase(PHRASES.botWin), 'lose');
      bumpScore(elements.scoreBot);
    } else {
      scores.draw += 1;
      setStatus(phrase(PHRASES.draw), 'draw');
      bumpScore(elements.scoreDraw);
    }

    if (result.line) highlightWinningLine(result.line);
    updateScoreboard();
  }

  function highlightWinningLine(line) {
    const cells = elements.board.children;
    line.forEach((index) => cells[index].classList.add('win-cell'));
  }

  function updateScoreboard() {
    elements.scoreYou.textContent = String(scores.you);
    elements.scoreBot.textContent = String(scores.bot);
    elements.scoreDraw.textContent = String(scores.draw);
  }

  function bumpScore(element) {
    element.classList.remove('bump');
    void element.offsetWidth;
    element.classList.add('bump');
  }

  restartGame();
  return { joinByCode };
}
