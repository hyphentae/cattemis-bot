import { initCheckers } from './checkers.js?v=20260716-code-only';
import { initChess } from './chess.js?v=20260716-code-only';
import { initSudoku } from './sudoku.js';
import { initTicTacToe } from './tictactoe.js?v=20260716-code-only';
import { initPixelCanvas } from './pixel-canvas.js?v=20260716-zoom40';
import { initMinesweeper } from './minesweeper.js?v=20260717-mines-longpress-v5';
import { createHapticFeedback } from './haptics.js?v=20260717-mines-longpress-v5';

const nativeTelegram = window.Telegram?.WebApp;
const telegram = {
  get initData() { return nativeTelegram?.initData ?? ''; },
  HapticFeedback: createHapticFeedback(nativeTelegram?.HapticFeedback),
};
const screens = document.querySelectorAll('.screen');

function initializeTelegram() {
  if (!nativeTelegram) return;

  nativeTelegram.ready();
  nativeTelegram.expand();
  nativeTelegram.setHeaderColor?.('#171525');
  nativeTelegram.setBackgroundColor?.('#11111b');
}

function showScreen(name) {
  telegram?.HapticFeedback?.impactOccurred('light');
  screens.forEach((screen) => screen.classList.remove('active'));
  document.getElementById(`screen-${name}`).classList.add('active');
}

document.getElementById('open-parabolic-chess').addEventListener('click', () => {
  const frame = document.getElementById('parabolic-frame');
  if (frame.getAttribute('src') === 'about:blank') {
    frame.src = frame.dataset.src;
  }
  showScreen('parabolic');
});

document.getElementById('leave-parabolic').addEventListener('click', () => {
  document.getElementById('parabolic-frame').src = 'about:blank';
  showScreen('menu');
});

document.getElementById('open-deltarune').addEventListener('click', () => {
  const frame = document.getElementById('deltarune-frame');
  if (frame.getAttribute('src') === 'about:blank') frame.src = frame.dataset.src;
  showScreen('deltarune');
});

document.getElementById('leave-deltarune').addEventListener('click', () => {
  document.getElementById('deltarune-frame').src = 'about:blank';
  showScreen('menu');
});
initializeTelegram();
initTicTacToe({ telegram, showScreen });
initCheckers({ telegram, showScreen });
initSudoku({ telegram, showScreen });
initChess({ telegram, showScreen });
initPixelCanvas({ telegram, showScreen });
initMinesweeper({ telegram, showScreen });

const launchedGame = new URLSearchParams(window.location.hash.slice(1)).get('game');
const gameLaunchButtons = {
  tictactoe: 'open-ttt',
  checkers: 'open-checkers',
  sudoku: 'open-sudoku',
  parabolic_chess: 'open-parabolic-chess',
  deltarune: 'open-deltarune',
  chess: 'open-chess',
  minesweeper: 'open-minesweeper',
};
const launchButton = document.getElementById(gameLaunchButtons[launchedGame]);
if (launchButton) {
  window.requestAnimationFrame(() => launchButton.click());
}
