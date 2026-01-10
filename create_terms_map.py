"""create_terms_map.py

Скрипт для создания словаря замен терминов из мира Наруто
Генерирует вымышленные названия для персонажей, техник, деревень и других сущностей
"""

from __future__ import annotations

import json
import os
from datetime import datetime

# -----------------------------
# 1) БАЗОВЫЙ СЛОВАРЬ
# -----------------------------
TERMS_MAP_BASE: dict[str, str] = {
    # Персонажи
    "Uzumaki": "Vexaris",  # клановое имя
    "Naruto": "Kael",

    "Uchiha": "Noctryn", # клановое имя
    "Sasuke": "Sael",
    "Itachi": "Varyn",
    "Madara": "Malrec",
    "Obito": "Orin",


    "Hyuga": "Aurel", # клановое имя
    "Neji": "Nolan",
    "Hinata": "Helia",

    "Sakura Haruno": "Lyra Caelum",
    "Kakashi Hatake": "Riven Ashcroft",

    "Senju": "Prime",
    "Hashirama": "Haldor",
    "Tobirama": "Torren",
    "Hiruzen Sarutobi": "Eldric Vane",
    "Minato Namikaze": "Miren Flux",
    "Jiraiya": "Jax Orenthal",
    "Tsunade": "Thalia Merrow",
    "Orochimaru": "Oren Khelt",
    "Gaara": "Gareth Dune",
    "Rock Lee": "Rex Unbound",


    "Shikamaru Nara": "Silas Korr",
    "Choji Akimichi": "Corin Masson",
    "Ino Yamanaka": "Iris Vale",

    # Кланы (в Narutopedia часто "Clan")
    "Clan": "Line",

    "Uchiha Clan": "Noctryn Line",
    "Senju Clan": "Prime Line",
    "Hyuga Clan": "Aurel Line",
    "Uzumaki Clan": "Vexaris Line",
    "Nara Clan": "Korr Line",
    "Akimichi Clan": "Masson Line",
    "Yamanaka Clan": "Vale Line",

    # Деревни/локации
    "Konohagakure": "Verdant Reach",
    "Konoha": "Verdant Reach",
    "Sunagakure": "Ash Dunes",
    "Kirigakure": "Mistfall",
    "Kumogakure": "Highspire",
    "Iwagakure": "Stonebound",

    # Онтология (чтобы LLM не могла восстановить Naruto по памяти)
    "Chakra": "Axiom",
    "Jutsu": "Pattern",
    "Ninja": "Operative",
    "Shinobi": "Operative",

    # Ранги
    "Genin": "Initiate",
    "Chunin": "Binder",
    "Jonin": "Executor",
    "Sannin": "Geezer", # все саннины - старикашки, логично же

    # Титулы
    "Kage": "Warden",
    "Hokage": "Verdant Warden",
    "Kazekage": "Dune Warden",
    "Mizukage": "Mist Warden",
    "Raikage": "Spire Warden",
    "Tsuchikage": "Stone Warden",

    # Техники/концепты
    "Rasengan": "Axiom Spiral",
    "Rasenshuriken": "Fracture Spiral",
    "Chidori": "Impulse Arc",
    "Shadow Clone Technique": "Echo Manifest",
    "Sage Mode": "Primal Alignment",
    "Eight Gates": "Eight Seals",

    # Глаза/способности
    "Sharingan": "Crimson Lens",
    "Rinnegan": "Parallax Eye",
    "Byakugan": "Clear Sight",

    # Легендарные способности
    "Amaterasu": "Black Pyre",
    "Susanoo": "Aegis Manifest",
    "Kamui": "Phase Fold",
    "Tsukuyomi": "Lucid Snare",
    "Izanagi": "Causal Override",
    "Izanami": "Recursive Bind",

    # Хвостатые звери
    "Nine-Tailed Fox": "Ninefold Apex",
    "Kurama": "Korvax",
    "One-Tailed Shukaku": "Dune Apex",
    "Shukaku": "Shakor",
    "Eight-Tailed Gyuki": "Storm Apex",
    "Gyuki": "Gryx",
    "Matatabi": "Kitekat",

    # Организации
    "Akatsuki": "Red Covenant",
    "ANBU": "Black Cell",

    # События
    "Chunin Exams": "Initiate Trials",
    "Great Ninja War": "Continental Conflict",
    "Fourth Great Ninja War": "Fourth Continental Conflict",
}


