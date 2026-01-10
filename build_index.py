"""
Скрипт для создания векторного индекса базы знаний.

Использует:
- Sentence-Transformers (all-MiniLM-L6-v2) для генерации эмбеддингов
- ChromaDB для хранения векторного индекса
- LangChain для разбиения текстов на чанки
"""

import os
import re
import time
import json
from pathlib import Path
from typing import List, Dict

# Импорты с поддержкой разных версий LangChain
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Fallback для старых версий LangChain
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Импорт Document с поддержкой разных версий
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.docstore.document import Document
    except ImportError:
        from langchain.schema import Document


# Конфигурация
KNOWLEDGE_BASE_DIR = Path("knowledge_base")
VECTOR_DB_DIR = Path("vector_index")
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Размерность для all-MiniLM-L6-v2
TERMS_MAP_FILE = Path("knowledge_base/terms_map.json")

# Параметры разбиения на чанки
CHUNK_SIZE = 500  # Примерно 500 токенов
CHUNK_OVERLAP = 50  # Перекрытие между чанками для сохранения контекста


def load_documents(knowledge_base_dir: Path) -> List[Document]:
    """
    Загружает все текстовые файлы из базы знаний.
    
    Returns:
        Список документов LangChain с метаданными
    """
    documents = []
    
    # Получаем все .txt файлы, исключая README.md и JSON файлы
    txt_files = list(knowledge_base_dir.glob("*.txt"))
    
    print(f"Найдено {len(txt_files)} текстовых файлов")
    
    for txt_file in txt_files:
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Извлекаем заголовок из первой строки (обычно это название статьи)
            lines = content.split("\n")
            title = lines[0].strip() if lines else txt_file.stem
            
            # Создаём документ с метаданными
            doc = Document(
                page_content=content,
                metadata={
                    "source": str(txt_file.relative_to(knowledge_base_dir)),
                    "title": title,
                    "filename": txt_file.name,
                }
            )
            documents.append(doc)
            print(f"  Загружен: {txt_file.name} ({len(content)} символов)")
            
        except Exception as e:
            print(f"  Ошибка при загрузке {txt_file.name}: {e}")
    
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """
    Разбивает документы на чанки с сохранением метаданных.
    
    Args:
        documents: Список исходных документов
        
    Returns:
        Список чанков с обновлёнными метаданными
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    print(f"\nРазбиение {len(documents)} документов на чанки...")
    chunks = text_splitter.split_documents(documents)
    
    # Добавляем информацию о позиции чанка в исходном документе
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
        # Сохраняем оригинальный источник
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = "unknown"
    
    print(f"Создано {len(chunks)} чанков")
    print(f"Средний размер чанка: {sum(len(c.page_content) for c in chunks) // len(chunks)} символов")
    
    return chunks


def create_vector_index(chunks: List[Document], vector_db_dir: Path) -> Chroma:
    """
    Создаёт векторный индекс в ChromaDB.
    
    Args:
        chunks: Список чанков для индексации
        vector_db_dir: Директория для сохранения индекса
        
    Returns:
        Объект Chroma с векторным индексом
    """
    print(f"\nИнициализация модели эмбеддингов: {EMBEDDING_MODEL_NAME}")
    print("Это может занять некоторое время при первом запуске (загрузка модели)...")
    
    # Инициализация модели эмбеддингов
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},  # Используем CPU, можно изменить на "cuda" при наличии GPU
    )
    
    print(f"Размерность эмбеддингов: {EMBEDDING_DIMENSION}")
    print(f"\nГенерация эмбеддингов для {len(chunks)} чанков...")
    
    # Создание векторного индекса в ChromaDB
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(vector_db_dir),
        collection_name="knowledge_base",
    )
    
    # Сохранение индекса на диск
    vectorstore.persist()
    
    print(f"Векторный индекс сохранён в: {vector_db_dir}")
    
    return vectorstore


def load_terms_map(terms_map_file: Path = None) -> dict:
    """
    Загружает словарь замен терминов.
    
    Args:
        terms_map_file: Путь к файлу terms_map.json
        
    Returns:
        Словарь {оригинальный_термин: замененный_термин}
    """
    if terms_map_file is None:
        terms_map_file = TERMS_MAP_FILE
    
    if not terms_map_file.exists():
        print(f"⚠ Предупреждение: файл {terms_map_file} не найден. Расширение запросов отключено.")
        return {}
    
    try:
        with open(terms_map_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ Предупреждение: не удалось загрузить {terms_map_file}: {e}")
        return {}


def expand_query(query: str, terms_map: dict = None) -> str:
    """
    Расширяет запрос, заменяя оригинальные термины на замененные.
    
    Это необходимо, так как в базе знаний все термины были заменены
    (например, "Sharingan" → "Crimson Lens"), и поиск по оригинальным
    терминам не находит нужные документы.
    
    Args:
        query: Исходный запрос пользователя
        terms_map: Словарь замен терминов (если None, загружается автоматически)
        
    Returns:
        Расширенный запрос с замененными терминами
    """
    if terms_map is None:
        terms_map = load_terms_map()
    
    if not terms_map:
        return query
    
    expanded_query = query
    replacements_made = []
    
    # Сортируем термины по длине (от длинных к коротким), чтобы сначала заменять
    # составные термины (например, "Uchiha Clan" перед "Uchiha")
    sorted_terms = sorted(terms_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replaced in sorted_terms:
        # Заменяем с учетом регистра (case-insensitive)
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        if pattern.search(expanded_query):
            expanded_query = pattern.sub(replaced, expanded_query)
            replacements_made.append((original, replaced))
    
    if replacements_made:
        print(f"  Расширение запроса: {replacements_made}")
    
    return expanded_query


def restore_original_terms(text: str, terms_map: dict = None) -> str:
    """
    Восстанавливает оригинальные термины в тексте.
    Выполняет обратную замену: заменённые термины → оригинальные.
    
    Это необходимо, так как в базе знаний все термины были заменены,
    но пользователю нужно показывать ответы с оригинальными терминами.
    
    Args:
        text: Текст с заменёнными терминами (из базы знаний)
        terms_map: Словарь замен (если None, загружается автоматически)
        
    Returns:
        Текст с восстановленными оригинальными терминами
        
    Example:
        >>> restore_original_terms("Crimson Lens is used by Noctryn Line")
        "Sharingan is used by Uchiha Clan"
    """
    if terms_map is None:
        terms_map = load_terms_map()
    
    if not terms_map:
        return text
    
    # Создаём обратный маппинг: заменённый → оригинальный
    reverse_map = {replaced: original for original, replaced in terms_map.items()}
    
    restored_text = text
    replacements_made = []
    
    # Сортируем по длине (от длинных к коротким), чтобы сначала заменять
    # составные термины (например, "Noctryn Line" перед "Noctryn")
    sorted_terms = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for replaced, original in sorted_terms:
        # Заменяем с учетом регистра (case-insensitive)
        pattern = re.compile(re.escape(replaced), re.IGNORECASE)
        if pattern.search(restored_text):
            restored_text = pattern.sub(original, restored_text)
            replacements_made.append((replaced, original))
    
    return restored_text


def load_vectorstore(vector_db_dir: Path = None) -> Chroma:
    """
    Загружает существующий векторный индекс из ChromaDB.
    
    Args:
        vector_db_dir: Путь к директории с индексом (по умолчанию VECTOR_DB_DIR)
        
    Returns:
        Объект Chroma с загруженным индексом
    """
    if vector_db_dir is None:
        vector_db_dir = VECTOR_DB_DIR
    
    if not vector_db_dir.exists():
        raise FileNotFoundError(
            f"Векторный индекс не найден в {vector_db_dir}. "
            "Сначала запустите build_index.py для создания индекса."
        )
    
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
    )
    
    vectorstore = Chroma(
        persist_directory=str(vector_db_dir),
        embedding_function=embeddings,
        collection_name="knowledge_base",
    )
    
    return vectorstore


def test_search(vectorstore: Chroma, test_queries: List[str] = None, use_query_expansion: bool = True, restore_terms: bool = True):
    """
    Тестирует поиск по векторному индексу.
    
    Args:
        vectorstore: Объект Chroma с индексом
        test_queries: Список тестовых запросов
        use_query_expansion: Использовать ли расширение запросов (замену терминов)
        restore_terms: Восстанавливать ли оригинальные термины в результатах
    """
    if test_queries is None:
        test_queries = [
            "What is the Crimson Lens?",
            "Who is Kael Vexaris?",
            "Tell me about Verdant Reach",
        ]
    
    terms_map = load_terms_map() if (use_query_expansion or restore_terms) else {}
    
    print("\n" + "="*60)
    print("ТЕСТИРОВАНИЕ ПОИСКА")
    print("="*60)
    if use_query_expansion and terms_map:
        print("(Используется расширение запросов для замены терминов)")
    if restore_terms and terms_map:
        print("(Восстанавливаются оригинальные термины в результатах)")
    
    for query in test_queries:
        print(f"\nЗапрос: {query}")
        print("-" * 60)
        
        # Расширяем запрос, заменяя оригинальные термины на замененные
        expanded_query = expand_query(query, terms_map) if use_query_expansion else query
        if expanded_query != query:
            print(f"Расширенный запрос: {expanded_query}")
        
        # Поиск топ-3 релевантных чанков
        results = vectorstore.similarity_search_with_score(expanded_query, k=3)
        
        for i, (doc, score) in enumerate(results, 1):
            # Восстанавливаем оригинальные термины в тексте
            content = doc.page_content
            if restore_terms and terms_map:
                content = restore_original_terms(content, terms_map)
            
            print(f"\nРезультат {i} (релевантность: {score:.4f}):")
            print(f"  Источник: {doc.metadata.get('source', 'unknown')}")
            print(f"  Заголовок: {doc.metadata.get('title', 'N/A')}")
            print(f"  Чанк ID: {doc.metadata.get('chunk_id', 'N/A')}")
            print(f"  Текст (первые 200 символов):")
            print(f"  {content[:200]}...")


def main():
    """Основная функция для построения векторного индекса."""
    start_time = time.time()
    
    print("="*60)
    print("ПОСТРОЕНИЕ ВЕКТОРНОГО ИНДЕКСА БАЗЫ ЗНАНИЙ")
    print("="*60)
    print(f"\nМодель эмбеддингов: {EMBEDDING_MODEL_NAME}")
    print(f"Размерность эмбеддингов: {EMBEDDING_DIMENSION}")
    print(f"Размер чанка: {CHUNK_SIZE} символов")
    print(f"Перекрытие чанков: {CHUNK_OVERLAP} символов")
    print(f"База знаний: {KNOWLEDGE_BASE_DIR}")
    print(f"Выходная директория: {VECTOR_DB_DIR}")
    
    # Проверка существования базы знаний
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"\nОШИБКА: Директория {KNOWLEDGE_BASE_DIR} не найдена!")
        return
    
    # Создание выходной директории
    VECTOR_DB_DIR.mkdir(exist_ok=True)
    
    # 1. Загрузка документов
    print("\n" + "="*60)
    print("ШАГ 1: ЗАГРУЗКА ДОКУМЕНТОВ")
    print("="*60)
    documents = load_documents(KNOWLEDGE_BASE_DIR)
    
    if not documents:
        print("ОШИБКА: Не найдено документов для индексации!")
        return
    
    # 2. Разбиение на чанки
    print("\n" + "="*60)
    print("ШАГ 2: РАЗБИЕНИЕ НА ЧАНКИ")
    print("="*60)
    chunks = split_documents(documents)
    
    # 3. Создание векторного индекса
    print("\n" + "="*60)
    print("ШАГ 3: ГЕНЕРАЦИЯ ЭМБЕДДИНГОВ И СОЗДАНИЕ ИНДЕКСА")
    print("="*60)
    vectorstore = create_vector_index(chunks, VECTOR_DB_DIR)
    
    # 4. Тестирование поиска
    print("\n" + "="*60)
    print("ШАГ 4: ТЕСТИРОВАНИЕ")
    print("="*60)
    test_search(vectorstore)
    
    # Итоговая статистика
    elapsed_time = time.time() - start_time
    print("\n" + "="*60)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("="*60)
    print(f"Обработано документов: {len(documents)}")
    print(f"Создано чанков: {len(chunks)}")
    print(f"Время выполнения: {elapsed_time:.2f} секунд ({elapsed_time/60:.2f} минут)")
    print(f"Векторный индекс сохранён в: {VECTOR_DB_DIR.absolute()}")
    print("\nИндекс готов к использованию!")


if __name__ == "__main__":
    main()
