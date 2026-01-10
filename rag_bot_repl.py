"""
Интерактивный REPL интерфейс для RAG-бота.

Позволяет общаться с ботом в консольном режиме.
"""

import sys
from rag_bot import RAGBot


def print_help():
    """Выводит справку по командам."""
    print("\n" + "="*80)
    print("СПРАВКА ПО КОМАНДАМ")
    print("="*80)
    print("  /help     - Показать эту справку")
    print("  /exit     - Выйти из программы")
    print("  /quit     - Выйти из программы")
    print("  /clear    - Очистить экран")
    print("  /verbose  - Переключить подробный режим вывода")
    print("  /fewshot  - Переключить использование Few-shot примеров")
    print("  /cot      - Переключить использование Chain-of-Thought")
    print("  /status   - Показать текущие настройки")
    print("="*80 + "\n")


def main():
    """Главная функция REPL интерфейса."""
    print("="*80)
    print("RAG-БОТ: ИНТЕРАКТИВНЫЙ РЕЖИМ")
    print("="*80)
    print("\nИнициализация бота...")
    
    try:
        bot = RAGBot()
        print("✓ Бот готов к работе!\n")
    except Exception as e:
        print(f"\n❌ ОШИБКА при инициализации: {e}")
        print("\nУбедитесь, что:")
        print("  1. Векторный индекс создан (python build_index.py)")
        print("  2. Установлен OpenAI: pip install openai")
        print("\nНастройте LLM провайдер:")
        print("  Вариант A: OpenAI API")
        print("    - Установите OPENAI_API_KEY")
        print("  Вариант B: Ollama (бесплатно, без API ключей) ⭐")
        print("    - Установите Ollama: https://ollama.ai")
        print("    - Запустите: ollama serve")
        print("    - Загрузите модель: ollama pull llama3.2")
        print("    - Установите: $env:LLM_PROVIDER='ollama' (Windows)")
        print("    - Или: export LLM_PROVIDER='ollama' (Linux/Mac)")
        sys.exit(1)
    
    # Настройки
    verbose = True
    use_few_shot = True
    use_cot = True
    
    print_help()
    print("Введите ваш вопрос (или команду, начинающуюся с /):")
    print("Для выхода введите /exit или /quit\n")
    
    while True:
        try:
            # Ввод пользователя
            user_input = input("> ").strip()
            
            if not user_input:
                continue
            
            # Обработка команд
            if user_input.startswith("/"):
                command = user_input.lower()
                
                if command in ["/exit", "/quit"]:
                    print("\nДо свидания!")
                    break
                
                elif command == "/help":
                    print_help()
                
                elif command == "/clear":
                    import os
                    os.system("cls" if os.name == "nt" else "clear")
                
                elif command == "/verbose":
                    verbose = not verbose
                    print(f"✓ Подробный режим: {'включен' if verbose else 'выключен'}")
                
                elif command == "/fewshot":
                    use_few_shot = not use_few_shot
                    print(f"✓ Few-shot примеры: {'включены' if use_few_shot else 'выключены'}")
                
                elif command == "/cot":
                    use_cot = not use_cot
                    print(f"✓ Chain-of-Thought: {'включен' if use_cot else 'выключен'}")
                
                elif command == "/status":
                    print("\n" + "="*80)
                    print("ТЕКУЩИЕ НАСТРОЙКИ")
                    print("="*80)
                    print(f"  Подробный режим: {'включен' if verbose else 'выключен'}")
                    print(f"  Few-shot примеры: {'включены' if use_few_shot else 'выключены'}")
                    print(f"  Chain-of-Thought: {'включен' if use_cot else 'выключен'}")
                    print(f"  Модель LLM: {bot.llm_model}")
                    print(f"  Количество чанков: {bot.k_chunks}")
                    print("="*80 + "\n")
                
                else:
                    print(f"❌ Неизвестная команда: {command}")
                    print("Введите /help для справки")
                
                continue
            
            # Обработка запроса пользователя
            print()  # Пустая строка перед ответом
            
            if verbose:
                result = bot.generate_answer(user_input, use_few_shot=use_few_shot, use_cot=use_cot)
                
                # Проверка на None (на случай ошибки)
                if result is None:
                    print("❌ Ошибка: метод generate_answer вернул None")
                    continue
                
                print(f"{'='*80}")
                print(f"Запрос: {user_input}")
                print(f"{'='*80}")
                
                if result.get('reasoning') and use_cot:
                    print(f"\n[Шаги рассуждения]")
                    print(result['reasoning'])
                    print()
                
                print(f"[Ответ]")
                print(result.get('answer', 'Ошибка: ответ не получен'))
                
                context_chunks = result.get('context_chunks', [])
                print(f"\n[Использовано чанков: {len(context_chunks)}]")
                for i, chunk in enumerate(context_chunks[:3], 1):
                    print(f"  {i}. {chunk.get('source', 'unknown')} (релевантность: {chunk.get('relevance', 0):.4f})")
                
                print(f"\n{'-'*80}\n")
            else:
                # Простой режим - только ответ
                answer = bot.chat(user_input, verbose=False)
                print(f"Ответ: {answer}\n")
        
        except KeyboardInterrupt:
            print("\n\nПрервано пользователем. Для выхода введите /exit")
        
        except EOFError:
            print("\n\nДо свидания!")
            break
        
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
