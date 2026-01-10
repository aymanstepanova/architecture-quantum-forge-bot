"""
Примеры использования RAG-бота.

Демонстрирует успешные диалоги и случаи, когда бот отвечает "Я не знаю".

ВАЖНО: Все примеры используют термины нового мира из базы знаний:
- Crimson Lens (вместо Sharingan)
- Kael Vexaris (вместо Naruto)
- Axiom Spiral (вместо Rasengan)
- Echo Manifest (вместо Shadow Clone Technique)
и т.д.

Бот работает с онтологией нового мира и не переводит термины обратно.
"""

from rag_bot import RAGBot
import os


def print_example(number: int, query: str, description: str = ""):
    """Выводит заголовок примера."""
    print("\n" + "="*80)
    print(f"ПРИМЕР {number}: {description}")
    print("="*80)
    print(f"Запрос: {query}")
    print("-"*80)


def run_examples():
    """Запускает примеры диалогов с RAG-ботом."""
    print("="*80)
    print("ПРИМЕРЫ ДИАЛОГОВ С RAG-БОТОМ")
    print("="*80)
    print("\nВсе примеры используют термины из базы знаний:")
    print("(Crimson Lens, Kael Vexaris, Axiom Spiral, Echo Manifest и т.д.)")
    print("\nИнициализация бота...")
    
    try:
        bot = RAGBot()
        print("✓ Бот готов!\n")
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\nУбедитесь, что:")
        print("  1. Векторный индекс создан (python build_index.py)")
        print("  2. Установлен OpenAI: pip install openai")
        print("  3. Установлена переменная окружения OPENAI_API_KEY")
        return
    
    # Успешные примеры диалогов (используем термины нового мира)
    successful_queries = [
        {
            "query": "Что такое Crimson Lens?",
            "description": "Вопрос о технике из базы знаний (новый мир)"
        },
        {
            "query": "Кто такой Kael Vexaris?",
            "description": "Вопрос о персонаже (новый мир)"
        },
        {
            "query": "Какие способности даёт Crimson Lens?",
            "description": "Вопрос о способностях техники (новый мир)"
        },
        {
            "query": "Что такое Axiom Spiral?",
            "description": "Вопрос о технике (новый мир)"
        },
        {
            "query": "Как работает Echo Manifest?",
            "description": "Вопрос о механике техники (новый мир)"
        }
    ]
    
    print("\n" + "="*80)
    print("УСПЕШНЫЕ ДИАЛОГИ (5 примеров)")
    print("="*80)
    
    for i, example in enumerate(successful_queries, 1):
        print_example(i, example["query"], example["description"])
        
        result = bot.generate_answer(example["query"])
        
        if result.get('reasoning'):
            print("\n[Шаги рассуждения]")
            print(result['reasoning'])
            print()
        
        print("[Ответ]")
        print(result['answer'])
        
        print(f"\n[Использовано чанков: {len(result['context_chunks'])}]")
        for j, chunk in enumerate(result['context_chunks'][:2], 1):
            print(f"  {j}. {chunk['source']} (релевантность: {chunk['relevance']:.4f})")
    
    # Примеры, когда бот должен ответить "Я не знаю"
    unknown_queries = [
        {
            "query": "Как приготовить борщ?",
            "description": "Вопрос вне предметной области базы знаний"
        },
        {
            "query": "Какая столица Франции?",
            "description": "Вопрос о реальном мире, не связанный с базой знаний"
        }
    ]
    
    print("\n\n" + "="*80)
    print("СЛУЧАИ 'Я НЕ ЗНАЮ' (2 примера)")
    print("="*80)
    print("\nБот должен честно признать, что не знает ответа на вопросы,")
    print("которые не относятся к предметной области базы знаний.\n")
    
    for i, example in enumerate(unknown_queries, 1):
        print_example(i, example["query"], example["description"])
        
        result = bot.generate_answer(example["query"])
        
        if result.get('reasoning'):
            print("\n[Шаги рассуждения]")
            print(result['reasoning'])
            print()
        
        print("[Ответ]")
        print(result['answer'])
        
        # Проверяем, содержит ли ответ признание незнания
        answer_lower = result['answer'].lower()
        knows_indicators = ["не знаю", "не знаю", "нет информации", "не могу", "не найдено"]
        if any(indicator in answer_lower for indicator in knows_indicators):
            print("\n✓ Бот корректно признал, что не знает ответа")
        else:
            print("\n⚠ Бот попытался ответить, хотя информации нет в базе знаний")
        
        print(f"\n[Использовано чанков: {len(result['context_chunks'])}]")
        if result['context_chunks']:
            for j, chunk in enumerate(result['context_chunks'][:2], 1):
                print(f"  {j}. {chunk['source']} (релевантность: {chunk['relevance']:.4f})")
    
    print("\n\n" + "="*80)
    print("ПРИМЕРЫ ЗАВЕРШЕНЫ")
    print("="*80)
    print("\nДля интерактивного режима запустите: python rag_bot_repl.py")


if __name__ == "__main__":
    run_examples()
