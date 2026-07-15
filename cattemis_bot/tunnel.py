"""Read tunnel URL written by cloudflared container."""
import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

TUNNEL_FILE = Path(os.getenv("TUNNEL_FILE", "/tunnel/url.txt"))


async def wait_for_tunnel_url(timeout: float = 60.0) -> str | None:
    """Poll TUNNEL_FILE until cloudflared writes the URL or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if TUNNEL_FILE.exists():
            url = TUNNEL_FILE.read_text().strip()
            if url.startswith("https://"):
                logger.info("[tunnel] URL: %s", url)
                return url
        await asyncio.sleep(1)
    logger.warning("[tunnel] timed out waiting for URL")
    return None
