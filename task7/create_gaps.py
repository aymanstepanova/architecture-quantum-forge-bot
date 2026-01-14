"""
Задание 7 — создание искусственных пробелов в базе знаний.

Сценарий:
- выбираем 2–3 "ключевые" сущности (файлы в knowledge_base/)
- убираем их из базы знаний (по умолчанию: безопасно ПЕРЕМЕЩАЕМ в task7/)
- пересобираем векторный индекс в отдельную директорию task7/vector_index_gapped/
- сохраняем метаданные операции в task7/removed_entities.json

Важно:
- По умолчанию скрипт работает в режиме dry-run (ничего не меняет).
- Реальные изменения выполняются только с флагом --apply.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
KB_DIR = REPO_ROOT / "knowledge_base"
VECTOR_INDEX_DIR = REPO_ROOT / "vector_index"

TASK7_DIR = REPO_ROOT / "task7"
TASK7_STATE_FILE = TASK7_DIR / "removed_entities.json"
TASK7_REMOVED_DIR = TASK7_DIR / "removed_entities"
TASK7_GAPPED_INDEX_DIR = TASK7_DIR / "vector_index_gapped"
TASK7_BACKUPS_DIR = TASK7_DIR / "backups"


# Выбираем сущности, которые минимально "размазаны" по другим документам,
# чтобы после удаления файла тема действительно пропала из тестовой базы.
DEFAULT_REMOVALS = [
    "Matatabi.txt",  # Kitekat
    "Five_Great_Shinobi_Countries.txt",  # Five Great Operative Countries
    "Genin.txt",  # Initiate
]


@dataclass(frozen=True)
class RemovedEntity:
    filename: str
    src_path: str
    dst_path: str


@dataclass(frozen=True)
class GapRun:
    run_id: str
    timestamp_utc: str
    removed_entities: List[RemovedEntity]
    gapped_index_dir: str
    original_index_backup_dir: Optional[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _load_state() -> List[dict]:
    if not TASK7_STATE_FILE.exists():
        return []
    return json.loads(TASK7_STATE_FILE.read_text(encoding="utf-8"))


def _append_state(run: GapRun) -> None:
    state = _load_state()
    state.append(
        {
            "run_id": run.run_id,
            "timestamp_utc": run.timestamp_utc,
            "removed_entities": [asdict(x) for x in run.removed_entities],
            "gapped_index_dir": run.gapped_index_dir,
            "original_index_backup_dir": run.original_index_backup_dir,
        }
    )
    TASK7_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _backup_original_index(dry_run: bool) -> Optional[Path]:
    """
    Создаёт резервную копию текущего vector_index в task7/backups/ с run_id.
    Возвращает путь к бэкапу или None, если исходного индекса нет.
    """
    if not VECTOR_INDEX_DIR.exists():
        return None

    _safe_mkdir(TASK7_BACKUPS_DIR)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = TASK7_BACKUPS_DIR / f"vector_index_original_{run_id}"

    if dry_run:
        return backup_dir

    # shutil.copytree требует, чтобы директории-назначения не было
    shutil.copytree(VECTOR_INDEX_DIR, backup_dir)
    return backup_dir


def _move_files(filenames: List[str], dry_run: bool) -> List[RemovedEntity]:
    missing: List[str] = []
    removed_entities: List[RemovedEntity] = []

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dst_dir = TASK7_REMOVED_DIR / run_id

    for name in filenames:
        src = KB_DIR / name
        if not src.exists():
            missing.append(name)
            continue
        dst = dst_dir / name
        removed_entities.append(
            RemovedEntity(
                filename=name,
                src_path=str(src),
                dst_path=str(dst),
            )
        )

    if missing:
        raise FileNotFoundError(f"Не найдены файлы в knowledge_base/: {missing}")

    if dry_run:
        return removed_entities

    _safe_mkdir(dst_dir)
    for ent in removed_entities:
        src = Path(ent.src_path)
        dst = Path(ent.dst_path)
        shutil.move(str(src), str(dst))

    return removed_entities


def _restore_last_run(dry_run: bool) -> None:
    state = _load_state()
    if not state:
        raise RuntimeError("Нет записей в task7/removed_entities.json — нечего восстанавливать.")

    last = state[-1]
    entities = last.get("removed_entities", [])
    if not entities:
        raise RuntimeError("Последний запуск не содержит removed_entities — нечего восстанавливать.")

    # Восстанавливаем файлы обратно в knowledge_base/
    for ent in entities:
        src = Path(ent["dst_path"])
        dst = KB_DIR / Path(ent["filename"]).name
        if dry_run:
            continue
        if not src.exists():
            raise FileNotFoundError(f"Ожидаемый удалённый файл не найден: {src}")
        shutil.move(str(src), str(dst))


def _rebuild_gapped_index(dry_run: bool) -> None:
    """
    Пересобирает индекс из текущего knowledge_base/ в task7/vector_index_gapped/.
    """
    if dry_run:
        return

    # Чистим директорию индекса, чтобы Chroma не смешивала коллекции
    if TASK7_GAPPED_INDEX_DIR.exists():
        shutil.rmtree(TASK7_GAPPED_INDEX_DIR)
    _safe_mkdir(TASK7_GAPPED_INDEX_DIR)

    # Импортируем build_index из корня репозитория
    sys.path.insert(0, str(REPO_ROOT))
    import build_index  # noqa: E402

    documents = build_index.load_documents(build_index.KNOWLEDGE_BASE_DIR)
    if not documents:
        raise RuntimeError("После удаления сущностей документов для индексации не осталось.")
    chunks = build_index.split_documents(documents)
    build_index.create_vector_index(chunks, TASK7_GAPPED_INDEX_DIR)


def main() -> int:
    parser = argparse.ArgumentParser(description="Создание пробелов в базе знаний (задание 7).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Применить изменения: переместить файлы и пересобрать индекс. Без флага работает dry-run.",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Восстановить файлы последнего запуска обратно в knowledge_base/. (dry-run без --apply)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=DEFAULT_REMOVALS,
        help="Список файлов из knowledge_base/, которые нужно убрать (по умолчанию 3 сущности).",
    )

    args = parser.parse_args()
    dry_run = not args.apply

    _safe_mkdir(TASK7_DIR)

    if args.restore:
        _restore_last_run(dry_run=dry_run)
        print("OK: восстановление выполнено." if not dry_run else "DRY-RUN: восстановление (без изменений).")
        return 0

    # 1) Backup оригинального индекса
    backup_dir = _backup_original_index(dry_run=dry_run)

    # 2) Убираем сущности из knowledge_base/
    removed_entities = _move_files(args.files, dry_run=dry_run)

    # 3) Пересобираем индекс в отдельную директорию task7/vector_index_gapped/
    _rebuild_gapped_index(dry_run=dry_run)

    run = GapRun(
        run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        timestamp_utc=_utc_now_iso(),
        removed_entities=removed_entities,
        gapped_index_dir=str(TASK7_GAPPED_INDEX_DIR),
        original_index_backup_dir=str(backup_dir) if backup_dir else None,
    )

    if not dry_run:
        _append_state(run)

    print("\n" + "=" * 80)
    print("ЗАДАНИЕ 7: СОЗДАНИЕ ПРОБЕЛОВ")
    print("=" * 80)
    print(f"Режим: {'DRY-RUN' if dry_run else 'APPLY'}")
    print(f"Удалено сущностей: {len(removed_entities)}")
    for e in removed_entities:
        print(f"- {e.filename}: {e.src_path} -> {e.dst_path}")
    print(f"Гэп-индекс: {TASK7_GAPPED_INDEX_DIR}")
    print(f"Бэкап исходного индекса: {backup_dir if backup_dir else 'нет (vector_index отсутствует)'}")
    if dry_run:
        print("\nЧтобы применить изменения, запустите: python task7/create_gaps.py --apply")
    else:
        print(f"\nСостояние сохранено в: {TASK7_STATE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

