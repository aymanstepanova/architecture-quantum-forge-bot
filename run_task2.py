"""
Главный скрипт для выполнения задания 2
Выполняет все шаги: скачивание, очистка, замена терминов
"""

import subprocess
import sys
import os

def run_script(script_name):
    """Запускает Python скрипт"""
    print(f"\n{'='*60}")
    print(f"Запуск: {script_name}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            check=True
        )
        print(f"\n✓ {script_name} выполнен успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Ошибка при выполнении {script_name}: {e}")
        return False

def main():
    print("="*60)
    print("Выполнение задания 2: Подготовка базы знаний")
    print("="*60)
    
    scripts = [
        "create_terms_map.py",
        "download_naruto_pages.py",
        "extract_text_from_html.py",
        "apply_replacements.py"
    ]
    
    for script in scripts:
        if not os.path.exists(script):
            print(f"\n⚠ Файл {script} не найден, пропускаю...")
            continue
        
        success = run_script(script)
        
        if not success:
            print(f"\n⚠ Скрипт {script} завершился с ошибкой")
            response = input("Продолжить выполнение? (y/n): ")
            if response.lower() != 'y':
                print("Выполнение прервано пользователем")
                return
    
    print("\n" + "="*60)
    print("Все шаги выполнены!")
    print("="*60)
    print("\nПроверьте результаты:")
    print("  - terms_map.json - словарь замен")
    print("  - knowledge_base/ - финальная база знаний")

if __name__ == "__main__":
    main()

