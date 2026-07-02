"""Direct-image downloader for Cattemis Bot.

Downloads a single image from a direct HTTP(S) URL that ends in a known
image extension.  Produces a ``DownloadResult`` with one local temp file.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from ..utils.media import IMAGE_EXTS, guess_ext_from_content_type
from . import DownloadResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIRECT_TIMEOUT: float = 40.0


# ---------------------------------------------------------------------------
# Domain / path check
# ---------------------------------------------------------------------------

def is_direct_image(url: str) -> bool:
    """Return True if *url* path ends with a known image extension."""
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return False
    return any(path.endswith(ext) for ext in IMAGE_EXTS)


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

async def download_direct_image(url: str) -> DownloadResult:
    """Download a single image from *url* to a temporary file.

    Raises:
        aiohttp.ClientResponseError: On HTTP errors.
    """
    temp_dir = tempfile.mkdtemp(prefix="img_bot_")
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    timeout = aiohttp.ClientTimeout(total=DIRECT_TIMEOUT)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type")
                ext = path_ext if path_ext in IMAGE_EXTS else guess_ext_from_content_type(content_type, ".jpg")
                file_path = Path(temp_dir) / f"image{ext}"
                file_path.write_bytes(await resp.read())

        logger.debug("Downloaded direct image from %s → %s", url, file_path)
        return DownloadResult(files=[str(file_path)], caption=None, temp_dir=temp_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
