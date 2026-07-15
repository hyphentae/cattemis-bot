const telegram = window.Telegram?.WebApp;

const elements = {
  screens: document.querySelectorAll('.screen'),
  userChip: document.getElementById('user-chip'),
  userName: document.getElementById('user-name'),
  board: document.getElementById('ttt-board'),
  status: document.getElementById('ttt-status'),
  scoreYou: document.getElementById('score-you'),
  scoreBot: document.getElementById('score-bot'),
  scoreDraw: document.getElementById('score-draw'),
};

const winningLines = [
  [0, 1, 2], [3, 4, 5], [6, 7, 8],
  [0, 3, 6], [1, 4, 7], [2, 5, 8],
  [0, 4, 8], [2, 4, 6],
];

const marks = {
  X: '<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-x"/></svg>',
  O: '<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#icon-o"/></svg>',
};

let board = [];
let gameOver = false;
let botThinking = false;
const scores = { you: 0, bot: 0, draw: 0 };

function initializeTelegram() {
  if (!telegram) return;

  telegram.ready();
  telegram.expand();
  telegram.setHeaderColor?.('#171525');
  telegram.setBackgroundColor?.('#11111b');

  const user = telegram.initDataUnsafe?.user;
  if (!user) return;

  elements.userName.textContent = [user.first_name, user.last_name].filter(Boolean).join(' ');
  elements.userChip.classList.add('visible');
}

function showScreen(name) {
  telegram?.HapticFeedback?.impactOccurred('light');
  elements.screens.forEach((screen) => screen.classList.remove('active'));
  document.getElementById(`screen-${name}`).classList.add('active');

  if (name === 'ttt') restartGame();
}

function restartGame() {
  board = Array(9).fill(null);
  gameOver = false;
  botThinking = false;
  setStatus('твой ход');
  renderBoard();
}

function renderBoard() {
  elements.board.replaceChildren();

  board.forEach((mark, index) => {
    const cell = document.createElement('button');
    cell.type = 'button';
    cell.className = `cell${mark ? ` ${mark.toLowerCase()}` : ''}`;
    cell.setAttribute('role', 'gridcell');
    cell.setAttribute('aria-label', mark ? `Клетка ${index + 1}: ${mark}` : `Клетка ${index + 1}: пусто`);
    cell.disabled = Boolean(mark) || gameOver || botThinking;
    cell.setAttribute('aria-disabled', String(cell.disabled));
    if (mark) cell.innerHTML = marks[mark];
    cell.addEventListener('click', () => playerMove(index));
    elements.board.appendChild(cell);
  });
}

function setStatus(text, state = '') {
  elements.status.textContent = text;
  elements.status.className = `status-bar${state ? ` ${state}` : ''}`;
}

function checkWinner(currentBoard) {
  for (const [a, b, c] of winningLines) {
    if (currentBoard[a] && currentBoard[a] === currentBoard[b] && currentBoard[a] === currentBoard[c]) {
      return { winner: currentBoard[a], line: [a, b, c] };
    }
  }
  return currentBoard.every(Boolean) ? { winner: 'draw' } : null;
}

function playerMove(index) {
  if (gameOver || botThinking || board[index]) return;

  telegram?.HapticFeedback?.selectionChanged();
  board[index] = 'X';

  const result = checkWinner(board);
  if (result) return endGame(result);

  botThinking = true;
  renderBoard();
  setStatus('Кэттемис думает...');
  window.setTimeout(botMove, 350);
}

function botMove() {
  const move = bestMove(board);
  if (move !== -1) board[move] = 'O';
  botThinking = false;

  const result = checkWinner(board);
  if (result) return endGame(result);
  renderBoard();
  setStatus('твой ход');
}

function endGame(result) {
  gameOver = true;
  renderBoard();
  const outcome = result.winner === 'X' ? 'success' : result.winner === 'O' ? 'error' : 'warning';
  telegram?.HapticFeedback?.notificationOccurred(outcome);

  if (result.winner === 'X') {
    scores.you += 1;
    setStatus('🎉 ты победил!', 'win');
    bumpScore(elements.scoreYou);
  } else if (result.winner === 'O') {
    scores.bot += 1;
    setStatus('🐾 Кэттемис победила', 'lose');
    bumpScore(elements.scoreBot);
  } else {
    scores.draw += 1;
    setStatus('🤝 ничья', 'draw');
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
  elements.scoreYou.textContent = scores.you;
  elements.scoreBot.textContent = scores.bot;
  elements.scoreDraw.textContent = scores.draw;
}

function bumpScore(element) {
  element.classList.remove('bump');
  void element.offsetWidth;
  element.classList.add('bump');
}

function minimax(currentBoard, maximizing) {
  const result = checkWinner(currentBoard);
  if (result?.winner === 'O') return 10;
  if (result?.winner === 'X') return -10;
  if (result?.winner === 'draw') return 0;

  const values = [];
  currentBoard.forEach((mark, index) => {
    if (mark) return;
    currentBoard[index] = maximizing ? 'O' : 'X';
    values.push(minimax(currentBoard, !maximizing));
    currentBoard[index] = null;
  });
  return maximizing ? Math.max(...values) : Math.min(...values);
}

function bestMove(currentBoard) {
  let bestScore = -Infinity;
  let move = -1;

  currentBoard.forEach((mark, index) => {
    if (mark) return;
    currentBoard[index] = 'O';
    const score = minimax(currentBoard, false);
    currentBoard[index] = null;
    if (score > bestScore) {
      bestScore = score;
      move = index;
    }
  });
  return move;
}

document.getElementById('open-ttt').addEventListener('click', () => showScreen('ttt'));
document.getElementById('back-menu').addEventListener('click', () => showScreen('menu'));
document.getElementById('restart-ttt').addEventListener('click', restartGame);

initializeTelegram();
restartGame();
