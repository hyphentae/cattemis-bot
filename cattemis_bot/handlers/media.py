"""Media URL processing and general message handler for Cattemis Bot.

Registers:
- ``process_media_url`` — download + send a single media URL.
- ``handle_link``       — the catch-all message handler (media or LLM).
"""

import asyncio
import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import InputMediaPhoto, Message, ReplyParameters
from aiogram.utils.chat_action import ChatActionSender

from ..config import settings
from ..downloaders import with_retry
from ..downloaders.cobalt import CobaltError, download_cobalt
from ..downloaders.direct import download_direct_image, is_direct_image
from ..downloaders.instagram import download_instagram_apify, is_instagram
from ..downloaders.tiktok import download_tiktok, is_tiktok
from ..downloaders.twitter import download_twitter_fx, is_twitter
from ..downloaders.ytdlp import download_ytdlp, human_ytdlp_error, is_youtube
from ..llm import ask_llm, human_instagram_api_error, human_twitter_error
from ..moderation import is_allowed_media_link, moderate_links
from ..state import state
from ..utils.media import send_local_media
from ..utils.telegram import safe_delete_message, safe_status_edit, tg_call
from ..utils.text import extract_urls_from_message, truncate
from ..vision import (
    describe_media_with_vision,
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

REDDIT_DOMAINS: frozenset[str] = frozenset(
    {"reddit.com", "www.reddit.com", "old.reddit.com", "m.reddit.com", "redd.it"}
)


def is_reddit(url: str) -> bool:
    """Return True if *url* belongs to Reddit."""
    from urllib.parse import urlparse

    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == d or host.endswith("." + d) for d in REDDIT_DOMAINS)


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
            "Хозяин... простите, пожалуйста... при обработке ссылки что-то пошло не так... TᴖT",
        )


# ---------------------------------------------------------------------------
# YouTube / Reddit: Cobalt primary, yt-dlp fallback
# ---------------------------------------------------------------------------


async def _download_youtube_or_reddit(url: str):
    """Download YouTube/Reddit media, preferring Cobalt over yt-dlp.

    Tries Cobalt first (free public instance). On ``error``, ``rate-limit``,
    or an empty response, falls back to the existing yt-dlp path.
    """
    if settings.cobalt_enabled:
        try:
            result = await with_retry(download_cobalt, url)
            state.inc("cobalt_downloads")
            return result
        except CobaltError as exc:
            logger.info("[cobalt] falling back to yt-dlp for %s: %s", url, exc)

    result = await with_retry(download_ytdlp, url)
    state.inc("ytdlp_downloads")
    return result


# ---------------------------------------------------------------------------
# Core media processor
# ---------------------------------------------------------------------------

async def process_media_url(
    message: Message,
    url: str,
    initial_status_text: str = "Скачиваю...",
) -> None:
    """Download media from *url* and send it to *message*.

    After a successful download the media is sent as a reply to *message*
    (the message that contained the original URL).
    """
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
        elif is_youtube(url) or is_reddit(url):
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
            "Хозяин, я все ещё хороший мальчик, но телеграм не дает отправить это видео (⁠눈⁠‸⁠눈⁠)",
        )

    except TelegramRetryAfter as exc:
        state.inc("media_errors")
        await asyncio.sleep(float(exc.retry_after) + 1)
        await safe_status_edit(
            status,
            "Хозяин... Telegram попросил меня подождать немножко, попробуй ещё разочек ^^",
        )

    except asyncio.TimeoutError:
        state.inc("media_errors")
        await safe_status_edit(
            status,
            "Хозяин... сервер отвечает слишком долго... п-попробуйте ещё раз, пожалуйста... (つ﹏<。)",
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
            media = [
                InputMediaPhoto(
                    media=img,
                    caption=title if i == 0 and title else None,
                )
                for i, img in enumerate(images[:10])
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
# Media context builder (vision + whisper)
# ---------------------------------------------------------------------------

async def _build_media_context(media_source: Message, raw_text: str) -> str | None:
    """Collect vision / whisper descriptions from *media_source*.

    Returns a combined string (newline-separated) or ``None`` if nothing
    could be extracted.
    """
    contexts: list[str] = []
    user_hint = raw_text or None

    # --- Photo ---
    if media_source.photo and settings.vision_enabled:
        photo = media_source.photo[-1]
        try:
            media_bytes, suffix = await download_telegram_file(photo.file_id, "photo.jpg")
            desc = await describe_media_with_vision(media_bytes, suffix, user_hint)
            if desc:
                contexts.append(f"Фото: {desc}")
        except Exception as exc:
            logger.warning("[vision] photo error: %s", exc)

    # --- Video ---
    elif media_source.video:
        if settings.vision_enabled:
            try:
                media_bytes, suffix = await download_telegram_file(
                    media_source.video.file_id, "video.mp4"
                )
                desc = await describe_media_with_vision(media_bytes, suffix, user_hint)
                if desc:
                    contexts.append(f"Видео: {desc}")
            except Exception as exc:
                logger.warning("[vision] video error: %s", exc)

        if settings.whisper_enabled:
            try:
                if not settings.vision_enabled:
                    media_bytes, suffix = await download_telegram_file(
                        media_source.video.file_id, "video.mp4"
                    )
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


# ---------------------------------------------------------------------------
# General message handler
# ---------------------------------------------------------------------------

@router.message()
async def handle_link(message: Message) -> None:
    """Catch-all handler: moderate links, process media, or use LLM."""
    state.inc("messages_total")
    state.track_chat(message.chat.id)

    deleted, urls = await moderate_links(message)
    if deleted:
        return

    raw_text = (message.text or message.caption or "").strip()

    if raw_text.startswith("/"):
        return

    if urls:
        allowed_urls = [url for url in urls if is_allowed_media_link(url)]
        if not allowed_urls:
            if message.chat.type == "private":
                await tg_call(message.answer, "Пришли мне ссылку на фото или видео.")
            return
        await process_media_url(message, allowed_urls[0])
        return

    if not raw_text and not (message.photo or message.video or message.voice or message.audio):
        return

    should_use_llm = settings.llm_enabled and message.chat.type == "private"
    if not should_use_llm and settings.llm_enabled:
        if await _is_reply_to_this_bot(message) or await _is_bot_mentioned(message):
            should_use_llm = True

    if should_use_llm:
        await _handle_llm(message, raw_text)
        return

    if message.chat.type == "private" and not (
        message.photo or message.video or message.voice or message.audio
    ):
        await tg_call(message.answer, "Пришли мне ссылку на фото или видео.")


async def _handle_llm(message: Message, raw_text: str) -> None:
    """Invoke the LLM and reply, collecting vision/whisper context first."""
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

            media_context = await _build_media_context(media_source, raw_text)

            if not raw_text and not media_context:
                return

            reply_input = raw_text or "Пользователь прислал медиа. Ответь по описанию."

            state.inc("llm_calls")
            reply = await ask_llm(
                message.chat.id,
                reply_input,
                user_name=message.from_user.first_name if message.from_user else None,
                media_context=media_context,
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
            "Хозяин... я задумался слишком сильно и не смог ответить TᴖT",
            reply_parameters=ReplyParameters(message_id=message.message_id),
            parse_mode=None,
        )
