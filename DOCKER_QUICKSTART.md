# Быстрый старт: RAG-бот в Docker

## Архитектура

Система состоит из двух контейнеров:
- **kb-updater** — обновляет векторный индекс по расписанию (cron)
- **rag-bot** — чат-бот, который использует векторную БД для ответов

## Предварительные требования

- Docker и Docker Compose установлены
- Векторный индекс создан (папка `vector_index/`)
- База знаний готова (папка `knowledge_base/`)

## Шаг 1: Настройка переменных окружения

Создайте файл `.env` (опционально) или установите переменные:

```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key-here"
$env:LLM_PROVIDER="openai"

# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"
export LLM_PROVIDER="openai"
```

## Шаг 1.1: Создать Telegram-бота и получить токен

1) В Telegram откройте `@BotFather` → `/newbot`  
2) Задайте имя и username, получите токен вида `123456:ABC-DEF...`  
3) Установите токен в окружение:

```bash
# Windows (PowerShell)
$env:TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."

# Linux/Mac
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
```

**Для использования Ollama (бесплатно):**
```bash
# Windows
$env:LLM_PROVIDER="ollama"
$env:OLLAMA_BASE_URL="http://host.docker.internal:11434"

# Linux/Mac
export LLM_PROVIDER="ollama"
export OLLAMA_BASE_URL="http://host.docker.internal:11434"
```

## Шаг 2: Сборка образов

```bash
# Собрать оба контейнера
docker-compose build

# Или собрать только один
docker-compose build kb-updater
docker-compose build rag-bot
```

Примечание: `docker-compose.yml` собирает оба сервиса из **одного** `Dockerfile` с двумя `target`
(`kb-updater` и `rag-bot`). Общий слой зависимостей кешируется, поэтому пересборка обычно заметно быстрее.

### Ещё быстрее: pip cache через BuildKit (Windows PowerShell)

Важно: `--mount=type=cache` пишется **в Dockerfile** (у нас уже добавлено), а не в команду `docker-compose build`.

Включите BuildKit и соберите:

```powershell
$env:DOCKER_BUILDKIT=1
$env:COMPOSE_DOCKER_CLI_BUILD=1

# предпочтительно (новый compose-плагин)
docker compose build

# либо старый docker-compose
docker-compose build
```

## Шаг 3: Запуск системы

```bash
# Запустить оба контейнера
docker-compose up

# Или в фоновом режиме
docker-compose up -d

# Запустить только бота (если индекс уже обновлён)
docker-compose up rag-bot
```

## Шаг 4: Проверка работы

### Вариант A: Интерактивный Python

```bash
# Войти в контейнер
docker-compose exec rag-bot python

# В Python:
from rag_bot import RAGBot
bot = RAGBot()
bot.chat("Что такое Crimson Lens?")
```

### Вариант B: Запуск примеров

```bash
# Скопировать примеры в контейнер и запустить
docker-compose exec rag-bot python rag_bot_examples.py
```

### Вариант C: REPL интерфейс

```bash
# Запустить интерактивный режим
docker-compose exec rag-bot python rag_bot_repl.py
```

### Вариант D: Проверка Telegram-бота

1) Убедитесь, что `rag-bot` запущен:

```bash
docker-compose ps
docker-compose logs rag-bot
```

2) В Telegram найдите вашего бота и отправьте сообщение:
- `Что такое Crimson Lens?`
- `/status`

## Базовые примеры запросов

### Успешные вопросы (из базы знаний):
- "Что такое Crimson Lens?"
- "Кто такой Kael Vexaris?"
- "Какие способности даёт Crimson Lens?"
- "Что такое Axiom Spiral?"
- "Как работает Echo Manifest?"

### Вопросы, на которые бот ответит "Я не знаю":
- "Как приготовить борщ?"
- "Какая столица Франции?"
- "Напиши пузырьковую сортировку на Python."
- "Сколько будет 2+2?"
- "Какая погода в Москве сегодня?"

## Быстрая проверка

```bash
# 1. Проверить, что контейнеры запущены
docker-compose ps

# 2. Посмотреть логи
docker-compose logs rag-bot      # Логи бота
docker-compose logs kb-updater  # Логи обновления индекса

# 3. Выполнить тестовый запрос
docker-compose exec rag-bot python -c "from rag_bot import RAGBot; bot = RAGBot(); print(bot.chat('Что такое Crimson Lens?', verbose=False))"

# 4. Проверить расписание обновления индекса
docker-compose exec kb-updater cat /etc/cron.d/update_index
```

## Управление контейнерами

```bash
# Остановить все контейнеры
docker-compose down

# Остановить только бота
docker-compose stop rag-bot

# Перезапустить обновление индекса
docker-compose restart kb-updater

# Выполнить обновление индекса вручную (без ожидания cron)
docker-compose exec kb-updater python update_index.py

# Остановить и удалить volumes (осторожно!)
docker-compose down -v
```

## Настройка расписания обновления

По умолчанию индекс обновляется каждый день в 06:00 UTC. Чтобы изменить расписание:

```bash
# В docker-compose.yml или через переменную окружения
export CRON_SCHEDULE="0 */6 * * *"  # Каждые 6 часов
docker-compose up -d kb-updater
```

Формат cron: `минута час день месяц день_недели`
- `0 6 * * *` — каждый день в 06:00
- `0 */6 * * *` — каждые 6 часов
- `*/30 * * * *` — каждые 30 минут

## Устранение проблем

**Ошибка: "Векторный индекс не найден"**
→ Убедитесь, что папка `vector_index/` существует и содержит индекс

**Ошибка: "API ключ не найден"**
→ Установите `OPENAI_API_KEY` или используйте Ollama (`LLM_PROVIDER=ollama`)

**Ошибка: "Не задана переменная окружения TELEGRAM_BOT_TOKEN"**
→ Установите `TELEGRAM_BOT_TOKEN` и перезапустите `rag-bot`

**Ошибка: "Connection refused" (Ollama)**
→ Убедитесь, что Ollama запущен на хосте и используйте `host.docker.internal:11434`

**Ошибка: "Модуль не найден"**
→ Пересоберите образ: `docker-compose build --no-cache`

## Структура volumes

**Общие volumes (используются обоими контейнерами):**
- `./vector_index` → векторный индекс (ChromaDB) — **общая БД**
- `./knowledge_base` → база знаний (текстовые файлы)
- `./hf_cache` → кеш моделей HuggingFace

**Volumes только для kb-updater:**
- `./raw_pages` → исходные HTML страницы
- `./cleaned_texts` → очищенные тексты
- `./logs` → логи обновления индекса
- `./state` → состояние (хеши файлов для инкрементального обновления)

Все данные сохраняются на хосте и доступны после перезапуска контейнеров.

## Важно

- Контейнер `kb-updater` обновляет `vector_index`, который использует `rag-bot`
- Оба контейнера монтируют один и тот же `vector_index`, поэтому бот видит обновления сразу
- Если нужно пересобрать индекс вручную, используйте: `docker-compose exec kb-updater python update_index.py`
