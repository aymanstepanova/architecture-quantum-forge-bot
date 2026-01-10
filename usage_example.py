"""
Пример использования векторного индекса базы знаний.

Демонстрирует:
1. Загрузку индекса
2. Расширение запросов (замена оригинальных терминов)
3. Поиск по векторному индексу
4. Работу с результатами поиска
"""

from build_index import (
    load_vectorstore,
    expand_query,
    restore_original_terms,
    load_terms_map,
    VECTOR_DB_DIR
)


def print_result(doc, score=None, index=1):
    """Красиво выводит результат поиска."""
    print(f"\n{'='*80}")
    print(f"Результат {index}")
    if score is not None:
        print(f"Релевантность: {score:.4f}")
    print(f"{'='*80}")
    print(f"📄 Источник: {doc.metadata.get('source', 'unknown')}")
    print(f"📑 Заголовок: {doc.metadata.get('title', 'N/A')}")
    print(f"🔢 Чанк ID: {doc.metadata.get('chunk_id', 'N/A')}")
    print(f"\n📝 Текст чанка:")
    print(f"{doc.page_content[:400]}...")
    if len(doc.page_content) > 400:
        print(f"\n... (всего {len(doc.page_content)} символов)")


def example_1_basic_search():
    """Пример 1: Базовый поиск с расширением запроса."""
    print("\n" + "="*80)
    print("ПРИМЕР 1: Базовый поиск с расширением запроса")
    print("="*80)
    
    # Загрузка индекса
    print("\n1. Загрузка векторного индекса...")
    vectorstore = load_vectorstore(VECTOR_DB_DIR)
    print(f"   ✓ Индекс загружен из: {VECTOR_DB_DIR}")
    
    # Загрузка словаря замен
    print("\n2. Загрузка словаря замен терминов...")
    terms_map = load_terms_map()
    print(f"   ✓ Загружено {len(terms_map)} терминов для замены")
    
    # Запрос пользователя с оригинальным термином
    user_query = "What is Sharingan?"
    print(f"\n3. Запрос пользователя: '{user_query}'")
    
    # Расширение запроса
    expanded_query = expand_query(user_query, terms_map)
    print(f"   Расширенный запрос: '{expanded_query}'")
    print(f"   (Sharingan → Crimson Lens)")
    
    # Поиск
    print(f"\n4. Выполнение поиска...")
    results = vectorstore.similarity_search_with_score(expanded_query, k=3)
    
    print(f"\n5. Найдено {len(results)} релевантных чанков:")
    print("   (Восстанавливаем оригинальные термины в результатах)")
    for i, (doc, score) in enumerate(results, 1):
        # Восстанавливаем оригинальные термины
        restored_content = restore_original_terms(doc.page_content, terms_map)
        # Создаём временный документ с восстановленным текстом
        from langchain_core.documents import Document
        restored_doc = Document(
            page_content=restored_content,
            metadata=doc.metadata
        )
        print_result(restored_doc, score, i)


def example_2_comparison():
    """Пример 2: Сравнение поиска с расширением и без."""
    print("\n" + "="*80)
    print("ПРИМЕР 2: Сравнение поиска с расширением и без")
    print("="*80)
    
    vectorstore = load_vectorstore(VECTOR_DB_DIR)
    terms_map = load_terms_map()
    
    query = "Tell me about the Uchiha clan"
    
    print(f"\nЗапрос: '{query}'")
    
    # Поиск БЕЗ расширения
    print("\n" + "-"*80)
    print("Поиск БЕЗ расширения запроса:")
    print("-"*80)
    results_without = vectorstore.similarity_search_with_score(query, k=3)
    if results_without:
        print(f"Найдено {len(results_without)} результатов:")
        for i, (doc, score) in enumerate(results_without[:2], 1):
            print(f"\n  {i}. {doc.metadata.get('source')} (релевантность: {score:.4f})")
            print(f"     {doc.page_content[:100]}...")
    else:
        print("  Результаты не найдены")
    
    # Поиск С расширением
    print("\n" + "-"*80)
    print("Поиск С расширением запроса:")
    print("-"*80)
    expanded_query = expand_query(query, terms_map)
    print(f"Расширенный запрос: '{expanded_query}'")
    print(f"(Uchiha → Noctryn, clan → Line)")
    
    results_with = vectorstore.similarity_search_with_score(expanded_query, k=3)
    if results_with:
        print(f"\nНайдено {len(results_with)} результатов:")
        print("(Восстанавливаем оригинальные термины)")
        for i, (doc, score) in enumerate(results_with[:2], 1):
            restored_content = restore_original_terms(doc.page_content, terms_map)
            print(f"\n  {i}. {doc.metadata.get('source')} (релевантность: {score:.4f})")
            print(f"     {restored_content[:100]}...")
    
    print("\n" + "="*80)
    print("Вывод: Расширение запроса позволяет находить релевантные документы!")
    print("="*80)


