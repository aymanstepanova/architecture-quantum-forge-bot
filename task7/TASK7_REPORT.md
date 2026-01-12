# Задание 7. Аналитика покрытия и качества базы знаний

## Цель
Оценить полноту/покрытие базы знаний для RAG-бота, найти «слепые зоны» (темы без ответа), и задать повторяемый способ автоматической проверки качества через **golden set**.

## Что сделано

- **Искусственные пробелы в базе**: скрипт [`task7/create_gaps.py`](task7/create_gaps.py)
  - Убирает (безопасно перемещает) 3 сущности из `knowledge_base/`:
    - `Matatabi.txt` (термин нового мира: Kitekat)
    - `Five_Great_Shinobi_Countries.txt` (Five Great Operative Countries)
    - `Genin.txt` (ранг: Initiate)
  - Пересобирает индекс в отдельную директорию: `task7/vector_index_gapped/`
  - Пишет состояние запуска в: `task7/removed_entities.json`

- **Логирование запросов**: модуль [`task7/rag_logger.py`](task7/rag_logger.py)
  - Формат логов: **JSONL**
  - Поля: query, timestamp, chunks_found, chunks_relevant, answer_length, answer, sources, is_successful, relevance_scores, has_reasoning, response_time_ms (+ category/expected)

- **Golden set**: [`task7/golden_questions.txt`](task7/golden_questions.txt)
  - 6–8 вопросов на известные темы
  - 3–5 вопросов на удалённые темы (должен честно отвечать «не знаю»)
  - 2–3 вопроса на отсутствующие темы

- **Автотестирование**: [`task7/evaluate.py`](task7/evaluate.py)
  - Прогоняет вопросы по очереди через `RAGBot`
  - Записывает подробные логи в `task7/logs.jsonl`
  - Сохраняет метрики и результаты в `task7/evaluation_results.json`

- **Анализ логов**: [`task7/analyze_logs.py`](task7/analyze_logs.py)
  - Генерирует сводный отчёт: `task7/analysis_report.md`

- **Диаграмма**: [`task7/evaluation_sequence.puml`](task7/evaluation_sequence.puml)
  - Sequence diagram процесса оценки (evaluate → RAGBot → VectorStore → LLM → logger → анализ)

## Как запускать (репродьюс)

1) Создать пробелы и пересобрать индекс для теста:

```bash
python task7/create_gaps.py --apply
```

2) Прогнать golden set и получить логи/метрики:

```bash
# пример под Ollama
python task7/evaluate.py --llm-provider ollama --llm-model mistral

# пример под OpenAI (нужен ключ)
# set OPENAI_API_KEY=...
# python task7/evaluate.py --llm-provider openai --llm-model gpt-4
```

3) Проанализировать логи:

```bash
python task7/analyze_logs.py
```

## Результаты (после прогона)

- Логи: `task7/logs.jsonl`
- Итоговые метрики: `task7/evaluation_results.json`
- Аналитический отчёт: `task7/analysis_report.md`

Примечание:
- `evaluation_results.json` — метрики **последнего прогона** (accuracy, разрез по категориям, детали по каждому вопросу).
- `analysis_report.md` строится по `logs.jsonl` и может агрегировать **несколько прогонов**, если лог не очищать между запусками.

В `analysis_report.md` будут видны:
- какие запросы чаще всего проваливаются (бот «не отвечает»)
- какие источники попадают в неуспешные случаи
- случаи с низкой релевантностью (высокий avg_score)
- базовые распределения по времени ответа и длине ответа

## Выводы и рекомендации (шаблон)

После прогона и анализа нужно зафиксировать:

1) **Какие темы плохо покрыты** (топ провалов из `analysis_report.md`).
2) **Сколько пробелов выявлено** (кол-во «ожидаемо не знаю», но бот отвечает / и наоборот).
3) **Рекомендации**:
   - добавить/расширить документы по темам провалов
   - улучшить чанкинг (размер/перекрытие), если релевантность низкая
   - добавить нормализацию/расширение запросов (если пользователи задают вопрос «старыми» терминами)

