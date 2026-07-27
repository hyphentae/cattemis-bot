# cattemis-bot — Go edition

[English](README.md) | **Русский**

`cattemis-bot` — Telegram-бот для загрузки медиа, необязательный LLM-ассистент и
игровой Mini App. В этой версии сам бот и API Mini App переписаны на Go с
сохранением возможностей Python-проекта и полезных дополнений из Rust-версии.

TypeScript используется для интерфейса Mini App, а Node.js — для отдельного
сервиса Parabolic Chess.

## Возможности

- загружает фотографии, видео и карусели из TikTok, Instagram, X/Twitter,
  YouTube и Reddit;
- прикладывает подпись или описание исходной публикации для всех поддерживаемых
  платформ;
- поддерживает прямые ссылки на изображения и видео;
- отправляет карусели Telegram-альбомами до 10 файлов и проверяет ограничения
  размера;
- работает с OpenRouter и другими OpenAI-совместимыми API;
- передаёт LLM фотографии, выбранные кадры видео и расшифровку аудио или видео;
- восстанавливает весь сохранённый альбом, если пользователь отвечает на один
  из ранее отправленных ботом файлов;
- предоставляет LLM инструменты `current_time` и необязательный `web_search`;
- удаляет неподдерживаемые ссылки не-администраторов в группах;
- хранит дополнительные домены, разрешённые через `/allowlink example.com`;
- принимает Telegram Stars и может показывать необязательную кнопку Ko-fi;
- ведёт статистику процесса и отдельную историю LLM для каждого чата;
- автоматически обновляет кнопку Mini App при смене адреса Cloudflare Quick
  Tunnel.

## Игры

Mini App сохраняет все игры исходного проекта и добавляет Flappy Kat из
Rust-версии.

| Игра | Short name в BotFather | Режимы |
|---|---|---|
| Крестики-нолики | `tictactoe` | бот, приватная комната, публичный поиск |
| Сапёр | `minesweeper` | 3 сложности, секундомер, звук/вибрация флажка, рекорды |
| Судоку | `sudoku` | 3 сложности, секундомер, ошибки, рекорды |
| Общий холст | `canvas` | постоянный общий холст 1000×1000 |
| Шахматы | `chess` | бот, приватная комната, публичный поиск |
| Parabolic Chess | `parabolic_chess` | сетевой режим через WebSocket |
| Шашки | `checkers` | бот, приватная комната, публичный поиск |
| Flappy Kat | `flappy` | локальный рекорд и общая таблица лидеров |

Команды `/ttt` и `/checkers` также запускают игры прямо через inline-кнопки
Telegram. Чтобы вызвать другого пользователя, ответь командой на его сообщение.

## Стек

- Go 1.24 — Telegram-бот, загрузчики, LLM-клиент, API Mini App, комнаты и
  таблицы лидеров;
- TypeScript 5 и Vite — интерфейс Mini App;
- Node.js, Express и WebSocket — Parabolic Chess;
- `yt-dlp`, FFmpeg и FFprobe — обработка медиа и резервные загрузчики;
- необязательный OpenAI Whisper CLI — локальная расшифровка аудио и видео;
- Docker Compose и Cloudflare Quick Tunnel — запуск сервисов и HTTPS-доступ из
  Telegram.

Go-код использует только стандартную библиотеку.

## Быстрый запуск

