"""Media URL and explicitly addressed LLM message handling for Cattemis Bot.

Registers:
- ``process_media_url`` — download + send a single media URL.
- ``handle_media_link`` — process messages containing URLs.
- ``handle_llm_message`` — process private or explicitly addressed LLM messages.
"""

import asyncio
import base64
import logging

from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import InputMediaPhoto, Message, ReplyParameters
from aiogram.utils.chat_action import ChatActionSender

from ..config import settings
from ..downloaders import with_retry
from ..downloaders.direct import download_direct_image, is_direct_image
from ..downloaders.instagram import download_instagram_apify, is_instagram
from ..downloaders.reddit import RedditNoImagesError, download_reddit_images, is_reddit
from ..downloaders.tiktok import download_tiktok, is_tiktok
from ..downloaders.twitter import download_twitter_fx, is_twitter
from ..downloaders.ytdlp import download_ytdlp, human_ytdlp_error, is_youtube
from ..llm import ask_llm, human_instagram_api_error, human_twitter_error
from ..moderation import is_allowed_media_link, moderate_links
from ..state import state
from ..utils.media import send_local_media
from ..utils.telegram import safe_delete_message, safe_status_edit, tg_call
from ..utils.text import extract_urls_from_message, truncate
from ..whisper import (
    download_telegram_file,
    extract_audio_from_video_bytes,
    transcribe_audio_with_whisper,
)

try:
    from yt_dlp.utils import DownloadError, ExtractorError
except ImportError:  # pragma: no cover
    DownloadError = Exception  # type: ignore[assignment,misc]
    ExtractorError = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)
router = Router(name="media")

# ---------------------------------------------------------------------------
# Bot mention helpers
# ---------------------------------------------------------------------------

async def _is_reply_to_this_bot(message: Message) -> bool:
    reply = message.reply_to_message
    if not reply or not reply.from_user:
        return False
    return reply.from_user.id == state.bot_id


async def _is_bot_mentioned(message: Message) -> bool:
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    bot_username = state.bot_username
    if not bot_username:
        return False
    expected = f"@{bot_username}"
    for entity in entities:
        if str(entity.type) == "mention":
            mention_text = text[entity.offset : entity.offset + entity.length].lower()
            if mention_text == expected:
                return True
    return False


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

async def _send_error(status: Message, url: str, exc: Exception) -> None:
    """Edit *status* with a human-readable error message for *exc*."""
    if is_instagram(url):
        await safe_status_edit(status, human_instagram_api_error(exc))
    elif is_twitter(url):
        await safe_status_edit(status, human_twitter_error(exc))
    else:
        await safe_status_edit(
            status,
            "Хозяин... простите, пожалуйста... при обработке ссылки что-то пошло не так... T_T",
        )


# ---------------------------------------------------------------------------
# YouTube / Reddit
# ---------------------------------------------------------------------------


async def _download_youtube_or_reddit(url: str):
    """Download YouTube/Reddit media via yt-dlp."""
    result = await with_retry(download_ytdlp, url)
    state.inc("ytdlp_downloads")
    return result


# ---------------------------------------------------------------------------
# Core media processor
# ---------------------------------------------------------------------------

async def process_media_url(
    message: Message,
    url: str,
    initial_status_text: str = "Скачиваю... :3",
) -> None:
    """Download media from *url* and send it to *message* as a reply."""
    status = await tg_call(message.answer, initial_status_text)
    result = None

    try:
        if is_tiktok(url):
            await _handle_tiktok(message, url, status)
            return

        if is_instagram(url):
            result = await with_retry(download_instagram_apify, url)
            state.inc("media_total")
            state.inc("instagram_downloads")
        elif is_twitter(url):
            result = await with_retry(download_twitter_fx, url)
            state.inc("media_total")
            state.inc("twitter_downloads")
        elif is_direct_image(url):
            result = await with_retry(download_direct_image, url)
            state.inc("media_total")
            state.inc("direct_image_downloads")
        elif is_youtube(url):
            result = await _download_youtube_or_reddit(url)
            state.inc("media_total")
        elif is_reddit(url):
            try:
                result = await with_retry(download_reddit_images, url)
            except RedditNoImagesError:
                result = await _download_youtube_or_reddit(url)
            state.inc("media_total")
        else:
            result = await with_retry(download_ytdlp, url)
            state.inc("media_total")
            state.inc("ytdlp_downloads")

        async with state.get_lock(message.chat.id):
            await safe_status_edit(status, "Отправляю...")
            await send_local_media(
                message,
                result.files,
                result.caption,
                reply_to_message_id=message.message_id,
            )
            await safe_delete_message(status)

    except (DownloadError, ExtractorError) as exc:
        state.inc("media_errors")
        await safe_status_edit(status, human_ytdlp_error(exc))

    except TelegramBadRequest:
        state.inc("media_errors")
        await safe_status_edit(
            status,
            "Хозяин... файл скачался, но Telegram не даёт его отправить... ну почему... (¬_¬) "
            "попробуй через веб напрямую~",
        )

    except TelegramRetryAfter as exc:
        state.inc("media_errors")
        await asyncio.sleep(float(exc.retry_after) + 1)
        await safe_status_edit(
            status,
            "Хозяин... Telegram попросил меня подождать немножко~ попробуй ещё разочек ^-^",
        )

    except asyncio.TimeoutError:
        state.inc("media_errors")
        await safe_status_edit(
            status,
            "Хозяин... сервер отвечает слишком долго... п-попробуйте ещё раз, пожалуйста... T_T",
        )

    except Exception as exc:
        state.inc("media_errors")
        logger.error("Unhandled error for %s: %s", url, exc, exc_info=True)
        await _send_error(status, url, exc)

    finally:
        if result is not None:
            result.cleanup()


