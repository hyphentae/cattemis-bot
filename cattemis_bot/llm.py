"""LLM chat integration for Cattemis Bot.

Wraps an OpenAI-compatible API (Ollama by default) with:
- Per-request cooldown to avoid spamming the backend.
- Per-chat message history trimming.
- Output post-processing (emoji removal, kaomoji repair).
- Optional media_context (Whisper transcriptions) injected into the user turn.
- Optional agent loop with a model-selected web-search tool.

The ``ask_llm`` coroutine is the single public interface.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openai import AsyncOpenAI

from .config import settings
from .state import state
from .utils.text import repair_truncated_kaomoji, strip_protocol_markers
from .web_search import format_search_context, search_web

logger = logging.getLogger(__name__)

_WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the internet for current or niche information. Use this "
            "when the answer may have changed, needs sources, or is not known. "
            "Do not use it for casual conversation or stable general knowledge."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A precise search query in the user's language.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}

MAX_AGENT_STEPS = 3


def strip_model_control_tokens(text: str) -> str:
    """Remove leaked chat-template control markers while preserving content."""
    text = re.sub(r"<\|channel\|>\s*", "", text)
    text = re.sub(r"<channel\|>\s*", "", text)
    text = re.sub(r"<\|(?:im_start|im_end|end|eot|assistant|user|system)\|>", "", text)
    text = re.sub(r"</?(?:analysis|think)>\s*", "", text, flags=re.IGNORECASE)
    return text


def current_time_context() -> str:
    """Return the current local date/time for the model's system context."""
    timezone_name = settings.llm_timezone
    try:
        now = datetime.now(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        logger.warning("[llm] unknown timezone %r, falling back to UTC", timezone_name)
        now = datetime.now(ZoneInfo("UTC"))
        timezone_name = "UTC"
    return (
        f"Текущая дата и время: {now:%Y-%m-%d %H:%M} ({timezone_name}). "
        "Используй это как сегодняшнюю дату и не утверждай, что сейчас 2025 год."
    )

# ---------------------------------------------------------------------------
# Client singleton (None when LLM is disabled)
# ---------------------------------------------------------------------------

_llm_client: AsyncOpenAI | None = (
    AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_request_timeout_seconds,
        max_retries=0,
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
    image_data_url: str | None = None,
) -> str:
    """Send *user_text* to the LLM and return the assistant reply.

    Args:
        chat_id:       Telegram chat id (used for per-chat history).
        user_text:     The user's message text.
        user_name:     Display name prepended to the user turn.
        media_context: Optional transcription of attached audio/video.
        image_data_url: Optional image encoded as a data URL for multimodal models.

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

    user_message_content: str | list[dict[str, object]] = user_content
    if image_data_url:
        user_message_content = [
            {"type": "text", "text": user_content},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]

    system_prompt = f"{settings.llm_system_prompt}\n\n{current_time_context()}"
    if settings.llm_web_search_enabled:
        system_prompt += (
            "У тебя есть инструмент web_search. Если пользователь спрашивает о том, чего ты не знаешь, сначала обязатеьлно вызови web_search и отвечай по его результатам. Если тебя спрашивают то, чего ты не знаешь, или просят найти что то актуальное, или что то в интернете, обязательно используй web_search. "
        )

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message_content},
    ]

    await asyncio.sleep(settings.llm_cooldown_seconds)

    tools = [_WEB_SEARCH_TOOL] if settings.llm_web_search_enabled else None
    logger.info("[llm] web_search_tool=%s model=%s chat_id=%s", bool(tools), settings.llm_model, chat_id)
    response = None
    for step in range(MAX_AGENT_STEPS):
        try:
            response = await _llm_client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None,
            )
        except Exception as exc:
            if tools and step == 0:
                logger.warning("[llm] request with tools failed, retrying without tools: %s", exc)
                tools = None
                continue
            raise

        if not response.choices:
            logger.warning("[llm] empty choices from model, chat_id=%s", chat_id)
            return "..."

        choice = response.choices[0]
        logger.info(
            "[llm] finish_reason=%r step=%d chat_id=%s",
            choice.finish_reason,
            step + 1,
            chat_id,
        )
        tool_calls = list(choice.message.tool_calls or []) if choice.message else []
        if not tool_calls:
            break

        messages.append(
            {
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [call.model_dump(exclude_none=True) for call in tool_calls],
            }
        )
        for call in tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
                query = str(arguments.get("query", "")).strip()
                results = await search_web(query, settings.llm_web_search_max_results)
                tool_content = format_search_context(results)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.warning("[llm] invalid web_search arguments: %s", exc)
                tool_content = "Не удалось разобрать запрос поиска. Попробуй сформулировать его иначе."
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": "web_search",
                    "content": tool_content,
                }
            )
    else:
        logger.warning("[llm] agent step limit reached, chat_id=%s", chat_id)

    if response is None or not response.choices:
        return "..."

    choice = response.choices[0]
    text = (choice.message.content or "") if choice.message else ""
    text = strip_protocol_markers(text)
    text = strip_model_control_tokens(text)
    text = repair_truncated_kaomoji(text)

    state.append_history(chat_id, "user", user_content, max_messages=settings.max_history_messages)
    state.append_history(chat_id, "assistant", text or "...", max_messages=settings.max_history_messages)

    return text or "..."
