"""Entry point for Cattemis Bot."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo

from .config import settings
from .state import state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

_BANNER = """\
┌──────────────────────────────────────────────┐
│   🐾 Cattemis bot started! Meow meow meow    │
└──────────────────────────────────────────────┘"""


async def _on_startup() -> None:
    me = await bot.get_me()
    state.bot_username = (me.username or "").lower()
    state.bot_id = me.id
    logger.info("Bot identity: @%s (id=%s)", state.bot_username, state.bot_id)
    if settings.llm_enabled:
        logger.info(
            "LLM enabled — base_url=%s model=%s cooldown=%.1fs",
            settings.llm_base_url, settings.llm_model, settings.llm_cooldown_seconds,
        )
    else:
        logger.info("LLM disabled")

    if settings.use_cloudflare:
        from .tunnel import wait_for_tunnel_url
        url = await wait_for_tunnel_url(timeout=60)
        if url:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Открыть",
                    web_app=WebAppInfo(url=url),
                )
            )
            logger.info("[tunnel] Mini App button set to %s", url)


def _register_routers() -> None:
    from .handlers.commands import router as commands_router
    from .handlers.games import router as games_router
    from .handlers.tictactoe import router as ttt_router
    from .handlers.checkers import router as checkers_router
    from .handlers.media import router as media_router

    dp.include_router(commands_router)
    dp.include_router(games_router)
    dp.include_router(ttt_router)
    dp.include_router(checkers_router)
    dp.include_router(media_router)


async def main() -> None:
    print(_BANNER)
    _register_routers()
    dp.startup.register(_on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
