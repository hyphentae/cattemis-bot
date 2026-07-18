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

function callNative(nativeFeedback, method, value?) {
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

function callTelegramBridge(type, value?) {
  const postEvent = window.Telegram?.WebView?.postEvent;
  if (typeof postEvent !== 'function') return false;
  const payload: Record<string, unknown> = { type };
  if (type === 'impact') payload.impact_style = value;
  if (type === 'notification') payload.notification_type = value;
  try {
    postEvent.call(window.Telegram.WebView, 'web_app_trigger_haptic_feedback', false, payload);
    return true;
  } catch {
    return false;
  }
}

export function createHapticFeedback(nativeFeedback) {
  const hapticFeedback = {
    impactOccurred(style = 'light') {
      if (!callNative(nativeFeedback, 'impactOccurred', style)
        && !callTelegramBridge('impact', style)
        && canVibrate()) vibrate(IMPACT_PATTERNS[style] ?? IMPACT_PATTERNS.light);
      return hapticFeedback;
    },
    notificationOccurred(type) {
      if (!callNative(nativeFeedback, 'notificationOccurred', type)
        && !callTelegramBridge('notification', type)
        && canVibrate()) vibrate(NOTIFICATION_PATTERNS[type] ?? NOTIFICATION_PATTERNS.warning);
      return hapticFeedback;
    },
    selectionChanged() {
      if (!callNative(nativeFeedback, 'selectionChanged')
        && !callTelegramBridge('selection_change')
        && canVibrate()) vibrate(8);
      return hapticFeedback;
    },
  };

  return hapticFeedback;
}
