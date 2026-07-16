# cattemis-bot

**English** | [Русский](README.ru.md)

`cattemis-bot` is a Telegram bot for downloading media, optional LLM chat, and a game-filled Mini App. The project runs with Docker Compose: the bot waits for a healthy Cloudflare Tunnel, reads its current URL, and automatically assigns the Mini App to the Telegram menu button.

## Features

- downloads media from TikTok, Instagram, X/Twitter, YouTube, Vimeo, and direct links;
- sends photos and videos to Telegram with file-size validation;
- optional LLM chat through an OpenAI-compatible API;
- optional voice and audio transcription with Whisper;
- link moderation and an admin-only command for posting as the bot;
- Mini App launch from the menu button, `/games`, or inline mode;
- a Catppuccin Mocha interface designed for Telegram WebView.

## Games

| Game | BotFather short name | Modes |
|---|---|---|
| Tic-tac-toe | `tictactoe` | bot, code-based room, public matchmaking |
| Minesweeper | `minesweeper` | easy, medium, hard |
| Sudoku | `sudoku` | single-player |
| Shared canvas | `canvas` | shared 1000×1000 canvas, one pixel every 10 seconds |
| Chess | `chess` | code-based room, public matchmaking |
| Parabolic Chess | `parabolic_chess` | WebSocket multiplayer |
| Checkers | `checkers` | bot, code-based room, public matchmaking |
| Deltarune | `deltarune` | Project Vinetrap inside the Mini App |

Regular chess, checkers, and tic-tac-toe rooms are stored in memory and reset when the `web` container restarts. The shared canvas is stored in the `canvas` Docker volume and persists across restarts.

## Technology

- Python 3.12, aiogram, and pydantic-settings — Telegram bot;
- Go 1.23 — Mini App server, rooms, chess, checkers, and canvas APIs;
- Node.js 22, Express, and WebSocket — Parabolic Chess;
- Docker Compose and Cloudflare Quick Tunnel — service orchestration and HTTPS access from Telegram.

## Quick start

