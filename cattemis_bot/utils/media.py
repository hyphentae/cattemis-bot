"""Media-type detection and local-file sending utilities.

Provides:
- Extension / content-type sets and lookup tables.
- ``guess_ext_from_content_type`` — map a MIME type to a file extension.
- ``send_local_media`` — send one or more local files to a Telegram chat.
"""

import logging
from pathlib import Path

from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from .telegram import tg_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMAGE_EXTS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp"})
VIDEO_EXTS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv", ".webm", ".m4v"})
AUDIO_EXTS: frozenset[str] = frozenset({".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac"})
MEDIA_EXTS: frozenset[str] = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

MEDIA_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
}

MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB — Telegram upload limit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def guess_ext_from_content_type(content_type: str | None, fallback: str = ".jpg") -> str:
    """Return a file extension for *content_type*, or *fallback* if unknown."""
    if not content_type:
        return fallback
    mime = content_type.split(";")[0].strip().lower()
    return MEDIA_CONTENT_TYPES.get(mime, fallback)


def _check_file_size(path: str) -> bool:
    """Return True if *path* is within the Telegram file-size limit."""
    size = Path(path).stat().st_size
    if size > MAX_FILE_SIZE:
        logger.warning("File %s is %.1f MB — exceeds Telegram 50 MB limit", path, size / 1_048_576)
        return False
    return True


async def send_local_media(
    message: Message,
    files: list[str],
    caption: str | None = None,
) -> None:
    """Send one or more local media files as a Telegram message.

    - Single file: sent as photo / video / audio / document depending on extension.
    - Multiple files: photos and videos are grouped into a media album; audio
      and other formats are sent individually.
    - Files larger than ``MAX_FILE_SIZE`` are skipped with a warning.
    """
    files = files[:10]
    if not files:
        raise RuntimeError("Нет файлов для отправки")

    caption_text: str | None = (caption or "").strip()[:1024] or None

    # Filter out oversized files
    valid_files: list[str] = []
    for path in files:
        if _check_file_size(path):
            valid_files.append(path)
        else:
            await tg_call(
                message.answer,
                f"Хозяин, файл слишком большой для Telegram (>50 MB) и пропущен.",
            )

    if not valid_files:
        raise RuntimeError("Все файлы превышают лимит Telegram 50 MB")

    if len(valid_files) == 1:
        await _send_single(message, valid_files[0], caption_text)
        return

    await _send_album(message, valid_files, caption_text)


async def _send_single(message: Message, path: str, caption: str | None) -> None:
    """Send a single local file to *message*."""
    ext = Path(path).suffix.lower()

    if ext in IMAGE_EXTS:
        await tg_call(message.answer_photo, FSInputFile(path), caption=caption)
    elif ext in VIDEO_EXTS:
        await tg_call(
            message.answer_video,
            FSInputFile(path),
            caption=caption,
            supports_streaming=True,
        )
    elif ext in AUDIO_EXTS:
        await tg_call(message.answer_audio, FSInputFile(path), caption=caption)
    else:
        await tg_call(message.answer_document, FSInputFile(path), caption=caption)


async def _send_album(message: Message, files: list[str], caption: str | None) -> None:
    """Send multiple local files as a media album + individual leftovers."""
    album: list[InputMediaPhoto | InputMediaVideo] = []
    leftovers: list[str] = []

    for i, path in enumerate(files):
        ext = Path(path).suffix.lower()
        item_caption = caption if i == 0 and caption else None

        if ext in IMAGE_EXTS:
            album.append(InputMediaPhoto(media=FSInputFile(path), caption=item_caption))
        elif ext in VIDEO_EXTS:
            album.append(InputMediaVideo(media=FSInputFile(path), caption=item_caption))
        else:
            leftovers.append(path)

    if album:
        await tg_call(message.answer_media_group, media=album)

    for i, path in enumerate(leftovers):
        ext = Path(path).suffix.lower()
        item_caption = caption if not album and i == 0 else None

        if ext in AUDIO_EXTS:
            await tg_call(message.answer_audio, FSInputFile(path), caption=item_caption)
        else:
            await tg_call(message.answer_document, FSInputFile(path), caption=item_caption)
