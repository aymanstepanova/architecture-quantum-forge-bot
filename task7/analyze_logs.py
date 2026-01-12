"""
Задание 7 — анализ логов запросов (JSONL), полученных из evaluate.py (или реального использования бота).

Выход:
  task7/analysis_report.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "task7" / "logs.jsonl"
DEFAULT_REPORT_PATH = REPO_ROOT / "task7" / "analysis_report.md"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows


def fmt_pct(x: float) -> str:
    return f"{x*100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Задание 7: анализ logs.jsonl")
    parser.add_argument("--log", type=str, default=str(DEFAULT_LOG_PATH))
    parser.add_argument("--out", type=str, default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--bad-score-threshold", type=float, default=1.5)
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)

    if not log_path.exists():
        print(f"ОШИБКА: лог не найден: {log_path}")
        return 2

    rows = read_jsonl(log_path)
    if not rows:
        print("ОШИБКА: лог пустой.")
        return 2

    total = len(rows)
    success = sum(1 for r in rows if r.get("is_successful") is True)
    success_rate = success / total

    by_cat = defaultdict(lambda: {"total": 0, "success": 0})
    for r in rows:
        cat = r.get("category") or "unknown"
        by_cat[cat]["total"] += 1
        by_cat[cat]["success"] += 1 if r.get("is_successful") is True else 0

    # темы, где бот "не отвечает" = is_successful False
    failed_queries = [r.get("query", "") for r in rows if r.get("is_successful") is False]
    top_failed = Counter([q.strip() for q in failed_queries if q.strip()]).most_common(10)

    # источники в успешных/неуспешных
    failed_sources = Counter()
    for r in rows:
        if r.get("is_successful") is False:
            for s in r.get("sources") or []:
                failed_sources[str(s)] += 1
    top_failed_sources = failed_sources.most_common(10)

    # нерелевантные источники: если средний score по запросу высокий
    bad_score_threshold = float(args.bad_score_threshold)
    high_score_cases = []
    for r in rows:
        scores = r.get("relevance_scores") or []
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score >= bad_score_threshold:
                high_score_cases.append((avg_score, r.get("query", ""), r.get("sources") or []))
    high_score_cases.sort(key=lambda x: x[0], reverse=True)
    high_score_cases = high_score_cases[:10]

    response_times = [int(r.get("response_time_ms") or 0) for r in rows]
    answer_lengths = [int(r.get("answer_length") or 0) for r in rows]

    md: List[str] = []
    md.append("# Анализ логов (Задание 7)\n")
    md.append(f"- Лог: `{log_path}`")
    md.append(f"- Всего запросов: **{total}**")
    md.append(f"- Успешных ответов (is_successful=true): **{success}** ({fmt_pct(success_rate)})\n")

    md.append("## Разбивка по категориям\n")
    md.append("| Категория | Всего | Успешных | Success rate |")
    md.append("|---|---:|---:|---:|")
    for cat, st in sorted(by_cat.items(), key=lambda x: x[0]):
        rate = (st["success"] / st["total"]) if st["total"] else 0.0
        md.append(f"| {cat} | {st['total']} | {st['success']} | {fmt_pct(rate)} |")
    md.append("")

    md.append("## Топ-10 запросов, где бот не отвечает (is_successful=false)\n")
    if top_failed:
        for q, c in top_failed:
            md.append(f"- {q} — {c}")
    else:
        md.append("- (нет)\n")

    md.append("\n## Топ-10 источников, чаще всего встречающихся в неуспешных кейсах\n")
    if top_failed_sources:
        for s, c in top_failed_sources:
            md.append(f"- {s} — {c}")
    else:
        md.append("- (нет)\n")

    md.append("\n## Кейсы с низкой релевантностью (avg_score >= threshold)\n")
    md.append(f"- Порог: **{bad_score_threshold}** (чем меньше score, тем лучше)\n")
    if high_score_cases:
        for avg_score, q, srcs in high_score_cases:
            md.append(f"- avg_score={avg_score:.4f} — {q} — sources={', '.join(map(str, srcs[:3]))}")
    else:
        md.append("- (нет)\n")

    md.append("\n## Распределения (простая статистика)\n")
    md.append(f"- Среднее время ответа: **{mean(response_times):.0f} ms** (min={min(response_times)} / max={max(response_times)})")
    md.append(f"- Средняя длина ответа: **{mean(answer_lengths):.0f} символов** (min={min(answer_lengths)} / max={max(answer_lengths)})\n")

    out_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"OK: отчёт сохранён в {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

