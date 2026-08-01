# cattemis-bot — Go edition

**English** | [Русский](README.ru.md)

`cattemis-bot` is a Telegram media downloader, optional LLM assistant, and
game-filled Mini App. This edition rewrites the bot and the Mini App API in Go
while preserving the features of the Python project and incorporating the
useful additions from the Rust version.

TypeScript is used for the Mini App interface, and Node.js powers the separate
Parabolic Chess service.

## Features

- downloads photos, videos, and carousels from TikTok, Instagram, X/Twitter,
  YouTube, and Reddit;
- includes the source post caption or description for every supported platform;
- supports direct image and video links;
- sends carousels as Telegram albums of up to 10 files and validates file-size
  limits;
- works with OpenRouter and other OpenAI-compatible APIs;
- sends photos, selected video frames, and audio/video transcripts to the LLM;
- restores the entire cached album when a user replies to one of the files
  previously sent by the bot;
- provides the LLM with `current_time` and optional `web_search` tools;
- moderates unsupported links posted by non-administrators in groups;
- stores extra allowed domains added through `/allowlink example.com`;
- accepts Telegram Stars and can display an optional Ko-fi button;
- keeps process statistics and separate LLM history for every chat;
- automatically updates the Telegram Mini App button when the Cloudflare Quick
  Tunnel address changes.

## Games

The Mini App retains all games from the original project and adds Flappy Kat
from the Rust edition.

| Game | BotFather short name | Modes |
|---|---|---|
| Tic-tac-toe | `tictactoe` | bot, private room, public matchmaking |
| Minesweeper | `minesweeper` | 3 difficulties, timer, flag sound/haptics, leaderboard |
| Sudoku | `sudoku` | 3 difficulties, timer, mistakes, leaderboard |
| Shared canvas | `canvas` | persistent shared 1000×1000 canvas |
| Chess | `chess` | bot, private room, public matchmaking |
| Parabolic Chess | `parabolic_chess` | WebSocket multiplayer |
| Checkers | `checkers` | bot, private room, public matchmaking |
| Flappy Kat | `flappy` | local high score and shared leaderboard |

The `/ttt` and `/checkers` commands also run games directly through Telegram
inline keyboards. Reply to another user's message with the command to challenge
that user.

`/wordle` starts a five-letter English Wordle directly in chat, without the Mini
App. Everyone gets the same daily word, while attempts are tracked per user.
The bot sends a PNG progress card after every guess and adds the player's avatar
to the final card.

## Technology

- Go 1.24 — Telegram bot, downloaders, LLM client, Mini App API, rooms, and
  leaderboards;
- TypeScript 5 and Vite — Mini App interface;
- Node.js, Express, and WebSocket — Parabolic Chess;
- `yt-dlp`, Deno, FFmpeg, and FFprobe — YouTube challenge solving, media
  processing, and downloader fallbacks;
- optional OpenAI Whisper CLI — local audio and video transcription;
- Docker Compose and Cloudflare Quick Tunnel — service orchestration and HTTPS
  access from Telegram.

The Go code uses only the standard library.

## Quick start

You need Docker with the Compose Plugin and a Telegram bot created through
[@BotFather](https://t.me/BotFather).

1. Copy the configuration template:

   ```bash
   cp .env.example .env
   ```

2. Set at least the bot token in `.env`:

   ```dotenv
   BOT_TOKEN=123456789:telegram_bot_token
   ```

3. Build and start every service:

   ```bash
   docker compose up -d --build
   ```

4. Check service status and logs:

   ```bash
   docker compose ps
   docker compose logs -f bot cloudflared web parabolic
   ```

The default `runtime` image includes local Whisper. If transcription is not
needed, use the smaller image:

```dotenv
DOCKER_TARGET=runtime-lite
WHISPER_ENABLED=false
```

After startup, `cloudflared` writes the current `trycloudflare.com` URL to a
shared volume. The bot waits for the tunnel health check and then assigns the
current URL to the Telegram menu button.

## LLM and media analysis

Example OpenRouter configuration:

```dotenv
LLM_ENABLED=true
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your_model
LLM_WEB_SEARCH_ENABLED=true
LLM_VISION_ENABLED=true
LLM_TIMEZONE=Asia/Almaty
LLM_VIDEO_FRAME_COUNT=3
WHISPER_ENABLED=true
```

In private chats, the bot responds to ordinary text and media messages. In
groups, an LLM request must:

1. contain the word `мяу`;
2. reply to the bot or mention its `@username`.

`LLM_VIDEO_FRAME_COUNT` controls how many evenly spaced video frames are sent
to the model and accepts values from 1 to 6. `LLM_TIMEZONE` accepts an IANA
timezone such as `Asia/Almaty` or a UTC offset such as `+05:00`.

See [`.env.example`](.env.example) for every available setting. The `.env` file
is ignored by Git; never publish bot tokens or API keys.

## Bot commands

| Command | Description |
|---|---|
| `/start` | start the bot |
| `/help` | show help |
| `/app` | open the Mini App |
| `/games` | open the HTML5 game picker |
| `/ttt` | play tic-tac-toe in Telegram messages |
| `/checkers` | play checkers in Telegram messages |
| `/wordle` | play a five-letter English Wordle in Telegram messages |
| `/donate` | support the bot through Telegram Stars or Ko-fi |
| `/paysupport` | show payment support information |
| `/ping` | check whether the bot is available |
| `/stats` | show statistics for the current process |
| `/reset` | clear LLM history for the current chat |
| `/allowlink example.com` | allow a domain in a private chat or as an administrator |

## Telegram HTML5 Games setup

In [@BotFather](https://t.me/BotFather):

1. enable inline mode with `/setinline`;
2. create eight games with `/newgame`;
3. use the exact short names from the Games table;
4. make sure the games belong to the same bot whose `BOT_TOKEN` is stored in
   `.env`.

Short names must match exactly. An invalid name can cause Telegram to reject
the complete inline result list with `GAME_INVALID`.

Games can be opened from any chat:

```text
@cattemis_bot
@cattemis_bot chess
```

Or through a direct link:

```text
https://t.me/cattemis_bot?game=chess
```

Game callbacks receive a signed HMAC user token, so leaderboards and multiplayer
work both through Telegram HTML5 Games and through the regular Mini App.

## Local validation

```bash
gofmt -w cmd internal resources web/server
go test ./...
go vet ./...

cd web/client
npm ci
npm run build
```

The bot requires `yt-dlp` with its EJS component, Deno, `ffmpeg`, and `ffprobe`
at runtime. The Docker image includes all of them. Local transcription
additionally requires the `whisper` CLI.

## Repository structure

```text
cmd/cattemis-bot/     application entry point
internal/bot/         commands, games, moderation, media, and state
internal/telegram/    Telegram Bot API client
internal/downloader/  platform downloaders and yt-dlp fallback
internal/llm/         OpenAI-compatible client and tools
resources/            shared strings.json
web/server/           Go Mini App API
web/client/           TypeScript Mini App
web/parabolic/        Parabolic Chess service
cloudflared/          Cloudflare Quick Tunnel
```

## Attribution

The Parabolic Chess integration is based on
[MellowYellow7777/parabolic-chess](https://github.com/MellowYellow7777/parabolic-chess).
See [`web/parabolic/UPSTREAM.md`](web/parabolic/UPSTREAM.md) for details.

Only download and share content that you own or have permission to use.
