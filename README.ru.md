# cattemis-bot

[English](README.md) | **Русский**

`cattemis-bot` — Telegram-бот с загрузкой медиа, необязательным LLM-чатом и игровым Mini App. Проект запускается через Docker Compose: бот ждёт готовый Cloudflare Tunnel, получает его актуальный адрес и автоматически назначает Mini App кнопкой меню.

## Возможности

- загрузка медиа из TikTok, Instagram, X/Twitter, YouTube, Vimeo и прямых ссылок;
- отправка фото и видео в Telegram с проверкой размера;
- необязательный LLM-чат через OpenAI-совместимый API;
- необязательная расшифровка голосовых и аудио через Whisper;
- модерация ссылок и команда отправки сообщений от имени бота;
- запуск Mini App из кнопки меню, команды `/games` или inline-режима;
- Catppuccin Mocha-интерфейс, адаптированный для Telegram WebView.

## Игры

| Игра | Short name в BotFather | Режимы |
|---|---|---|
| Крестики-нолики | `tictactoe` | бот, комната по коду, публичный поиск |
| Сапёр | `minesweeper` | лёгкий, средний, сложный |
| Судоку | `sudoku` | одиночная игра |
| Общий холст | `canvas` | общий холст 1000×1000, один пиксель в 10 секунд |
| Шахматы | `chess` | комната по коду, публичный поиск |
| Parabolic Chess | `parabolic_chess` | сетевой режим через WebSocket |
| Шашки | `checkers` | бот, комната по коду, публичный поиск |
| Deltarune | `deltarune` | Project Vinetrap внутри Mini App |

Комнаты обычных шахмат, шашек и крестиков-ноликов хранятся в памяти и сбрасываются при перезапуске контейнера `web`. Общий холст хранится в Docker volume `canvas` и переживает перезапуск.

## Стек

- Python 3.12, aiogram и pydantic-settings — Telegram-бот;
- Go 1.23 — Mini App, API комнат, шахмат, шашек и общего холста;
- Node.js 22, Express и WebSocket — Parabolic Chess;
- Docker Compose и Cloudflare Quick Tunnel — запуск сервисов и HTTPS-доступ из Telegram.

## Быстрый запуск

