import { formatGameTime, loadLeaderboard, submitLeaderboardScore } from './leaderboard.ts';

const DIFFICULTIES = {
  easy: { givens: 40 },
  medium: { givens: 32 },
  hard: { givens: 26 },
};

const BASE_SOLUTION = [
  '534678912',
  '672195348',
  '198342567',
  '859761423',
  '426853791',
  '713924856',
  '961537284',
  '287419635',
  '345286179',
].join('');

const PHRASES = {
  ready: [
    'выбери пустую клеточку, хозяин :3',
    'я приготовил цифры, хозяин... мяу',
    'ушки торчком — начинаем судоку owo',
  ],
  correct: [
    'OwO, хозяин, ты угадал!',
    'умница, хозяин... ещё клеточку!',
    ':3c',
  ],
  mistake: [
    'ой, эта цифра сюда не хочет, хозяин T_T',
    'почти, хозяин... попробуй другую :3',
    'цифры запутались в моём хвостике, owo',
  ],
};

function randomPhrase(group) {
  return group[Math.floor(Math.random() * group.length)];
}

function shuffle(values) {
  const copy = [...values];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }
  return copy;
}

function rotateGrid(grid) {
  const rotated = Array(81).fill('0');
  for (let row = 0; row < 9; row += 1) {
    for (let col = 0; col < 9; col += 1) {
      rotated[col * 9 + (8 - row)] = grid[row * 9 + col];
    }
  }
  return rotated.join('');
}

function countSolutions(grid, limit = 2) {
  const cells = [...grid];
  let count = 0;
  const solve = () => {
    if (count >= limit) return;
    let target = -1;
    let candidates = [];
    for (let index = 0; index < 81; index += 1) {
      if (cells[index] !== '0') continue;
      const available = possibleValues(cells, index);
      if (!available.length) return;
      if (target === -1 || available.length < candidates.length) {
        target = index;
        candidates = available;
        if (available.length === 1) break;
      }
    }
    if (target === -1) {
      count += 1;
      return;
    }
    for (const value of candidates) {
      cells[target] = value;
      solve();
      cells[target] = '0';
      if (count >= limit) return;
    }
  };
  solve();
  return count;
}

function possibleValues(cells, index) {
  const row = Math.floor(index / 9);
  const col = index % 9;
  const used = new Set();
  for (let offset = 0; offset < 9; offset += 1) {
    used.add(cells[row * 9 + offset]);
    used.add(cells[offset * 9 + col]);
  }
  const boxRow = Math.floor(row / 3) * 3;
  const boxCol = Math.floor(col / 3) * 3;
  for (let rowOffset = 0; rowOffset < 3; rowOffset += 1) {
    for (let colOffset = 0; colOffset < 3; colOffset += 1) {
      used.add(cells[(boxRow + rowOffset) * 9 + boxCol + colOffset]);
    }
  }
  return ['1', '2', '3', '4', '5', '6', '7', '8', '9'].filter((value) => !used.has(value));
}

export function createSudokuPuzzle(difficulty = 'medium') {
  const digits = shuffle(['1', '2', '3', '4', '5', '6', '7', '8', '9']);
  const digitMap = new Map(digits.map((digit, index) => [String(index + 1), digit]));
  const remap = (grid) => [...grid].map((value) => value === '0' ? '0' : digitMap.get(value)).join('');
  let solution = remap(BASE_SOLUTION);
  const rotations = Math.floor(Math.random() * 4);
  for (let count = 0; count < rotations; count += 1) {
    solution = rotateGrid(solution);
  }
  const cells = [...solution];
  let givens = 81;
  const target = DIFFICULTIES[difficulty]?.givens ?? DIFFICULTIES.medium.givens;
  for (const index of shuffle(Array.from({ length: 81 }, (_, value) => value))) {
    if (givens <= target) break;
    const previous = cells[index];
    cells[index] = '0';
    if (countSolutions(cells.join('')) !== 1) cells[index] = previous;
    else givens -= 1;
  }
  const puzzle = cells.join('');
  return { puzzle, solution };
}

