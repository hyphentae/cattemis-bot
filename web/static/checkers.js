import { hasTelegramAuth, telegramAuthHeaders } from './telegram-auth.js?v=20260716-code-only';

const POLL_INTERVAL_MS = 1000;

export function initCheckers({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-checkers'),
    lobbyBack: document.getElementById('checkers-lobby-back'),
    create: document.getElementById('create-checkers-room'),
    createBot: document.getElementById('create-checkers-bot'),
    findPublic: document.getElementById('find-checkers-public'),
    joinForm: document.getElementById('join-checkers-form'),
    codeInput: document.getElementById('checkers-room-code'),
    lobbyMessage: document.getElementById('checkers-lobby-message'),
    leave: document.getElementById('leave-checkers'),
    copyCode: document.getElementById('copy-room-code'),
    matchTitle: document.getElementById('checkers-match-title'),
    activeCode: document.getElementById('active-room-code'),
    redName: document.getElementById('checkers-red-name'),
    blueName: document.getElementById('checkers-blue-name'),
    turn: document.getElementById('checkers-turn'),
    status: document.getElementById('checkers-status'),
    board: document.getElementById('checkers-board'),
    hint: document.getElementById('checkers-hint'),
  };

  let room = null;
  let selected = null;
  let pollTimer = null;
  let requestPending = false;
  let animating = false;

  elements.open.addEventListener('click', openLobby);
  elements.lobbyBack.addEventListener('click', () => showScreen('menu'));
  elements.create.addEventListener('click', createRoom);
  elements.createBot.addEventListener('click', createBotGame);
  elements.findPublic.addEventListener('click', findPublicGame);
  elements.joinForm.addEventListener('submit', joinRoom);
  elements.leave.addEventListener('click', leaveRoom);
  elements.copyCode.addEventListener('click', copyRoomCode);
  elements.codeInput.addEventListener('input', () => {
    elements.codeInput.value = elements.codeInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  });

  function openLobby() {
    clearMessage();
    if (!hasTelegramAuth(telegram)) {
      showMessage('хозяин, онлайн-игра работает только внутри Telegram :3');
    }
    showScreen('checkers-lobby');
  }

  async function createRoom() {
    if (requestPending) return;
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/checkers/create', { method: 'POST' });
      openGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function createBotGame() {
    if (requestPending) return;
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/checkers/create-bot', { method: 'POST' });
      openGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function findPublicGame() {
    if (requestPending) return;
    setPending(true);
    clearMessage();
    try {
      room = await api('/api/checkers/public', { method: 'POST' });
      openGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function joinRoom(event) {
    event.preventDefault();
    if (requestPending) return;
    const code = elements.codeInput.value.trim().toUpperCase();
    if (code.length !== 6) {
      showMessage('хозяин, нужен кодик из шести символов :3');
      return;
    }

    setPending(true);
    clearMessage();
    try {
      room = await api('/api/checkers/join', {
        method: 'POST',
        body: JSON.stringify({ code }),
      });
      openGame();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setPending(false);
    }
  }

  async function joinByCode(code) {
    room = await api('/api/checkers/join', { method: 'POST', body: JSON.stringify({ code }) });
    openGame();
  }

  function openGame() {
    // The room request has completed; unlock cells before the first board render.
    setPending(false);
    selected = null;
    showScreen('checkers-game');
    render();
    if (!room.bot) startPolling();
    telegram?.HapticFeedback?.notificationOccurred('success');
  }

  function leaveRoom() {
    stopPolling();
    room = null;
    selected = null;
    showScreen('checkers-lobby');
  }

  async function copyRoomCode() {
    if (!room?.code) return;
    try {
      await navigator.clipboard.writeText(room.code);
      elements.status.textContent = 'кодик скопирован, хозяин :3';
      telegram?.HapticFeedback?.notificationOccurred('success');
    } catch {
      elements.status.textContent = `хозяин, кодик комнаты: ${room.code}`;
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(refreshRoom, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer !== null) window.clearInterval(pollTimer);
    pollTimer = null;
  }

  async function refreshRoom() {
    if (!room || requestPending || animating || document.hidden) return;
    try {
      const next = await api(`/api/checkers/state?code=${encodeURIComponent(room.code)}`);
      if (next.version !== room.version) {
        const previousBoard = cloneBoard(room.board);
        await animateRoomUpdate(previousBoard, next);
        room = next;
        selected = room.forced_from ?? null;
        render();
        telegram?.HapticFeedback?.selectionChanged();
      }
      if (room.status === 'finished') stopPolling();
    } catch (error) {
      elements.status.textContent = `ой, хозяин... ${error.message}`;
    }
  }

  function render() {
    if (!room) return;
    elements.activeCode.textContent = room.code;
    elements.copyCode.hidden = room.bot || room.public;
    elements.matchTitle.hidden = !(room.bot || room.public);
    elements.matchTitle.textContent = room.bot ? 'хозяин против катемиса' : 'публичная партия';
    elements.redName.textContent = room.red.name;
    elements.blueName.textContent = room.blue?.name ?? (room.public ? 'ищем соперника...' : 'ждём друга...');
    elements.turn.textContent = room.status === 'active'
      ? (room.turn === room.you ? 'твой ход, хозяин' : 'ждём ход...')
      : 'ждём...';

    if (room.status === 'waiting') {
      elements.status.textContent = room.public
        ? 'ищу соперника в публичном лобби, хозяин... :3'
        : 'хозяин, отправь кодик другу — я пока погрею место :3';
      elements.hint.textContent = room.public
        ? 'как только кто-нибудь найдётся, партия начнётся сама'
        : 'нажми на кодик, и я скопирую его лапкой';
    } else if (room.status === 'finished') {
      const won = room.winner === room.you;
      elements.status.textContent = won
        ? 'хозяин победил! я горжусь тобой :3'
        : (room.bot ? 'катемис победил, мяу >:3' : 'друг победил... реванш?');
      elements.hint.textContent = 'вернись назад — устроим ещё одну партию, хозяин';
    } else if (room.turn === room.you) {
      elements.status.textContent = room.forced_from
        ? 'ещё можно бить этой шашкой, хозяин!'
        : 'твой ход, хозяин :3';
      elements.hint.textContent = 'выбери шашку, а потом зелёную точку';
    } else {
      elements.status.textContent = room.bot ? 'катемис думает... мяу' : 'теперь ход друга';
      elements.hint.textContent = 'я сам обновлю доску, хозяин';
    }

    renderBoard();
  }

  function renderBoard(board = room.board, interactive = true) {
    elements.board.replaceChildren();
    const reversed = room.you === 'blue';
    const indexes = Array.from({ length: 8 }, (_, index) => reversed ? 7 - index : index);
    const availableFrom = new Set(room.moves.map((move) => key(move.from)));
    const targets = interactive && selected
      ? new Set(room.moves.filter((move) => samePosition(move.from, selected)).map((move) => key(move.to)))
      : new Set();

    for (const row of indexes) {
      for (const col of indexes) {
        const piece = board[row][col];
        const position = { row, col };
        const square = document.createElement('button');
        square.type = 'button';
        square.className = `checkers-square ${(row + col) % 2 ? 'dark' : 'light'}`;
        square.setAttribute('role', 'gridcell');
        square.setAttribute('aria-label', squareLabel(position, piece));
        square.dataset.row = String(row);
        square.dataset.col = String(col);

        if (interactive && selected && samePosition(selected, position)) square.classList.add('selected');
        if (targets.has(key(position))) square.classList.add('target');
        if (piece) {
          const checker = document.createElement('span');
          checker.className = `checker ${piece.toLowerCase() === 'r' ? 'red' : 'blue'}${piece === piece.toUpperCase() ? ' king' : ''}`;
          checker.textContent = piece === piece.toUpperCase() ? '♛' : '';
          square.appendChild(checker);
        }

        const canSelect = interactive && room.status === 'active' && room.turn === room.you && availableFrom.has(key(position));
        const canMove = interactive && targets.has(key(position));
        square.disabled = !(canSelect || canMove) || requestPending;
        square.setAttribute('aria-disabled', String(square.disabled));
        square.addEventListener('click', () => handleSquare(position, canSelect, canMove));
        elements.board.appendChild(square);
      }
    }
  }

  async function handleSquare(position, canSelect, canMove) {
    if (canSelect) {
      selected = position;
      telegram?.HapticFeedback?.selectionChanged();
      renderBoard();
      return;
    }
    if (!canMove || !selected || requestPending) return;

    const previousBoard = cloneBoard(room.board);
    requestPending = true;
    renderBoard();
    if (room.bot) {
      elements.status.textContent = 'катемис думает над ходом... ушки торчком owo';
      elements.status.classList.add('thinking');
      elements.board.classList.add('bot-thinking');
    }
    try {
      const next = await api('/api/checkers/move', {
        method: 'POST',
        body: JSON.stringify({ code: room.code, from: selected, to: position }),
      });
      await animateRoomUpdate(previousBoard, next);
      room = next;
      selected = room.forced_from ?? null;
      telegram?.HapticFeedback?.impactOccurred('medium');
      render();
    } catch (error) {
      elements.status.textContent = `ой, хозяин... ${error.message}`;
      await refreshRoom();
    } finally {
      requestPending = false;
      elements.status.classList.remove('thinking');
      elements.board.classList.remove('bot-thinking');
      if (room) render();
    }
  }

  async function animateRoomUpdate(previousBoard, nextRoom) {
    const moves = nextRoom.last_moves ?? [];
    if (!moves.length || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    animating = true;
    const animatedBoard = cloneBoard(previousBoard);
    try {
      for (let index = 0; index < moves.length; index += 1) {
        const move = moves[index];
        const botMove = Boolean(room?.bot && index > 0);
        if (botMove) {
          elements.status.textContent = 'катемис ходит... следи за лапками, хозяин :3';
          await delay(130);
        }
        await animateCheckerMove(move, botMove);
        applyAnimatedMove(animatedBoard, move);
        renderBoard(animatedBoard, false);
        if (botMove) telegram?.HapticFeedback?.selectionChanged();
        await delay(55);
      }
    } finally {
      animating = false;
    }
  }

  async function animateCheckerMove(move, botMove) {
    const fromSquare = findSquare(move.from);
    const toSquare = findSquare(move.to);
    const checker = fromSquare?.querySelector('.checker');
    if (!fromSquare || !toSquare || !checker) return;

    const boardRect = elements.board.getBoundingClientRect();
    const checkerRect = checker.getBoundingClientRect();
    const targetRect = toSquare.getBoundingClientRect();
    const moving = checker.cloneNode(true);
    moving.classList.add('checker-moving');
    if (botMove) moving.classList.add('bot-move');
    Object.assign(moving.style, {
      left: `${checkerRect.left - boardRect.left - elements.board.clientLeft}px`,
      top: `${checkerRect.top - boardRect.top - elements.board.clientTop}px`,
      width: `${checkerRect.width}px`,
      height: `${checkerRect.height}px`,
    });
    elements.board.appendChild(moving);
    checker.style.opacity = '0';

    const captured = Math.abs(move.to.row - move.from.row) === 2
      ? findSquare({ row: (move.from.row + move.to.row) / 2, col: (move.from.col + move.to.col) / 2 })?.querySelector('.checker')
      : null;
    const captureAnimation = captured?.animate([
      { opacity: 1, transform: 'scale(1)' },
      { opacity: 0, transform: 'scale(.25) rotate(18deg)' },
    ], { duration: botMove ? 360 : 280, easing: 'cubic-bezier(.4, 0, .2, 1)', fill: 'forwards' });

    const targetX = targetRect.left + (targetRect.width - checkerRect.width) / 2 - checkerRect.left;
    const targetY = targetRect.top + (targetRect.height - checkerRect.height) / 2 - checkerRect.top;
    const movement = moving.animate([
      { transform: 'translate3d(0, 0, 0)' },
      { transform: `translate3d(${targetX}px, ${targetY}px, 0)` },
    ], {
      duration: botMove ? 390 : 310,
      easing: 'cubic-bezier(.4, 0, .2, 1)',
      fill: 'forwards',
    });
    await Promise.all([movement.finished.catch(() => {}), captureAnimation?.finished.catch(() => {})]);
    moving.remove();
  }

  function applyAnimatedMove(board, move) {
    let piece = board[move.from.row][move.from.col];
    board[move.from.row][move.from.col] = '';
    if (Math.abs(move.to.row - move.from.row) === 2) {
      board[(move.from.row + move.to.row) / 2][(move.from.col + move.to.col) / 2] = '';
    }
    if (piece === 'r' && move.to.row === 0) piece = 'R';
    if (piece === 'b' && move.to.row === 7) piece = 'B';
    board[move.to.row][move.to.col] = piece;
  }

  function findSquare(position) {
    return elements.board.querySelector(`[data-row="${position.row}"][data-col="${position.col}"]`);
  }

  function cloneBoard(board) { return board.map((row) => [...row]); }
  function delay(milliseconds) { return new Promise((resolve) => window.setTimeout(resolve, milliseconds)); }

  async function api(path, options = {}) {
    if (!hasTelegramAuth(telegram)) throw new Error('хозяин, открой игру внутри Telegram :3');
    const response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...telegramAuthHeaders(telegram),
        ...options.headers,
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'сервер молчит... попробуй ещё раз, хозяин T_T');
    return payload;
  }

  function setPending(pending) {
    requestPending = pending;
    elements.create.disabled = pending;
    elements.createBot.disabled = pending;
    elements.findPublic.disabled = pending;
    elements.joinForm.querySelector('button').disabled = pending;
  }

  function showMessage(message) {
    elements.lobbyMessage.textContent = message.toLowerCase().includes('хозяин')
      ? message
      : `ой, хозяин... ${message}`;
  }
  function clearMessage() { elements.lobbyMessage.textContent = ''; }
  function key(position) { return `${position.row}:${position.col}`; }
  function samePosition(a, b) { return a?.row === b?.row && a?.col === b?.col; }
  function squareLabel(position, piece) {
    if (!piece) return `Клетка ${position.row + 1}, ${position.col + 1}: пусто`;
    const color = piece.toLowerCase() === 'r' ? 'красная' : 'синяя';
    const rank = piece === piece.toUpperCase() ? ' дамка' : ' шашка';
    return `Клетка ${position.row + 1}, ${position.col + 1}: ${color}${rank}`;
  }
  return { joinByCode };
}
