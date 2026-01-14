"""
Задание 7 — автоматическое тестирование (evaluation) RAG-бота на golden set.

Запуск (пример):
  python task7/create_gaps.py --apply
  python task7/evaluate.py --llm-provider ollama --llm-model mistral

Результаты:
- task7/logs.jsonl                (подробные логи запросов)
- task7/evaluation_results.json   (сводка метрик + результаты по каждому вопросу)
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    # когда task7 — пакет (есть task7/__init__.py)
    from task7.rag_logger import (
        RAGLogger,
        LogRecord,
        utc_now_iso,
        extract_sources_and_scores,
        count_relevant,
    )
except ModuleNotFoundError:
    # когда запускают как "python task7/evaluate.py" и sys.path[0] == task7/
    from rag_logger import (  # type: ignore
        RAGLogger,
        LogRecord,
        utc_now_iso,
        extract_sources_and_scores,
        count_relevant,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = REPO_ROOT / "task7" / "golden_questions.txt"
DEFAULT_LOG_PATH = REPO_ROOT / "task7" / "logs.jsonl"
DEFAULT_RESULTS_PATH = REPO_ROOT / "task7" / "evaluation_results.json"
DEFAULT_GAPPED_INDEX_DIR = REPO_ROOT / "task7" / "vector_index_gapped"


REFUSAL_PATTERNS = [
    "я не знаю",
    "не знаю ответа",
    "не смог найти",
    "нет информации",
    "не могу найти",
    "не удалось найти",
    "не могу ответить",
]


@dataclass(frozen=True)
class GoldenQuestion:
    query: str
    expected: str
    category: str


def parse_golden_questions(path: Path) -> List[GoldenQuestion]:
    text = path.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in text.splitlines()]

    items: List[GoldenQuestion] = []
    q: Optional[str] = None
    expected: Optional[str] = None
    category: Optional[str] = None

    def flush():
        nonlocal q, expected, category
        if q and expected and category:
            items.append(GoldenQuestion(query=q.strip(), expected=expected.strip(), category=category.strip()))
        q, expected, category = None, None, None

    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("Q:"):
            flush()
            q = s[len("Q:") :].strip()
        elif s.startswith("EXPECTED:"):
            expected = s[len("EXPECTED:") :].strip()
        elif s.startswith("CATEGORY:"):
            category = s[len("CATEGORY:") :].strip()

    flush()
    return items


def looks_like_refusal(answer: str) -> bool:
    a = (answer or "").strip().lower()
    return any(pat in a for pat in REFUSAL_PATTERNS)


def normalize_expected_keywords(expected: str) -> List[str]:
    """
    Для известных тем EXPECTED хранит ключевые слова через '|'.
    Для отсутствующих/удалённых ожидается 'не знаю'.
    """
    if not expected:
        return []
    if expected.strip().lower() == "не знаю":
        return []
    return [kw.strip() for kw in expected.split("|") if kw.strip()]


def is_correct_answer(expected: str, category: str, answer: str) -> bool:
    exp_is_unknown = expected.strip().lower() == "не знаю"
    refusal = looks_like_refusal(answer)

    if category in ("удалённая_тема", "отсутствующая_тема"):
        # корректно: честно отказался
        return exp_is_unknown and refusal

    # известная_тема
    if refusal:
        return False
    keywords = normalize_expected_keywords(expected)
    if not keywords:
        # если в golden set забыли ключевые слова — используем только не-отказ и длину
        return len((answer or "").strip()) >= 50
    ans = (answer or "").lower()
    return any(kw.lower() in ans for kw in keywords) and len((answer or "").strip()) >= 50


def compute_prf(results: List[Dict]) -> Dict[str, float]:
    """
    Precision/Recall/F1 для "известная_тема" как позитивного класса.
    """
    tp = fp = fn = 0
    for r in results:
        expected_pos = r["category"] == "известная_тема"
        predicted_pos = r["predicted_success"] is True
        if predicted_pos and expected_pos:
            tp += 1
        elif predicted_pos and not expected_pos:
            fp += 1
        elif (not predicted_pos) and expected_pos:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def main() -> int:
    parser = argparse.ArgumentParser(description="Задание 7: evaluate RAG bot on golden set")
    parser.add_argument("--questions", type=str, default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--log", type=str, default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--results", type=str, default=str(DEFAULT_RESULTS_PATH))
    parser.add_argument("--vector-index", type=str, default=str(DEFAULT_GAPPED_INDEX_DIR))
    parser.add_argument("--llm-provider", type=str, default=os.getenv("LLM_PROVIDER", "ollama"))
    parser.add_argument("--llm-model", type=str, default=os.getenv("LLM_MODEL", None))
    parser.add_argument("--openai-api-key", type=str, default=os.getenv("OPENAI_API_KEY", None))
    parser.add_argument("--use-few-shot", action="store_true", default=True)
    parser.add_argument("--no-few-shot", action="store_false", dest="use_few_shot")
    parser.add_argument("--use-cot", action="store_true", default=True)
    parser.add_argument("--no-cot", action="store_false", dest="use_cot")
    parser.add_argument("--relevance-threshold", type=float, default=1.0)
    args = parser.parse_args()

    questions_path = Path(args.questions)
    log_path = Path(args.log)
    results_path = Path(args.results)
    vector_index_dir = Path(args.vector_index)

    if not questions_path.exists():
        print(f"ОШИБКА: golden set не найден: {questions_path}")
        return 2

    if not vector_index_dir.exists():
        print(f"ОШИБКА: не найден индекс для теста: {vector_index_dir}")
        print("Сначала создайте пробелы и пересоберите индекс: python task7/create_gaps.py --apply")
        return 2

    golden = parse_golden_questions(questions_path)
    if not golden:
        print("ОШИБКА: golden set пустой (не удалось распарсить вопросы).")
        return 2

    # Импортируем RAGBot из корня репозитория
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from rag_bot import RAGBot  # noqa: E402

    bot = RAGBot(
        vector_db_dir=vector_index_dir,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        api_key=args.openai_api_key,
    )

    logger = RAGLogger(log_path)

    per_question: List[Dict] = []
    correct = 0
    by_category: Dict[str, Dict[str, int]] = {}

    for item in golden:
        with logger.time_call() as t:
            error: Optional[str] = None
            try:
                result = bot.generate_answer(
                    item.query,
                    use_few_shot=args.use_few_shot,
                    use_cot=args.use_cot,
                    enable_protection=True,
                )
            except Exception as e:
                result = {"answer": "", "context_chunks": [], "reasoning": None}
                error = str(e)

        answer = (result or {}).get("answer") or ""
        context_chunks = (result or {}).get("context_chunks") or []
        reasoning = (result or {}).get("reasoning")

        sources, scores = extract_sources_and_scores(context_chunks)
        chunks_found = len(context_chunks)
        chunks_relevant = count_relevant(scores, threshold=float(args.relevance_threshold))

        predicted_success = (not looks_like_refusal(answer)) and (len(answer.strip()) >= 50)
        is_ok = is_correct_answer(item.expected, item.category, answer)

        if is_ok:
            correct += 1

        by_category.setdefault(item.category, {"total": 0, "correct": 0})
        by_category[item.category]["total"] += 1
        by_category[item.category]["correct"] += 1 if is_ok else 0

        rec = LogRecord(
            query=item.query,
            timestamp=utc_now_iso(),
            chunks_found=chunks_found,
            chunks_relevant=chunks_relevant,
            answer_length=len(answer),
            answer=answer,
            sources=sources,
            is_successful=predicted_success,
            relevance_scores=scores,
            has_reasoning=bool(reasoning),
            response_time_ms=t.elapsed_ms,
            category=item.category,
            expected=item.expected,
            llm_provider=getattr(bot, "llm_provider", None),
            llm_model=getattr(bot, "llm_model", None),
            error=error,
        )
        logger.append(rec)

        per_question.append(
            {
                "query": item.query,
                "expected": item.expected,
                "category": item.category,
                "answer": answer,
                "chunks_found": chunks_found,
                "chunks_relevant": chunks_relevant,
                "sources": sources,
                "relevance_scores": scores,
                "response_time_ms": t.elapsed_ms,
                "predicted_success": predicted_success,
                "is_correct": is_ok,
                "error": error,
            }
        )

    accuracy = correct / len(golden)
    prf = compute_prf(per_question)

    avg_score = None
    all_scores = [s for r in per_question for s in (r.get("relevance_scores") or [])]
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)

    summary = {
        "timestamp_utc": utc_now_iso(),
        "vector_index_dir": str(vector_index_dir),
        "questions_file": str(questions_path),
        "log_file": str(log_path),
        "total": len(golden),
        "correct": correct,
        "accuracy": accuracy,
        "by_category": by_category,
        "known_theme_prf": prf,
        "avg_relevance_score": avg_score,
        "llm_provider": getattr(bot, "llm_provider", None),
        "llm_model": getattr(bot, "llm_model", None),
        "use_few_shot": bool(args.use_few_shot),
        "use_cot": bool(args.use_cot),
        "relevance_threshold": float(args.relevance_threshold),
    }

    results_path.write_text(
        json.dumps({"summary": summary, "results": per_question}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 80)
    print("EVALUATION DONE")
    print("=" * 80)
    print(f"Accuracy: {accuracy:.3f} ({correct}/{len(golden)})")
    print(f"Logs: {log_path}")
    print(f"Results: {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

