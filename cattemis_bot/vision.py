"""Vision and Whisper helpers for Cattemis Bot.

Public interface:
- ``download_telegram_file``         — fetch a Telegram file as raw bytes.
- ``describe_media_with_vision``     — send image/video frame to LLM for description.
- ``transcribe_audio_with_whisper``  — transcribe audio bytes via faster-whisper.
- ``extract_frame_from_video_bytes`` — pull a single JPEG frame from video bytes.
- ``extract_audio_from_video_bytes`` — extract mono WAV audio from video bytes.

All heavy work is guarded by the feature flags
``settings.vision_enabled`` / ``settings.whisper_enabled``, so calling
any function when the feature is off is a safe no-op that returns ``""``
or ``None``.
"""

import asyncio
import base64
import logging
import tempfile
from pathlib import Path

import aiohttp

from .config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}

IMAGE_MIME_MAP: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
}

# ---------------------------------------------------------------------------
# Whisper model singleton
# ---------------------------------------------------------------------------

_whisper_model = None


def _get_whisper_model():
    """Lazy-load WhisperModel singleton (only when whisper is enabled)."""
    global _whisper_model  # noqa: PLW0603
    if _whisper_model is not None:
        return _whisper_model
    if not settings.whisper_enabled:
        return None
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]

        _whisper_model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info(
            "[whisper] model loaded: size=%s device=%s compute=%s",
            settings.whisper_model_size,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
    except Exception as exc:  # pragma: no cover
        logger.error("[whisper] failed to load model: %s", exc)
        _whisper_model = None
    return _whisper_model


# ---------------------------------------------------------------------------
# Telegram file download
# ---------------------------------------------------------------------------

async def download_telegram_file(file_id: str, fallback_name: str) -> tuple[bytes, str]:
    """Download a Telegram file by *file_id* and return ``(bytes, ext)``."""
    from .main import bot  # lazy import to avoid circular dep

    file = await bot.get_file(file_id)
    url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"
    timeout = aiohttp.ClientTimeout(total=90)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.read()
    ext = Path(file.file_path or fallback_name).suffix or Path(fallback_name).suffix or ".bin"
    return data, ext


# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

async def extract_frame_from_video_bytes(
    video_bytes: bytes, suffix: str = ".mp4"
) -> bytes | None:
    """Extract the frame at 1 second as JPEG from *video_bytes*.

    Returns ``None`` if ffmpeg fails or is unavailable.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as vtmp:
        vtmp.write(video_bytes)
        video_path = Path(vtmp.name)
    frame_path = video_path.with_suffix(".jpg")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", "00:00:01", "-vframes", "1", str(frame_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        rc = await proc.wait()
        if rc != 0 or not frame_path.exists() or frame_path.stat().st_size == 0:
            return None
        return frame_path.read_bytes()
    finally:
        video_path.unlink(missing_ok=True)
        if frame_path.exists():
            frame_path.unlink(missing_ok=True)


async def extract_audio_from_video_bytes(
    video_bytes: bytes, suffix: str = ".mp4"
) -> tuple[bytes, str] | tuple[None, None]:
    """Extract mono 16 kHz WAV audio from *video_bytes* via ffmpeg.

    Returns ``(wav_bytes, ".wav")`` or ``(None, None)`` on failure.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as vtmp:
        vtmp.write(video_bytes)
        video_path = Path(vtmp.name)
    audio_path = video_path.with_suffix(".wav")
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            str(audio_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        rc = await proc.wait()
        if rc != 0 or not audio_path.exists() or audio_path.stat().st_size == 0:
            return None, None
        return audio_path.read_bytes(), ".wav"
    finally:
        video_path.unlink(missing_ok=True)
        if audio_path.exists():
            audio_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Vision (image / video frame → LLM)
# ---------------------------------------------------------------------------

async def describe_media_with_vision(
    media_bytes: bytes,
    suffix: str,
    user_text: str | None = None,
) -> str:
    """Send *media_bytes* to the LLM and return a short description.

    Videos are converted to a single JPEG frame first so that OpenRouter
    treats the request as image input (avoids the $1 minimum balance
    required for native video upload).

    Returns an empty string when vision or LLM is disabled, or on error.
    """
    if not settings.vision_enabled or not settings.llm_enabled:
        return ""

    try:
        from openai import AsyncOpenAI  # local import — already a dep

        client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        suffix_lower = (suffix or "").lower()

        if suffix_lower in VIDEO_EXTS:
            frame_bytes = await extract_frame_from_video_bytes(media_bytes, suffix_lower)
            if not frame_bytes:
                return ""
            payload_bytes = frame_bytes
            mime = "image/jpeg"
        else:
            payload_bytes = media_bytes
            mime = IMAGE_MIME_MAP.get(suffix_lower, "image/jpeg")

        b64_data = base64.b64encode(payload_bytes).decode("ascii")
        data_url = f"data:{mime};base64,{b64_data}"

        prompt = settings.vision_prompt
        if user_text:
            prompt += f"\n\nКомментарий пользователя: {user_text.strip()}"

        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Опиши это медиа."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=220,
        )
        from .utils.text import cleanup_llm_text

        return cleanup_llm_text(response.choices[0].message.content or "")
    except Exception as exc:  # pragma: no cover
        logger.error("[vision] error describing media: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Whisper (audio / voice transcription)
# ---------------------------------------------------------------------------

async def transcribe_audio_with_whisper(
    audio_bytes: bytes, suffix: str = ".ogg"
) -> str:
    """Transcribe *audio_bytes* using faster-whisper.

    Returns an empty string when Whisper is disabled, model not loaded,
    or on transcription error.
    """
    if not settings.whisper_enabled:
        return ""

    model = _get_whisper_model()
    if model is None:
        return ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".ogg") as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name

    try:
        segments, _info = await asyncio.to_thread(
            model.transcribe, temp_path, language="ru", vad_filter=True
        )
        from .utils.text import cleanup_llm_text

        text = " ".join(
            segment.text.strip() for segment in segments if segment.text.strip()
        )
        return cleanup_llm_text(text)
    except Exception as exc:  # pragma: no cover
        logger.error("[whisper] transcription error: %s", exc)
        return ""
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
