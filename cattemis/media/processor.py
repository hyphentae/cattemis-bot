import asyncio
import shutil

import aiohttp
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import InputMediaPhoto, Message
from yt_dlp.utils import DownloadError

from ..state import get_chat_lock
from ..telegram_utils import safe_delete_message, safe_status_edit, tg_call
from .downloaders import (
    download_direct_image,
    download_instagram_apify,
    download_tiktok,
    download_twitter_fx,
    download_ytdlp,
)
from .errors import human_instagram_api_error, human_twitter_error, human_ytdlp_error, with_retry
from .links import is_direct_image, is_instagram, is_tiktok, is_twitter
from .sender import send_local_media


async def process_media_url(message: Message, url: str, initial_status_text: str = "Скачиваю..."):
    status = await tg_call(message.answer, initial_status_text)
    temp_dirs: list[str] = []

    try:
        if is_tiktok(url):
            data = await with_retry(download_tiktok, url)
            title = (data.get("title") or "").strip()

            async with get_chat_lock(message.chat.id):
                images = data.get("images") or []
                if images:
                    media = [
                        InputMediaPhoto(
                            media=img,
                            caption=title[:1024] if i == 0 and title else None,
                        )
                        for i, img in enumerate(images[:10])
                    ]
                    await tg_call(message.answer_media_group, media=media)
                    await safe_delete_message(status)
                    return

                video_url = data.get("hdplay") or data.get("play") or data.get("play_addr")
                if not video_url:
                    raise RuntimeError("TikWM не вернул ссылку на видео")

                await tg_call(
                    message.answer_video,
                    video=video_url,
                    caption=title[:1024] if title else None,
                    supports_streaming=True,
                )
                await safe_delete_message(status)
                return

        if is_instagram(url):
            result = await with_retry(download_instagram_apify, url)
            temp_dirs.append(result["temp_dir"])
            async with get_chat_lock(message.chat.id):
                await safe_status_edit(status, "Отправляю...")
                await send_local_media(message, result["files"], result.get("caption"))
                await safe_delete_message(status)
                return

        if is_twitter(url):
            result = await with_retry(download_twitter_fx, url)
            temp_dirs.append(result["temp_dir"])
            async with get_chat_lock(message.chat.id):
                await safe_status_edit(status, "Отправляю...")
                await send_local_media(message, result["files"], result.get("caption"))
                await safe_delete_message(status)
                return

        if is_direct_image(url):
            result = await with_retry(download_direct_image, url)
            temp_dirs.append(result["temp_dir"])
            async with get_chat_lock(message.chat.id):
                await safe_status_edit(status, "Отправляю...")
                await send_local_media(message, result["files"], result.get("caption"))
                await safe_delete_message(status)
                return

        result = await with_retry(download_ytdlp, url)
        temp_dirs.append(result["temp_dir"])

        async with get_chat_lock(message.chat.id):
            await safe_status_edit(status, "Отправляю...")
            await send_local_media(message, result["files"], result.get("caption"))
            await safe_delete_message(status)

    except aiohttp.ClientResponseError as e:
        text = str(e).lower()
        if is_tiktok(url):
            await safe_status_edit(status, "Хозяин, TikTok не отдал ничего... Попробуй ещё раз попозже, лапочка (⁠｡⁠・⁠/⁠/⁠ε⁠/⁠/⁠・⁠｡⁠)")
        elif is_instagram(url):
            await safe_status_edit(status, "Хозяин, Instagram почему-то не отдал ничего, Попробуй ещё разочек (⁠｡⁠・⁠/⁠/⁠ε⁠/⁠/⁠・⁠｡⁠)")
        elif is_twitter(url):
            if "404" in text:
                await safe_status_edit(status, "Хозяин, Twitter/X пост не найден или его уже удалили, прости пожалуйста (⁠´⁠ ⁠.⁠ ⁠.̫⁠ ⁠.⁠ ⁠`⁠)")
            else:
                await safe_status_edit(status, "Хозяин, Twitter/X почему-то не отдал медиа. Попробуй чуть позже ^^")
        else:
            await safe_status_edit(status, "Упс, не получилось скачать (⁠´⁠ ⁠.⁠ ⁠.̫⁠ ⁠.⁠ ⁠`⁠) Не наказывай меня, Хозяин, но я не знаю почему")

    except asyncio.TimeoutError:
        await safe_status_edit(status, "Хозяин... сервер отвечает слишком долго... п-попробуйте ещё раз, пожалуйста... (つ﹏<。)")

    except DownloadError as e:
        await safe_status_edit(status, human_ytdlp_error(e))

    except TelegramBadRequest:
        await safe_status_edit(status, "Хозяин, я все ещё хороший мальчик, но телеграм не дает отправить это видео (⁠눈⁠‸⁠눈⁠)")

    except TelegramRetryAfter as e:
        await asyncio.sleep(float(e.retry_after) + 1)
        await safe_status_edit(status, "Хозяин... Telegram попросил меня подождать немножко, попробуй ещё разочек ^^")

    except Exception as e:
        print(f"[media] Unhandled error for {url}: {e}")
        if is_instagram(url):
            await safe_status_edit(status, human_instagram_api_error(e))
        elif is_twitter(url):
            await safe_status_edit(status, human_twitter_error(e))
        else:
            await safe_status_edit(status, "Хозяин... простите, пожалуйста... при обработке ссылки что-то пошло не так... TᴖT")

    finally:
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
