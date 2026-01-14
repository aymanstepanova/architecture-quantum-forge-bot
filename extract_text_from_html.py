"""
Скрипт для извлечения чистого текста из HTML страниц фандома
Удаляет навигацию, рекламу и другие служебные элементы
"""

import os
import json
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Ошибка: модуль 'beautifulsoup4' не установлен.")
    print("Установите его командой: pip install beautifulsoup4")
    exit(1)

RAW_DIR = "raw_pages"
CLEANED_DIR = "cleaned_texts"
os.makedirs(CLEANED_DIR, exist_ok=True)

def clean_text(text):
    """Очищает текст от лишних пробелов и символов"""
    # Удаляем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    # Удаляем пробелы в начале и конце строк
    text = text.strip()
    return text

def extract_main_content(soup):
    """Извлекает основной контент статьи из HTML"""
    # Пытаемся найти основной контент статьи
    # В Fandom обычно это div с классом mw-parser-output или article-content
    content_selectors = [
        'div.mw-parser-output',
        'div#content',
        'article',
        'div.content',
    ]
    
    main_content = None
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
    
    if not main_content:
        # Если не нашли, берем body
        main_content = soup.find('body')
    
    if not main_content:
        return ""
    
    # Удаляем ненужные элементы
    unwanted_tags = [
        'nav', 'header', 'footer', 'aside',
        'script', 'style', 'noscript',
        '.navbox', '.infobox', '.mw-editsection',
        '.reference', '.mw-references-wrap',
        '.mw-cite-backlink', '.catlinks',
        '.dablink', '.hatnote',
        'table.navbox', 'div.navbox',
    ]
    
    for tag in unwanted_tags:
        for element in main_content.select(tag):
            element.decompose()
    
    # Извлекаем текст
    text = main_content.get_text(separator='\n', strip=True)
    
    # Очищаем текст
    lines = []
    for line in text.split('\n'):
        line = clean_text(line)
        if line and len(line) > 10:  # Пропускаем очень короткие строки
            lines.append(line)
    
    return '\n\n'.join(lines)

def process_html_file(html_path):
    """Обрабатывает один HTML файл и извлекает текст"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Извлекаем заголовок
        title = soup.find('h1')
        title_text = title.get_text(strip=True) if title else os.path.basename(html_path).replace('.html', '')
        
        # Извлекаем основной контент
        content = extract_main_content(soup)
        
        if not content or len(content) < 100:
            print(f"⚠ Предупреждение: мало контента в {html_path}")
        
        # Сохраняем очищенный текст
        output_filename = os.path.basename(html_path).replace('.html', '.txt')
        output_path = os.path.join(CLEANED_DIR, output_filename)
        
        # Формируем документ
        document = f"{title_text}\n{'='*len(title_text)}\n\n{content}"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document)
        
        return {
            'input': html_path,
            'output': output_path,
            'title': title_text,
            'length': len(content)
        }
        
    except Exception as e:
        print(f"✗ Ошибка при обработке {html_path}: {e}")
        return None

def main():
    print("Извлечение текста из HTML файлов...")
    print(f"Входная директория: {RAW_DIR}")
    print(f"Выходная директория: {CLEANED_DIR}\n")
    
    # Загружаем метаданные
    metadata_path = os.path.join(RAW_DIR, 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        html_files = [item['file'] for item in metadata.get('downloaded', [])]
    else:
        # Если метаданных нет, обрабатываем все HTML файлы
        html_files = [os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR) if f.endswith('.html')]
    
    processed = []
    failed = []
    
    for i, html_path in enumerate(html_files, 1):
        if not os.path.exists(html_path):
            print(f"[{i}/{len(html_files)}] Файл не найден: {html_path}")
            failed.append(html_path)
            continue
        
        print(f"[{i}/{len(html_files)}] Обработка: {os.path.basename(html_path)}")
        result = process_html_file(html_path)
        
        if result:
            processed.append(result)
            print(f"  ✓ Извлечено {result['length']} символов")
        else:
            failed.append(html_path)
    
    # Сохраняем метаданные обработки
    processing_metadata = {
        'processed': processed,
        'failed': failed,
        'total': len(html_files),
        'success': len(processed)
    }
    
    with open(os.path.join(CLEANED_DIR, 'processing_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(processing_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Завершено!")
    print(f"Успешно обработано: {len(processed)}/{len(html_files)}")
    if failed:
        print(f"Ошибки: {len(failed)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

