"""TikTok downloader for Cattemis Bot.

Uses the TikWM public API to retrieve video/image data for a TikTok URL.
The returned dict is consumed directly by the media handler (no temp files —
Telegram can accept direct URLs for TikTok content).
"""

import logging

import aiohttp

from ..state import state

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIKWM_API_URL: str = "https://www.tikwm.com/api/"
TIKWM_TIMEOUT: float = 40.0
TIKWM_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

TIKTOK_DOMAINS: frozenset[str] = frozenset(
    {
        "tiktok.com",
        "www.tiktok.com",
        "m.tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
    }
)


# ---------------------------------------------------------------------------
# Domain check
# ---------------------------------------------------------------------------

def is_tiktok(url: str) -> bool:
    """Return True if *url* belongs to a TikTok domain."""
    from urllib.parse import urlparse

    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return _host_matches(host, TIKTOK_DOMAINS)


def _host_matches(host: str, allowed: frozenset[str]) -> bool:
    host = (host or "").lower()
    return any(host == item or host.endswith("." + item) for item in allowed)


# ---------------------------------------------------------------------------
# Rate-limit helper (shared via state)
# ---------------------------------------------------------------------------

async def _rate_limit() -> None:
    """Ensure at least 1.1 s between TikWM API calls."""
    import time

    async with state.api_lock:
        now = __import__("time").monotonic()
        diff = now - state.last_api_call
        if diff < 1.1:
            await __import__("asyncio").sleep(1.1 - diff)
        state.last_api_call = __import__("time").monotonic()


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

async def download_tiktok(url: str) -> dict:
    """Fetch TikTok media data via TikWM API.

    Returns:
        The ``data`` sub-dict from the TikWM JSON response.

    Raises:
        RuntimeError: If the API reports an error or returns no data.
    """
    await _rate_limit()

    timeout = aiohttp.ClientTimeout(total=TIKWM_TIMEOUT)
    headers = {"User-Agent": TIKWM_USER_AGENT}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.post(TIKWM_API_URL, data={"url": url, "hd": 1}) as resp:
            resp.raise_for_status()
            payload = await resp.json(content_type=None)

    if payload.get("code") != 0 or not payload.get("data"):
        raise RuntimeError(payload.get("msg") or "TikWM не вернул данные")

    logger.debug("TikWM response for %s: code=%s", url, payload.get("code"))
    return payload["data"]
