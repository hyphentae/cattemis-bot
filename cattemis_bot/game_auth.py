"""Signed authentication tokens for Telegram HTML5 Game launches."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from aiogram.types import User

TOKEN_PREFIX = "catemis-game-v1"


def create_game_auth_token(
    user: User,
    bot_token: str,
    chat_instance: str = "",
    issued_at: int | None = None,
) -> str:
    """Create a compact HMAC-signed user token for the game WebView."""
    payload = {
        "id": user.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or "",
        "chat_instance": chat_instance,
        "auth_date": issued_at if issued_at is not None else int(time.time()),
    }
    encoded = _base64url(json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode())
    message = f"{TOKEN_PREFIX}.{encoded}".encode()
    signature = _base64url(hmac.new(bot_token.encode(), message, hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
