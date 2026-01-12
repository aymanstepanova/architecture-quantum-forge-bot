"""
Последовательный пайплайн (как run_task2.py), без инкрементальности:
1) create_terms_map.py (если нет terms_map.json)
2) download_naruto_pages.py
3) extract_text_from_html.py
4) apply_replacements.py
5) build_index.py (полная пересборка индекса) — ТОЛЬКО если изменилась knowledge_base/*.txt
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"
VECTOR_DB_DIR = ROOT / "vector_index"
STATE_DIR = ROOT / "state"
KB_STATE_FILE = STATE_DIR / "kb_hashes.json"
LOGS_DIR = ROOT / "logs"

def _base_env() -> dict:
    env = os.environ.copy()
    # Важно для Windows: скрипты печатают символы ✓/⚠/✗/⏳, cp1251 на этом падает
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_script(script_filename: str) -> Tuple[bool, str]:
    """
    Запускает скрипт из корня репозитория максимально близко к "python <script>".
    """
    try:
        subprocess.run(
            [sys.executable, str(ROOT / script_filename)],
            check=True,
            env=_base_env(),
        )
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, str(e)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log_filename() -> str:
    return f"update_index_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M%SZ')}.json"


def _dir_stats(path: Path) -> Dict[str, Any]:
    """
    Простая статистика по директории (для "размера итогового индекса").
    """
    if not path.exists():
        return {"exists": False, "files": 0, "bytes": 0}
    total_bytes = 0
    total_files = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total_files += 1
                try:
                    total_bytes += p.stat().st_size
                except Exception:
                    pass
    except Exception:
        # best-effort
        pass
    return {"exists": True, "files": total_files, "bytes": total_bytes}


def _write_run_log(log_obj: Dict[str, Any]) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOGS_DIR / _log_filename()
    out_path.write_text(json.dumps(log_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _compute_kb_hashes() -> Dict[str, str]:
    """
    Считаем хэши для knowledge_base/*.txt (это и есть "сканирование источника" на изменения).
    """
    if not KB_DIR.exists():
        return {}
    out: Dict[str, str] = {}
    for p in sorted(KB_DIR.glob("*.txt")):
        if not p.is_file():
            continue
        content = p.read_text(encoding="utf-8", errors="ignore")
        out[p.name] = _sha256_text(content)
    return out


def _read_json(path: Path, default: Dict) -> Dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def backup_and_clear_vector_index() -> None:
    """
    Перед полной пересборкой индекса делаем best-effort бэкап и чистим vector_index/,
    чтобы не получить дубли/странные состояния.
    """
    if not VECTOR_DB_DIR.exists():
        return

    backup_root = ROOT / "vector_index_backup"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    backup_dir = backup_root / f"before_update_index_{ts}"
    try:
        backup_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(VECTOR_DB_DIR, backup_dir)
    except Exception:
        # бэкап best-effort
        pass

    shutil.rmtree(VECTOR_DB_DIR, ignore_errors=True)

def main() -> int:
    started_at = _utc_now_iso()
    errors: List[Dict[str, Any]] = []
    rebuilt_index = False
    changed: List[str] = []
    removed: List[str] = []

    # Шаг 0: terms_map.json (только если отсутствует)
    terms_map_path = ROOT / "terms_map.json"
    if not terms_map_path.exists():
        create_terms_script_name = "create_terms_map.py"
        ok, err = run_script(create_terms_script_name)
        if not ok:
            errors.append({"step": create_terms_script_name, "error": err})
            log_path = _write_run_log(
                {
                    "timestamp_start": started_at,
                    "timestamp_end": _utc_now_iso(),
                    "status": "failed",
                    "rebuilt_index": False,
                    "changed_files": [],
                    "removed_files": [],
                    "kb_txt_files": len(_compute_kb_hashes()),
                    "index_stats": _dir_stats(VECTOR_DB_DIR),
                    "errors": errors,
                }
            )
            print(f"[ERROR] {create_terms_script_name} завершился с ошибкой: {err}")
            print(f"[LOG] {log_path}")
            return 0

    download_script_name = "download_naruto_pages.py"
    ok, err = run_script(download_script_name)
    if not ok:
        errors.append({"step": download_script_name, "error": err})
        log_path = _write_run_log(
            {
                "timestamp_start": started_at,
                "timestamp_end": _utc_now_iso(),
                "status": "failed",
                "rebuilt_index": False,
                "changed_files": [],
                "removed_files": [],
                "kb_txt_files": len(_compute_kb_hashes()),
                "index_stats": _dir_stats(VECTOR_DB_DIR),
                "errors": errors,
            }
        )
        print(f"[ERROR] {download_script_name} завершился с ошибкой: {err}")
        print(f"[LOG] {log_path}")
        # Не падаем, чтобы docker/cron не уходил в бесконечные рестарты
        return 0

    extract_script_name = "extract_text_from_html.py"
    ok, err = run_script(extract_script_name)
    if not ok:
        errors.append({"step": extract_script_name, "error": err})
        log_path = _write_run_log(
            {
                "timestamp_start": started_at,
                "timestamp_end": _utc_now_iso(),
                "status": "failed",
                "rebuilt_index": False,
                "changed_files": [],
                "removed_files": [],
                "kb_txt_files": len(_compute_kb_hashes()),
                "index_stats": _dir_stats(VECTOR_DB_DIR),
                "errors": errors,
            }
        )
        print(f"[ERROR] {extract_script_name} завершился с ошибкой: {err}")
        print(f"[LOG] {log_path}")
        return 0

    replacements_script_name = "apply_replacements.py"
    ok, err = run_script(replacements_script_name)
    if not ok:
        errors.append({"step": replacements_script_name, "error": err})
        log_path = _write_run_log(
            {
                "timestamp_start": started_at,
                "timestamp_end": _utc_now_iso(),
                "status": "failed",
                "rebuilt_index": False,
                "changed_files": [],
                "removed_files": [],
                "kb_txt_files": len(_compute_kb_hashes()),
                "index_stats": _dir_stats(VECTOR_DB_DIR),
                "errors": errors,
            }
        )
        print(f"[ERROR] {replacements_script_name} завершился с ошибкой: {err}")
        print(f"[LOG] {log_path}")
        return 0

    # Шаг 5: пересборка индекса — только если изменились knowledge_base/*.txt
    current_hashes = _compute_kb_hashes()
    prev_state = _read_json(KB_STATE_FILE, default={"version": 1, "hashes": {}, "updated_at": None})
    prev_hashes = prev_state.get("hashes", {}) if isinstance(prev_state, dict) else {}

    changed = sorted([fn for fn, h in current_hashes.items() if prev_hashes.get(fn) != h])
    removed = sorted([fn for fn in prev_hashes.keys() if fn not in current_hashes])

    print("\n" + "=" * 80)
    print("ПРОВЕРКА ИЗМЕНЕНИЙ В knowledge_base/")
    print("=" * 80)
    print(f"Файлов .txt сейчас: {len(current_hashes)}")
    print(f"Новых/изменённых: {len(changed)}")
    print(f"Удалённых: {len(removed)}")

    if not changed and not removed:
        print("Изменений нет — индекс не пересобираю.")
        log_path = _write_run_log(
            {
                "timestamp_start": started_at,
                "timestamp_end": _utc_now_iso(),
                "status": "success",
                "rebuilt_index": False,
                "changed_files": [],
                "removed_files": [],
                "kb_txt_files": len(current_hashes),
                "index_stats": _dir_stats(VECTOR_DB_DIR),
                "errors": [],
            }
        )
        print(f"[LOG] {log_path}")
        return 0

    # rebuild
    backup_and_clear_vector_index()
    build_index_script_name = "build_index.py"
    ok, err = run_script(build_index_script_name)
    if not ok:
        print(f"[ERROR] {build_index_script_name} завершился с ошибкой: {err}")
        errors.append({"step": build_index_script_name, "error": err})
        log_path = _write_run_log(
            {
                "timestamp_start": started_at,
                "timestamp_end": _utc_now_iso(),
                "status": "failed",
                "rebuilt_index": False,
                "changed_files": changed,
                "removed_files": removed,
                "kb_txt_files": len(current_hashes),
                "index_stats": _dir_stats(VECTOR_DB_DIR),
                "errors": errors,
            }
        )
        print(f"[LOG] {log_path}")
        return 0
    rebuilt_index = True

    # обновляем state (после успешной пересборки)
    _write_json(
        KB_STATE_FILE,
        {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "hashes": current_hashes,
            "changed_files": changed,
            "removed_files": removed,
        },
    )
    finished_at = _utc_now_iso()
    log_obj = {
        "timestamp_start": started_at,
        "timestamp_end": finished_at,
        "status": "success" if not errors else "success_with_errors",
        "rebuilt_index": rebuilt_index,
        "changed_files": changed,
        "removed_files": removed,
        "kb_txt_files": len(current_hashes),
        "index_stats": _dir_stats(VECTOR_DB_DIR),
        "errors": errors,
        # удобный "человекочитаемый" пример строки
        "message": f"index updated at {finished_at}, {len(changed)} files changed, {len(removed)} removed, {len(errors)} errors",
    }
    log_path = _write_run_log(log_obj)
    print(f"[LOG] {log_path}")
    print(log_obj["message"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

