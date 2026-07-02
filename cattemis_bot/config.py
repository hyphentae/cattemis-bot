"""Configuration module for Cattemis Bot.

All settings are loaded from environment variables or a .env file using
pydantic-settings. Import the singleton ``settings`` object throughout the
codebase instead of calling ``os.getenv`` directly.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration loaded from environment / .env file."""

    # --- Telegram ---
    bot_token: str

    # --- Apify (Instagram downloader) ---
    apify_token: str = ""
    apify_instagram_actor: str = "elis~instagram-downloader-api"

    # --- LLM ---
    llm_enabled: bool = False
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "dummy"
    llm_model: str = "gemma4:e4b"
    llm_system_prompt: str = (
        "Ты милый телеграм-бот. Отвечай кратко и дружелюбно. "
        "Не выдумывай факты. Если не уверен — честно скажи об этом."
    )
    llm_cooldown_seconds: float = 5.0
    llm_max_tokens: int = 480
    llm_temperature: float = 0.6

    # --- Downloader limits ---
    max_media_items: int = 10
    """Maximum number of media files per download batch."""

    retry_attempts: int = 2
    retry_delay: float = 1.2

    # --- Misc ---
    admin_cache_ttl: int = 60
    """Seconds to cache admin lists for a chat."""

    max_history_messages: int = 8
    """Number of chat history messages passed to LLM context."""

    max_file_size: int = 50 * 1024 * 1024
    """Maximum file size in bytes accepted by Telegram (50 MB)."""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
