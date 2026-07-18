import { loadLeaderboard, submitLeaderboardScore } from './leaderboard.ts';

const DIFFICULTIES = {
  easy: { rows: 9, cols: 9, mines: 10, cellSize: 32 },
  medium: { rows: 16, cols: 16, mines: 40, cellSize: 25 },
  hard: { rows: 16, cols: 30, mines: 99, cellSize: 23 },
};

export function initMinesweeper({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-minesweeper'),
    leave: document.getElementById('leave-minesweeper'),
    restart: document.getElementById('restart-minesweeper'),
    difficulties: document.getElementById('mines-difficulties'),
    board: document.getElementById('mines-board'),
    screen: document.getElementById('screen-minesweeper'),
    viewport: document.getElementById('mines-viewport'),
    minesLeft: document.getElementById('mines-left'),
    time: document.getElementById('mines-time'),
    mode: document.getElementById('mines-mode'),
    status: document.getElementById('mines-status'),
    leaderboard: document.getElementById('mines-leaderboard'),
  };

  let difficulty = 'easy';
  let config = DIFFICULTIES[difficulty];
  let cells = [];
  let started = false;
  let finished = false;
  let flagMode = false;
  let elapsed = 0;
  let timer = null;
  let animatedCells = new Set();
  let suppressedLongPressIndex = -1;
  let suppressLongPressUntil = 0;
  const longPressed = new WeakSet();

  elements.open.addEventListener('click', () => {
    newGame();
    showScreen('minesweeper');
  });
  elements.leave.addEventListener('click', () => {
    stopTimer();
    showScreen('menu');
  });
  elements.restart.addEventListener('click', newGame);
  elements.screen.addEventListener('selectstart', (event) => event.preventDefault());
  elements.screen.addEventListener('dragstart', (event) => event.preventDefault());
  elements.mode.addEventListener('click', () => setFlagMode(!flagMode));
  elements.difficulties.addEventListener('click', (event) => {
    const button = (event.target as Element).closest<HTMLElement>('[data-difficulty]');
    if (!button || button.dataset.difficulty === difficulty) return;
    difficulty = button.dataset.difficulty;
    newGame();
  });

  function newGame() {
    stopTimer();
    config = DIFFICULTIES[difficulty];
    cells = Array.from({ length: config.rows * config.cols }, () => ({
      mine: false,
      revealed: false,
      flagged: false,
      adjacent: 0,
    }));
    started = false;
    finished = false;
    elapsed = 0;
    animatedCells = new Set();
    suppressedLongPressIndex = -1;
    suppressLongPressUntil = 0;
    elements.time.textContent = '000';
    elements.board.className = 'mines-board';
    elements.board.style.setProperty('--mines-columns', config.cols);
    elements.board.style.setProperty('--mine-cell-size', `${config.cellSize}px`);
    elements.viewport.scrollTo({ top: 0, left: 0 });
    setFlagMode(false);
    setStatus('разминируй :3c');
    updateDifficultyButtons();
    render();
    void refreshLeaderboard();
  }

  function placeMines(safeIndex) {
    const excluded = new Set([safeIndex, ...neighbors(safeIndex)]);
    const candidates = cells.map((_, index) => index).filter((index) => !excluded.has(index));
    shuffle(candidates);
    candidates.slice(0, config.mines).forEach((index) => { cells[index].mine = true; });
    cells.forEach((cell, index) => {
      cell.adjacent = neighbors(index).filter((neighbor) => cells[neighbor].mine).length;
    });
  }

  function reveal(index) {
    const cell = cells[index];
    if (finished || cell.flagged) return;
    if (cell.revealed) {
      revealAround(index);
      return;
    }
    if (!started) {
      placeMines(index);
      started = true;
      startTimer();
    }
    if (cell.mine) {
      lose(index);
      return;
    }

    revealEmptyArea(index);
    telegram?.HapticFeedback?.selectionChanged();
    if (cells.filter((candidate) => candidate.revealed).length === cells.length - config.mines) win();
    render();
  }

  function revealEmptyArea(startIndex) {
    const queue = [startIndex];
    const visited = new Set();
    while (queue.length) {
      const index = queue.shift();
      if (visited.has(index)) continue;
      visited.add(index);
      const cell = cells[index];
      if (cell.flagged || cell.mine) continue;
      if (!cell.revealed) animatedCells.add(index);
      cell.revealed = true;
      if (cell.adjacent === 0) {
        neighbors(index).forEach((neighbor) => {
          if (!cells[neighbor].revealed) queue.push(neighbor);
        });
      }
    }
  }

  function revealAround(index) {
    const cell = cells[index];
    if (!cell.revealed || cell.adjacent === 0) return;
    const nearby = neighbors(index);
    if (nearby.filter((neighbor) => cells[neighbor].flagged).length !== cell.adjacent) return;
    const hidden = nearby.filter((neighbor) => !cells[neighbor].revealed && !cells[neighbor].flagged);
    const mine = hidden.find((neighbor) => cells[neighbor].mine);
    if (mine !== undefined) {
      lose(mine);
      return;
    }
    hidden.forEach(revealEmptyArea);
    if (cells.filter((candidate) => candidate.revealed).length === cells.length - config.mines) win();
    render();
  }

  function toggleFlag(index, hapticStyle = 'light') {
    const cell = cells[index];
    if (finished || cell.revealed) return;
    if (!cell.flagged && flaggedCount() >= config.mines) {
      setStatus('все флажки уже расставлены, хозяин');
      return;
    }
    cell.flagged = !cell.flagged;
    if (hapticStyle === 'flag') {
      if (cell.flagged) telegram?.HapticFeedback?.impactOccurred('heavy');
      else telegram?.HapticFeedback?.impactOccurred('medium');
    } else {
      telegram?.HapticFeedback?.impactOccurred(hapticStyle);
    }
    updateCounter();
    render();
  }

  function handleCell(button, index) {
    if (longPressed.delete(button) || isLongPressSuppressed(index)) return;
    if (flagMode) toggleFlag(index);
    else reveal(index);
  }

  function suppressLongPressFollowUp(index) {
    suppressedLongPressIndex = index;
    suppressLongPressUntil = performance.now() + 800;
  }

  function isLongPressSuppressed(index) {
    return index === suppressedLongPressIndex && performance.now() < suppressLongPressUntil;
  }

  function lose(explodedIndex) {
    finished = true;
    stopTimer();
    cells.forEach((cell, index) => {
      if (cell.mine && !cell.revealed) animatedCells.add(index);
      if (cell.mine) cell.revealed = true;
    });
    cells[explodedIndex].exploded = true;
    elements.board.classList.add('lost');
    setStatus('ой... мина, хозяин T_T', 'lose');
    telegram?.HapticFeedback?.notificationOccurred('error');
    render();
  }

  function win() {
    finished = true;
    stopTimer();
    cells.forEach((cell) => { if (cell.mine) cell.flagged = true; });
    elements.board.classList.add('won');
    setStatus(`поле очищено за ${elapsed} сек., хозяин :3`, 'win');
    telegram?.HapticFeedback?.notificationOccurred('success');
    updateCounter();
    void submitLeaderboardScore({
      telegram,
      game: 'minesweeper',
      difficulty,
      seconds: Math.max(1, elapsed),
      element: elements.leaderboard,
    });
  }

  function refreshLeaderboard() {
    return loadLeaderboard({
      telegram,
      game: 'minesweeper',
      difficulty,
      element: elements.leaderboard,
    });
  }

  function render() {
    elements.board.replaceChildren();
    cells.forEach((cell, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'mine-cell';
      button.setAttribute('role', 'gridcell');
      button.setAttribute('aria-label', cellLabel(cell, index));
      button.setAttribute('aria-pressed', String(cell.flagged));
      button.disabled = finished || (cell.revealed && cell.adjacent === 0 && !cell.mine);
      button.setAttribute('aria-disabled', String(button.disabled));
      if (animatedCells.has(index)) button.classList.add('fresh');
      if (cell.revealed) {
        button.classList.add('revealed');
        if (cell.mine) button.classList.add('mine');
        if (cell.exploded) button.classList.add('exploded');
        if (cell.adjacent && !cell.mine) {
          button.textContent = String(cell.adjacent);
          button.dataset.number = String(cell.adjacent);
        }
      } else if (cell.flagged) {
        button.classList.add('flagged');
        button.textContent = '⚑';
      }
      button.addEventListener('click', () => handleCell(button, index));
      bindLongPress(button, index);
      elements.board.appendChild(button);
    });
    animatedCells.clear();
    updateCounter();
  }

  function bindLongPress(button, index) {
    let longPressTimer = null;
    let startX = 0;
    let startY = 0;
    let pointerId = null;
    const cancel = () => {
      if (longPressTimer !== null) window.clearTimeout(longPressTimer);
      longPressTimer = null;
      button.classList.remove('long-pressing');
    };
    button.addEventListener('pointerdown', (event) => {
      if (event.pointerType === 'mouse' || !event.isPrimary) return;
      cancel();
      startX = event.clientX;
      startY = event.clientY;
      pointerId = event.pointerId;
      button.classList.add('long-pressing');
      try { button.setPointerCapture(pointerId); } catch { /* WebView may not support capture */ }
      longPressTimer = window.setTimeout(() => {
        longPressed.add(button);
        suppressLongPressFollowUp(index);
        toggleFlag(index, 'flag');
        cancel();
      }, 500);
    });
    button.addEventListener('pointermove', (event) => {
      if (event.pointerId !== pointerId || longPressTimer === null) return;
      if (Math.hypot(event.clientX - startX, event.clientY - startY) > 10) cancel();
    });
    button.addEventListener('pointerup', cancel);
    button.addEventListener('pointercancel', cancel);
    button.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      const handledByLongPress = longPressed.has(button);
      cancel();
      if (!handledByLongPress && !isLongPressSuppressed(index)) {
        longPressed.add(button);
        suppressLongPressFollowUp(index);
        toggleFlag(index, 'flag');
      }
    });
  }

  function neighbors(index) {
    const row = Math.floor(index / config.cols);
    const col = index % config.cols;
    const result = [];
    for (let rowOffset = -1; rowOffset <= 1; rowOffset += 1) {
      for (let colOffset = -1; colOffset <= 1; colOffset += 1) {
        if (!rowOffset && !colOffset) continue;
        const nextRow = row + rowOffset;
        const nextCol = col + colOffset;
        if (nextRow >= 0 && nextRow < config.rows && nextCol >= 0 && nextCol < config.cols) {
          result.push(nextRow * config.cols + nextCol);
        }
      }
    }
    return result;
  }

  function updateDifficultyButtons() {
    elements.difficulties.querySelectorAll<HTMLElement>('[data-difficulty]').forEach((button) => {
      const selected = button.dataset.difficulty === difficulty;
      button.classList.toggle('selected', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  }

  function setFlagMode(value) {
    flagMode = value;
    elements.mode.setAttribute('aria-pressed', String(value));
    elements.mode.textContent = value ? 'режим: флажки' : 'режим: открывать';
    elements.board.classList.toggle('flag-mode', value);
  }

  function updateCounter() {
    elements.minesLeft.textContent = String(Math.max(0, config.mines - flaggedCount())).padStart(2, '0');
  }

  function flaggedCount() { return cells.filter((cell) => cell.flagged).length; }

  function startTimer() {
    stopTimer();
    timer = window.setInterval(() => {
      elapsed = Math.min(999, elapsed + 1);
      elements.time.textContent = String(elapsed).padStart(3, '0');
      if (elapsed === 999) stopTimer();
    }, 1000);
  }

  function stopTimer() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
  }

  function setStatus(message, state = '') {
    elements.status.textContent = message;
    elements.status.className = `status-bar${state ? ` ${state}` : ''}`;
  }

  function cellLabel(cell, index) {
    const position = `строка ${Math.floor(index / config.cols) + 1}, столбец ${index % config.cols + 1}`;
    if (cell.flagged && !cell.revealed) return `${position}: флажок`;
    if (!cell.revealed) return `${position}: закрыто`;
    if (cell.mine) return `${position}: мина`;
    return `${position}: ${cell.adjacent || 'пусто'}`;
  }

  function shuffle(values) {
    for (let index = values.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [values[index], values[randomIndex]] = [values[randomIndex], values[index]];
    }
  }

  newGame();
}