Требуются Docker с Compose Plugin и Telegram-бот, созданный через
[@BotFather](https://t.me/BotFather).

1. Скопируй шаблон конфигурации:

   ```bash
   cp .env.example .env
   ```

2. Укажи как минимум токен бота в `.env`:

   ```dotenv
   BOT_TOKEN=123456789:telegram_bot_token
   ```

3. Собери и запусти все сервисы:

   ```bash
   docker compose up -d --build
   ```

4. Проверь состояние и логи:

   ```bash
   docker compose ps
   docker compose logs -f bot cloudflared web parabolic
   ```

Стандартный образ `runtime` включает локальный Whisper. Если расшифровка не
нужна, используй уменьшенный образ:

```dotenv
DOCKER_TARGET=runtime-lite
WHISPER_ENABLED=false
```

После запуска `cloudflared` записывает текущий адрес `trycloudflare.com` в общий
volume. Бот ждёт успешную healthcheck-проверку туннеля, а затем назначает
актуальный URL кнопке меню Telegram.

## LLM и анализ медиа

Пример конфигурации OpenRouter:

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

В личном чате бот отвечает на обычные текстовые и медиа-сообщения. В группе
LLM-запрос должен:

1. содержать слово `мяу`;
2. быть ответом на сообщение бота или содержать его `@username`.

`LLM_VIDEO_FRAME_COUNT` задаёт количество равномерно выбранных кадров видео и
принимает значения от 1 до 6. `LLM_TIMEZONE` принимает IANA-имя, например
`Asia/Almaty`, или смещение UTC, например `+05:00`.

Все доступные настройки перечислены в [`.env.example`](.env.example). Файл
`.env` исключён из Git; никогда не публикуй токены бота и API-ключи.

## Команды бота

| Команда | Назначение |
|---|---|
| `/start` | запустить бота |
| `/help` | показать справку |
| `/app` | открыть Mini App |
| `/games` | открыть выбор HTML5-игр |
| `/ttt` | крестики-нолики в сообщениях Telegram |
| `/checkers` | шашки в сообщениях Telegram |
| `/donate` | поддержать бота через Telegram Stars или Ko-fi |
| `/paysupport` | показать информацию о поддержке платежей |
| `/ping` | проверить доступность бота |
| `/stats` | показать статистику текущего процесса |
| `/reset` | очистить историю LLM текущего чата |
| `/allowlink example.com` | разрешить домен в личном чате или от имени администратора |

## Настройка Telegram HTML5 Games

В [@BotFather](https://t.me/BotFather):

1. включи inline-режим через `/setinline`;
2. создай восемь игр через `/newgame`;
3. используй точные short name из таблицы «Игры»;
4. убедись, что игры принадлежат тому же боту, чей `BOT_TOKEN` хранится в
   `.env`.

Short name должен совпадать буквально. Неверное имя может привести к отклонению
всего списка inline-результатов с ошибкой `GAME_INVALID`.

Игры можно открыть из любого чата:

```text
@cattemis_bot
@cattemis_bot chess
```

Или по прямой ссылке:

```text
https://t.me/cattemis_bot?game=chess
```

Игровой callback получает подписанный HMAC-токен пользователя, поэтому таблицы
лидеров и мультиплеер работают как через Telegram HTML5 Games, так и через
обычный Mini App.

## Локальная проверка

```bash
gofmt -w cmd internal resources web/server
go test ./...
go vet ./...

cd web/client
npm ci
npm run build
```

Для работы бота требуются `yt-dlp`, `ffmpeg` и `ffprobe`. Для локальной
расшифровки дополнительно нужен CLI `whisper`.

## Структура репозитория

```text
cmd/cattemis-bot/     точка входа приложения
internal/bot/         команды, игры, модерация, медиа и состояние
internal/telegram/    клиент Telegram Bot API
internal/downloader/  загрузчики платформ и yt-dlp fallback
internal/llm/         OpenAI-совместимый клиент и инструменты
resources/            общий strings.json
web/server/           Go API Mini App
web/client/           TypeScript Mini App
web/parabolic/        сервис Parabolic Chess
cloudflared/          Cloudflare Quick Tunnel
```

## Атрибуция

Интеграция Parabolic Chess основана на проекте
[MellowYellow7777/parabolic-chess](https://github.com/MellowYellow7777/parabolic-chess).
Подробности находятся в [`web/parabolic/UPSTREAM.md`](web/parabolic/UPSTREAM.md).

Загружай и распространяй только контент, на который у тебя есть права или
разрешение автора.
