"""
Скрипт для проверки окружения перед запуском задания 2
"""

import sys

def check_module(module_name, install_command):
    """Проверяет, установлен ли модуль"""
    try:
        __import__(module_name)
        print(f"✓ {module_name} установлен")
        return True
    except ImportError:
        print(f"✗ {module_name} не установлен")
        print(f"  Установите командой: {install_command}")
        return False

def main():
    print("Проверка окружения для выполнения задания 2")
    print("=" * 50)
    
    checks = [
        ("requests", "pip install requests"),
        ("bs4", "pip install beautifulsoup4"),
        ("lxml", "pip install lxml"),
    ]
    
    all_ok = True
    for module, command in checks:
        if not check_module(module, command):
            all_ok = False
    
    print("=" * 50)
    if all_ok:
        print("✓ Все зависимости установлены. Можно запускать скрипты!")
    else:
        print("✗ Некоторые зависимости отсутствуют. Установите их перед продолжением.")
        sys.exit(1)

if __name__ == "__main__":
    main()

