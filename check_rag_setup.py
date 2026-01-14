"""
Скрипт для проверки готовности системы к запуску RAG-бота.

Проверяет:
- Наличие векторного индекса
- Установленные зависимости
- Наличие API ключа OpenAI
"""

import os
import sys
from pathlib import Path


def check_vector_index():
    """Проверяет наличие векторного индекса."""
    print("Проверка векторного индекса...")
    
    vector_index_dir = Path("vector_index")
    if not vector_index_dir.exists():
        print("  ❌ Векторный индекс не найден!")
        print("     Запустите: python build_index.py")
        return False
    
    # Проверяем наличие файлов ChromaDB
    chroma_db = vector_index_dir / "chroma.sqlite3"
    if not chroma_db.exists():
        print("  ❌ Файл базы данных ChromaDB не найден!")
        print("     Запустите: python build_index.py")
        return False
    
    print("  ✓ Векторный индекс найден")
    return True


def check_dependencies():
    """Проверяет установленные зависимости."""
    print("\nПроверка зависимостей...")
    
    required_packages = {
        "langchain": "langchain",
        "langchain_community": "langchain-community",
        "chromadb": "chromadb",
        "sentence_transformers": "sentence-transformers",
        "openai": "openai",
    }
    
    missing = []
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"  ✓ {package} установлен")
        except ImportError:
            print(f"  ❌ {package} не установлен")
            missing.append(package)
    
    if missing:
        print(f"\n  Установите недостающие пакеты:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True


def check_llm_provider():
    """Проверяет настройку LLM провайдера (OpenAI или Ollama)."""
    print("\nПроверка LLM провайдера...")
    
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if llm_provider == "ollama":
        print("  ✓ Используется Ollama (локальные модели)")
        print("     Проверка подключения к Ollama...")
        
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                print("  ✓ Ollama сервер доступен")
                return True
            else:
                print("  ⚠ Ollama сервер отвечает, но с ошибкой")
                return False
        except ImportError:
            print("  ⚠ Библиотека requests не установлена (не критично)")
            print("     Убедитесь, что Ollama запущен: ollama serve")
            return True  # Не критично
        except Exception as e:
            print(f"  ❌ Не удалось подключиться к Ollama: {e}")
            print("     Убедитесь, что Ollama запущен: ollama serve")
            print("     Или используйте OpenAI: $env:LLM_PROVIDER='openai'")
            return False
    
    else:  # OpenAI
        print("  ✓ Используется OpenAI API")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("  ❌ API ключ OpenAI не найден!")
            print("     Установите переменную окружения OPENAI_API_KEY:")
            print("     Windows: $env:OPENAI_API_KEY='your-key'")
            print("     Linux/Mac: export OPENAI_API_KEY='your-key'")
            print("\n     Или используйте Ollama (бесплатно):")
            print("     Windows: $env:LLM_PROVIDER='ollama'")
            print("     Linux/Mac: export LLM_PROVIDER='ollama'")
            return False
        
        # Проверяем формат ключа (должен начинаться с sk-)
        if not api_key.startswith("sk-"):
            print("  ⚠ API ключ имеет необычный формат (обычно начинается с 'sk-')")
            print("     Убедитесь, что ключ правильный")
            return False
        
        print("  ✓ API ключ OpenAI найден")
        return True


def check_build_index_module():
    """Проверяет наличие модуля build_index."""
    print("\nПроверка модуля build_index...")
    
    try:
        import build_index
        print("  ✓ Модуль build_index доступен")
        return True
    except ImportError:
        print("  ❌ Модуль build_index не найден!")
        print("     Убедитесь, что файл build_index.py находится в текущей директории")
        return False


def main():
    """Основная функция проверки."""
    print("="*80)
    print("ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ К ЗАПУСКУ RAG-БОТА")
    print("="*80)
    
    checks = [
        check_build_index_module(),
        check_vector_index(),
        check_dependencies(),
        check_llm_provider(),
    ]
    
    print("\n" + "="*80)
    if all(checks):
        print("✓ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("  Система готова к запуску RAG-бота.")
        print("\n  Запустите:")
        print("    python rag_bot_repl.py  # Интерактивный режим")
        print("    python rag_bot_examples.py  # Примеры диалогов")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        print("  Исправьте указанные проблемы перед запуском.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
