# Быстрый старт: RAG-бот (Задание 4)

## Шаг 1: Проверка готовности системы

```bash
python check_rag_setup.py
```

Этот скрипт проверит:
- ✓ Наличие векторного индекса
- ✓ Установленные зависимости
- ✓ Наличие API ключа OpenAI

## Шаг 2: Установка зависимостей (если нужно)

```bash
pip install -r requirements_task4.txt
```

## Шаг 3: Настройка LLM провайдера

**Вариант A: OpenAI API** (требует API ключ)
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key-here"

# Linux/Mac
export OPENAI_API_KEY="sk-your-key-here"
```

**Вариант B: Ollama** ⭐ Рекомендуется (бесплатно, без API ключей)
```bash
# 1. Установите Ollama: https://ollama.ai
# 2. Запустите: ollama serve
# 3. Загрузите модель: ollama pull llama3.2
# 4. Настройте:
$env:LLM_PROVIDER="ollama"  # Windows
export LLM_PROVIDER="ollama"  # Linux/Mac
```

См. `setup_ollama.md` для подробной инструкции.

## Шаг 4: Запуск

### Интерактивный режим (рекомендуется)
```bash
python rag_bot_repl.py
```

### Примеры диалогов
```bash
python rag_bot_examples.py
```

### Программное использование
```python
from rag_bot import RAGBot

# С OpenAI
bot = RAGBot(llm_provider="openai")
# Или с Ollama (бесплатно)
bot = RAGBot(llm_provider="ollama", llm_model="llama3.2")

answer = bot.chat("Что такое Sharingan?")
print(answer)
```

## Основные команды в REPL

- Просто введите вопрос для получения ответа
- `/help` - справка по командам
- `/exit` - выход
- `/status` - текущие настройки
- `/fewshot` - переключить Few-shot примеры
- `/cot` - переключить Chain-of-Thought

## Что реализовано

✅ Полный RAG-пайплайн (поиск → промптинг → генерация)  
✅ Few-shot prompting с примерами из базы знаний  
✅ Chain-of-Thought (модель объясняет шаги)  
✅ REPL интерфейс для интерактивного общения  
✅ Автоматическое расширение запросов и восстановление терминов  
✅ Обработка случаев "Я не знаю"  

## Структура файлов

- `rag_bot.py` - основной модуль RAG-бота
- `rag_bot_repl.py` - интерактивный интерфейс
- `rag_bot_examples.py` - примеры диалогов
- `check_rag_setup.py` - проверка готовности системы
- `README_task4.md` - полная документация

## Примеры вопросов

**Успешные вопросы (из базы знаний):**
- "Что такое Sharingan?"
- "Кто такой Naruto?"
- "Какие способности даёт Sharingan?"
- "Что такое Rasengan?"

**Вопросы, на которые бот ответит "Я не знаю":**
- "Как приготовить борщ?"
- "Какая столица Франции?"

## Устранение проблем

**Ошибка: "API ключ не найден" или "Превышена квота"**
→ Используйте Ollama: `ollama serve` и `$env:LLM_PROVIDER="ollama"`

**Ошибка: "Векторный индекс не найден"**
→ Запустите: `python build_index.py`

**Ошибка: "OpenAI не установлен"**
→ Установите: `pip install openai` (нужна даже для Ollama)

**Ошибка: "Connection refused" (Ollama)**
→ Убедитесь, что Ollama запущен: `ollama serve`

## Дополнительная информация

См. `README_task4.md` для полной документации.
