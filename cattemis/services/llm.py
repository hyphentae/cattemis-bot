import asyncio
import re

from aiogram.types import Message

from ..config import (
    LLM_ENABLED,
    LLM_MAX_INPUT_CHARS,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_SYSTEM_PROMPT,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    PERSONA_NORMAL,
    PERSONA_PROMPTS,
)
from ..runtime import llm_client, llm_semaphore
from ..state import get_llm_history
from ..telegram_utils import get_bot_username

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)


def strip_unicode_emoji(text: str) -> str:
    return EMOJI_RE.sub("", text)


def cleanup_llm_text(text: str) -> str:
    text = strip_unicode_emoji(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" ?([,.;:!?]){2,}", r"\1", text)
    return text.strip()


def compact_llm_text(text: str, limit: int = LLM_MAX_INPUT_CHARS) -> str:
    text = re.sub(r"[ \t]{2,}", " ", (text or "").strip())
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def build_llm_system_prompt(persona: str) -> str:
    persona_prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS[PERSONA_NORMAL])
    return f"{LLM_SYSTEM_PROMPT}\n\n{persona_prompt}"


async def prepare_llm_text(message: Message, raw_text: str) -> str:
    text = raw_text or ""
    bot_username = await get_bot_username()
    if bot_username:
        text = re.sub(rf"@{re.escape(bot_username)}\b", "", text, flags=re.IGNORECASE)
    return compact_llm_text(text) or compact_llm_text(raw_text)


def build_llm_user_content(user_text: str, user_name: str | None = None) -> str:
    display_name = (user_name or "user").strip() or "user"
    return f"User name: {display_name}\nMessage: {compact_llm_text(user_text)}"


def remember_llm_exchange(
    key: tuple[int, int],
    user_content: str,
    assistant_text: str,
) -> None:
    history = get_llm_history(key)
    if history is None:
        return
    history.append({"role": "user", "content": user_content})
    history.append({"role": "assistant", "content": compact_llm_text(assistant_text, 1000)})


async def ask_llm(
    user_text: str,
    user_name: str | None = None,
    persona: str = PERSONA_NORMAL,
    history_key: tuple[int, int] | None = None,
) -> str:
    if not LLM_ENABLED or llm_client is None:
        return "LLM отключён."

    user_content = build_llm_user_content(user_text, user_name)
    messages = [{"role": "system", "content": build_llm_system_prompt(persona)}]

    if history_key is not None:
        history = get_llm_history(history_key)
        if history:
            messages.extend(history)

    messages.append({"role": "user", "content": user_content})

    async with llm_semaphore:
        response = await asyncio.wait_for(
            llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                extra_body={
                    "chat_template_kwargs": {
                        "enable_thinking": False,
                    }
                },
            ),
            timeout=LLM_TIMEOUT_SECONDS,
        )

    text = response.choices[0].message.content or ""
    text = cleanup_llm_text(text)
    if history_key is not None:
        remember_llm_exchange(history_key, user_content, text)
    return text or "..."
