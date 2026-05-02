from __future__ import annotations

import json
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.run_workspace import list_runs
from app.task_runner import TaskRunnerError

WORKTREE_LIFECYCLE_DIR = "worktree-lifecycle-plans"
RECENT_THRESHOLD_DAYS = 2


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _report_path(repo: Path) -> Path:
    return repo / "reports" / WORKTREE_LIFECYCLE_DIR / f"{_timestamp()}.json"


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


def _run_git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        raise TaskRunnerError("git não disponível no ambiente.") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"git {' '.join(args)} falhou."
        raise TaskRunnerError(detail)
    return completed.stdout.strip()


def _parse_worktree_list(repo: Path) -> list[dict[str, str]]:
    output = _run_git(repo, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line.strip():
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            if current:
                entries.append(current)
                current = {}
            current["path"] = value.strip()
        elif key in {"HEAD", "branch"}:
            current[key.lower()] = value.strip()
    if current:
        entries.append(current)
    return entries


def _runs_by_workspace(repo: Path) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for group in list_runs(repo=repo)["groups"]:
        for run in group["runs"]:
            workspace_path = str(run.get("workspace_path", "")).strip()
            if not workspace_path:
                continue
            mapping[(repo / workspace_path).resolve().as_posix()] = run
    return mapping


def _age_days(value: str) -> int | None:
    try:
        updated = datetime.fromisoformat(value)
    except ValueError:
        return None
    return max((datetime.now().astimezone() - updated).days, 0)


def run_worktree_lifecycle_plan(*, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    worktrees = _parse_worktree_list(repo)
    linked_runs = _runs_by_workspace(repo)

    entries: list[dict[str, Any]] = []
    counts = {
        "active": 0,
        "recent_validation": 0,
        "stale_candidate": 0,
        "protected": 0,
        "needs_review": 0,
    }

    for entry in worktrees:
        path = entry.get("path", "")
        branch = entry.get("branch", "")
        linked_run = linked_runs.get(path)
        classification = "needs_review"
        reasons: list[str] = []

        if Path(path).resolve().as_posix() == repo.resolve().as_posix():
            classification = "protected"
            reasons.append("repo principal protegido")
        elif linked_run is None:
            classification = "needs_review"
            reasons.append("worktree sem run associada")
        else:
            run_status = str(linked_run.get("status", "")).strip()
            updated_at = str(linked_run.get("updated_at", "")).strip()
            age_days = _age_days(updated_at)
            if run_status == "running":
                classification = "active"
                reasons.append("run ainda está em running")
            elif age_days is not None and age_days <= RECENT_THRESHOLD_DAYS:
                classification = "recent_validation"
                reasons.append("run recente preservada para validação")
            elif run_status in {"done", "failed"}:
                classification = "stale_candidate"
                reasons.append("run antiga pode entrar em limpeza futura controlada")
            else:
                classification = "needs_review"
                reasons.append("estado da run não classificado automaticamente")

        counts[classification] += 1
        entries.append(
            {
                "path": path,
                "branch": branch,
                "linked_run_id": None if linked_run is None else linked_run.get("id"),
                "linked_run_status": None if linked_run is None else linked_run.get("status"),
                "classification": classification,
                "reasons": reasons,
            }
        )

    report_path = _report_path(repo)
    payload = {
        "ok": True,
        "generated_at": _now_iso(),
        "report_path": report_path.relative_to(repo).as_posix(),
        "summary": {
            "total_worktrees": len(entries),
            **counts,
        },
        "worktrees": entries,
        "removed_worktrees": "none",
    }
    _write_json_atomic(report_path, payload)
    return payload
