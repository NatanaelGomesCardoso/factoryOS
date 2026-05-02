from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_context_router import context_pack_for_run
from app.codex_profile import codex_plan_for_run
from app.routing_contracts import routing_contract_validation_payload
from app.run_workspace import list_runs, run_workspace_readiness, run_workspace_sync_plan, show_run
from app.state_hygiene import factory_state_audit, factory_state_plan
from app.task_runner import TaskRunnerError, show_task

LONG_RUN_PLAN_VERSION = "v0"
LONG_RUN_REPORTS_DIR = "factory-long-run-plans"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TARGET_MINUTES_MIN = 15
TARGET_MINUTES_MAX = 60
MAX_STEPS_MIN = 1
MAX_STEPS_MAX = 6


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / LONG_RUN_REPORTS_DIR


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


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str):
        raise TaskRunnerError("id da run inválido.")
    normalized = run_id.strip()
    if not normalized:
        raise TaskRunnerError("id da run vazio.")
    if "/" in normalized or "\\" in normalized:
        raise TaskRunnerError("path traversal não permitido no id da run.")
    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise TaskRunnerError("id da run contém caracteres inválidos.")
    return normalized


def _validate_target_minutes(target_minutes: int) -> int:
    if target_minutes < TARGET_MINUTES_MIN or target_minutes > TARGET_MINUTES_MAX:
        raise TaskRunnerError(
            f"target_minutes precisa ficar entre {TARGET_MINUTES_MIN} e {TARGET_MINUTES_MAX}."
        )
    return target_minutes


def _validate_max_steps(max_steps: int) -> int:
    if max_steps < MAX_STEPS_MIN or max_steps > MAX_STEPS_MAX:
        raise TaskRunnerError(f"max_steps precisa ficar entre {MAX_STEPS_MIN} e {MAX_STEPS_MAX}.")
    return max_steps


def _running_runs(repo: Path) -> list[dict[str, Any]]:
    groups = list_runs(repo=repo)["groups"]
    running_group = next((group for group in groups if group["status"] == "running"), {"runs": []})
    return [run for run in running_group.get("runs", []) if isinstance(run, dict)]


