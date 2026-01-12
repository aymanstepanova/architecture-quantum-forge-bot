# Задание 6 — Автоматическое ежедневное обновление базы знаний (Docker Scheduler)

## Что сделано

- **Источник данных**: «сервер с API», получение документов **эмулируется** скриптом `download_naruto_pages.py` (он скачивает HTML и кладёт их в `raw_pages/`).
- **Авто-обновление**: `update_index.py` последовательно выполняет пайплайн как в `run_task2.py`:
  - `create_terms_map.py` (если нет `terms_map.json`)
  - `download_naruto_pages.py` → `raw_pages/`
  - `extract_text_from_html.py` → `cleaned_texts/`
  - `apply_replacements.py` → `knowledge_base/`
  - затем **пересобирает `vector_index/` через `build_index.py` только если изменилась `knowledge_base/*.txt`**
- **Состояние изменений**: `state/kb_hashes.json` (хэши файлов `knowledge_base/*.txt`)
- **Периодический запуск**: cron **внутри Docker** (через `docker-compose.yml`)

## Как запускать

### 1) Разовый запуск (проверка руками)

```bash
python update_index.py
```

Скрипт выводит краткую статистику изменений (сколько файлов изменилось) и, если нужно, пересобирает индекс.

### Важно про Windows и стабильность индекса

Если вы запускаете скрипт **не в Docker**, а напрямую на Windows, и видите ошибки вида `Error loading hnsw index`,
рекомендуется:
- запускать всё через Docker (Linux внутри контейнера), или
- вынести индекс в ASCII‑путь, задав переменную `VECTOR_DB_DIR` (например `C:\tmp\vector_index`).

### 2) Ежедневный запуск через Docker cron

```bash
docker compose up -d --build
```

Расписание по умолчанию: **каждый день в 06:00 UTC** (переменная `CRON_SCHEDULE` в `docker-compose.yml`).

Посмотреть логи cron:

```bash
docker compose logs -f kb-updater
```

## Что происходит при ошибках

- Если любой шаг пайплайна падает — скрипт печатает ошибку и завершает работу.

## Как проверить, что индекс пересобирается только при изменениях

1. Запустите `python update_index.py` два раза подряд.
2. Во второй раз вы должны увидеть: **“Изменений нет — индекс не пересобираю.”**

## Файлы задания

- `update_index.py` — скрипт обновления пайплайна + rebuild индекса при изменениях
- `docker-compose.yml`, `Dockerfile`, `entrypoint.sh`, `crontab` — Docker планировщик (cron)
- `requirements_task6.txt` — зависимости
- `update_architecture.puml` — архитектурная диаграмма (PlantUML)

