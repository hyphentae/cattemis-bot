import asyncio
import os
import uvicorn
from cattemis_bot.main import main
from web.app import create_app

WEB_ENABLED = os.getenv("WEB_ENABLED", "true").lower() == "true"

if WEB_ENABLED:
    async def run_all():
        app = create_app()
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await asyncio.gather(main(), server.serve())

    asyncio.run(run_all())
else:
    asyncio.run(main())