def example_3_multiple_terms():
    """Пример 3: Поиск с несколькими терминами."""
    print("\n" + "="*80)
    print("ПРИМЕР 3: Поиск с несколькими заменяемыми терминами")
    print("="*80)
    
    vectorstore = load_vectorstore(VECTOR_DB_DIR)
    terms_map = load_terms_map()
    
    # Запрос с несколькими оригинальными терминами
    query = "How does Naruto use Rasengan and Shadow Clone Technique?"
    print(f"\nЗапрос: '{query}'")
    
    expanded_query = expand_query(query, terms_map)
    print(f"Расширенный запрос: '{expanded_query}'")
    print("Замены:")
    print("  - Naruto → Kael")
    print("  - Rasengan → Axiom Spiral")
    print("  - Shadow Clone Technique → Echo Manifest")
    
    results = vectorstore.similarity_search_with_score(expanded_query, k=3)
    
    print(f"\nНайдено {len(results)} релевантных чанков:")
    print("(Восстанавливаем оригинальные термины)")
    for i, (doc, score) in enumerate(results, 1):
        restored_content = restore_original_terms(doc.page_content, terms_map)
        from langchain_core.documents import Document
        restored_doc = Document(
            page_content=restored_content,
            metadata=doc.metadata
        )
        print_result(restored_doc, score, i)


def example_4_already_replaced():
    """Пример 4: Поиск по уже заменённым терминам (тоже работает)."""
    print("\n" + "="*80)
    print("ПРИМЕР 4: Поиск по уже заменённым терминам")
    print("="*80)
    
    vectorstore = load_vectorstore(VECTOR_DB_DIR)
    
    # Запрос с уже заменёнными терминами
    query = "What is Crimson Lens?"
    print(f"\nЗапрос: '{query}'")
    print("(Термин уже заменён, расширение не требуется)")
    
    results = vectorstore.similarity_search_with_score(query, k=3)
    
    print(f"\nНайдено {len(results)} релевантных чанков:")
    # Восстанавливаем термины, если они были заменены
    terms_map = load_terms_map()
    if terms_map:
        print("(Восстанавливаем оригинальные термины)")
        for i, (doc, score) in enumerate(results, 1):
            restored_content = restore_original_terms(doc.page_content, terms_map)
            from langchain_core.documents import Document
            restored_doc = Document(
                page_content=restored_content,
                metadata=doc.metadata
            )
            print_result(restored_doc, score, i)
    else:
        for i, (doc, score) in enumerate(results, 1):
            print_result(doc, score, i)


def example_5_usage_in_rag():
    """Пример 5: Использование в RAG-пайплайне."""
    print("\n" + "="*80)
    print("ПРИМЕР 5: Использование в RAG-пайплайне")
    print("="*80)
    
    vectorstore = load_vectorstore(VECTOR_DB_DIR)
    terms_map = load_terms_map()
    
    def search_knowledge_base(user_query: str, k: int = 5):
        """
        Функция для поиска в базе знаний.
        Используется в RAG-пайплайне перед отправкой в LLM.
        """
        # Расширяем запрос
        expanded_query = expand_query(user_query, terms_map)
        
        # Поиск релевантных чанков
        results = vectorstore.similarity_search_with_score(expanded_query, k=k)
        
        # Формируем контекст для LLM
        context_chunks = []
        for doc, score in results:
            # Восстанавливаем оригинальные термины в тексте
            content = restore_original_terms(doc.page_content, terms_map)
            
            context_chunks.append({
                "content": content,  # Теперь с оригинальными терминами!
                "source": doc.metadata.get("source"),
                "title": doc.metadata.get("title"),
                "relevance": float(score)
            })
        
        return context_chunks
    
    # Пример использования
    user_question = "What abilities does Sharingan give to Uchiha clan members?"
    print(f"\nВопрос пользователя: '{user_question}'")
    
    # Поиск релевантных чанков
    context = search_knowledge_base(user_question, k=3)
    
    print(f"\nНайдено {len(context)} релевантных чанков для контекста:")
    print("\n" + "-"*80)
    print("КОНТЕКСТ ДЛЯ LLM:")
    print("-"*80)
    
    for i, chunk in enumerate(context, 1):
        print(f"\n[Чанк {i}]")
        print(f"Источник: {chunk['source']}")
        print(f"Релевантность: {chunk['relevance']:.4f}")
        print(f"Текст: {chunk['content'][:200]}...")
    
    print("\n" + "-"*80)
    print("Этот контекст можно передать в LLM для генерации ответа.")
    print("-"*80)


def main():
    """Запуск всех примеров."""
    print("="*80)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ВЕКТОРНОГО ИНДЕКСА")
    print("="*80)
    print("\nДемонстрация работы с векторным индексом базы знаний:")
    print("- Загрузка индекса")
    print("- Расширение запросов (замена терминов)")
    print("- Поиск релевантных чанков")
    print("- Использование в RAG-пайплайне")
    
    try:
        # Проверка существования индекса
        if not VECTOR_DB_DIR.exists():
            print(f"\n❌ ОШИБКА: Векторный индекс не найден в {VECTOR_DB_DIR}")
            print("   Сначала запустите: python build_index.py")
            return
        
        # Запуск примеров
        example_1_basic_search()
        example_2_comparison()
        example_3_multiple_terms()
        example_4_already_replaced()
        example_5_usage_in_rag()
        
        print("\n" + "="*80)
        print("ВСЕ ПРИМЕРЫ ВЫПОЛНЕНЫ")
        print("="*80)
        print("\nТеперь вы можете использовать эти функции в своём RAG-боте!")
        
    except FileNotFoundError as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("   Убедитесь, что векторный индекс создан (python build_index.py)")
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
