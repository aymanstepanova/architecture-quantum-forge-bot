"""
Скрипт для применения замен терминов к очищенным текстам
Заменяет все упоминания оригинальных терминов на вымышленные
"""

import os
import json
import re
from pathlib import Path

CLEANED_DIR = "cleaned_texts"
OUTPUT_DIR = "knowledge_base"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_terms_map(map_file='terms_map.json'):
    """Загружает словарь замен"""
    with open(map_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_replacement_patterns(terms_map):
    """Создает регулярные выражения для замены с учетом границ слов"""
    patterns = []
    
    # Сортируем по длине (от длинных к коротким), чтобы сначала заменять составные термины
    sorted_terms = sorted(terms_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_terms:
        # Экранируем специальные символы в оригинальном термине
        escaped_original = re.escape(original)
        
        # Создаем паттерн с границами слов
        # Учитываем, что термины могут быть частью предложений
        pattern = r'\b' + escaped_original + r'\b'
        
        patterns.append((pattern, replacement))
    
    return patterns

def apply_replacements(text, patterns):
    """Применяет все замены к тексту"""
    result = text
    
    for pattern, replacement in patterns:
        # Используем re.IGNORECASE для регистронезависимого поиска
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result

def process_text_file(input_path, patterns, output_dir=OUTPUT_DIR):
    """Обрабатывает один текстовый файл"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Применяем замены
        replaced_content = apply_replacements(content, patterns)
        
        # Сохраняем результат
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(replaced_content)
        
        # Подсчитываем количество замен
        replacements_count = 0
        for pattern, replacement in patterns:
            matches = len(re.findall(pattern, content, flags=re.IGNORECASE))
            if matches > 0:
                replacements_count += matches
        
        return {
            'input': input_path,
            'output': output_path,
            'replacements': replacements_count,
            'original_length': len(content),
            'new_length': len(replaced_content)
        }
        
    except Exception as e:
        print(f"✗ Ошибка при обработке {input_path}: {e}")
        return None

def main():
    print("Применение замен терминов к текстам...")
    print(f"Входная директория: {CLEANED_DIR}")
    print(f"Выходная директория: {OUTPUT_DIR}\n")
    
    # Загружаем словарь замен
    print("Загрузка словаря замен...")
    terms_map = load_terms_map()
    print(f"✓ Загружено {len(terms_map)} терминов")
    
    # Создаем паттерны для замены
    print("Создание паттернов замены...")
    patterns = create_replacement_patterns(terms_map)
    print(f"✓ Создано {len(patterns)} паттернов\n")
    
    # Находим все текстовые файлы
    text_files = [os.path.join(CLEANED_DIR, f) for f in os.listdir(CLEANED_DIR) 
                  if f.endswith('.txt') and f != 'processing_metadata.json']
    
    if not text_files:
        print("⚠ Не найдено текстовых файлов для обработки!")
        return
    
    print(f"Найдено {len(text_files)} файлов для обработки\n")
    
    processed = []
    failed = []
    total_replacements = 0
    
    for i, text_file in enumerate(text_files, 1):
        print(f"[{i}/{len(text_files)}] Обработка: {os.path.basename(text_file)}")
        result = process_text_file(text_file, patterns)
        
        if result:
            processed.append(result)
            total_replacements += result['replacements']
            print(f"  ✓ Применено {result['replacements']} замен")
        else:
            failed.append(text_file)
    
    # Копируем terms_map.json в knowledge_base
    import shutil
    shutil.copy('terms_map.json', os.path.join(OUTPUT_DIR, 'terms_map.json'))
    
    # Сохраняем метаданные обработки
    processing_metadata = {
        'processed': processed,
        'failed': failed,
        'total_files': len(text_files),
        'success': len(processed),
        'total_replacements': total_replacements,
        'terms_map_file': 'terms_map.json'
    }
    
    with open(os.path.join(OUTPUT_DIR, 'replacement_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(processing_metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Завершено!")
    print(f"Успешно обработано: {len(processed)}/{len(text_files)}")
    print(f"Всего применено замен: {total_replacements}")
    if failed:
        print(f"Ошибки: {len(failed)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

