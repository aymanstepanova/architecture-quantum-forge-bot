"""
Скрипт для скачивания страниц из naruto.fandom.com
Скачивает HTML страницы по списку URL и сохраняет их для дальнейшей обработки.

Улучшения:
- Рандомная пауза между запросами (меньше шансов капчи/антибота)
- Проверка валидности HTML (не сохраняем заглушки/капчу)
- Повторы (retries) с бэкоффом
- Сохранение "плохих" HTML в raw_pages/failed для отладки
"""

import os
import time
import json
import random
from urllib.parse import urlparse

import requests

# Список ключевых страниц из мира Наруто (40+)
NARUTO_PAGES = [
    # Персонажи
    "https://naruto.fandom.com/wiki/Naruto_Uzumaki",
    "https://naruto.fandom.com/wiki/Sasuke_Uchiha",
    "https://naruto.fandom.com/wiki/Sakura_Haruno",
    "https://naruto.fandom.com/wiki/Kakashi_Hatake",
    "https://naruto.fandom.com/wiki/Itachi_Uchiha",
    "https://naruto.fandom.com/wiki/Madara_Uchiha",
    "https://naruto.fandom.com/wiki/Obito_Uchiha",
    "https://naruto.fandom.com/wiki/Hashirama_Senju",
    "https://naruto.fandom.com/wiki/Tobirama_Senju",
    "https://naruto.fandom.com/wiki/Hiruzen_Sarutobi",
    "https://naruto.fandom.com/wiki/Minato_Namikaze",
    "https://naruto.fandom.com/wiki/Jiraiya",
    "https://naruto.fandom.com/wiki/Tsunade",
    "https://naruto.fandom.com/wiki/Orochimaru",
    "https://naruto.fandom.com/wiki/Gaara",
    "https://naruto.fandom.com/wiki/Rock_Lee",
    "https://naruto.fandom.com/wiki/Neji_Hyuga",
    "https://naruto.fandom.com/wiki/Hinata_Hyuga",
    "https://naruto.fandom.com/wiki/Shikamaru_Nara",
    "https://naruto.fandom.com/wiki/Choji_Akimichi",
    "https://naruto.fandom.com/wiki/Ino_Yamanaka",
    "https://naruto.fandom.com/wiki/Kabuto_Yakushi",

    # Техники и дзюцу
    "https://naruto.fandom.com/wiki/Rasengan",
    "https://naruto.fandom.com/wiki/Chidori",
    "https://naruto.fandom.com/wiki/Shadow_Clone_Technique",
    "https://naruto.fandom.com/wiki/Sharingan",
    "https://naruto.fandom.com/wiki/Rinnegan",
    "https://naruto.fandom.com/wiki/Byakugan",
    "https://naruto.fandom.com/wiki/Sage_Mode",
    "https://naruto.fandom.com/wiki/Eight_Gates",

    # Деревни и организации
    "https://naruto.fandom.com/wiki/Konohagakure",
    "https://naruto.fandom.com/wiki/Sunagakure",
    "https://naruto.fandom.com/wiki/Kirigakure",
    "https://naruto.fandom.com/wiki/Kumogakure",
    "https://naruto.fandom.com/wiki/Iwagakure",
    "https://naruto.fandom.com/wiki/Akatsuki",
    "https://naruto.fandom.com/wiki/Five_Great_Shinobi_Countries",

    # Кланы
    "https://naruto.fandom.com/wiki/Uchiha_Clan",
    "https://naruto.fandom.com/wiki/Senju_Clan",
    "https://naruto.fandom.com/wiki/Hyuga_Clan",
    "https://naruto.fandom.com/wiki/Uzumaki_Clan",

    # Хвостатые звери (без херни в названии, по факту их больше!)
    "https://naruto.fandom.com/wiki/Kurama",
    "https://naruto.fandom.com/wiki/Shukaku",
    "https://naruto.fandom.com/wiki/Matatabi",

    # События
    "https://naruto.fandom.com/wiki/Fourth_Great_Ninja_War",
    "https://naruto.fandom.com/wiki/Chunin_Exams",

    # Просто термины (ЭТО БАЗА! ЭТО ЗНАТЬ НАДА!)
    "https://naruto.fandom.com/wiki/Shinobi",
    "https://naruto.fandom.com/wiki/Hokage",
    "https://naruto.fandom.com/wiki/Anbu",
    "https://naruto.fandom.com/wiki/Sannin",
    "https://naruto.fandom.com/wiki/Genin",
]

