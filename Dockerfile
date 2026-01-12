# syntax=docker/dockerfile:1.5
#
# Единый Dockerfile с общим слоем зависимостей (deps) и двумя target:
# - kb-updater: обновление индекса по расписанию (cron)
# - rag-bot: Telegram-бот, использующий общий vector_index
#

FROM python:3.11-slim AS deps

WORKDIR /app

# Сначала зависимости (максимально кешируется).
# Ставим superset: индекс + актуализатор + Telegram/OpenAI.
COPY requirements_index.txt requirements_task6.txt requirements_bot.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements_task6.txt && \
    pip install -r requirements_bot.txt

# -----------------------------
# kb-updater target
# -----------------------------
FROM deps AS kb-updater

RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY update_index.py build_index.py ./
COPY create_terms_map.py download_naruto_pages.py extract_text_from_html.py apply_replacements.py ./
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV CRON_SCHEDULE="0 6 * * *"

ENTRYPOINT ["/app/entrypoint.sh"]

# -----------------------------
# rag-bot target
# -----------------------------
FROM deps AS rag-bot

WORKDIR /app

COPY rag_bot.py build_index.py telegram_bot.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "telegram_bot.py"]

