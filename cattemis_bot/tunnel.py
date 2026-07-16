"""Read tunnel URL written by cloudflared container."""
import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

TUNNEL_FILE = Path(os.getenv("TUNNEL_FILE", "/tunnel/url.txt"))


def current_tunnel_url() -> str | None:
    """Return the tunnel URL currently published by cloudflared."""
    try:
        url = TUNNEL_FILE.read_text().strip()
    except OSError:
        return None
    return url if url.startswith("https://") else None


async def wait_for_tunnel_url(timeout: float = 60.0) -> str | None:
    """Poll TUNNEL_FILE until cloudflared writes the URL or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if TUNNEL_FILE.exists():
            try:
                url = current_tunnel_url()
                if url:
                    logger.info("[tunnel] URL: %s", url)
                    return url
            except OSError as exc:
                logger.debug("[tunnel] URL file changed while reading: %s", exc)
        await asyncio.sleep(1)
    logger.warning("[tunnel] timed out waiting for URL")
    return None