Требуются Docker с Compose Plugin и Telegram-бот, созданный через [@BotFather](https://t.me/BotFather).

1. Создай `.env` в корне проекта:

   ```dotenv
   BOT_TOKEN=123456789:telegram_bot_token

   # Необязательно: Instagram через Apify
   APIFY_TOKEN=
   APIFY_INSTAGRAM_ACTOR=elis~instagram-downloader-api

   # Необязательно: LLM
   LLM_ENABLED=false
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_API_KEY=dummy
   LLM_MODEL=gemma4:e4b

   # Необязательно: Whisper
   WHISPER_ENABLED=false
   WHISPER_MODEL_SIZE=base
   WHISPER_DEVICE=cpu
   WHISPER_COMPUTE_TYPE=int8
   ```

2. Собери и запусти сервисы:

   ```bash
   docker compose up -d --build
   ```

3. Проверь состояние и логи:

   ```bash
   docker compose ps
   docker compose logs -f bot cloudflared web parabolic
   ```

После старта `cloudflared` записывает текущий адрес `trycloudflare.com` в общий volume. Контейнер `bot` запускается только после успешной healthcheck-проверки туннеля, а затем назначает этот URL кнопке меню Telegram.

Перезапуск отдельного сервиса:

```bash
docker compose restart bot
docker compose restart web
```

После изменений исходников, встроенных в образ, сервис нужно пересобрать:

```bash
docker compose up -d --build web
```

## Настройка Telegram HTML5 Games

В [@BotFather](https://t.me/BotFather):

1. включи inline-режим через `/setinline`;
2. создай через `/newgame` восемь игр с short name из таблицы выше;
3. убедись, что игры созданы именно для того бота, чей `BOT_TOKEN` находится в `.env`.

Short name должен совпадать буквально. Если хотя бы одно имя неверно, Telegram может отклонить всю inline-выдачу с ошибкой `GAME_INVALID`.

Игры можно вызвать в любом чате:

```text
@cattemis_bot
@cattemis_bot chess
```

Или открыть прямой ссылкой:

```text
https://t.me/cattemis_bot?game=chess
```

Обработчик callback формирует актуальный адрес игры с подписанным идентификатором Telegram-пользователя. Секрет подписи — `BOT_TOKEN`; он передаётся контейнерам `bot` и `web`, но не попадает в URL.

## Команды бота

| Команда | Назначение |
|---|---|
| `/help` | справка |
| `/ping` | проверка доступности бота |
| `/games` | выбор зарегистрированной HTML5-игры |
| `/ttt` | крестики-нолики в сообщениях Telegram |
| `/checkers` | шашки в сообщениях Telegram |
| `/say_cattemis <текст>` | отправить текст от имени бота; в группах доступно администраторам |
| `/stats` | статистика текущего процесса |
| `/reset` | очистить историю LLM для текущего чата |

## Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|---|---:|---|
| `BOT_TOKEN` | — | обязательный токен Telegram Bot API |
| `APIFY_TOKEN` | пусто | токен Apify для Instagram |
| `APIFY_INSTAGRAM_ACTOR` | `elis~instagram-downloader-api` | actor для Instagram |
| `LLM_ENABLED` | `false` | включить LLM-ответы |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-совместимый endpoint |
| `LLM_API_KEY` | `dummy` | ключ LLM endpoint |
| `LLM_MODEL` | `gemma4:e4b` | название модели |
| `LLM_SYSTEM_PROMPT` | встроенный | системный промпт |
| `LLM_COOLDOWN_SECONDS` | `5.0` | задержка перед LLM-запросом |
| `LLM_MAX_TOKENS` | `480` | максимальный ответ LLM |
| `LLM_TEMPERATURE` | `0.6` | температура генерации |
| `LLM_WEB_SEARCH_ENABLED` | `false` | включить веб-поиск для LLM |
| `LLM_WEB_SEARCH_MAX_RESULTS` | `5` | число результатов веб-поиска |
| `WHISPER_ENABLED` | `false` | включить транскрибацию |
| `WHISPER_MODEL_SIZE` | `base` | размер модели Whisper |
| `WHISPER_DEVICE` | `cpu` | устройство Whisper |
| `WHISPER_COMPUTE_TYPE` | `int8` | тип вычислений Whisper |
| `MAX_MEDIA_ITEMS` | `10` | файлов в одной загрузке |
| `MAX_FILE_SIZE` | `52428800` | предел одного файла в байтах |
| `RETRY_ATTEMPTS` | `2` | число повторных попыток загрузки |
| `RETRY_DELAY` | `1.2` | задержка между попытками |
| `ADMIN_CACHE_TTL` | `60` | TTL списка администраторов |
| `MAX_HISTORY_MESSAGES` | `8` | сообщений в истории LLM |
| `WEB_ENABLED` | `true` | флаг веб-приложения |
| `WEB_PORT` | `8080` | порт веб-приложения |
| `USE_CLOUDFLARE` | `true` | ожидать Cloudflare Tunnel и назначать Menu Button |

`.env` исключён из Git. Не публикуй токен бота и API-ключи.

## Архитектура

```text
Telegram
   │
   ├── Bot API ───────────────► bot (Python / aiogram)
   │                                │
   │                                └── читает URL туннеля из volume
   │
   └── Mini App WebView ──────► cloudflared
                                      │
                                      ▼
                                web (Go :8080)
                                  │       │
                                  │       └── volume canvas
                                  ▼
                            parabolic (Node :3000)
```

## Структура репозитория

```text
cattemis_bot/      Python-пакет бота, обработчики и загрузчики
cloudflared/       контейнер Quick Tunnel и публикация его URL
web/server/        Go API и сервер статических файлов
web/static/        HTML, CSS и JavaScript Mini App
web/parabolic/     отдельный Node/WebSocket-сервис Parabolic Chess
docker-compose.yml оркестрация сервисов и volumes
run.py             точка входа контейнера бота
```

## Проверка изменений

```bash
PYTHONPYCACHEPREFIX=/tmp/cattemis-pycache python -m compileall -q cattemis_bot
docker build -t cattemis-web-check web/server
docker build -t cattemis-parabolic-check web/parabolic
docker compose config -q
```

Go-тесты запускаются на этапе сборки `web/server`.

## Attribution

Интеграция Parabolic Chess основана на проекте [MellowYellow7777/parabolic-chess](https://github.com/MellowYellow7777/parabolic-chess). Подробности находятся в [`web/parabolic/UPSTREAM.md`](web/parabolic/UPSTREAM.md).
