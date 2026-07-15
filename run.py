import asyncio
import os
import re
import subprocess
import uvicorn
from aiogram.types import MenuButtonWebApp, WebAppInfo
from cattemis_bot.main import main, bot
from web.app import create_app

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"
WEB_PORT = int(os.getenv("WEB_PORT", "8080"))
USE_CLOUDFLARE = os.getenv("USE_CLOUDFLARE", "true").lower() == "true"


async def start_cloudflared_and_set_button() -> subprocess.Popen | None:
    """Start cloudflared quick tunnel, parse URL, set Mini App button."""
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{WEB_PORT}"],
        stderr=subprocess.PIPE,
        text=True,
    )
    url = None
    for line in proc.stderr:
        match = re.search(r"https://[\w-]+\.trycloudflare\.com", line)
        if match:
            url = match.group(0)
            break

    if url:
        print(f"[cloudflared] tunnel URL: {url}")
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть",
                web_app=WebAppInfo(url=url),
            )
        )
        print(f"[cloudflared] Mini App button set to {url}")
    else:
        print("[cloudflared] failed to get tunnel URL")

    return proc


if WEB_ENABLED:
    async def run_all():
        app = create_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=WEB_PORT, log_level="info")
        server = uvicorn.Server(config)

        cf_proc = None
        if USE_CLOUDFLARE:
            cf_proc = await start_cloudflared_and_set_button()

        try:
            await asyncio.gather(main(), server.serve())
        finally:
            if cf_proc:
                cf_proc.terminate()

    asyncio.run(run_all())
else:
    asyncio.run(main())
