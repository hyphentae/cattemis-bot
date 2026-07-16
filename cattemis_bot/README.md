# Cattemis Bot

A Telegram bot that downloads media from TikTok, Instagram, Twitter/X, YouTube, Vimeo and direct image links, with optional LLM chat and group link moderation.

---

## Package structure

```
cattemis_bot/
├── main.py              # Entry point — initialise, register routers, start polling
├── config.py            # All settings via pydantic-settings (reads .env)
├── state.py             # Global BotState dataclass (counters, caches, locks)
├── llm.py               # ask_llm + human-readable error helpers
├── moderation.py        # moderate_links, is_admin_message, is_allowed_media_link
├── whisper.py           # Telegram file download, video audio extraction, Whisper transcription
├── utils/
│   ├── __init__.py      # Re-exports most-used helpers
│   ├── media.py         # Extension sets, guess_ext_from_content_type, send_local_media
│   ├── telegram.py      # tg_call, safe_status_edit, safe_delete_message
│   └── text.py          # cleanup_llm_text, fix_truncated_kaomoji, extract_urls_from_message, truncate
├── downloaders/
│   ├── __init__.py      # DownloadResult dataclass, with_retry, is_retryable
│   ├── tiktok.py        # download_tiktok (TikWM API, returns raw dict)
│   ├── instagram.py     # download_instagram_apify (Apify actor)
│   ├── twitter.py       # download_twitter_fx (FxTwitter API)
│   ├── direct.py        # download_direct_image (plain HTTP GET)
│   └── ytdlp.py         # download_ytdlp (yt-dlp, executor thread)
└── handlers/
    ├── __init__.py
    ├── commands.py      # /help /ping /stats /reset /say_cattemis
    └── media.py         # media-link and explicitly addressed LLM handlers
```

---

## Environment variables

All variables can be set in a `.env` file in the project root or as real environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | **yes** | — | Telegram Bot API token |
| `APIFY_TOKEN` | no | `""` | Apify API token for Instagram downloads |
| `APIFY_INSTAGRAM_ACTOR` | no | `elis~instagram-downloader-api` | Apify actor ID for Instagram |
| `LLM_ENABLED` | no | `false` | Enable LLM chat (`true`/`false`) |
| `LLM_BASE_URL` | no | `http://localhost:11434/v1` | OpenAI-compatible API base URL |
| `LLM_API_KEY` | no | `dummy` | API key for LLM backend |
| `LLM_MODEL` | no | `gemma4:e4b` | Model name to pass to the LLM API |
| `LLM_SYSTEM_PROMPT` | no | (built-in) | System prompt for the LLM |
| `LLM_COOLDOWN_SECONDS` | no | `5.0` | Delay before each LLM call (seconds) |
| `LLM_MAX_TOKENS` | no | `480` | Max tokens in LLM response |
| `LLM_TEMPERATURE` | no | `0.6` | Sampling temperature for LLM |
| `MAX_MEDIA_ITEMS` | no | `10` | Max files per download batch |
| `RETRY_ATTEMPTS` | no | `2` | Number of retry attempts for downloads |
| `RETRY_DELAY` | no | `1.2` | Seconds between retries |
| `ADMIN_CACHE_TTL` | no | `60` | Seconds to cache chat admin lists |
| `MAX_HISTORY_MESSAGES` | no | `8` | LLM context window (message count) |
| `MAX_FILE_SIZE` | no | `52428800` | Max upload size in bytes (50 MB) |

---

---

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env
echo "BOT_TOKEN=your_token_here" > .env

# Run
python -m cattemis_bot.main
```

---

## Commands

| Command | Description |
|---|---|
| `/help` | Show help message |
| `/ping` | Liveness check — responds with `pong 🏓` |
| `/say_cattemis <text>` | Bot repeats your text (admin-only in groups) |
| `/stats` | Show runtime statistics |
| `/reset` | Clear LLM conversation history for this chat |

---

## Architecture notes

- **No `global` keyword** — all shared mutable state lives in `state.BotState`.
- **All `asyncio.Lock` objects** are created in `BotState`, never ad-hoc.
- **Logging** uses the standard `logging` module throughout; `print` is gone.
- **`DownloadResult.cleanup()`** removes temp dirs; called in `finally` blocks in `process_media_url`.
- **File size guard** in `send_local_media` warns and skips files >50 MB instead of letting Telegram reject them.
- **`dict.fromkeys`** is used for O(1) URL deduplication everywhere.

### Mini App checkers multiplayer

The Go web service serves the Mini App and an authenticated checkers API. A
player creates a six-character room code and a second Telegram user joins with
that code. Requests are authenticated with signed `Telegram.WebApp.initData`;
the web service receives `BOT_TOKEN` through the shared `.env` file.

Rooms are held in memory and expire after six hours of inactivity, so active
games are reset whenever the `web` container restarts.

The Telegram HTML5 Games `tictactoe`, `checkers`, `sudoku`, `parabolic_chess`,
`chess`, and `minesweeper` each open their matching screen. Use `/games` for a compact picker,
or type `@cattemis_bot` in any chat to publish a game through inline mode. Game
launches use a signed token in the URL fragment, so authenticated multiplayer
continues to work without a permanent Cloudflare domain.

Parabolic Chess runs as a separate Node/WebSocket service behind the same Go
reverse proxy and opens inside the Mini App. Its source and attribution live in
`web/parabolic`; the integration is based on MellowYellow7777's public project.
