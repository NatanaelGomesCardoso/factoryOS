from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

MVP_APPLY_PLAN_VERSION = "v0"
MVP_APPLY_PLAN_REPORTS_DIR = "mvp-apply-plans"


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, *, max_length: int = 64) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:max_length] or "mvp-apply-plan"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return path.with_name(f"{path.name}-{secrets.token_hex(3)}")


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _resolve_report_path(repo: Path, report_path: str | Path) -> Path:
    candidate = Path(report_path)
    if not candidate.is_absolute():
        candidate = (repo / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise TaskRunnerError(f"report inexistente: {candidate}")
    if not candidate.is_file() or candidate.is_symlink():
        raise TaskRunnerError(f"report inválido: {candidate}")
    try:
        candidate.relative_to(repo.resolve())
    except ValueError as exc:
        raise TaskRunnerError("report precisa ficar dentro do repo.") from exc
    return candidate


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.name}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")
    return payload


def _report_path(repo: Path, project_name: str) -> Path:
    return _unique_path(repo / "reports" / MVP_APPLY_PLAN_REPORTS_DIR / f"{_timestamp()}-{_slugify(project_name)}.json")


def run_mvp_apply_plan_create(
    *,
    canary_report: str | Path,
    dry_run: bool = True,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("mvp-apply-plan-create aceita somente --dry-run nesta sprint.")

    repo = _repo_root(repo)
    canary_path = _resolve_report_path(repo, canary_report)
    canary = _load_json(canary_path)
    project_name = str(canary.get("project_name", "")).strip()
    if not project_name:
        raise TaskRunnerError("canary sem project_name.")

    export_plan_ref = str(canary.get("export_plan_report_path", "")).strip()
    if not export_plan_ref:
        raise TaskRunnerError("canary sem export_plan_report_path.")
    export_plan_path = _resolve_report_path(repo, export_plan_ref)
    export_plan = _load_json(export_plan_path)

    candidate_files = [item for item in export_plan.get("candidate_files", []) if isinstance(item, dict)]
    would_apply_files = [str(item.get("path", "")).strip() for item in candidate_files if str(item.get("path", "")).strip()]
    allowed_files = [str(item).strip() for item in export_plan.get("allowed_files", []) if str(item).strip()]
    disallowed_files = [str(item).strip() for item in export_plan.get("disallowed_files", []) if str(item).strip()]
    blocked = bool(disallowed_files or not would_apply_files)
    safe_to_apply_later = bool(not disallowed_files and all(path in set(allowed_files) for path in would_apply_files))

    report_path = _report_path(repo, project_name)
    created_at = _now_iso()
    report = {
        "ok": True,
        "mvp_apply_plan_version": MVP_APPLY_PLAN_VERSION,
        "project_name": project_name,
        "dry_run": True,
        "human_review_required": True,
        "safe_to_apply": False,
        "safe_to_apply_later": safe_to_apply_later,
        "blocked": blocked,
        "review_state": "pending_human_review",
        "canary_report_path": canary_path.relative_to(repo).as_posix(),
        "canary_report_absolute": str(canary_path),
        "build_plan_report_path": str(canary.get("build_plan_report", "")),
        "export_plan_report_path": export_plan_path.relative_to(repo).as_posix(),
        "export_plan_report_absolute": str(export_plan_path),
        "diff_report_path": str(canary.get("diff_report_path", "")),
        "would_apply_files": would_apply_files,
        "would_apply_count": len(would_apply_files),
        "allowed_files": allowed_files,
        "disallowed_files": disallowed_files,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "executed_live": False,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": created_at,
        "finished_at": _now_iso(),
        "reasons": [
            "human_review_required=true",
            "safe_to_apply=false",
        ] + (["disallowed_files presentes"] if disallowed_files else []),
    }
    _write_json_atomic(report_path, report)
    return report

