import { hasTelegramAuth, telegramAuthHeaders } from './telegram-auth.ts';

export function formatGameTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`;
}

export async function loadLeaderboard({ telegram, game, difficulty, element }) {
  if (!hasTelegramAuth(telegram)) {
    renderMessage(element, 'открой игру через Telegram, чтобы увидеть рекорды');
    return [];
  }

  renderMessage(element, 'загружаю рекорды...');
  try {
    const params = new URLSearchParams({ game, difficulty });
    const response = await fetch(`/api/leaderboard?${params}`, {
      headers: telegramAuthHeaders(telegram),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'не удалось загрузить рекорды');
    renderEntries(element, payload.entries || [], game);
    return payload.entries || [];
  } catch (error) {
    renderMessage(element, error instanceof Error ? error.message : 'не удалось загрузить рекорды');
    return [];
  }
}

export async function submitLeaderboardScore({ telegram, game, difficulty, seconds, mistakes = 0, element }) {
  if (!hasTelegramAuth(telegram)) return [];
  try {
    const response = await fetch('/api/leaderboard', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...telegramAuthHeaders(telegram) },
      body: JSON.stringify({ game, difficulty, seconds, mistakes }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'не удалось сохранить рекорд');
    renderEntries(element, payload.entries || [], game);
    return payload.entries || [];
  } catch (error) {
    renderMessage(element, error instanceof Error ? error.message : 'не удалось сохранить рекорд');
    return [];
  }
}

function renderEntries(element, entries, game) {
  element.replaceChildren();
  if (!entries.length) {
    renderMessage(element, 'пока рекордов нет — стань первым :3');
    return;
  }
  const list = document.createElement('ol');
  list.className = 'leaderboard-list';
  entries.forEach((entry) => {
    const item = document.createElement('li');
    const name = document.createElement('span');
    const score = document.createElement('strong');
    name.textContent = entry.name;
    score.textContent = formatGameTime(entry.seconds);
    if (game === 'sudoku' && entry.mistakes) score.textContent += ` · ${entry.mistakes} ош.`;
    item.append(name, score);
    list.appendChild(item);
  });
  element.appendChild(list);
}

function renderMessage(element, message) {
  element.replaceChildren();
  const text = document.createElement('p');
  text.className = 'leaderboard-message';
  text.textContent = message;
  element.appendChild(text);
}
