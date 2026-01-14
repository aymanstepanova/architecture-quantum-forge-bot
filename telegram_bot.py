"""
Telegram-бот интерфейс для RAGBot.

Использует python-telegram-bot (v20+), long polling.
Каждое сообщение обрабатывается независимо (без истории диалога).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Iterable, List

from telegram import Update
from telegram.constants import ChatAction
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from rag_bot import RAGBot


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_bot")

# Не засвечиваем токен в логах httpx/httpcore (они логируют URL целиком).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def _split_telegram_message(text: str, max_len: int = 4000) -> List[str]:
    """
    Telegram ограничивает сообщение ~4096 символов. Делаем запас и режем по строкам/пробелам.
    """
    text = (text or "").strip()
    if not text:
        return ["(пустой ответ)"]

    parts: List[str] = []
    cur = text
    while len(cur) > max_len:
        cut = cur.rfind("\n", 0, max_len)
        if cut == -1:
            cut = cur.rfind(" ", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(cur[:cut].rstrip())
        cur = cur[cut:].lstrip()
    if cur:
        parts.append(cur)
    return parts


def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return val


def _init_rag_bot() -> RAGBot:
    """
    Инициализация тяжёлая (загрузка индекса + модель/клиент). Делаем один раз на процесс.
    """
    logger.info("Инициализация RAGBot...")
    bot = RAGBot(
        llm_provider=os.getenv("LLM_PROVIDER"),
        llm_model=os.getenv("LLM_MODEL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL"),
    )
    logger.info("RAGBot готов (provider=%s, model=%s)", bot.llm_provider, bot.llm_model)
    return bot


# Один экземпляр на процесс
RAG = _init_rag_bot()


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    await update.message.reply_text(
        "Привет! Я RAG-бот.\n\n"
        "Просто напишите вопрос — я попробую ответить на основе базы знаний.\n"
        "Команды:\n"
        "/help — помощь\n"
        "/status — текущие настройки"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    await update.message.reply_text(
        "Как пользоваться:\n"
        "- отправьте текстовый вопрос одним сообщением\n\n"
        "Примеры:\n"
        "- Что такое Crimson Lens?\n"
        "- Кто такой Kael Vexaris?\n\n"
        "Если информации нет в базе знаний — я отвечу «Я не знаю»."
    )


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    await update.message.reply_text(
        "Статус:\n"
        f"- LLM_PROVIDER: {RAG.llm_provider}\n"
        f"- LLM_MODEL: {RAG.llm_model}\n"
        f"- K_CHUNKS: {RAG.k_chunks}"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    if not update.message or not update.message.text:
        return

    query = update.message.text.strip()
    if not query:
        return

    try:
        # typing — необязательная операция, на сетевых сбоях не валим обработку
        try:
            await update.message.chat.send_action(action=ChatAction.TYPING)
        except (TimedOut, NetworkError):
            pass

        # RAGBot синхронный; чтобы не блокировать event loop — в thread
        answer = await asyncio.to_thread(RAG.chat, query, False, True)

        for part in _split_telegram_message(answer):
            # Иногда Telegram API может рвать соединение/тормозить — делаем 2 попытки.
            last_exc: Exception | None = None
            for attempt in range(2):
                try:
                    await update.message.reply_text(part)
                    last_exc = None
                    break
                except (TimedOut, NetworkError) as e:
                    last_exc = e
                    await asyncio.sleep(1.0 + attempt)
            if last_exc is not None:
                raise last_exc
    except Exception as e:
        logger.exception("Ошибка обработки сообщения: %s", e)
        await update.message.reply_text(
            "❌ Ошибка при обработке запроса. Проверьте логи контейнера rag-bot."
        )


def main() -> None:
    token = _require_env("TELEGRAM_BOT_TOKEN")

    # Увеличиваем таймауты: иначе при долгом ответе/сети может падать sendMessage.
    tg_request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
    )
    application = ApplicationBuilder().token(token).request(tg_request).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Запуск Telegram-бота (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

