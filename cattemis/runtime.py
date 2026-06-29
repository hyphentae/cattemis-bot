import asyncio

from aiogram import Bot, Dispatcher
from openai import AsyncOpenAI

from .config import (
    BOT_TOKEN,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_CONCURRENCY,
    LLM_ENABLED,
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

llm_client = (
    AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
    )
    if LLM_ENABLED
    else None
)
llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
