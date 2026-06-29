import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GambleOutcome:
    max_roll: int
    title: str
    text: str
    multiplier: str
    art_prize: bool = False


GAMBLE_OUTCOMES = [
    GambleOutcome(
        5,
        "Джекпот",
        "Каттемис нашёл выигрыш в чёрной шкатулке. Сейчас попробую выдать призовой артик.",
        "x5",
        art_prize=True,
    ),
    GambleOutcome(
        20,
        "Крупный выигрыш",
        "Ставка прошла сквозь туман и вернулась с процентами.",
        "x3",
    ),
    GambleOutcome(
        55,
        "Маленький плюс",
        "Не богатство, но свечи сегодня горят в твою сторону.",
        "x1.5",
    ),
    GambleOutcome(
        85,
        "Проигрыш",
        "Кубики легли холодной стороной. Бывает.",
        "x0",
    ),
    GambleOutcome(
        100,
        "Критический проигрыш",
        "Дом забрал ставку и оставил драматичную паузу.",
        "x0",
    ),
]


def pick_gamble_outcome() -> tuple[int, GambleOutcome]:
    roll = random.randint(1, 100)
    for outcome in GAMBLE_OUTCOMES:
        if roll <= outcome.max_roll:
            return roll, outcome
    return roll, GAMBLE_OUTCOMES[-1]


def compact_payload(text: str, limit: int = 80) -> str:
    text = re.sub(r"[ \t]{2,}", " ", (text or "").strip())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def gamble_payload(raw_text: str) -> str:
    payload = raw_text.partition(" ")[2].strip()
    return compact_payload(payload)


def gamble_plan_text() -> str:
    return (
        "План /gamble:\n"
        "1. MVP без базы: бросок 1-100, весовые исходы, текстовый результат, редкий арт-приз.\n"
        "2. Если нужен прогресс: SQLite-кошелёк, дневной бонус, cooldown, журнал транзакций.\n"
        "3. Антиабуз: лимит ставок на чат/пользователя, запрет отрицательных ставок, lock на чат.\n"
        "4. Контент: отдельные таблицы исходов для обычного и гот-режима, редкие медиа-призы через существующий downloader.\n"
        "5. Админка: /gamble_config для шансов, лимитов и включения экономики."
    )
