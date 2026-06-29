import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_PATH = Path(__file__).resolve().parent.parent


def env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


def env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


BOT_TOKEN = os.getenv("BOT_TOKEN")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_INSTAGRAM_ACTOR = os.getenv("APIFY_INSTAGRAM_ACTOR", "elis~instagram-downloader-api")

LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")
LLM_MAX_TOKENS = env_int("LLM_MAX_TOKENS", 220, minimum=64)
LLM_HISTORY_TURNS = env_int("LLM_HISTORY_TURNS", 4, minimum=0)
LLM_MAX_INPUT_CHARS = env_int("LLM_MAX_INPUT_CHARS", 1200, minimum=200)
LLM_TIMEOUT_SECONDS = env_float("LLM_TIMEOUT_SECONDS", 45.0, minimum=5.0)
LLM_TEMPERATURE = env_float("LLM_TEMPERATURE", 0.45, minimum=0.0)
LLM_CONCURRENCY = env_int("LLM_CONCURRENCY", 1, minimum=1)
LLM_SYSTEM_PROMPT = os.getenv(
    "LLM_SYSTEM_PROMPT",
    "Ты Каттемис, умный и лёгкий телеграм-бот. Отвечай кратко, дружелюбно и по делу. "
    "Не выдумывай факты. Если не уверен — честно скажи об этом. "
    "В ролевом диалоге можно описывать свои короткие действия в *звёздочках*, "
    "но нельзя управлять действиями пользователя.",
)

PERSONA_NORMAL = "normal"
PERSONA_GOTH = "goth"
PERSONA_PROMPTS = {
    PERSONA_NORMAL: (
        "Режим: обычный Каттемис. Тон живой, тёплый, немного игривый, без лишнего текста. "
        "Если пользователь начинает RP, поддерживай сцену настолько, насколько хватает контекста."
    ),
    PERSONA_GOTH: (
        "Режим: гот-Каттемис. Тон мрачновато-ироничный, нежный, атмосферный: ночь, бархат, "
        "пост-панк, чёрный лак, но без токсичности и без тяжёлого пафоса. "
        "Сохраняй полезность, краткость и способность к RP."
    ),
}

DEFAULT_PERSONA = os.getenv("CATTEMIS_DEFAULT_PERSONA", PERSONA_NORMAL).strip().lower()
if DEFAULT_PERSONA not in PERSONA_PROMPTS:
    DEFAULT_PERSONA = PERSONA_NORMAL

TIKWM_API = "https://www.tikwm.com/api/"

TIKTOK_DOMAINS = {
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
}

INSTAGRAM_DOMAINS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
}

TWITTER_DOMAINS = {
    "x.com",
    "www.x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
}

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}

VIMEO_DOMAINS = {
    "vimeo.com",
    "www.vimeo.com",
}

ALLOWED_MEDIA_HOSTS = (
    TIKTOK_DOMAINS
    | INSTAGRAM_DOMAINS
    | TWITTER_DOMAINS
    | YOUTUBE_DOMAINS
    | VIMEO_DOMAINS
)

GROUP_CHAT_TYPES = {"group", "supergroup"}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

MEDIA_CONTENT_TYPES = {
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

RETRY_ATTEMPTS = 2
RETRY_DELAY = 1.2
ADMIN_CACHE_TTL = 60

PRAISE_REPLIES = [
    "ананас",
]

PRAISE_KEYWORDS = [
    "огурец",
]

ARTISTS_CONFIG_PATH = ROOT_PATH / "artists.json"
