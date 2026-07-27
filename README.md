# cattemis-bot — Go edition

Полная Go-версия Telegram-бота `cattemis-bot`, объединяющая возможности актуального
Python-репозитория и приложенного Rust-проекта. Сам бот и Mini App API написаны на Go.
TypeScript используется только для интерфейса Mini App, а Node.js — для отдельного
режима Parabolic Chess.

## Что умеет бот

- скачивает фото, видео и карусели из TikTok, Instagram, X/Twitter, YouTube и Reddit;
- прикладывает подпись/описание исходной публикации ко всем поддерживаемым платформам;
- поддерживает прямые ссылки на изображения и видео;
- отправляет карусели альбомами по 10 файлов и проверяет лимиты Telegram;
- общается через любой OpenAI-совместимый API, включая OpenRouter;
- передаёт LLM фотографии, несколько кадров видео и расшифровку аудио/видео;
- подхватывает весь альбом, если пользователь отвечает на один из ранее отправленных ботом файлов;
- предоставляет LLM инструменты `current_time` и необязательный `web_search`;
- удаляет неподдерживаемые ссылки не-администраторов в группах;
- хранит дополнительные разрешённые домены после `/allowlink example.com`;
- принимает поддержку через Telegram Stars и необязательную кнопку Ko-fi;
- ведёт статистику процесса и отдельную историю LLM для каждого чата;
- автоматически обновляет кнопку Mini App при смене адреса Cloudflare Quick Tunnel.

## Игры

Mini App сохраняет все игры исходного репозитория и добавляет Flappy Kat из Rust-версии:

| Игра | Режимы |
|---|---|
| Крестики-нолики | бот, приватная комната, публичный поиск |
| Шашки | бот, приватная комната, публичный поиск |
| Шахматы | бот, приватная комната, публичный поиск |
| Сапёр | 3 сложности, секундомер, звук/вибрация флажка, рекорды |
| Судоку | 3 сложности, секундомер, ошибки, рекорды |
| Flappy Kat | локальный рекорд и общая таблица лидеров |
| Общий холст | 1000×1000, общий постоянный прогресс |
| Parabolic Chess | сетевой режим через WebSocket |

Команды `/ttt` и `/checkers` также запускают игры прямо на inline-кнопках Telegram.
Чтобы вызвать другого пользователя, ответь командой на его сообщение или используй
`text_mention`.

## Быстрый запуск

1. Скопируй пример конфигурации и укажи токен:

   ```bash
   cp .env.example .env
   ```

2. Запусти все сервисы:

   ```bash
   docker compose up -d --build
   docker compose logs -f bot cloudflared web parabolic
   ```

По умолчанию собирается образ `runtime` с локальным Whisper. Если расшифровка не нужна,
укажи `DOCKER_TARGET=runtime-lite` и `WHISPER_ENABLED=false` — образ будет заметно меньше.

## LLM и медиа

Для OpenRouter:

```dotenv
LLM_ENABLED=true
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=...
LLM_MODEL=...
LLM_WEB_SEARCH_ENABLED=true
LLM_VISION_ENABLED=true
WHISPER_ENABLED=true
```

В личном чате бот отвечает на обычный текст и медиа. В группе сообщение должно одновременно:

1. содержать слово `мяу`;
2. быть ответом на сообщение бота или содержать `@username` бота.

`LLM_VIDEO_FRAME_COUNT` задаёт количество равномерно выбранных кадров (1–6).
`LLM_TIMEZONE` принимает IANA-имя (`Asia/Almaty`) или смещение (`+05:00`).

## Команды

| Команда | Назначение |
|---|---|
| `/help` | справка |
| `/app` | открыть Mini App |
| `/games` | выбрать Telegram HTML5 Game |
| `/ttt` | крестики-нолики в сообщении |
| `/checkers` | шашки в сообщении |
| `/donate` | Telegram Stars / Ko-fi |
| `/paysupport` | помощь с платежом |
| `/ping` | проверка доступности |
| `/stats` | статистика процесса |
| `/reset` | очистить историю LLM текущего чата |
| `/allowlink example.com` | разрешить домен (администратор/личный чат) |

## Telegram HTML5 Games

В `@BotFather` включи inline mode и создай игры с short name:

```text
tictactoe
minesweeper
sudoku
canvas
chess
parabolic_chess
checkers
flappy
```

Игровой callback получает подписанный HMAC-токен пользователя, поэтому таблицы лидеров и
мультиплеер работают и при запуске через HTML5 Game, и через обычный Telegram Mini App.

## Локальная проверка

```bash
gofmt -w cmd internal resources web/server
go test ./...

cd web/client
npm ci
npm run build
```

Проект не использует сторонние Go-модули: Telegram Bot API, загрузчики и LLM-клиент
реализованы на стандартной библиотеке. Во время работы нужны `yt-dlp`, `ffmpeg` и
`ffprobe`; для локальной расшифровки дополнительно нужен CLI `whisper`.

## Структура

```text
cmd/cattemis-bot/     точка входа
internal/bot/         команды, игры, модерация, медиа и состояние
internal/telegram/    Telegram Bot API
internal/downloader/  загрузчики платформ и yt-dlp fallback
internal/llm/         OpenAI-совместимый клиент и инструменты
resources/            единый strings.json
web/server/           Go API Mini App
web/client/           TypeScript Mini App
web/parabolic/        Parabolic Chess
cloudflared/          Cloudflare Quick Tunnel
```

Скачивай и распространяй только контент, на который у тебя есть права или разрешение автора.
