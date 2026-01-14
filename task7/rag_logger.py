"""
Задание 7 — логирование запросов к RAG-боту.

Формат: JSONL (одна строка = один JSON-объект), чтобы было удобно:
- дописывать потоково
- анализировать постфактум
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class LogRecord:
    query: str
    timestamp: str
    chunks_found: int
    chunks_relevant: int
    answer_length: int
    answer: str
    sources: List[str]
    is_successful: bool
    relevance_scores: List[float]
    has_reasoning: bool
    response_time_ms: int

    # Дополнительные поля (не обязательные, но полезные для аналитики)
    category: Optional[str] = None
    expected: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    error: Optional[str] = None


class RAGLogger:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: LogRecord) -> None:
        line = json.dumps(asdict(record), ensure_ascii=False)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def time_call(self):
        """
        Контекст-менеджер для измерения времени выполнения.
        Использование:

            with logger.time_call() as t:
                result = ...
            ms = t.elapsed_ms
        """

        return _Timer()


class _Timer:
    def __init__(self):
        self._start = None
        self.elapsed_ms: int = 0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        end = time.perf_counter()
        self.elapsed_ms = int(round((end - (self._start or end)) * 1000))
        return False


def extract_sources_and_scores(context_chunks: List[Dict[str, Any]]) -> tuple[list[str], list[float]]:
    sources: List[str] = []
    scores: List[float] = []

    for ch in context_chunks or []:
        src = ch.get("source") or "unknown"
        sources.append(str(src))
        try:
            scores.append(float(ch.get("relevance")))
        except Exception:
            # на всякий случай
            pass

    return sources, scores


def count_relevant(scores: List[float], threshold: float) -> int:
    return sum(1 for s in scores if s <= threshold)

