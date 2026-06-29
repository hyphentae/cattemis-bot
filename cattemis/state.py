import asyncio
from collections import deque
from dataclasses import dataclass

from aiogram.types import Message

from .config import (
    DEFAULT_PERSONA,
    LLM_HISTORY_TURNS,
    PERSONA_GOTH,
    PERSONA_NORMAL,
    PERSONA_PROMPTS,
)


@dataclass
class ChatSettings:
    persona: str = DEFAULT_PERSONA


_chat_locks: dict[int, asyncio.Lock] = {}
_chat_settings: dict[int, ChatSettings] = {}
_llm_history: dict[tuple[int, int], deque[dict[str, str]]] = {}


def get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


def get_chat_settings(chat_id: int) -> ChatSettings:
    settings = _chat_settings.get(chat_id)
    if settings is None:
        settings = ChatSettings()
        _chat_settings[chat_id] = settings
    return settings


def set_chat_persona(chat_id: int, persona: str) -> bool:
    persona = persona.strip().lower()
    if persona not in PERSONA_PROMPTS:
        return False
    get_chat_settings(chat_id).persona = persona
    return True


def persona_label(persona: str) -> str:
    if persona == PERSONA_GOTH:
        return "гот-режим"
    return "обычный режим"


def llm_context_key(message: Message) -> tuple[int, int]:
    return message.chat.id, message.message_thread_id or 0


def get_llm_history(key: tuple[int, int]) -> deque[dict[str, str]] | None:
    maxlen = LLM_HISTORY_TURNS * 2
    if maxlen <= 0:
        _llm_history.pop(key, None)
        return None

    history = _llm_history.get(key)
    if history is None or history.maxlen != maxlen:
        items = list(history or [])[-maxlen:]
        history = deque(items, maxlen=maxlen)
        _llm_history[key] = history
    return history


def current_persona(chat_id: int) -> str:
    persona = get_chat_settings(chat_id).persona
    if persona not in {PERSONA_NORMAL, PERSONA_GOTH}:
        return PERSONA_NORMAL
    return persona
