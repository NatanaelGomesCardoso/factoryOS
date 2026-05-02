from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

REPORT_RETENTION_VERSION = "v1"
REPORT_RETENTION_DIR = "report-retention"
OLD_THRESHOLD_DAYS = 7
ARCHIVE_THRESHOLD_DAYS = 30
ARCHIVE_KEEP_PER_CATEGORY = 12


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports"


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _report_path(repo: Path, mode: str) -> Path:
    return reports_root(repo) / REPORT_RETENTION_DIR / f"{_timestamp()}-{mode}.json"


def _age_days(path: Path) -> int:
    modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    return max((datetime.now().astimezone() - modified).days, 0)


def _report_category(relative_path: Path) -> str:
    if len(relative_path.parts) > 2:
        return relative_path.parts[1]
    if relative_path.suffix.lower() == ".json":
        return "root-json"
    if relative_path.suffix.lower() in {".md", ".markdown"}:
        return "root-markdown"
    if relative_path.suffix.lower() == ".txt":
        return "root-text"
    return "root-other"


def _size_class(size_bytes: int) -> str:
    if size_bytes < 8_192:
        return "small"
    if size_bytes < 65_536:
        return "medium"
    return "large"


def _age_class(age_days: int) -> str:
    if age_days <= OLD_THRESHOLD_DAYS:
        return "fresh"
    if age_days <= ARCHIVE_THRESHOLD_DAYS:
        return "warm"
    return "stale"


def _visible_reports(repo: Path) -> list[dict[str, Any]]:
    root = reports_root(repo)
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.name.startswith("."):
            continue
        relative = path.relative_to(repo)
        age_days = _age_days(path)
        size_bytes = path.stat().st_size
        entries.append(
            {
                "relative_path": relative.as_posix(),
                "category": _report_category(relative),
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
                "size_bytes": size_bytes,
                "size_class": _size_class(size_bytes),
                "age_days": age_days,
                "age_class": _age_class(age_days),
            }
        )
    return entries


def _action_for_entry(entry: dict[str, Any]) -> tuple[str, bool]:
    age_class = str(entry["age_class"])
    size_class = str(entry["size_class"])
    if age_class == "stale" and size_class == "large":
        return "delete_candidate", True
    if age_class in {"warm", "stale"}:
        return "archive", False
    return "keep", False


def _build_retention_report(*, repo: Path, mode: str) -> dict[str, Any]:
    entries = _visible_reports(repo)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(str(entry["category"]), []).append(entry)

    categories: list[dict[str, Any]] = []
    counts = {"keep": 0, "archive": 0, "delete_candidate": 0}
    human_review_required = False
    for category, items in sorted(grouped.items()):
        items.sort(key=lambda item: (item["modified_at"], item["relative_path"]), reverse=True)
        category_actions: list[dict[str, Any]] = []
        for item in items:
            action, item_review = _action_for_entry(item)
            counts[action] += 1
            human_review_required = human_review_required or item_review
            category_actions.append(
                {
                    "relative_path": item["relative_path"],
                    "action": action,
                    "age_class": item["age_class"],
                    "size_class": item["size_class"],
                    "age_days": item["age_days"],
                    "size_bytes": item["size_bytes"],
                    "human_review_required": item_review,
                }
            )
        archive_candidates = [item for item in items if _action_for_entry(item)[0] == "archive"]
        delete_candidates = [item for item in items if _action_for_entry(item)[0] == "delete_candidate"]
        categories.append(
            {
                "category": category,
                "total_count": len(items),
                "archive_candidate_count": len(archive_candidates),
                "delete_candidate_count": len(delete_candidates),
                "newest_report": items[0]["relative_path"] if items else "",
                "oldest_report": items[-1]["relative_path"] if items else "",
                "items": category_actions[:20],
            }
        )

    report_path = _report_path(repo, mode)
    payload = {
        "ok": True,
        "report_retention_version": REPORT_RETENTION_VERSION,
        "mode": mode,
        "generated_at": _now_iso(),
        "report_path": report_path.relative_to(repo).as_posix(),
        "summary": {
            "total_reports": len(entries),
            "category_count": len(categories),
            "keep_count": counts["keep"],
            "archive_count": counts["archive"],
            "delete_candidate_count": counts["delete_candidate"],
        },
        "categories": categories,
        "safe_to_apply": False,
        "human_review_required": human_review_required or counts["delete_candidate"] > 0,
        "deleted_files": [],
        "moved_files": [],
        "reports_sample": entries[:20],
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
    }
    _write_json_atomic(report_path, payload)
    return payload


def run_report_retention_audit(*, repo: Path | None = None) -> dict[str, Any]:
    return _build_retention_report(repo=repo or repo_root(), mode="audit")


def run_report_retention_cleanup_plan(*, repo: Path | None = None) -> dict[str, Any]:
    return _build_retention_report(repo=repo or repo_root(), mode="cleanup-plan")


def run_report_retention_plan(*, repo: Path | None = None) -> dict[str, Any]:
    return run_report_retention_cleanup_plan(repo=repo)
