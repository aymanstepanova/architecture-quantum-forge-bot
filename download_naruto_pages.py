"""
Скрипт для скачивания страниц из naruto.fandom.com
Скачивает HTML страницы по списку URL и сохраняет их для дальнейшей обработки
"""

import os
import time
from urllib.parse import urljoin, urlparse
import json

try:
    import requests
except ImportError:
    print("Ошибка: модуль 'requests' не установлен.")
    print("Установите его командой: pip install requests")
    exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Ошибка: модуль 'beautifulsoup4' не установлен.")
    print("Установите его командой: pip install beautifulsoup4")
    exit(1)

# Список ключевых страниц из мира Наруто
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
    
    # Кланы
    "https://naruto.fandom.com/wiki/Uchiha_Clan",
    "https://naruto.fandom.com/wiki/Senju_Clan",
    "https://naruto.fandom.com/wiki/Hyuga_Clan",
    "https://naruto.fandom.com/wiki/Uzumaki_Clan",
    
    # Хвостатые звери
    "https://naruto.fandom.com/wiki/Nine-Tailed_Fox",
    "https://naruto.fandom.com/wiki/One-Tailed_Shukaku",
    "https://naruto.fandom.com/wiki/Eight-Tailed_Gyuki",
    
    # События
    "https://naruto.fandom.com/wiki/Fourth_Great_Ninja_War",
    "https://naruto.fandom.com/wiki/Chunin_Exams",
]

OUTPUT_DIR = "raw_pages"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_page(url, output_dir=OUTPUT_DIR):
    """Скачивает HTML страницу и сохраняет её"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Извлекаем название страницы из URL
        page_name = urlparse(url).path.split('/')[-1]
        if not page_name or page_name == 'wiki':
            page_name = urlparse(url).path.split('/')[-2]
        
        output_path = os.path.join(output_dir, f"{page_name}.html")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"✓ Скачано: {page_name}")
        return output_path
        
    except Exception as e:
        print(f"✗ Ошибка при скачивании {url}: {e}")
        return None

def main():
    print(f"Начинаю скачивание {len(NARUTO_PAGES)} страниц...")
    print(f"Сохранение в директорию: {OUTPUT_DIR}\n")
    
    downloaded = []
    failed = []
    
    for i, url in enumerate(NARUTO_PAGES, 1):
        print(f"[{i}/{len(NARUTO_PAGES)}] Обработка: {url}")
        result = download_page(url)
        
        if result:
            downloaded.append({
                'url': url,
                'file': result,
                'name': os.path.basename(result).replace('.html', '')
            })
        else:
            failed.append(url)
        
        # Небольшая задержка, чтобы не перегружать сервер
        time.sleep(1)
    
    # Сохраняем метаданные
    metadata = {
        'downloaded': downloaded,
        'failed': failed,
        'total': len(NARUTO_PAGES),
        'success': len(downloaded)
    }
    
    with open(os.path.join(OUTPUT_DIR, 'metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Завершено!")
    print(f"Успешно скачано: {len(downloaded)}/{len(NARUTO_PAGES)}")
    if failed:
        print(f"Ошибки: {len(failed)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