You need Docker with the Compose Plugin and a Telegram bot created through [@BotFather](https://t.me/BotFather).

1. Create a `.env` file in the project root:

   ```dotenv
   BOT_TOKEN=123456789:telegram_bot_token

   # Optional: Instagram through Apify
   APIFY_TOKEN=
   APIFY_INSTAGRAM_ACTOR=elis~instagram-downloader-api

   # Optional: LLM
   LLM_ENABLED=false
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_API_KEY=dummy
   LLM_MODEL=gemma4:e4b

   # Optional: Whisper
   WHISPER_ENABLED=false
   WHISPER_MODEL_SIZE=base
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE_TYPE=int8
   ```

2. Build and start the services:

   ```bash
   docker compose up -d --build
   ```

3. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f bot cloudflared web parabolic
   ```

After startup, `cloudflared` writes the current `trycloudflare.com` URL to a shared volume. The `bot` container starts only after the tunnel health check succeeds, then assigns that URL to the Telegram menu button.

Restart an individual service:

```bash
docker compose restart bot
docker compose restart web
```

Rebuild a service after changing source files included in its image:

```bash
docker compose up -d --build web
```

## Telegram HTML5 Games setup

In [@BotFather](https://t.me/BotFather):

1. enable inline mode with `/setinline`;
2. create eight games with `/newgame`, using the exact short names from the table above;
3. make sure the games belong to the same bot whose `BOT_TOKEN` is stored in `.env`.

Short names must match exactly. If even one name is invalid, Telegram may reject the entire inline result list with `GAME_INVALID`.

Games can be published in any chat:

```text
@cattemis_bot
@cattemis_bot chess
```

Or opened through a direct link:

```text
https://t.me/cattemis_bot?game=chess
```

The callback handler builds a current launch URL containing a signed Telegram user identity. The signing secret is `BOT_TOKEN`; it is passed to the `bot` and `web` containers but is never included in the URL.

## Bot commands

| Command | Description |
|---|---|
| `/help` | show help |
| `/ping` | check whether the bot is available |
| `/games` | open the registered HTML5 game picker |
| `/ttt` | play tic-tac-toe in Telegram messages |
| `/checkers` | play checkers in Telegram messages |
| `/say_cattemis <text>` | post as the bot; restricted to administrators in groups |
| `/stats` | show statistics for the current process |
| `/reset` | clear LLM history for the current chat |

## Environment variables

| Variable | Default | Description |
|---|---:|---|
| `BOT_TOKEN` | — | required Telegram Bot API token |
| `APIFY_TOKEN` | empty | Apify token for Instagram |
| `APIFY_INSTAGRAM_ACTOR` | `elis~instagram-downloader-api` | Instagram actor |
| `LLM_ENABLED` | `false` | enable LLM responses |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint |
| `LLM_API_KEY` | `dummy` | LLM endpoint API key |
| `LLM_MODEL` | `gemma4:e4b` | model name |
| `LLM_SYSTEM_PROMPT` | built in | system prompt |
| `LLM_COOLDOWN_SECONDS` | `5.0` | delay before an LLM request |
| `LLM_MAX_TOKENS` | `480` | maximum LLM response length |
| `LLM_TEMPERATURE` | `0.6` | generation temperature |
| `LLM_WEB_SEARCH_ENABLED` | `false` | enable LLM web search |
| `LLM_WEB_SEARCH_MAX_RESULTS` | `5` | maximum web search results |
| `WHISPER_ENABLED` | `false` | enable transcription |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model size |
| `WHISPER_DEVICE` | `cpu` | Whisper device |
| `WHISPER_COMPUTE_TYPE` | `int8` | Whisper compute type |
| `MAX_MEDIA_ITEMS` | `10` | files in one download batch |
| `MAX_FILE_SIZE` | `52428800` | maximum file size in bytes |
| `RETRY_ATTEMPTS` | `2` | number of download retries |
| `RETRY_DELAY` | `1.2` | delay between retries |
| `ADMIN_CACHE_TTL` | `60` | administrator list cache TTL |
| `MAX_HISTORY_MESSAGES` | `8` | messages retained in LLM history |
| `WEB_ENABLED` | `true` | web application flag |
| `WEB_PORT` | `8080` | web application port |
| `USE_CLOUDFLARE` | `true` | wait for Cloudflare Tunnel and assign the menu button |

`.env` is excluded from Git. Never publish the bot token or API keys.

## Architecture

```text
Telegram
   │
   ├── Bot API ───────────────► bot (Python / aiogram)
   │                                │
   │                                └── reads the tunnel URL from a volume
   │
   └── Mini App WebView ──────► cloudflared
                                      │
                                      ▼
                                web (Go :8080)
                                  │       │
                                  │       └── canvas volume
                                  ▼
                            parabolic (Node :3000)
```

## Repository structure

```text
cattemis_bot/      Python bot package, handlers, and downloaders
cloudflared/       Quick Tunnel container and URL publication
web/server/        Go API and static file server
web/static/        Mini App HTML, CSS, and JavaScript
web/parabolic/     standalone Parabolic Chess Node/WebSocket service
docker-compose.yml service and volume orchestration
run.py             bot container entry point
```

## Validation

```bash
PYTHONPYCACHEPREFIX=/tmp/cattemis-pycache python -m compileall -q cattemis_bot
docker build -t cattemis-web-check web/server
docker build -t cattemis-parabolic-check web/parabolic
docker compose config -q
```

Go tests run as part of the `web/server` image build.

## Attribution

The Parabolic Chess integration is based on [MellowYellow7777/parabolic-chess](https://github.com/MellowYellow7777/parabolic-chess). See [`web/parabolic/UPSTREAM.md`](web/parabolic/UPSTREAM.md) for details.