OUTPUT_DIR = "raw_pages"
FAILED_DIR = os.path.join(OUTPUT_DIR, "failed")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

# Сетевой таймаут (сек)
REQUEST_TIMEOUT = 30

# Пауза между запросами (сек): базовая + небольшой рандом
SLEEP_MIN = 5
SLEEP_MAX = 10.0

# Ретраи
MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # экспоненциальный бэкофф: 2^attempt


def page_name_from_url(url: str) -> str:
    """Извлекает имя страницы из URL"""
    page_name = urlparse(url).path.split("/")[-1]
    if not page_name or page_name == "wiki":
        parts = [p for p in urlparse(url).path.split("/") if p]
        page_name = parts[-1] if parts else "page"
    return page_name


def is_valid_fandom_html(html_text: str) -> bool:
    """
    Проверяет, что это реальная статья, а не капча/заглушка/редирект на "JS required".
    Fandom часто отдаёт HTML-заглушку при антиботе.
    """
    if not html_text or len(html_text) < 5000:
        return False

    red_flags = [
        "A required part of this site couldn’t load"
    ]
    low = html_text.lower()
    if any(flag.lower() in low for flag in red_flags):
        return False

    # Признаки статьи на Fandom
    if "mw-parser-output" not in low and "page__main" not in low and "article-content" not in low:
        return False

    return True


def download_page(url: str, output_dir: str = OUTPUT_DIR) -> dict:
    """
    Скачивает HTML страницу и сохраняет её.
    Возвращает dict с результатом (для metadata.json).
    """
    page_name = page_name_from_url(url)
    output_path = os.path.join(output_dir, f"{page_name}.html")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            status = resp.status_code
            html = resp.text

            if status >= 400:
                raise requests.HTTPError(f"HTTP {status}")

            if not is_valid_fandom_html(html):
                # Сохраним "плохой" ответ для диагностики
                bad_path = os.path.join(FAILED_DIR, f"{page_name}.attempt{attempt}.html")
                with open(bad_path, "w", encoding="utf-8") as f:
                    f.write(html)
                raise ValueError("Получен HTML с заглушкой без основного контента")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)

            return {
                "url": url,
                "file": output_path,
                "name": page_name,
                "status": status,
                "attempts": attempt,
            }

        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                sleep_s = (BACKOFF_BASE ** attempt) + random.uniform(0.2, 0.8)
                print(f"  ⚠ Попытка {attempt}/{MAX_RETRIES} неудачна: {e}")
                print(f"  ⏳ Ретрай через {sleep_s:.1f} сек...")
                time.sleep(sleep_s)

    return {
        "url": url,
        "file": None,
        "name": page_name,
        "status": None,
        "attempts": MAX_RETRIES,
        "error": last_error,
    }


def main():
    print(f"Начинаю скачивание {len(NARUTO_PAGES)} страниц...")
    print(f"Сохранение в директорию: {OUTPUT_DIR}")
    print(f"Плохие ответы (капча/заглушки): {FAILED_DIR}\n")

    downloaded = []
    failed = []

    for i, url in enumerate(NARUTO_PAGES, 1):
        print(f"[{i}/{len(NARUTO_PAGES)}] {url}")
        result = download_page(url)

        if result.get("file"):
            downloaded.append(result)
            print(f"  ✓ Скачано: {result['name']} (attempt {result['attempts']})")
        else:
            failed.append(result)
            print(f"  ✗ Не удалось: {result['name']} | {result.get('error')}")

        # Пауза между запросами, чтобы не триггерить антибот
        delay = 5
        print(f"  ⏳ Пауза {delay:.1f} сек\n")
        time.sleep(delay)

    metadata = {
        "downloaded": downloaded,
        "failed": failed,
        "total": len(NARUTO_PAGES),
        "success": len(downloaded),
        "failed_count": len(failed),
        "sleep_range_sec": [SLEEP_MIN, SLEEP_MAX],
        "max_retries": MAX_RETRIES,
        "timeout_sec": REQUEST_TIMEOUT,
    }

    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Завершено!")
    print(f"Успешно скачано: {len(downloaded)}/{len(NARUTO_PAGES)}")
    if failed:
        print(f"Ошибки: {len(failed)} (смотри {os.path.join(OUTPUT_DIR, 'metadata.json')})")
        print(f"Примеры плохих HTML лежат в: {FAILED_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