export function initSudoku({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-sudoku'),
    leave: document.getElementById('leave-sudoku'),
    fresh: document.getElementById('new-sudoku'),
    board: document.getElementById('sudoku-board'),
    keypad: document.getElementById('sudoku-keypad'),
    status: document.getElementById('sudoku-status'),
    mistakes: document.getElementById('sudoku-mistakes'),
    time: document.getElementById('sudoku-time'),
    difficulties: document.getElementById('sudoku-difficulties'),
    leaderboard: document.getElementById('sudoku-leaderboard'),
    screen: document.getElementById('screen-sudoku'),
  };

  let puzzle = '';
  let solution = '';
  let values = [];
  let selected = null;
  let mistakes = 0;
  let completed = false;
  let cellEffect = null;
  let revealBoard = false;
  let difficulty = 'medium';
  let elapsed = 0;
  let timer = null;

  elements.open.addEventListener('click', () => {
    newGame();
    showScreen('sudoku');
  });
  elements.leave.addEventListener('click', () => {
    stopTimer();
    showScreen('menu');
  });
  elements.fresh.addEventListener('click', newGame);
  elements.difficulties.addEventListener('click', (event) => {
    const button = (event.target as Element).closest<HTMLElement>('[data-difficulty]');
    if (!button || button.dataset.difficulty === difficulty) return;
    difficulty = button.dataset.difficulty;
    newGame();
  });
  document.addEventListener('keydown', handleKeydown);

  buildKeypad();

  function newGame() {
    stopTimer();
    ({ puzzle, solution } = createSudokuPuzzle(difficulty));
    values = [...puzzle];
    selected = firstEmptyCell();
    mistakes = 0;
    completed = false;
    cellEffect = null;
    revealBoard = true;
    elements.mistakes.textContent = '0';
    elapsed = 0;
    elements.time.textContent = '00:00';
    updateDifficultyButtons();
    setStatus(randomPhrase(PHRASES.ready));
    renderBoard();
    startTimer();
    void refreshLeaderboard();
  }

  function buildKeypad() {
    for (let number = 1; number <= 9; number += 1) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = String(number);
      button.setAttribute('aria-label', `Ввести ${number}`);
      button.addEventListener('click', () => enterValue(String(number)));
      elements.keypad.appendChild(button);
    }
    const erase = document.createElement('button');
    erase.type = 'button';
    erase.className = 'erase';
    erase.textContent = '⌫';
    erase.setAttribute('aria-label', 'Очистить клетку');
    erase.addEventListener('click', eraseValue);
    elements.keypad.appendChild(erase);
  }

  function renderBoard() {
    elements.board.replaceChildren();
    elements.board.classList.toggle('completed', completed);
    const selectedValue = selected === null ? '0' : values[selected];

    values.forEach((value, index) => {
      const row = Math.floor(index / 9);
      const col = index % 9;
      const cell = document.createElement('button');
      cell.type = 'button';
      cell.className = 'sudoku-cell';
      cell.style.setProperty('--cell-index', String(index));
      cell.setAttribute('role', 'gridcell');
      cell.setAttribute('aria-label', cellLabel(index, value));
      if (col === 2 || col === 5) cell.classList.add('box-right');
      if (row === 2 || row === 5) cell.classList.add('box-bottom');
      if (puzzle[index] !== '0') cell.classList.add('fixed');
      if (index === selected) cell.classList.add('selected');
      if (selected !== null && isRelated(index, selected)) cell.classList.add('related');
      if (selectedValue !== '0' && value === selectedValue) cell.classList.add('same-value');
      if (value !== '0' && value !== solution[index]) cell.classList.add('error');
      if (cellEffect?.index === index) cell.classList.add(cellEffect.type);
      if (revealBoard) cell.classList.add('appearing');
      cell.textContent = value === '0' ? '' : value;
      cell.addEventListener('click', () => selectCell(index));
      elements.board.appendChild(cell);
    });

    elements.keypad.querySelectorAll('button').forEach((button) => {
      button.disabled = completed;
    });
    revealBoard = false;
  }

  function selectCell(index) {
    selected = index;
    cellEffect = null;
    telegram?.HapticFeedback?.selectionChanged();
    renderBoard();
  }

  function enterValue(value) {
    if (completed || selected === null) return;
    if (puzzle[selected] !== '0') {
      setStatus('эта цифра уже была здесь, хозяин :3');
      return;
    }

    const previous = values[selected];
    values[selected] = value;
    if (value !== solution[selected]) {
      cellEffect = { index: selected, type: 'value-error' };
      if (previous !== value) {
        mistakes += 1;
        elements.mistakes.textContent = String(mistakes);
        replayClass(elements.mistakes, 'bump');
      }
      setStatus(randomPhrase(PHRASES.mistake), 'lose');
      telegram?.HapticFeedback?.notificationOccurred('error');
    } else {
      cellEffect = { index: selected, type: 'value-correct' };
      setStatus(randomPhrase(PHRASES.correct));
      telegram?.HapticFeedback?.selectionChanged();
    }

    if (values.every((cell, index) => cell === solution[index])) {
      completed = true;
      stopTimer();
      setStatus('всё сошлось! хозяин, ты настоящий гений, мяу :3', 'win');
      telegram?.HapticFeedback?.notificationOccurred('success');
      void submitLeaderboardScore({
        telegram,
        game: 'sudoku',
        difficulty,
        seconds: Math.max(1, elapsed),
        mistakes,
        element: elements.leaderboard,
      });
    }
    renderBoard();
  }

  function eraseValue() {
    if (completed || selected === null || puzzle[selected] !== '0') return;
    values[selected] = '0';
    cellEffect = { index: selected, type: 'value-erased' };
    setStatus('стёр лапкой, хозяин :3');
    renderBoard();
  }

  function handleKeydown(event) {
    if (!elements.screen.classList.contains('active')) return;
    if (/^[1-9]$/.test(event.key)) {
      enterValue(event.key);
      return;
    }
    if (event.key === 'Backspace' || event.key === 'Delete' || event.key === '0') {
      event.preventDefault();
      eraseValue();
      return;
    }
    const directions = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
    };
    if (directions[event.key] && selected !== null) {
      event.preventDefault();
      const row = Math.floor(selected / 9);
      const col = selected % 9;
      const [rowStep, colStep] = directions[event.key];
      const nextRow = Math.max(0, Math.min(8, row + rowStep));
      const nextCol = Math.max(0, Math.min(8, col + colStep));
      selected = nextRow * 9 + nextCol;
      renderBoard();
    }
  }

  function firstEmptyCell() {
    return [...puzzle].findIndex((value) => value === '0');
  }

  function updateDifficultyButtons() {
    elements.difficulties.querySelectorAll<HTMLElement>('[data-difficulty]').forEach((button) => {
      const selectedDifficulty = button.dataset.difficulty === difficulty;
      button.classList.toggle('selected', selectedDifficulty);
      button.setAttribute('aria-pressed', String(selectedDifficulty));
    });
  }

  function startTimer() {
    timer = window.setInterval(() => {
      elapsed = Math.min(86400, elapsed + 1);
      elements.time.textContent = formatGameTime(elapsed);
      if (elapsed === 86400) stopTimer();
    }, 1000);
  }

  function stopTimer() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
  }

  function refreshLeaderboard() {
    return loadLeaderboard({ telegram, game: 'sudoku', difficulty, element: elements.leaderboard });
  }

  function isRelated(left, right) {
    const leftRow = Math.floor(left / 9);
    const leftCol = left % 9;
    const rightRow = Math.floor(right / 9);
    const rightCol = right % 9;
    return leftRow === rightRow
      || leftCol === rightCol
      || (Math.floor(leftRow / 3) === Math.floor(rightRow / 3)
        && Math.floor(leftCol / 3) === Math.floor(rightCol / 3));
  }

  function cellLabel(index, value) {
    const row = Math.floor(index / 9) + 1;
    const col = index % 9 + 1;
    return `Строка ${row}, столбец ${col}: ${value === '0' ? 'пусто' : value}`;
  }

  function setStatus(text, state = '') {
    elements.status.textContent = text;
    elements.status.className = `status-bar${state ? ` ${state}` : ''}`;
    replayClass(elements.status, 'status-pop');
  }

  function replayClass(element, className) {
    element.classList.remove(className);
    void element.offsetWidth;
    element.classList.add(className);
  }
}
