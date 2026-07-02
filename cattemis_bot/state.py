"""Global mutable state for Cattemis Bot.

A single ``BotState`` instance is created at import time and shared across
all modules via ``from .state import state``.  No ``global``
keyword is used anywhere in the project; all mutations go through this object.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import TypeAlias

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ChatHistory: TypeAlias = list[dict[str, str]]
AdminCache: TypeAlias = dict[int, tuple[float, set[int]]]


# ---------------------------------------------------------------------------
# BotState
# ---------------------------------------------------------------------------

@dataclass
class BotState:
    """Container for all runtime state of the bot."""

    # Uptime tracking
    started_at: float = field(default_factory=time.time)

    # Counters
    messages_total: int = 0
    commands_used: int = 0
    llm_calls: int = 0
    llm_errors: int = 0
    media_total: int = 0
    media_errors: int = 0
    tiktok_downloads: int = 0
    instagram_downloads: int = 0
    twitter_downloads: int = 0
    direct_image_downloads: int = 0
    ytdlp_downloads: int = 0

    # Sets / dicts
    unique_chats: set[int] = field(default_factory=set)
    admin_cache: AdminCache = field(default_factory=dict)
    chat_locks: dict[int, asyncio.Lock] = field(default_factory=dict)
    chat_histories: dict[int, ChatHistory] = field(default_factory=dict)

    # Bot identity (populated on startup)
    bot_username: str | None = None
    bot_id: int | None = None

    # API rate-limiting (shared across downloaders)
    api_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_api_call: float = 0.0

    # Artists list (populated on startup)
    artists: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Counter helpers
    # ------------------------------------------------------------------

    def inc(self, key: str, value: int = 1) -> None:
        """Increment an integer counter by *value*."""
        current = getattr(self, key, 0)
        setattr(self, key, current + value)

    def track_chat(self, chat_id: int) -> None:
        """Record *chat_id* as having been seen."""
        self.unique_chats.add(chat_id)

    # ------------------------------------------------------------------
    # Per-chat lock helpers
    # ------------------------------------------------------------------

    def get_lock(self, chat_id: int) -> asyncio.Lock:
        """Return (creating if necessary) the asyncio.Lock for *chat_id*."""
        if chat_id not in self.chat_locks:
            self.chat_locks[chat_id] = asyncio.Lock()
        return self.chat_locks[chat_id]

    # ------------------------------------------------------------------
    # Per-chat history helpers
    # ------------------------------------------------------------------

    def get_history(self, chat_id: int) -> ChatHistory:
        """Return the message history list for *chat_id*."""
        if chat_id not in self.chat_histories:
            self.chat_histories[chat_id] = []
        return self.chat_histories[chat_id]

    def append_history(self, chat_id: int, role: str, content: str, max_messages: int = 8) -> None:
        """Append a message to the history, trimming to *max_messages*."""
        history = self.get_history(chat_id)
        history.append({"role": role, "content": content})
        if len(history) > max_messages:
            self.chat_histories[chat_id] = history[-max_messages:]

    def clear_history(self, chat_id: int) -> None:
        """Remove all history entries for *chat_id*."""
        self.chat_histories.pop(chat_id, None)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

state = BotState()
