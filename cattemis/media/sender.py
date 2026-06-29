from pathlib import Path

from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo, Message

from ..config import AUDIO_EXTS, IMAGE_EXTS, VIDEO_EXTS
from ..telegram_utils import tg_call


async def send_local_media(message: Message, files: list[str], caption: str | None = None):
    files = files[:10]
    if not files:
        raise RuntimeError("Нет файлов для отправки")

    caption = (caption or "").strip()[:1024] or None

    if len(files) == 1:
        path = files[0]
        ext = Path(path).suffix.lower()

        if ext in IMAGE_EXTS:
            await tg_call(message.answer_photo, FSInputFile(path), caption=caption)
            return

        if ext in VIDEO_EXTS:
            await tg_call(
                message.answer_video,
                FSInputFile(path),
                caption=caption,
                supports_streaming=True,
            )
            return

        if ext in AUDIO_EXTS:
            await tg_call(message.answer_audio, FSInputFile(path), caption=caption)
            return

        await tg_call(message.answer_document, FSInputFile(path), caption=caption)
        return

    album = []
    leftovers = []

    for path in files:
        ext = Path(path).suffix.lower()
        item_caption = caption if len(album) == 0 and caption else None

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
