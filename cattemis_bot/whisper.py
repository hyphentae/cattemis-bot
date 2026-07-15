"""Telegram file and Whisper helpers for audio transcription."""

import asyncio
import logging
import tempfile
from pathlib import Path

import aiohttp

from .config import settings

logger = logging.getLogger(__name__)
_whisper_model = None


def _get_whisper_model():
    """Lazy-load the configured Whisper model."""
    global _whisper_model  # noqa: PLW0603
    if _whisper_model is not None or not settings.whisper_enabled:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]

        _whisper_model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("[whisper] model loaded")
    except Exception as exc:  # pragma: no cover
        logger.error("[whisper] failed to load model: %s", exc)
    return _whisper_model


async def download_telegram_file(file_id: str, fallback_name: str) -> tuple[bytes, str]:
    """Download a Telegram file and return its bytes and extension."""
    from .main import bot

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90)) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.read()
    ext = Path(file.file_path or fallback_name).suffix or Path(fallback_name).suffix or ".bin"
    return data, ext


async def extract_audio_from_video_bytes(
    video_bytes: bytes, suffix: str = ".mp4"
) -> tuple[bytes | None, str | None]:
    """Extract mono 16 kHz WAV audio from video bytes using ffmpeg."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as vtmp:
        vtmp.write(video_bytes)
        video_path = Path(vtmp.name)
    audio_path = video_path.with_suffix(".wav")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", str(audio_path),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        if await proc.wait() != 0 or not audio_path.exists() or not audio_path.stat().st_size:
            return None, None
        return audio_path.read_bytes(), ".wav"
    finally:
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)


async def transcribe_audio_with_whisper(audio_bytes: bytes, suffix: str = ".ogg") -> str:
    """Transcribe audio bytes, returning an empty string when disabled or unavailable."""
    if not settings.whisper_enabled:
        return ""
    model = _get_whisper_model()
    if model is None:
        return ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".ogg") as tmp:
        tmp.write(audio_bytes)
        temp_path = Path(tmp.name)
    try:
        segments, _info = await asyncio.to_thread(
            model.transcribe, str(temp_path), language="ru", vad_filter=True
        )
        from .utils.text import cleanup_llm_text

        return cleanup_llm_text(" ".join(s.text.strip() for s in segments if s.text.strip()))
    except Exception as exc:  # pragma: no cover
        logger.error("[whisper] transcription error: %s", exc)
        return ""
    finally:
        temp_path.unlink(missing_ok=True)
