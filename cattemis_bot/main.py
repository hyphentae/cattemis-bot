"""Entry point for Cattemis Bot.

Run from the folder that *contains* cattemis_bot/:

    python -m cattemis_bot.main

Or use the run.py launcher placed next to the cattemis_bot/ folder:

    python run.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import settings
from .state import state

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bot / Dispatcher singletons
# ---------------------------------------------------------------------------

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------

_BANNER = """\
┌──────────────────────────────────────────────┐
│   🐾 Cattemis bot started! Meow meow meow    │
└──────────────────────────────────────────────┘"""

# ---------------------------------------------------------------------------
# Startup hook
# ---------------------------------------------------------------------------

async def _on_startup() -> None:
    """Populate bot identity cache on startup."""
    me = await bot.get_me()
    state.bot_username = (me.username or "").lower()
    state.bot_id = me.id
    logger.info("Bot identity: @%s (id=%s)", state.bot_username, state.bot_id)
    if settings.llm_enabled:
        logger.info(
            "LLM enabled — base_url=%s model=%s cooldown=%.1fs",
            settings.llm_base_url,
            settings.llm_model,
            settings.llm_cooldown_seconds,
        )
    else:
        logger.info("LLM disabled")
# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

def _register_routers() -> None:
    """Import and include all handler routers onto the Dispatcher."""
    from .handlers.commands import router as commands_router
    from .handlers.media import router as media_router

    dp.include_router(commands_router)
    dp.include_router(media_router)
# ---------------------------------------------------------------------------
# Main coroutine
# ---------------------------------------------------------------------------

async def main() -> None:
    """Initialise and run the bot."""
    print(_BANNER)
    _register_routers()
    dp.startup.register(_on_startup)
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
