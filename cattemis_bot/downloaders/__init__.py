"""Downloaders sub-package for Cattemis Bot.

Exports the shared ``DownloadResult`` dataclass and the ``with_retry`` /
``is_retryable`` helpers used by every individual downloader module.
"""

import asyncio
import shutil
from dataclasses import dataclass

import aiohttp

from ..config import settings

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class DownloadResult:
    """Holds files produced by a downloader along with optional metadata.

    Call ``cleanup()`` when the files are no longer needed to remove the
    temporary directory.
    """

    files: list[str]
    caption: str | None = None
    temp_dir: str | None = None

    def cleanup(self) -> None:
        """Remove the temporary directory and all its contents."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

# Markers in exception messages that indicate a transient failure
_RETRY_TEXT_MARKERS: tuple[str, ...] = (
    "timed out",
    "timeout",
    "temporarily unavailable",
    "connection reset",
    "server disconnected",
    "too many requests",
    "http 429",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
)

# HTTP status codes that warrant a retry
_RETRY_HTTP_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def is_retryable(exc: Exception) -> bool:
    """Return True if *exc* represents a transient error worth retrying."""
    if isinstance(exc, asyncio.TimeoutError):
        return True

    if isinstance(
        exc,
        (
            aiohttp.ClientConnectionError,
            aiohttp.ClientPayloadError,
            aiohttp.ServerDisconnectedError,
            aiohttp.ClientOSError,
        ),
    ):
        return True

    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status in _RETRY_HTTP_STATUSES

    text = str(exc).lower()
    return any(marker in text for marker in _RETRY_TEXT_MARKERS)


async def with_retry(func, /, *args, attempts: int | None = None, delay: float | None = None, **kwargs):
    """Call *func* with *args*/*kwargs*, retrying on transient errors.

    Args:
        func: Async callable to invoke.
        attempts: Maximum attempts (defaults to ``settings.retry_attempts``).
        delay: Seconds to wait between attempts (defaults to ``settings.retry_delay``).

    Raises:
        The last exception if all attempts fail.
    """
    max_attempts = attempts if attempts is not None else settings.retry_attempts
    wait = delay if delay is not None else settings.retry_delay
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts or not is_retryable(exc):
                raise
            await asyncio.sleep(wait)

    raise last_error  # type: ignore[misc]


__all__ = ["DownloadResult", "is_retryable", "with_retry"]
