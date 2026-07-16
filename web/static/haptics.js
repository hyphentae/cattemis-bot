const IMPACT_PATTERNS = {
  light: 10,
  medium: 20,
  heavy: 55,
  rigid: [12, 8, 12],
  soft: 8,
};

const NOTIFICATION_PATTERNS = {
  success: [12, 28, 18],
  warning: [22, 28, 22],
  error: [30, 35, 30],
};

function vibrate(pattern) {
  try {
    navigator.vibrate?.(pattern);
  } catch {
    // iOS and some Telegram WebViews do not expose the Vibration API.
  }
}

function canVibrate() {
  return typeof navigator.vibrate === 'function';
}

function callNative(nativeFeedback, method, value) {
  const callback = nativeFeedback?.[method];
  if (typeof callback !== 'function') return false;
  try {
    callback.call(nativeFeedback, value);
    return true;
  } catch {
    // Keep the browser vibration fallback available on older clients.
    return false;
  }
}

export function createHapticFeedback(nativeFeedback) {
  const hapticFeedback = {
    impactOccurred(style = 'light') {
      if (canVibrate()) vibrate(IMPACT_PATTERNS[style] ?? IMPACT_PATTERNS.light);
      else callNative(nativeFeedback, 'impactOccurred', style);
      return hapticFeedback;
    },
    notificationOccurred(type) {
      if (canVibrate()) vibrate(NOTIFICATION_PATTERNS[type] ?? NOTIFICATION_PATTERNS.warning);
      else callNative(nativeFeedback, 'notificationOccurred', type);
      return hapticFeedback;
    },
    selectionChanged() {
      if (canVibrate()) vibrate(8);
      else callNative(nativeFeedback, 'selectionChanged');
      return hapticFeedback;
    },
  };

  return hapticFeedback;
}