async def _handle_tiktok(message: Message, url: str, status: Message) -> None:
    """Handle TikTok-specific download (direct URL, no temp files)."""
    data = await with_retry(download_tiktok, url)
    title = truncate(data.get("title") or "", max_len=1024)
    state.inc("media_total")
    state.inc("tiktok_downloads")

    reply_params = ReplyParameters(message_id=message.message_id)

    async with state.get_lock(message.chat.id):
        images = data.get("images") or []
        if images:
            images = images[: settings.max_media_items]
            for start in range(0, len(images), 10):
                chunk = images[start : start + 10]
                chunk_title = title if start == 0 else None

                if len(chunk) == 1:
                    await tg_call(
                        message.answer_photo,
                        photo=chunk[0],
                        caption=chunk_title,
                        reply_parameters=reply_params,
                    )
                    continue

                media = [
                    InputMediaPhoto(
                        media=img,
                        caption=chunk_title if i == 0 else None,
                    )
                    for i, img in enumerate(chunk)
                ]
                await tg_call(
                    message.answer_media_group,
                    media=media,
                    reply_parameters=reply_params,
                )
            await safe_delete_message(status)
            return

        video_url = data.get("hdplay") or data.get("play") or data.get("play_addr")
        if not video_url:
            raise RuntimeError("TikWM не вернул ссылку на видео")

        await tg_call(
            message.answer_video,
            video=video_url,
            caption=title,
            supports_streaming=True,
            reply_parameters=reply_params,
        )
        await safe_delete_message(status)


# ---------------------------------------------------------------------------
# Media context builder (Whisper)
# ---------------------------------------------------------------------------

async def _build_media_context(media_source: Message, raw_text: str) -> str | None:
    """Collect Whisper transcriptions from *media_source*."""
    contexts: list[str] = []

    # --- Video ---
    if media_source.video and settings.whisper_enabled:
        try:
            media_bytes, suffix = await download_telegram_file(
                media_source.video.file_id, "video.mp4"
            )
            try:
                extracted_audio, audio_suffix = await extract_audio_from_video_bytes(
                    media_bytes, suffix or ".mp4"
                )
                if extracted_audio:
                    transcript = await transcribe_audio_with_whisper(
                        extracted_audio, audio_suffix or ".wav"
                    )
                    if transcript:
                        contexts.append(f"Аудио из видео: {transcript}")
            except Exception as exc:
                logger.warning("[whisper] video audio error: %s", exc)
        except Exception as exc:
            logger.warning("[whisper] video download error: %s", exc)

    # --- Voice ---
    elif media_source.voice and settings.whisper_enabled:
        try:
            audio_bytes, suffix = await download_telegram_file(
                media_source.voice.file_id, "voice.ogg"
            )
            transcript = await transcribe_audio_with_whisper(audio_bytes, suffix or ".ogg")
            if transcript:
                contexts.append(f"Расшифровка голосового: {transcript}")
        except Exception as exc:
            logger.warning("[whisper] voice error: %s", exc)

    # --- Audio file ---
    elif media_source.audio and settings.whisper_enabled:
        try:
            audio_bytes, suffix = await download_telegram_file(
                media_source.audio.file_id, "audio.mp3"
            )
            transcript = await transcribe_audio_with_whisper(audio_bytes, suffix or ".mp3")
            if transcript:
                contexts.append(f"Расшифровка аудио: {transcript}")
        except Exception as exc:
            logger.warning("[whisper] audio error: %s", exc)

    return "\n\n".join(contexts) if contexts else None


