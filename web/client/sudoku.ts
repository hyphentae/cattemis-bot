const BASE_PUZZLE = [
  '530070000',
  '600195000',
  '098000060',
  '800060003',
  '400803001',
  '700020006',
  '060000280',
  '000419005',
  '000080079',
].join('');

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

export function createSudokuPuzzle() {
  const digits = shuffle(['1', '2', '3', '4', '5', '6', '7', '8', '9']);
  const digitMap = new Map(digits.map((digit, index) => [String(index + 1), digit]));
  const remap = (grid) => [...grid].map((value) => value === '0' ? '0' : digitMap.get(value)).join('');
  let puzzle = remap(BASE_PUZZLE);
  let solution = remap(BASE_SOLUTION);
  const rotations = Math.floor(Math.random() * 4);
  for (let count = 0; count < rotations; count += 1) {
    puzzle = rotateGrid(puzzle);
    solution = rotateGrid(solution);
  }
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

  elements.open.addEventListener('click', () => {
    newGame();
    showScreen('sudoku');
  });
  elements.leave.addEventListener('click', () => showScreen('menu'));
  elements.fresh.addEventListener('click', newGame);
  document.addEventListener('keydown', handleKeydown);

  buildKeypad();

  function newGame() {
    ({ puzzle, solution } = createSudokuPuzzle());
    values = [...puzzle];
    selected = firstEmptyCell();
    mistakes = 0;
    completed = false;
    cellEffect = null;
    revealBoard = true;
    elements.mistakes.textContent = '0';
    setStatus(randomPhrase(PHRASES.ready));
    renderBoard();
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
      setStatus('всё сошлось! хозяин, ты настоящий гений, мяу :3', 'win');
      telegram?.HapticFeedback?.notificationOccurred('success');
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
