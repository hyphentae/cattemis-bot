function gameAuthToken() {
  return new URLSearchParams(window.location.hash.slice(1)).get('game_auth') ?? '';
}

export function hasTelegramAuth(telegram) {
  return Boolean(telegram?.initData || gameAuthToken());
}

export function telegramAuthHeaders(telegram) {
  if (telegram?.initData) return { 'X-Telegram-Init-Data': telegram.initData };
  const token = gameAuthToken();
  return token ? { 'X-Telegram-Game-Auth': token } : {};
}
