from . import handlers  # noqa: F401
from .config import LLM_BASE_URL, LLM_ENABLED, LLM_MODEL
from .runtime import bot, dp
from .services.artists import load_artists_config


async def main():
    print("🐾 Бот запущен! :3")
    load_artists_config()

    if LLM_ENABLED:
        print(f"[llm] enabled, base_url={LLM_BASE_URL}, model={LLM_MODEL}")
    else:
        print("[llm] disabled")

    await dp.start_polling(bot)
