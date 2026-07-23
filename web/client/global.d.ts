interface TelegramHapticFeedback {
  impactOccurred(style: string): void;
  notificationOccurred(type: string): void;
  selectionChanged(): void;
}

interface TelegramWebApp {
  initData: string;
  HapticFeedback?: TelegramHapticFeedback;
  ready(): void;
  expand(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
}

interface Window {
  Telegram?: {
    WebApp?: TelegramWebApp;
    WebView?: {
      postEvent?(eventType: string, callback: boolean, eventData: Record<string, unknown>): void;
    };
  };
}
