"""Launcher — place this file next to the cattemis_bot/ folder and run:

    python run.py

To run WITHOUT web interface:
    WEB_ENABLED=false python run.py
"""
import asyncio
import os

from cattemis_bot.main import main

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"

if WEB_ENABLED:
    import uvicorn
    from web.app import create_app

    async def run_all():
        app = create_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await asyncio.gather(
            main(),
            server.serve(),
        )

    asyncio.run(run_all())
else:
    asyncio.run(main())
