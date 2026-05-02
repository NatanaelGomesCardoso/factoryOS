from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

MVP_BUILD_PLAN_VERSION = "v0"
MVP_BUILD_PLAN_REPORTS_DIR = "mvp-build-plans"


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
    return normalized[:max_length] or "mvp-build-plan"


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
    return _unique_path(repo / "reports" / MVP_BUILD_PLAN_REPORTS_DIR / f"{_timestamp()}-{_slugify(project_name)}.json")


def _route_for_category(category: str) -> str:
    normalized = str(category).strip()
    if normalized in {"docs_only", "code_small"}:
        return "capsule"
    if normalized in {"code_medium", "factory_start"}:
        return "capsule"
    return "blocked"


def _base_task(
    *,
    candidate_id: str,
    title: str,
    category: str,
    component: str,
    source: str,
    reason: str,
    derived_from: str,
) -> dict[str, Any]:
    execution_mode = _route_for_category(category)
    return {
        "task_id": f"{component}-{candidate_id}",
        "candidate_id": candidate_id,
        "title": title,
        "category": category,
        "component": component,
        "source": source,
        "derived_from_candidate_id": derived_from,
        "execution_mode_recommendation": execution_mode,
        "routing": execution_mode,
        "capsule_recommended": execution_mode == "capsule",
        "full_repo_required": False,
        "blocked": execution_mode == "blocked",
        "reason": reason,
        "status": "planned",
    }


def _tasks_from_intake(intake: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [item for item in intake.get("task_candidates", []) if isinstance(item, dict)]
    if not candidates:
        raise TaskRunnerError("report de intake não contém task_candidates.")

    tasks: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        candidate_id = str(candidate.get("candidate_id", "")).strip() or f"candidate-{index + 1}"
        title = str(candidate.get("title", "")).strip() or candidate_id
        category = str(candidate.get("category", "")).strip() or "code_small"
        source = str(candidate.get("source", "")).strip() or "project_intake"
        reason = str(candidate.get("reason", "")).strip() or "Plano derivado do intake."

        if candidate_id.endswith("-mvp-scaffold") or category == "code_small":
            tasks.append(
                _base_task(
                    candidate_id=f"{candidate_id}-backend",
                    title=f"{title} - backend scaffold",
                    category="code_small",
                    component="backend",
                    source=source,
                    reason=f"{reason} Separação backend.",
                    derived_from=candidate_id,
                )
            )
            tasks.append(
                _base_task(
                    candidate_id=f"{candidate_id}-frontend",
                    title=f"{title} - frontend scaffold",
                    category="code_small",
                    component="frontend",
                    source=source,
                    reason=f"{reason} Separação frontend.",
                    derived_from=candidate_id,
                )
            )
            continue

        component = "backend" if candidate_id.endswith(("-discovery", "-spec")) or index % 2 == 0 else "frontend"
        tasks.append(
            _base_task(
                candidate_id=candidate_id,
                title=title,
                category=category,
                component=component,
                source=source,
                reason=reason,
                derived_from=candidate_id,
            )
        )

    return tasks


def _summary(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    backend_tasks = [task for task in tasks if task.get("component") == "backend"]
    frontend_tasks = [task for task in tasks if task.get("component") == "frontend"]
    capsule_tasks = [task for task in tasks if task.get("routing") == "capsule"]
    blocked_tasks = [task for task in tasks if bool(task.get("blocked"))]
    return {
        "backend_tasks": len(backend_tasks),
        "frontend_tasks": len(frontend_tasks),
        "capsule_tasks": len(capsule_tasks),
        "blocked_tasks": len(blocked_tasks),
        "docs_only_tasks": sum(1 for task in tasks if task.get("category") == "docs_only"),
        "code_small_tasks": sum(1 for task in tasks if task.get("category") == "code_small"),
    }


def run_mvp_build_plan_create(
    *,
    project_name: str,
    from_intake: str | Path,
    dry_run: bool = True,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("mvp-build-plan-create aceita somente --dry-run nesta sprint.")

    repo = _repo_root(repo)
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")

    intake_path = _resolve_report_path(repo, from_intake)
    intake = _load_json(intake_path)
    tasks = _tasks_from_intake(intake)
    summary = _summary(tasks)
    report_path = _report_path(repo, normalized_project)
    report_relative = report_path.relative_to(repo).as_posix()
    created_at = _now_iso()

    report = {
        "ok": True,
        "mvp_build_plan_version": MVP_BUILD_PLAN_VERSION,
        "project_name": normalized_project,
        "project_kind": str(intake.get("project_kind", "")).strip(),
        "source_intake_report": intake_path.relative_to(repo).as_posix(),
        "source_intake_report_absolute": str(intake_path),
        "source_intake_project_name": str(intake.get("project_name", "")).strip(),
        "dry_run": True,
        "executed_live": False,
        "build_plan_generated": True,
        "build_plan_kind": "dry_run",
        "planned_tasks": tasks,
        "planned_task_count": len(tasks),
        "planned_components": {
            "backend": summary["backend_tasks"],
            "frontend": summary["frontend_tasks"],
        },
        "routing_summary": {
            "capsule": summary["capsule_tasks"],
            "blocked": summary["blocked_tasks"],
            "docs_only": summary["docs_only_tasks"],
            "code_small": summary["code_small_tasks"],
        },
        "generated_backend_frontend_split": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_relative,
        "created_at": created_at,
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report