def _eligible_run_snapshots(repo: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for run in _running_runs(repo):
        run_id = str(run.get("id", "")).strip()
        readiness = run_workspace_readiness(run_id, repo=repo)["workspace"]
        sync_plan = run_workspace_sync_plan(run_id, repo=repo)["plan"]
        candidates.append(
            {
                "run_id": run_id,
                "task_id": str(run.get("task_id", "")).strip(),
                "status": str(run.get("status", "")).strip(),
                "readiness_status": str(readiness.get("status", "")).strip(),
                "readiness_reasons": [str(item) for item in readiness.get("reasons", []) if str(item).strip()],
                "sync_plan_status": str(sync_plan.get("status", "")).strip(),
                "sync_plan_reasons": [str(item) for item in sync_plan.get("reasons", []) if str(item).strip()],
            }
        )
    return candidates


def _resolve_run_selection(run_id: str | None, *, repo: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    candidates = _eligible_run_snapshots(repo)
    eligible = [
        item for item in candidates
        if item["status"] == "running"
        and item["readiness_status"] == "ready"
        and item["sync_plan_status"] in {"already_current", "fast_forward_available"}
    ]

    if run_id is not None:
        normalized_run_id = _validate_run_id(run_id)
        run = show_run(normalized_run_id, repo=repo)["run"]
        if str(run.get("status", "")).strip() != "running":
            raise TaskRunnerError("run precisa estar em running para planejar long run.")
        return run, {
            "selection_status": "explicit",
            "eligible_runs_count": len(eligible),
            "candidates": candidates[:3],
        }

    if not eligible:
        return None, {
            "selection_status": "blocked",
            "eligible_runs_count": 0,
            "candidates": candidates[:3],
            "reason": "nenhuma run elegível disponível para auto seleção.",
        }
    if len(eligible) > 1:
        return None, {
            "selection_status": "needs_review",
            "eligible_runs_count": len(eligible),
            "candidates": candidates[:3],
            "reason": "mais de uma run elegível encontrada; passe --run-id explicitamente.",
        }

    selected = show_run(str(eligible[0]["run_id"]), repo=repo)["run"]
    return selected, {
        "selection_status": "auto_selected",
        "eligible_runs_count": 1,
        "candidates": candidates[:3],
    }


def _report_path(repo: Path, run_id: str) -> Path:
    return _reports_root(repo) / f"{_timestamp()}-{run_id}.json"


def _step_gates(
    *,
    readiness_status: str,
    sync_plan_status: str,
    budget_status: str,
    context_status: str,
) -> list[str]:
    gates = ["manual_review_required", "live_blocked", "dry_run_plan_only"]
    gates.append(f"readiness:{readiness_status or 'unknown'}")
    gates.append(f"sync_plan:{sync_plan_status or 'unknown'}")
    gates.append(f"budget:{budget_status or 'unknown'}")
    gates.append(f"context:{context_status or 'unknown'}")
    return gates


def run_factory_long_run_plan(
    run_id: str | None = None,
    *,
    target_minutes: int = 30,
    max_steps: int = 6,
    live: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    if live:
        raise TaskRunnerError("live execution is out of scope for Long Run Dry-Run Planner V0.")

    repo = repo or repo_root()
    validated_target_minutes = _validate_target_minutes(target_minutes)
    validated_max_steps = _validate_max_steps(max_steps)

    run, selection = _resolve_run_selection(run_id, repo=repo)
    if run is None:
        return {
            "ok": False,
            "plan_version": LONG_RUN_PLAN_VERSION,
            "planner_status": "dry_run_plan_only",
            "required_manual_review": True,
            "allowed_to_execute_live": False,
            "target_minutes": validated_target_minutes,
            "max_steps": validated_max_steps,
            "selection_status": selection["selection_status"],
            "eligible_runs_count": selection["eligible_runs_count"],
            "candidates": selection["candidates"],
            "blockers": [selection["reason"]],
            "risks": ["run selection unresolved"],
            "gates": ["manual_review_required", "live_blocked"],
        }

    normalized_run_id = str(run["id"])
    task = show_task(str(run["task_id"]), repo=repo)["task"]
    routing_contract = routing_contract_validation_payload(task=task, run=run)
    codex_plan = codex_plan_for_run(normalized_run_id, max_steps=validated_max_steps, repo=repo)
    context_pack = context_pack_for_run(normalized_run_id, repo=repo)
    readiness = run_workspace_readiness(normalized_run_id, repo=repo)["workspace"]
    sync_plan = run_workspace_sync_plan(normalized_run_id, repo=repo)["plan"]
    audit_result = factory_state_audit(repo=repo)
    plan_result = factory_state_plan(repo=repo)

    budget_status = str(codex_plan.get("budget_status", "blocked")).strip() or "blocked"
    context_status = str(context_pack.get("context_status", "blocked")).strip() or "blocked"
    readiness_status = str(readiness.get("status", "")).strip()
    sync_plan_status = str(sync_plan.get("status", "")).strip()

    blockers: list[str] = []
    risks: list[str] = []
    warnings: list[str] = []

    if not bool(routing_contract.get("valid", False)):
        blockers.extend([str(item) for item in routing_contract.get("reasons", []) if str(item).strip()])
    if budget_status != "ok":
        blockers.extend([str(item) for item in codex_plan.get("reasons", []) if str(item).strip()])
    if context_status != "ok":
        blockers.extend([str(item) for item in context_pack.get("reasons", []) if str(item).strip()])
    if readiness_status != "ready":
        blockers.extend([str(item) for item in readiness.get("reasons", []) if str(item).strip()])
    if sync_plan_status not in {"already_current", "fast_forward_available"}:
        blockers.extend([str(item) for item in sync_plan.get("reasons", []) if str(item).strip()])

    warnings.extend([str(item) for item in routing_contract.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in codex_plan.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in context_pack.get("warnings", []) if str(item).strip()])

    context_chars = int(context_pack.get("context_chars", 0))
    context_limit = int(context_pack.get("context_limit_chars", 0) or 0)
    if context_limit and context_chars >= int(context_limit * 0.85):
        risks.append("contexto perto do limite configurado.")
    if sync_plan_status == "fast_forward_available":
        risks.append("workspace requer sync fast-forward antes de live futura.")
    if selection.get("selection_status") == "auto_selected":
        risks.append("run selecionada automaticamente; revisar antes de rodada longa.")
    if int(audit_result.get("stats", {}).get("blocked_count", 0)) > 0:
        risks.append("factory state audit encontrou itens bloqueados no workspace.")

    step_gates = _step_gates(
        readiness_status=readiness_status,
        sync_plan_status=sync_plan_status,
        budget_status=budget_status,
        context_status=context_status,
    )
    steps = [
        {
            "step": step_number,
            "recommended_profile": codex_plan.get("recommended_profile"),
            "model": codex_plan.get("model"),
            "reasoning_effort": codex_plan.get("reasoning_effort"),
            "context_status": context_status,
            "estimated_context_chars": context_chars,
            "budget_status": budget_status,
            "gates": step_gates,
        }
        for step_number in range(1, validated_max_steps + 1)
    ]

    report_path = _report_path(repo, normalized_run_id)
    report = {
        "ok": not blockers,
        "plan_version": LONG_RUN_PLAN_VERSION,
        "run_id": normalized_run_id,
        "target_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "allowed_to_execute_live": False,
        "planner_status": "dry_run_plan_only",
        "required_manual_review": True,
        "route_contract": routing_contract.get("routing_contract", {}),
        "routing_contract_validation": routing_contract,
        "codex_profile_summary": {
            "recommended_profile": codex_plan.get("recommended_profile"),
            "model": codex_plan.get("model"),
            "reasoning_effort": codex_plan.get("reasoning_effort"),
            "budget_status": budget_status,
        },
        "context_budget_summary": {
            "category": context_pack.get("category"),
            "context_policy": context_pack.get("context_policy"),
            "context_status": context_status,
            "context_chars": context_chars,
            "context_limit_chars": context_limit,
            "estimated_changed_files": codex_plan.get("estimated_changed_files"),
            "max_changed_files": codex_plan.get("max_changed_files"),
        },
        "hygiene_summary": {
            "audit_report": audit_result.get("report_path"),
            "plan_report": plan_result.get("report_path"),
            "running_tasks_count": audit_result.get("stats", {}).get("running_tasks_count", 0),
            "running_runs_count": audit_result.get("stats", {}).get("running_runs_count", 0),
            "needs_review_count": audit_result.get("stats", {}).get("needs_review_count", 0),
            "blocked_count": audit_result.get("stats", {}).get("blocked_count", 0),
            "safe_to_close_count": plan_result.get("stats", {}).get("safe_to_close_count", 0),
        },
        "readiness_status": readiness_status,
        "sync_plan_status": sync_plan_status,
        "estimated_reports_count": validated_max_steps + 5,
        "estimated_worktree_count": 1,
        "steps": steps,
        "risks": risks,
        "warnings": warnings,
        "blockers": blockers,
        "gates": ["manual_review_required", "live_blocked", f"selection:{selection['selection_status']}"],
        "selection_status": selection["selection_status"],
        "eligible_runs_count": selection["eligible_runs_count"],
        "codex_plan": codex_plan,
        "context_pack": context_pack,
        "readiness": readiness,
        "sync_plan": sync_plan,
        "report_path": report_path.relative_to(repo).as_posix(),
        "generated_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
