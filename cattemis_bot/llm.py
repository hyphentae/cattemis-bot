"""LLM chat integration for Cattemis Bot.

Wraps an OpenAI-compatible API (Ollama by default) with:
- Per-request cooldown to avoid spamming the backend.
- Per-chat message history trimming.
- Output post-processing (emoji removal, kaomoji repair).
- Optional media_context (Whisper transcriptions) injected into the user turn.

The ``ask_llm`` coroutine is the single public interface.
"""

import asyncio
import logging

from openai import AsyncOpenAI

from .config import settings
from .state import state
from .utils.text import cleanup_llm_text, fix_truncated_kaomoji

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton (None when LLM is disabled)
# ---------------------------------------------------------------------------

_llm_client: AsyncOpenAI | None = (
    AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )
    if settings.llm_enabled
    else None
)

# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def human_instagram_api_error(error: Exception) -> str:
    """Map an Instagram/Apify error to a friendly Russian message."""
    text = str(error).lower()
    if "apify_token" in text:
        return "П-простите, хозяин... APIFY_TOKEN не задан... T_T"
    if "http 401" in text or "http 403" in text:
        return "П-простите, хозяин... Apify не принял токен... T_T"
    if "http 402" in text:
        return "Хозяин... у Apify, похоже, закончился баланс или лимит... T_T"
    if "не вернул результатов" in text:
        return "Хозяин... Apify ничего не нашёл по этой ссылке... простите... T_T"
    if "не вернул прямые ссылки" in text:
        return "Хозяин... Apify обработал ссылку, но не отдал прямые ссылки на медиа... T_T"
    if "не удалось скачать медиафайлы" in text:
        return "Хозяин... ссылки достать получилось, н-но сами файлы скачать не вышло... T_T"
    if "timed out" in text:
        return "Хозяин... Instagram через Apify отвечает слишком долго... попробуйте ещё разочек... T_T"
    return "П-простите, хозяин... не получилось скачать Instagram через Apify... T_T"


def human_twitter_error(error: Exception) -> str:
    """Map a Twitter/X download error to a friendly Russian message."""
    text = str(error).lower()
    if "распарсить ссылку" in text:
        return "П-простите, хозяин... я не понял ссылку на пост... T_T"
    if "не вернул медиа" in text:
        return "Хозяин... в этом посте не нашлось медиа... T_T"
    if "404" in text:
        return "Хозяин... пост не найден или его уже удалили... T_T"
    if "403" in text:
        return "П-простите, хозяин... твиттер не отдал данные по этому посту... (¬_¬)"
    if "timed out" in text:
        return "Хозяин... твиттер отвечает слишком долго... попробуйте ещё разочек... (¬_¬)"
    return "П-простите, хозяин... не получилось скачать медиа из твиттера... T_T"


# ---------------------------------------------------------------------------
# Core LLM call
# ---------------------------------------------------------------------------

async def ask_llm(
    chat_id: int,
    user_text: str,
    user_name: str | None = None,
    media_context: str | None = None,
) -> str:
    """Send *user_text* to the LLM and return the assistant reply.

    Args:
        chat_id:       Telegram chat id (used for per-chat history).
        user_text:     The user's message text.
        user_name:     Display name prepended to the user turn.
        media_context: Optional transcription of attached audio/video.

    Returns:
        The cleaned assistant reply, or ``"..."`` if the model returned nothing.
    """
    if not settings.llm_enabled or _llm_client is None:
        return "LLM отключён."

    display_name = (user_name or "user").strip() or "user"
    history = state.get_history(chat_id)

    if media_context:
        user_content = f"{display_name}: {user_text}\n\nОписание медиа:\n{media_context}"
    else:
        user_content = f"{display_name}: {user_text}"

    messages = [
        {"role": "system", "content": settings.llm_system_prompt},
        *history,
        {"role": "user", "content": user_content},
    ]

    await asyncio.sleep(settings.llm_cooldown_seconds)

    response = await _llm_client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    if not response.choices:
        logger.warning("[llm] empty choices from model, chat_id=%s", chat_id)
        return "..."

    choice = response.choices[0]
    logger.info("[llm] finish_reason=%r chat_id=%s", choice.finish_reason, chat_id)

    text = (choice.message.content or "") if choice.message else ""
    text = cleanup_llm_text(text)
    text = fix_truncated_kaomoji(text)

    state.append_history(chat_id, "user", user_content, max_messages=settings.max_history_messages)
    state.append_history(chat_id, "assistant", text or "...", max_messages=settings.max_history_messages)

    return text or "..."
