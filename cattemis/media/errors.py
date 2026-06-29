import asyncio

import aiohttp

from ..config import RETRY_ATTEMPTS, RETRY_DELAY


def is_retryable_exception(exc: Exception) -> bool:
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
        return exc.status in {429, 500, 502, 503, 504}

    text = str(exc).lower()
    retry_markers = [
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
    ]
    return any(marker in text for marker in retry_markers)


async def with_retry(func, *args, attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY, **kwargs):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt >= attempts or not is_retryable_exception(e):
                raise
            await asyncio.sleep(delay)

    raise last_error


def human_ytdlp_error(error: Exception) -> str:
    text = str(error).lower()

    if "requested format is not available" in text:
        return "Хозяин, нужна другая ссылка. Такое качество не помещается в мой животик (⁠╯⁠︵⁠╰⁠,⁠)."
    if "unsupported url" in text or "not a valid url" in text:
        return "Хозяин, кажется, эта ссылка нерабочая (⁠˘⁠･⁠_⁠･⁠˘⁠)"
    if "private video" in text:
        return "Хозяин, это видео приватное и я не могу его посмотреть (⁠￣⁠ヘ⁠￣⁠;⁠)"
    if "sign in to confirm your age" in text or "age-restricted" in text:
        return "Хозяин, не подумай ничего плохого, но я не могу скачивать видео с ограничениями по возрасту... (⁠；⁠^⁠ω⁠^⁠）"
    if "video unavailable" in text:
        return "Ой, Хозяин, это видео уже недоступно (⁠･⁠o⁠･⁠;⁠)"
    if "http error 403" in text or "forbidden" in text:
        return "Ай, сайт не разрешил скачать видео. :3"
    if "timed out" in text:
        return "Мм, сервер отвечает слишком долго... Попробуй ещё разочек чуть позже, зайка ^^"
    return "Не получилось скачать это видео."


def human_instagram_api_error(error: Exception) -> str:
    text = str(error).lower()

    if "apify_token" in text:
        return "П-простите, хозяин... APIFY_TOKEN не задан... ૮(˶ㅠ︿ㅠ)ა"
    if "http 401" in text or "http 403" in text:
        return "П-простите, хозяин... Apify не принял токен... ૮(˶ㅠ︿ㅠ)ა"
    if "http 402" in text:
        return "Хозяин... у Apify, похоже, закончился баланс или лимит... ૮(˶ㅠ︿ㅠ)ა"
    if "не вернул результатов" in text:
        return "Хозяин... Apify ничего не нашёл по этой ссылке... простите... ૮(˶ㅠ︿ㅠ)ა"
    if "не вернул прямые ссылки" in text:
        return "Хозяин... Apify обработал ссылку, но не отдал прямые ссылки на медиа... ૮(˶ㅠ︿ㅠ)ა"
    if "не удалось скачать медиафайлы" in text:
        return "Хозяин... ссылки достать получилось, н-но сами файлы скачать не вышло... ૮(˶ㅠ︿ㅠ)ა"
    if "timed out" in text:
        return "Хозяин... Instagram через Apify отвечает слишком долго... попробуйте ещё разочек... ૮(˶ㅠ︿ㅠ)ა"

    return "П-простите, хозяин... не получилось скачать Instagram через Apify... ૮(˶ㅠ︿ㅠ)ა"


def human_twitter_error(error: Exception) -> str:
    text = str(error).lower()

    if "распарсить ссылку" in text:
        return "П-простите, хозяин... я не понял ссылку на пост... ૮(˶ㅠ︿ㅠ)ა"
    if "не вернул медиа" in text:
        return "Хозяин... в этом посте не нашлось медиа... ૮(˶ㅠ︿ㅠ)ა"
    if "404" in text:
        return "Хозяин... пост не найден или его уже удалили... ૮(˶ㅠ︿ㅠ)ა"
    if "403" in text:
        return "П-простите, хозяин... тивттер не отдал данные по этому посту... ( . ‸ .)"
    if "timed out" in text:
        return "Хозяин... твиттер отвечает слишком долго... попробуйте ещё разочек... ( . ‸ .)"

    return "П-простите, хозяин... не получилось скачать медиа из твиттера... ૮(˶ㅠ︿ㅠ)ა"