async def _build_media_image(media_source: Message) -> str | None:
    """Return an attached photo or video thumbnail as a safe inline data URL."""
    file_id: str | None = None
    filename = "image.jpg"
    if media_source.photo:
        file_id = media_source.photo[-1].file_id
    elif media_source.video and media_source.video.thumbnail:
        file_id = media_source.video.thumbnail.file_id
        filename = "video-thumbnail.jpg"

    if not file_id:
        return None
    try:
        image_bytes, suffix = await download_telegram_file(file_id, filename)
        mime = "image/png" if (suffix or "").lower() == ".png" else "image/jpeg"
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception as exc:
        logger.warning("[media] image download error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Targeted message handlers
# ---------------------------------------------------------------------------


class HasURLsFilter(BaseFilter):
    """Match non-command messages containing at least one URL."""

    async def __call__(self, message: Message) -> bool:
        raw_text = (message.text or message.caption or "").strip()
        return not raw_text.startswith("/") and bool(extract_urls_from_message(message))


class LLMMessageFilter(BaseFilter):
    """Match only messages that should be passed to the configured LLM."""

    async def __call__(self, message: Message) -> bool:
        if not settings.llm_enabled:
            return False

        raw_text = (message.text or message.caption or "").strip()
        if raw_text.startswith("/") or extract_urls_from_message(message):
            return False

        has_media = bool(message.photo or message.video or message.voice or message.audio)
        if not raw_text and not has_media:
            return False

        if message.chat.type == "private":
            return True

        # An attachment alone must not summon the bot in a group.
        return await _is_reply_to_this_bot(message) or await _is_bot_mentioned(message)


@router.message(HasURLsFilter())
async def handle_media_link(message: Message) -> None:
    """Moderate and process messages containing media links."""
    state.inc("messages_total")
    state.track_chat(message.chat.id)

    deleted, urls = await moderate_links(message)
    if deleted:
        return

    allowed_urls = [url for url in urls if is_allowed_media_link(url)]
    if not allowed_urls:
        if message.chat.type == "private":
            await tg_call(
                message.answer,
                "Хозяин... я умею скачивать только медиа :3 отправь ссылку на фото или видео~",
            )
        return

    await process_media_url(message, allowed_urls[0])


@router.message(LLMMessageFilter())
async def handle_llm_message(message: Message) -> None:
    """Pass an eligible message to the LLM."""
    state.inc("messages_total")
    state.track_chat(message.chat.id)
    raw_text = (message.text or message.caption or "").strip()
    await _handle_llm(message, raw_text)


async def _handle_llm(message: Message, raw_text: str) -> None:
    """Invoke the LLM and reply, collecting Whisper context first."""
    from ..main import bot  # lazy import to avoid circular dep

    try:
        async with ChatActionSender.typing(
            bot=bot,
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
        ):
            has_own_media = bool(
                message.photo or message.video or message.voice or message.audio
            )
            media_source = message if has_own_media else (message.reply_to_message or message)

            media_context, image_data_url = await asyncio.gather(
                _build_media_context(media_source, raw_text),
                _build_media_image(media_source),
            )

            if not raw_text and not media_context and not image_data_url:
                return

            if raw_text:
                reply_input = raw_text
            elif media_source.photo:
                reply_input = "Пользователь прислал фотографию. Кратко отреагируй на неё."
            else:
                reply_input = "Пользователь прислал видео. Ответь по доступному превью и расшифровке."

            state.inc("llm_calls")
            reply = await ask_llm(
                message.chat.id,
                reply_input,
                user_name=message.from_user.first_name if message.from_user else None,
                media_context=media_context,
                image_data_url=image_data_url,
            )

        reply = reply.strip()[:4000] or "..."
        await tg_call(
            message.answer,
            reply,
            reply_parameters=ReplyParameters(message_id=message.message_id),
            parse_mode=None,
        )
    except Exception as exc:
        state.inc("llm_errors")
        logger.error("[llm] error: %s", exc, exc_info=True)
        await tg_call(
            message.answer,
            "Хозяин... я задумался слишком сильно и уронил хвостиком... простите T_T",
            reply_parameters=ReplyParameters(message_id=message.message_id),
            parse_mode=None,
        )
