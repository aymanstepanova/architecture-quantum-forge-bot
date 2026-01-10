# Knowledge Base (Task 2)

Эта папка содержит уникальную базу знаний для проверки RAG.

Исходные тексты взяты из Narutopedia, затем очищены от HTML и переписаны через подмену терминов.

## Принцип подмены терминов

- Подмена не является переводом: изменена онтология мира (например, `Chakra → Axiom`, `Jutsu → Pattern`).
- Термины заменяются так, чтобы модель не могла восстановить вселенную по памяти.
- Для совместимости добавлены варианты написания с диакритикой (Hyūga, Chūnin, Jōnin).

## Файлы

- `terms_map.json` — словарь замен (лежит в корне репозитория и копируется в эту папку на последнем шаге).
- `replacement_metadata.json` — статистика замен (создаётся скриптом `apply_replacements.py`).


## Примеры замен

- `Konoha` → `Verdant Reach`
- `Chakra` → `Axiom`
- `Jutsu` → `Pattern`
- `Hokage` → `Verdant Warden`
- `Akatsuki` → `Red Covenant`
- `Sharingan` → `Crimson Lens`
- `Chunin Exams` → `Initiate Trials`


_Сгенерировано: 2026-01-11T02:46:40_
