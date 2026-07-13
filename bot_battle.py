"""bot_battle.py — запускает два экземпляра LLM из cattemis_bot и заставляет их разговаривать.

Запуск из корня репо (рядом с папкой cattemis_bot/):

    python bot_battle.py

Переменные окружения берутся из .env как обычно.
"""

import asyncio
import sys
import os

# Чтобы импорты cattemis_bot работали
sys.path.insert(0, os.path.dirname(__file__))

from cattemis_bot.llm import ask_llm

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

ROUNDS = 10          # сколько обменов реплик
DELAY = 1.5          # пауза между репликами (секунды)
FIRST_MESSAGE = "Привет! Расскажи что-нибудь интересное о себе."

# Два разных chat_id — у каждого своя история диалога
CHAT_ID_A = 9000001
CHAT_ID_B = 9000002

# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------

async def battle() -> None:
    print("=" * 50)
    print("🐾 Bot Battle начинается! Meow meow")
    print("=" * 50)

    message = FIRST_MESSAGE
    print(f"\n[Затравка]: {message}\n")

    for i in range(ROUNDS):
        # Бот A отвечает на последнее сообщение
        reply_a = await ask_llm(CHAT_ID_A, message, user_name="BotB")
        print(f"[Bot A, раунд {i+1}]: {reply_a}\n")
        await asyncio.sleep(DELAY)

        # Бот B отвечает на реплику A
        reply_b = await ask_llm(CHAT_ID_B, reply_a, user_name="BotA")
        print(f"[Bot B, раунд {i+1}]: {reply_b}\n")
        await asyncio.sleep(DELAY)

        # Следующий раунд — B передаёт слово обратно A
        message = reply_b

    print("=" * 50)
    print("🐾 Конец! Meow~")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(battle())
