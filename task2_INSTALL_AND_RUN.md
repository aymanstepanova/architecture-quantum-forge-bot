# Инструкция по выполнению задания 2

## Установка зависимостей

Сначала установите необходимые библиотеки:

```bash
pip install requests beautifulsoup4 lxml
```

Или используйте файл requirements:

```bash
pip install -r requirements_task2.txt
```

## Выполнение задания

Запустите скрипты в следующем порядке:

### Шаг 1: Создание словаря замен (уже выполнен)
```bash
python create_terms_map.py
```
Создает файл `terms_map.json` со словарем замен терминов.

### Шаг 2: Скачивание страниц из фандома
```bash
python download_naruto_pages.py
```
Скачивает HTML страницы из naruto.fandom.com в папку `raw_pages/`.

### Шаг 3: Извлечение текста из HTML
```bash
python extract_text_from_html.py
```
Извлекает чистый текст из HTML файлов и сохраняет в папку `cleaned_texts/`.

### Шаг 4: Применение замен терминов
```bash
python apply_replacements.py
```
Применяет замены из словаря к текстам и сохраняет финальные документы в `knowledge_base/`.

## Автоматический запуск

Или запустите все скрипты автоматически:

```bash
python run_task2.py
```

## Результат

После выполнения всех шагов вы получите:
- `knowledge_base/` - папка с 40+ обработанными документами
- `terms_map.json` - словарь замен терминов
- `knowledge_base/README.md` - описание базы знаний

