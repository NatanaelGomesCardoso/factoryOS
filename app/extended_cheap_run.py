from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

EXTENDED_RUN_VERSION = "v0"
DEFAULT_MAX_MINUTES = 60
MAX_MINUTES_LIMIT = 120
DEFAULT_MAX_TASKS = 10
MAX_TASKS_LIMIT = 30
ALLOWED_CATEGORIES = ["docs_only", "code_small", "code_medium"]
BLOCKED_CATEGORIES = ["security_review", "heavy_review", "live_canary"]
STOP_CONDITIONS = [
    "task_failed",
    "budget_exceeded",
    "timeout",
    "disallowed_file",
    "human_review_required",
    "critical_output_log_budget_blocked",
    "secret_suspected",
    "push_deploy_paid_api_or_secrets_detected",
    "change_outside_allowlist",
]
BUDGET_CAPS = {
    "tokens_per_task_warning": 40_000,
    "tokens_per_task_block": 70_000,
    "total_tokens_warning": 300_000,
    "total_tokens_block": 500_000,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_text_atomic(path: Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _validate_max_minutes(max_minutes: int | None) -> int:
    value = DEFAULT_MAX_MINUTES if max_minutes is None else int(max_minutes)
    if value < 1 or value > MAX_MINUTES_LIMIT:
        raise TaskRunnerError("max-minutes deve estar entre 1 e 120.")
    return value


def _validate_max_tasks(max_tasks: int | None) -> int:
    value = DEFAULT_MAX_TASKS if max_tasks is None else int(max_tasks)
    if value < 1 or value > MAX_TASKS_LIMIT:
        raise TaskRunnerError("max-tasks deve estar entre 1 e 30.")
    return value


def _report_path(repo: Path, kind: str) -> Path:
    return repo / "reports" / "extended-cheap-runs" / f"{_timestamp()}-{kind}-{secrets.token_hex(3)}.json"


def _base_payload(*, repo: Path, dry_run: bool, rehearsal: bool, max_minutes: int, max_tasks: int) -> dict[str, Any]:
    return {
        "ok": True,
        "extended_cheap_run_version": EXTENDED_RUN_VERSION,
        "dry_run": dry_run,
        "rehearsal": rehearsal,
        "max_minutes": max_minutes,
        "max_tasks": max_tasks,
        "allowed_categories": ALLOWED_CATEGORIES,
        "blocked_categories": BLOCKED_CATEGORIES,
        "capsule_first": True,
        "task_by_task": True,
        "stop_conditions": STOP_CONDITIONS,
        "budget_caps": BUDGET_CAPS,
        "human_review_required": True,
        "live_execution_allowed": False,
        "requires_new_gate_for_live": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }


def _write_report(repo: Path, payload: dict[str, Any], *, kind: str) -> dict[str, Any]:
    report_path = _report_path(repo, kind)
    payload["report_path"] = report_path.relative_to(repo).as_posix()
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "Sprint 080.M.2 extended cheap task run policy 2h V0 proof",
        f"report_path={report['report_path']}",
        f"dry_run={str(report['dry_run']).lower()}",
        f"rehearsal={str(report['rehearsal']).lower()}",
        f"max_minutes={report['max_minutes']}",
        f"max_tasks={report['max_tasks']}",
        "live_execution_allowed=false",
        "requires_new_gate_for_live=true",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / "reports" / "extended-cheap-task-run-policy-2h-v0-proof.txt", "\n".join(lines) + "\n")


def run_extended_cheap_run_plan(*, max_minutes: int | None, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factory-extended-cheap-run-plan V0 exige --dry-run.")
    repo = repo or repo_root()
    minutes = _validate_max_minutes(max_minutes)
    payload = _base_payload(repo=repo, dry_run=True, rehearsal=False, max_minutes=minutes, max_tasks=DEFAULT_MAX_TASKS)
    payload["plan"] = {
        "mode": "plan_only",
        "live_execution": "blocked_until_new_gate",
        "category_policy": "somente docs_only/code_small/code_medium de baixo risco, uma tarefa por vez",
    }
    return _write_report(repo, payload, kind="plan")


def run_extended_cheap_run_rehearsal(*, max_minutes: int | None, max_tasks: int | None, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factory-extended-cheap-run-rehearsal V0 exige --dry-run.")
    repo = repo or repo_root()
    minutes = _validate_max_minutes(max_minutes)
    tasks = _validate_max_tasks(max_tasks)
    payload = _base_payload(repo=repo, dry_run=True, rehearsal=True, max_minutes=minutes, max_tasks=tasks)
    payload["rehearsal_steps"] = [
        {"step": index + 1, "category": ALLOWED_CATEGORIES[index % len(ALLOWED_CATEGORIES)], "execution": "blocked_dry_run"}
        for index in range(tasks)
    ]
    payload["blocked_category_checks"] = {category: "blocked_requires_separate_gate" for category in BLOCKED_CATEGORIES}
    return _write_report(repo, payload, kind="rehearsal")


def run_extended_cheap_run_gate(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factory-extended-cheap-run-gate V0 exige --dry-run.")
    repo = repo or repo_root()
    payload = _base_payload(repo=repo, dry_run=True, rehearsal=False, max_minutes=DEFAULT_MAX_MINUTES, max_tasks=DEFAULT_MAX_TASKS)
    payload["gate_decision"] = "live_blocked_requires_new_gate"
    payload["blocked_category_checks"] = {category: "blocked" for category in BLOCKED_CATEGORIES}
    return _write_report(repo, payload, kind="gate")
