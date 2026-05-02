from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.report_retention import run_report_retention_plan
from app.state_hygiene import factory_state_audit, factory_state_plan
from app.task_runner import TaskRunnerError
from app.worktree_lifecycle import run_worktree_lifecycle_plan

FACTORY_MAINTENANCE_DIR = "factory-maintenance-plans"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _report_path(repo: Path) -> Path:
    return repo / "reports" / FACTORY_MAINTENANCE_DIR / f"{_timestamp()}.json"


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


def run_factory_maintenance_plan(*, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    retention = run_report_retention_plan(repo=repo)
    worktrees = run_worktree_lifecycle_plan(repo=repo)
    state_audit = factory_state_audit(repo=repo)
    state_plan = factory_state_plan(repo=repo)

    report_path = _report_path(repo)
    payload = {
        "ok": True,
        "generated_at": _now_iso(),
        "report_path": report_path.relative_to(repo).as_posix(),
        "report_retention_plan_report": retention.get("report_path"),
        "worktree_lifecycle_plan_report": worktrees.get("report_path"),
        "factory_state_audit_report": state_audit.get("report_path"),
        "factory_state_plan_report": state_plan.get("report_path"),
        "summary": {
            "reports_total": retention.get("summary", {}).get("total_reports", 0),
            "archive_candidate_count": retention.get("summary", {}).get("archive_candidate_count", 0),
            "worktrees_total": worktrees.get("summary", {}).get("total_worktrees", 0),
            "stale_candidate_worktrees": worktrees.get("summary", {}).get("stale_candidate", 0),
            "running_tasks_count": state_audit.get("stats", {}).get("running_tasks_count", 0),
            "running_runs_count": state_audit.get("stats", {}).get("running_runs_count", 0),
        },
        "deleted_files": "none",
        "removed_worktrees": "none",
    }
    _write_json_atomic(report_path, payload)
    return payload