# -----------------------------
# 2) ДОБАВЛЕНИЕ ВАРИАНТОВ НАПИСАНИЯ
# -----------------------------

def with_diacritics(base_map: dict[str, str]) -> dict[str, str]:
    """Добавляет в карту распространенные варианты с макронами (Hyūga, Chūnin, Jōnin).

    Мы делаем это именно здесь (в terms_map.json), потому что apply_replacements.py
    ищет по ключам из JSON (пусть и с IGNORECASE), но НЕ нормализует диакритику.
    """

    extended = dict(base_map)

    # Hyuga -> Hyūga (персонажи и клан)
    macrons = {
        "Hyuga": "Hyūga",
        "Chunin": "Chūnin",
        "Jonin": "Jōnin",
    }

    for plain, macron in macrons.items():
        # пробегаем по ключам, где встречается plain, добавляем вариант с macron
        for k, v in list(extended.items()):
            if plain in k:
                extended[k.replace(plain, macron)] = v

    return extended


# -----------------------------
# 3) README для knowledge_base/
# -----------------------------

def write_kb_readme(output_dir: str, terms_map: dict[str, str]) -> None:
    os.makedirs(output_dir, exist_ok=True)

    # Небольшая «паспортная» информация + краткая логика подмены
    lines = []
    lines.append("# Knowledge Base (Task 2)\n")
    lines.append("Эта папка содержит уникальную базу знаний для проверки RAG.\n")
    lines.append("Исходные тексты взяты из Narutopedia, затем очищены от HTML и переписаны через подмену терминов.\n")

    lines.append("## Принцип подмены терминов\n")
    lines.append("- Подмена не является переводом: изменена онтология мира (например, `Chakra → Axiom`, `Jutsu → Pattern`).")
    lines.append("- Термины заменяются так, чтобы модель не могла восстановить вселенную по памяти.")
    lines.append("- Для совместимости добавлены варианты написания с диакритикой (Hyūga, Chūnin, Jōnin).\n")

    lines.append("## Файлы\n")
    lines.append("- `terms_map.json` — словарь замен (лежит в корне репозитория и копируется в эту папку на последнем шаге).")
    lines.append("- `replacement_metadata.json` — статистика замен (создаётся скриптом `apply_replacements.py`).")
    lines.append("\n")

    # Короткий сэмпл, чтобы README выглядел «живым», но не раздувать файл
    sample_keys = [
        "Naruto Uzumaki",
        "Konoha",
        "Chakra",
        "Jutsu",
        "Hokage",
        "Akatsuki",
        "Sharingan",
        "Chunin Exams",
    ]
    lines.append("## Примеры замен\n")
    for k in sample_keys:
        if k in terms_map:
            lines.append(f"- `{k}` → `{terms_map[k]}`")

    lines.append("\n")
    lines.append(f"_Сгенерировано: {datetime.now().isoformat(timespec='seconds')}_\n")

    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# -----------------------------
# 4) MAIN
# -----------------------------

def main() -> None:
    print("Создание словаря замен терминов...")

    terms_map = with_diacritics(TERMS_MAP_BASE)

    # Пишем terms_map.json в корень (ожидается apply_replacements.py)
    out_path = "terms_map.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(terms_map, f, ensure_ascii=False, indent=2)

    print(f"✓ Сохранено: {out_path}")
    print(f"✓ Терминов: {len(terms_map)} (включая варианты с диакритикой)")

    # Создаем knowledge_base/README.md (директория может быть пустой до последнего шага)
    write_kb_readme("knowledge_base", terms_map)
    print("✓ Создано: knowledge_base/README.md")


if __name__ == "__main__":
    main()
