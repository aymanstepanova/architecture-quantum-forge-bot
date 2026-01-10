"""
RAG-бот с техниками Few-shot и Chain-of-Thought промптинга.

Использует векторный индекс из задания 3 для поиска релевантных фрагментов
и генерирует ответы с помощью LLM.
"""

import os
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from build_index import (
    load_vectorstore,
    expand_query,
    restore_original_terms,
    load_terms_map,
    VECTOR_DB_DIR
)

# Импорты для LLM
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠ Предупреждение: OpenAI не установлен. Установите: pip install openai")

# Конфигурация
DEFAULT_LLM_PROVIDER = "openai"  # "openai" или "ollama"
DEFAULT_LLM_MODEL_OPENAI = "gpt-4"  # GPT-4 лучше работает с русским языком
DEFAULT_LLM_MODEL_OLLAMA = "mistral"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 1000
DEFAULT_K_CHUNKS = 5  # Количество релевантных чанков для контекста
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"  # URL Ollama сервера


class RAGBot:
    """
    RAG-бот с поддержкой Few-shot и Chain-of-Thought промптинга.
    """
    
    def __init__(
        self,
        vector_db_dir: Path = None,
        llm_provider: str = None,
        llm_model: str = None,
        api_key: str = None,
        ollama_base_url: str = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        k_chunks: int = DEFAULT_K_CHUNKS,
    ):
        """
        Инициализация RAG-бота.
        
        Args:
            vector_db_dir: Путь к векторному индексу
            llm_provider: Провайдер LLM ("openai" или "ollama")
            llm_model: Модель LLM для использования
            api_key: API ключ для OpenAI (если не указан, берётся из OPENAI_API_KEY)
            ollama_base_url: URL Ollama сервера (по умолчанию http://localhost:11434)
            temperature: Температура для генерации
            max_tokens: Максимальное количество токенов в ответе
            k_chunks: Количество релевантных чанков для контекста
        """
        # Загрузка векторного индекса
        if vector_db_dir is None:
            vector_db_dir = VECTOR_DB_DIR
        
        print(f"Загрузка векторного индекса из {vector_db_dir}...")
        self.vectorstore = load_vectorstore(vector_db_dir)
        print("✓ Векторный индекс загружен")
        
        # Загрузка словаря замен терминов
        self.terms_map = load_terms_map()
        if self.terms_map:
            print(f"✓ Загружено {len(self.terms_map)} терминов для замены")
        
        # Настройка LLM
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).lower()
        
        # Выбираем модель по умолчанию в зависимости от провайдера
        if not llm_model:
            if self.llm_provider == "ollama":
                self.llm_model = DEFAULT_LLM_MODEL_OLLAMA
            else:
                self.llm_model = DEFAULT_LLM_MODEL_OPENAI
        else:
            self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.k_chunks = k_chunks
        
        # Инициализация клиента LLM
        if self.llm_provider == "ollama":
            # Используем Ollama (локальные модели, бесплатно)
            ollama_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "OpenAI библиотека не установлена. Установите: pip install openai\n"
                    "Ollama использует OpenAI-совместимый API."
                )
            
            # Ollama использует OpenAI-совместимый API
            self.client = OpenAI(
                base_url=ollama_url + "/v1",
                api_key="ollama"  # Ollama не требует реальный ключ
            )
            print(f"✓ LLM клиент инициализирован (Ollama, модель: {self.llm_model})")
            print(f"  URL: {ollama_url}")
            print(f"  ⚠ Убедитесь, что Ollama запущен: ollama serve")
            print(f"  ⚠ И модель загружена: ollama pull {self.llm_model}")
        
        elif self.llm_provider == "openai":
            # Используем OpenAI API
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "OpenAI не установлен. Установите: pip install openai\n"
                    "Или используйте Ollama: llm_provider='ollama'"
                )
            
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "API ключ OpenAI не найден. Установите переменную окружения OPENAI_API_KEY\n"
                    "или передайте api_key при инициализации RAGBot.\n"
                    "Или используйте Ollama: llm_provider='ollama'"
                )
            
            self.client = OpenAI(api_key=self.api_key)
            print(f"✓ LLM клиент инициализирован (OpenAI, модель: {self.llm_model})")
        
        else:
            raise ValueError(
                f"Неизвестный провайдер LLM: {self.llm_provider}\n"
                "Поддерживаемые провайдеры: 'openai', 'ollama'"
            )
        
        # Загрузка few-shot примеров
        self.few_shot_examples = self._load_few_shot_examples()
        print(f"✓ Загружено {len(self.few_shot_examples)} few-shot примеров")
    
    def _load_few_shot_examples(self) -> List[Dict[str, str]]:
        """
        Загружает few-shot примеры из базы знаний.
        
        Returns:
            Список словарей с ключами 'question' и 'answer'
        """
        examples = []
        
        # Попытка извлечь примеры из векторного индекса
        # Ищем чанки с определениями и описаниями для формирования вопрос-ответ пар
        try:
            # Запросы для поиска определений
            definition_queries = [
                "What is Sharingan",
                "What is Rasengan",
            ]
            
            for query in definition_queries:
                try:
                    # Расширяем запрос для поиска в базе
                    expanded_query = expand_query(query, self.terms_map)
                    results = self.vectorstore.similarity_search(expanded_query, k=1)
                    
                    if results:
                        doc = results[0]
                        content = restore_original_terms(doc.page_content, self.terms_map)
                        title = doc.metadata.get('title', '').strip()
                        
                        if title and content:
                            # Извлекаем первые 2-3 предложения как ответ
                            sentences = [s.strip() for s in content.split('.') if s.strip()]
                            if len(sentences) >= 2:
                                # Формируем вопрос-ответ пару
                                # Восстанавливаем оригинальный термин в вопросе
                                original_term = title
                                # Пытаемся найти оригинальный термин в terms_map
                                reverse_map = {v: k for k, v in self.terms_map.items()}
                                if title in reverse_map:
                                    original_term = reverse_map[title]
                                
                                question = f"Что такое {original_term}?"
                                answer = '. '.join(sentences[:2]) + '.'
                                
                                # Ограничиваем длину ответа
                                if len(answer) > 300:
                                    answer = answer[:300] + '...'
                                
                                examples.append({
                                    "question": question,
                                    "answer": answer
                                })
                                
                                if len(examples) >= 2:
                                    break
                except Exception:
                    # Игнорируем ошибки при извлечении примеров
                    continue
        except Exception:
            # Если не удалось извлечь примеры, используем предопределённые
            pass
        
        # Если не удалось извлечь примеры, используем предопределённые
        if not examples:
            examples = [
                {
                    "question": "Что такое Sharingan?",
                    "answer": "[Шаги рассуждения]\n1. Ищу информацию о Sharingan в предоставленных документах.\n2. В документах указано, что Sharingan - это kekkei genkai клана Uchiha.\n3. Следовательно, могу дать ответ.\n\n[Ответ]\nSharingan (буквально: Копирующее Колесо Глаз) - это наследственная способность клана Uchiha, которая появляется выборочно среди его членов. Оно считается одним из трёх великих додзюцу. Sharingan даёт пользователю две основные способности: Глаз Проницательности и Глаз Гипноза."
                },
                {
                    "question": "Кто такой Naruto?",
                    "answer": "[Шаги рассуждения]\n1. Ищу информацию о Naruto в документах.\n2. Найдена информация о персонаже Naruto Uzumaki.\n3. Могу дать ответ на основе найденной информации.\n\n[Ответ]\nNaruto Uzumaki - главный персонаж истории, ниндзя из деревни Konoha. Он является джинчуурики Девятихвостого лиса и мечтает стать Hokage."
                }
            ]
        
        return examples[:2]  # Возвращаем максимум 2 примера
    
    def _format_few_shot_prompt(self) -> str:
        """
        Форматирует few-shot примеры для промпта.
        
        Returns:
            Строка с форматированными примерами
        """
        few_shot_text = ""
        for example in self.few_shot_examples:
            few_shot_text += f"Q: {example['question']}\n"
            few_shot_text += f"A: {example['answer']}\n\n"
        
        return few_shot_text
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """
        Форматирует найденные чанки в контекст для промпта.
        
        Args:
            chunks: Список словарей с ключами 'content', 'source', 'title'
            
        Returns:
            Отформатированный контекст
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get('source', 'unknown')
            title = chunk.get('title', 'N/A')
            content = chunk.get('content', '')
            
            context_parts.append(
                f"[Документ {i}]\n"
                f"Источник: {source}\n"
                f"Заголовок: {title}\n"
                f"Содержание: {content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_prompt(
        self,
        user_query: str,
        context_chunks: List[Dict],
        use_few_shot: bool = True,
        use_cot: bool = True,
        is_relevant: bool = True
    ) -> Tuple[str, str]:
        """
        Строит промпт для LLM с учётом Few-shot и Chain-of-Thought.
        
        Args:
            user_query: Запрос пользователя
            context_chunks: Найденные релевантные чанки
            use_few_shot: Использовать ли few-shot примеры
            use_cot: Использовать ли Chain-of-Thought
            
        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        # System промпт с Chain-of-Thought
        if use_cot:
            system_prompt = """Ты помощник, который отвечает на вопросы на основе предоставленной базы знаний.

КРИТИЧЕСКИ ВАЖНО:
- Отвечай ТОЛЬКО на русском языке (никогда не используй другие языки, включая английский, португальский и т.д.)
- НИКОГДА не смешивай языки в одном предложении
- Все слова в ответе должны быть на русском языке, кроме имён собственных из контекста
- ВСЕГДА используй информацию из предоставленного контекста, даже если она кажется неполной
- Если в контексте есть упоминания запрашиваемого персонажа/объекта, это релевантная информация - ОБЯЗАТЕЛЬНО используй её
- НЕ говори "Я не знаю", если в контексте есть хоть какая-то информация по запросу
- НО: Если контекст НЕРЕЛЕВАНТЕН для запроса (не содержит информации по теме), ОБЯЗАТЕЛЬНО ответь "Я не знаю" и НЕ добавляй выдуманную информацию
- НИКОГДА не выдумывай факты, не упомянутые в контексте
- НИКОГДА не делай предположений о том, что не упомянуто в контексте
- ВСЕ имена и термины в контексте - это РЕАЛЬНЫЕ имена персонажей и объектов этого мира, НЕ псевдонимы
- Используй имена и термины ТОЧНО так, как они указаны в контексте (не переводи и не меняй их)
- Пиши грамматически правильный, связный текст на русском языке
- Используй правильные русские грамматические формы и окончания

ВАЖНО: Всегда следуй этим шагам:
1. Внимательно прочитай ВЕСЬ предоставленный контекст
2. Найди ВСЕ упоминания запрашиваемого персонажа/объекта в контексте
3. Собери информацию из всех найденных фрагментов
4. Используй имена и термины ТОЧНО так, как они указаны в контексте
5. Сформируй связный ответ на основе найденной информации
6. Если информации много, выбери наиболее важные факты

Формат ответа (строго соблюдай):
[Шаги рассуждения]
1. В предоставленном контексте я нашел информацию о [имя/объект]...
2. В документах указано, что...
3. Следовательно, могу дать следующий ответ...

[Ответ]
Твой полный ответ на русском языке здесь. Используй информацию из контекста. Используй имена и термины ТОЧНО так, как они указаны в контексте. Без дублирования шагов рассуждения."""
        else:
            system_prompt = """Ты помощник, который отвечает на вопросы на основе предоставленной базы знаний.

КРИТИЧЕСКИ ВАЖНО:
- Отвечай ТОЛЬКО на русском языке (никогда не используй другие языки, включая английский, португальский и т.д.)
- НИКОГДА не смешивай языки в одном предложении
- Все слова в ответе должны быть на русском языке, кроме имён собственных из контекста
- ВСЕГДА используй информацию из предоставленного контекста
- Если в контексте есть упоминания запрашиваемого персонажа/объекта, ОБЯЗАТЕЛЬНО используй эту информацию
- НЕ говори "Я не знаю", если в контексте есть информация по запросу
- НО: Если контекст НЕРЕЛЕВАНТЕН для запроса (не содержит информации по теме), ОБЯЗАТЕЛЬНО ответь "Я не знаю" и НЕ добавляй выдуманную информацию
- НИКОГДА не выдумывай факты, не упомянутые в контексте
- НИКОГДА не делай предположений о том, что не упомянуто в контексте
- ВСЕ имена и термины в контексте - это РЕАЛЬНЫЕ имена персонажей и объектов этого мира, НЕ псевдонимы
- Используй имена и термины ТОЧНО так, как они указаны в контексте (не переводи и не меняй их)
- Пиши грамматически правильный, связный текст на русском языке
- Используй правильные русские грамматические формы и окончания

Используй только информацию из предоставленного контекста.
Используй имена и термины ТОЧНО так, как они указаны в контексте.
Если информации действительно нет в контексте или контекст нерелевантен, честно скажи "Я не знаю" и НЕ добавляй выдуманную информацию."""
        
        # User промпт
        user_prompt_parts = []
        
        # Few-shot примеры
        if use_few_shot and self.few_shot_examples:
            few_shot_text = self._format_few_shot_prompt()
            user_prompt_parts.append("Примеры вопросов и ответов:\n")
            user_prompt_parts.append(few_shot_text)
            user_prompt_parts.append("---\n")
        
        # Контекст из базы знаний
        context_text = self._format_context(context_chunks)
        if is_relevant:
            user_prompt_parts.append("Контекст из базы знаний (ОБЯЗАТЕЛЬНО используй эту информацию для ответа):\n")
            user_prompt_parts.append(context_text)
            user_prompt_parts.append("\n---\n")
            user_prompt_parts.append("ВАЖНО: В предоставленном контексте есть информация по запросу. Используй её для формирования ответа.\n")
        else:
            user_prompt_parts.append("Контекст из базы знаний (НЕРЕЛЕВАНТЕН для данного запроса):\n")
            user_prompt_parts.append(context_text)
            user_prompt_parts.append("\n---\n")
            user_prompt_parts.append("ВАЖНО: Предоставленный контекст НЕ содержит информации по запросу. Ответь честно: 'Я не знаю'.\n")
        user_prompt_parts.append("---\n")
        
        # Запрос пользователя
        user_prompt_parts.append(f"Q: {user_query}\n")
        if use_cot:
            user_prompt_parts.append("A: [Начни с шагов рассуждения, затем дай ответ на основе предоставленного контекста]")
        else:
            user_prompt_parts.append("A: [Ответь на основе предоставленного контекста]")
        
        user_prompt = "\n".join(user_prompt_parts)
        
        return system_prompt, user_prompt
    
    def search_knowledge_base(self, query: str, k: int = None, min_relevance: float = None, restore_terms: bool = False) -> List[Dict]:
        """
        Ищет релевантные чанки в базе знаний.
        
        Args:
            query: Запрос пользователя
            k: Количество чанков для возврата (по умолчанию self.k_chunks)
            min_relevance: Минимальная релевантность (максимальный score, меньше = лучше)
            restore_terms: Восстанавливать ли оригинальные термины (по умолчанию False - оставляем как в базе)
            
        Returns:
            Список словарей с информацией о чанках
        """
        k = k or self.k_chunks
        
        # Расширяем запрос (заменяем оригинальные термины)
        expanded_query = expand_query(query, self.terms_map)
        
        # Поиск большего количества чанков для лучшей фильтрации
        search_k = k * 2 if min_relevance else k
        results = self.vectorstore.similarity_search_with_score(expanded_query, k=search_k)
        
        # Формируем контекст для LLM с фильтрацией по релевантности
        context_chunks = []
        for doc, score in results:
            # В ChromaDB score - это расстояние (меньше = лучше)
            # Для cosine similarity: 0 = идеально, 1+ = плохо
            # Фильтруем только очень плохие результаты (если указан min_relevance)
            if min_relevance is not None and score > min_relevance:
                continue
            
            # НЕ восстанавливаем термины - оставляем как в базе знаний (на языке нового мира)
            # Это важно, чтобы модель не путалась с "псевдонимами"
            content = doc.page_content if not restore_terms else restore_original_terms(doc.page_content, self.terms_map)
            
            context_chunks.append({
                "content": content,
                "source": doc.metadata.get("source"),
                "title": doc.metadata.get("title"),
                "relevance": float(score)
            })
            
            if len(context_chunks) >= k:
                break
        
        return context_chunks
    
    def generate_answer(
        self,
        query: str,
        use_few_shot: bool = True,
        use_cot: bool = True,
        k_chunks: int = None
    ) -> Dict[str, any]:
        """
        Генерирует ответ на запрос пользователя.
        
        Args:
            query: Запрос пользователя
            use_few_shot: Использовать ли few-shot примеры
            use_cot: Использовать ли Chain-of-Thought
            k_chunks: Количество чанков для поиска
            
        Returns:
            Словарь с ключами:
            - 'answer': ответ модели
            - 'context_chunks': использованные чанки
            - 'reasoning': шаги рассуждения (если use_cot=True)
        """
        # Поиск релевантных чанков
        # Используем более мягкую фильтрацию по релевантности (score < 1.5 обычно приемлемо)
        context_chunks = self.search_knowledge_base(query, k=k_chunks, min_relevance=1.5)
        
        if not context_chunks:
            return {
                "answer": "Извините, я не смог найти релевантную информацию в базе знаний для вашего запроса.",
                "context_chunks": [],
                "reasoning": None
            }
        
        # Проверяем релевантность найденных чанков
        # Если средняя релевантность очень низкая (score > 1.0), контекст скорее всего нерелевантен
        avg_relevance = sum(chunk['relevance'] for chunk in context_chunks) / len(context_chunks)
        
        # Проверяем, есть ли в контексте упоминания ключевых слов из запроса
        query_lower = query.lower()
        # Извлекаем ключевые слова (исключаем стоп-слова и короткие слова)
        stop_words = {'как', 'что', 'кто', 'где', 'когда', 'почему', 'какой', 'какая', 'какое', 'какие', 
                     'это', 'этот', 'эта', 'это', 'для', 'приготовить', 'сделать', 'дать', 'рассказать'}
        query_terms = [term.strip() for term in query_lower.split() 
                      if len(term.strip()) > 2 and term.strip() not in stop_words]
        
        has_relevant_content = False
        if query_terms:
            for chunk in context_chunks:
                content_lower = chunk['content'].lower()
                # Проверяем, есть ли хотя бы одно ключевое слово из запроса в контексте
                if any(term in content_lower for term in query_terms):
                    has_relevant_content = True
                    break
        
        # Если контекст явно нерелевантен (высокий score И нет ключевых слов), возвращаем "Я не знаю"
        if avg_relevance > 1.0 and not has_relevant_content:
            return {
                "answer": "Извините, я не знаю ответа на этот вопрос. В базе знаний нет информации по данной теме.",
                "context_chunks": context_chunks,
                "reasoning": None
            }
        
        # Определяем, релевантен ли контекст для промпта
        is_relevant = avg_relevance < 1.0 or has_relevant_content
        
        
        # Построение промпта
        system_prompt, user_prompt = self._build_prompt(
            query,
            context_chunks,
            use_few_shot=use_few_shot,
            use_cot=use_cot,
            is_relevant=is_relevant
        )
        
        # Генерация ответа через LLM
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Извлекаем шаги рассуждения и очищаем ответ от дублирования
            reasoning = None
            final_answer = answer
            
            if use_cot and ("[Шаги рассуждения]" in answer or "[Ответ]" in answer):
                # Разделяем reasoning и ответ
                if "[Ответ]" in answer:
                    parts = answer.split("[Ответ]")
                    if len(parts) >= 2:
                        reasoning_part = parts[0].replace("[Шаги рассуждения]", "").strip()
                        final_answer = parts[1].strip()
                        
                        # Очищаем reasoning от лишних заголовков
                        reasoning_lines = []
                        for line in reasoning_part.split('\n'):
                            line = line.strip()
                            if line and not line.lower().startswith("шаги рассуждения"):
                                reasoning_lines.append(line)
                        
                        if reasoning_lines:
                            reasoning = "\n".join(reasoning_lines)
                
                # Если формат другой, пытаемся извлечь reasoning
                elif "[Шаги рассуждения]" in answer or "1." in answer[:200]:
                    lines = answer.split('\n')
                    reasoning_lines = []
                    answer_lines = []
                    in_reasoning = False
                    in_answer = False
                    
                    for line in lines:
                        line_lower = line.lower()
                        if "[шаги рассуждения]" in line_lower or (line.strip().startswith("1.") and not in_answer):
                            in_reasoning = True
                            in_answer = False
                            if "[шаги рассуждения]" not in line_lower:
                                reasoning_lines.append(line.strip())
                        elif "[ответ]" in line_lower or (in_reasoning and not line.strip().startswith(("1.", "2.", "3.", "4.", "5.")) and line.strip()):
                            in_answer = True
                            in_reasoning = False
                            if "[ответ]" not in line_lower:
                                answer_lines.append(line.strip())
                        elif in_reasoning:
                            if line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
                                reasoning_lines.append(line.strip())
                        elif in_answer:
                            answer_lines.append(line.strip())
                    
                    if reasoning_lines:
                        reasoning = "\n".join(reasoning_lines)
                    if answer_lines:
                        final_answer = "\n".join(answer_lines)
            
            # Очищаем финальный ответ от дублирования reasoning
            if reasoning and reasoning in final_answer:
                final_answer = final_answer.replace(reasoning, "").strip()
            
            # Убираем повторяющиеся заголовки и дублирование
            if "Шаги рассуждения:" in final_answer:
                final_answer = final_answer.split("Шаги рассуждения:")[-1].strip()
            if "Ответ:" in final_answer:
                final_answer = final_answer.split("Ответ:")[-1].strip()
            
            # Очищаем от дублирования reasoning в ответе
            if reasoning:
                # Убираем reasoning из ответа, если он там есть
                reasoning_clean = reasoning.replace("[Шаги рассуждения]", "").strip()
                if reasoning_clean in final_answer:
                    final_answer = final_answer.replace(reasoning_clean, "").strip()
                # Убираем по частям
                for line in reasoning_clean.split('\n'):
                    if line.strip() and line.strip() in final_answer:
                        final_answer = final_answer.replace(line.strip(), "").strip()
            
            # Убираем лишние пустые строки
            final_answer = "\n".join([line for line in final_answer.split('\n') if line.strip()])
            
            return {
                "answer": final_answer,
                "context_chunks": context_chunks,
                "reasoning": reasoning
            }
            
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg.lower():
                return {
                    "answer": (
                        "❌ Ошибка: Превышена квота OpenAI API.\n\n"
                        "РЕШЕНИЕ: Используйте локальную модель через Ollama:\n"
                        "1. Установите Ollama: https://ollama.ai\n"
                        "2. Запустите сервер: ollama serve\n"
                        "3. Загрузите модель: ollama pull mistral\n"
                        "4. Используйте бота с провайдером Ollama:\n"
                        "   bot = RAGBot(llm_provider='ollama', llm_model='mistral')"
                    ),
                    "context_chunks": context_chunks,
                    "reasoning": None
                }
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                if self.llm_provider == "ollama":
                    ollama_url = getattr(self.client, 'base_url', 'http://localhost:11434').replace("/v1", "")
                    return {
                        "answer": (
                            f"❌ Ошибка: Не удалось подключиться к Ollama.\n\n"
                            "РЕШЕНИЕ:\n"
                            f"1. Убедитесь, что Ollama запущен: ollama serve\n"
                            f"2. Проверьте URL: {ollama_url}\n"
                            f"3. Убедитесь, что модель загружена: ollama pull {self.llm_model}"
                        ),
                        "context_chunks": context_chunks,
                        "reasoning": None
                    }
                else:
                    return {
                        "answer": f"❌ Ошибка подключения к API: {error_msg}",
                        "context_chunks": context_chunks,
                        "reasoning": None
                    }
            else:
                return {
                    "answer": f"❌ Ошибка при генерации ответа: {error_msg}",
                    "context_chunks": context_chunks,
                    "reasoning": None
                }
    
    def chat(self, query: str, verbose: bool = True) -> str:
        """
        Упрощённый метод для получения ответа (без деталей).
        
        Args:
            query: Запрос пользователя
            verbose: Выводить ли детальную информацию
            
        Returns:
            Ответ бота
        """
        result = self.generate_answer(query)
        
        # Проверка на None (на случай ошибки)
        if result is None:
            error_msg = "Ошибка: не удалось получить ответ от модели"
            if verbose:
                print(f"\n❌ {error_msg}")
            return error_msg
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"Запрос: {query}")
            print(f"{'='*80}")
            
            if result.get('reasoning'):
                print(f"\n[Шаги рассуждения]")
                print(result['reasoning'])
                print()
            
            print(f"[Ответ]")
            print(result.get('answer', 'Ошибка: ответ не получен'))
            
            context_chunks = result.get('context_chunks', [])
            print(f"\n[Использовано чанков: {len(context_chunks)}]")
            for i, chunk in enumerate(context_chunks[:3], 1):
                print(f"  {i}. {chunk.get('source', 'unknown')} (релевантность: {chunk.get('relevance', 0):.4f})")
        
        return result.get('answer', 'Ошибка: ответ не получен')


def main():
    """Демонстрация работы RAG-бота."""
    print("="*80)
    print("ИНИЦИАЛИЗАЦИЯ RAG-БОТА")
    print("="*80)
    
    try:
        # Инициализация бота
        bot = RAGBot()
        
        print("\n" + "="*80)
        print("RAG-БОТ ГОТОВ К РАБОТЕ")
        print("="*80)
        print("\nПримеры использования:")
        print("  bot.chat('Что такое Sharingan?')")
        print("  bot.generate_answer('Кто такой Naruto?')")
        print("\nДля интерактивного режима запустите: python rag_bot_repl.py")
        
        # Тестовый запрос
        print("\n" + "="*80)
        print("ТЕСТОВЫЙ ЗАПРОС")
        print("="*80)
        test_query = "Что такое Sharingan?"
        bot.chat(test_query)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
