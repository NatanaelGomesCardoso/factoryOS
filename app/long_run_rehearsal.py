from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.codex_cost_audit import run_codex_cost_audit
from app.long_run_planner import run_factory_long_run_plan
from app.maintenance_plan import run_factory_maintenance_plan
from app.report_index import latest_report
from app.run_workspace import run_workspace_readiness, run_workspace_sync_plan, show_run
from app.task_runner import TaskRunnerError

LONG_RUN_REHEARSAL_VERSION = "v0"
LONG_RUN_REHEARSAL_REPORTS_DIR = "factory-long-run-rehearsals"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TARGET_MINUTES_MIN = 15
TARGET_MINUTES_MAX = 60
MAX_STEPS_MIN = 1
MAX_STEPS_MAX = 6
RECENT_REHEARSAL_HOURS = 24


@dataclass(frozen=True, slots=True)
class LatestLongRunRehearsalResult:
    available: bool
    report_path: str
    view_path: str | None
    run_id: str
    final_status: str
    final_decision: str
    allowed_to_execute_live: bool
    executed_live: bool
    readiness_status: str
    sync_plan_status: str
    budget_status: str
    context_status: str
    token_target_status: str
    generated_at: str
    target_minutes: int
    max_steps: int
    global_config_dependency: bool


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / LONG_RUN_REHEARSAL_REPORTS_DIR


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


def _report_path(repo: Path, run_id: str) -> Path:
    return _reports_root(repo) / f"{_timestamp()}-{run_id}.json"


def _latest_cost_audit(repo: Path) -> dict[str, Any]:
    latest = latest_report("codex-cost-audits", repo=repo)
    if latest is None:
        return run_codex_cost_audit(repo=repo)

    payload = latest.payload
    classification = payload.get("classification", {})
    status = str(classification.get("status", "")).strip()
    if status in {"ideal", "preferred_ok"}:
        return payload
    return run_codex_cost_audit(repo=repo)


def run_factory_long_run_rehearsal(
    run_id: str,
    *,
    target_minutes: int = 30,
    max_steps: int = 6,
    dry_run: bool = True,
    repo: Path | None = None,
) -> dict[str, Any]:
    from app.factory_start import run_factory_start

    if not dry_run:
        raise TaskRunnerError("Long Run Controlled Dry-Run Rehearsal V0 aceita somente --dry-run.")

    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    validated_target_minutes = _validate_target_minutes(target_minutes)
    validated_max_steps = _validate_max_steps(max_steps)

    run = show_run(normalized_run_id, repo=repo)["run"]
    if str(run.get("status", "")).strip() != "running":
        raise TaskRunnerError("run precisa estar em running para o rehearsal.")

    readiness = run_workspace_readiness(normalized_run_id, repo=repo)["workspace"]
    sync_plan = run_workspace_sync_plan(normalized_run_id, repo=repo)["plan"]
    readiness_status = str(readiness.get("status", "")).strip() or "unknown"
    sync_plan_status = str(sync_plan.get("status", "")).strip() or "unknown"

    long_run_plan = run_factory_long_run_plan(
        run_id=normalized_run_id,
        target_minutes=validated_target_minutes,
        max_steps=validated_max_steps,
        repo=repo,
    )
    maintenance_plan = run_factory_maintenance_plan(repo=repo)
    cost_audit = _latest_cost_audit(repo)
    plan_only_report = run_factory_start(
        run_id=normalized_run_id,
        target_minutes=validated_target_minutes,
        max_steps=validated_max_steps,
        plan_only=True,
        cost_aware=True,
        repo=repo,
    )
    dry_run_report = run_factory_start(
        run_id=normalized_run_id,
        target_minutes=validated_target_minutes,
        max_steps=min(2, validated_max_steps),
        dry_run=True,
        cost_aware=True,
        evaluate=True,
        repo=repo,
    )

    classification = cost_audit.get("classification", {})
    token_target_status = str(classification.get("status", "")).strip() or "missing"
    budget_status = str(plan_only_report.get("budget_status", "blocked")).strip() or "blocked"
    context_status = str(plan_only_report.get("context_status", "blocked")).strip() or "blocked"

    blockers: list[str] = []
    warnings: list[str] = []

    if readiness_status != "ready":
        blockers.extend([str(item) for item in readiness.get("reasons", []) if str(item).strip()])
    if sync_plan_status not in {"already_current", "fast_forward_available"}:
        blockers.extend([str(item) for item in sync_plan.get("reasons", []) if str(item).strip()])
    if not bool(long_run_plan.get("ok", False)):
        blockers.extend([str(item) for item in long_run_plan.get("blockers", []) if str(item).strip()])
    if maintenance_plan.get("deleted_files") != "none":
        blockers.append("maintenance plan registrou deleted_files diferente de none.")
    if maintenance_plan.get("removed_worktrees") != "none":
        blockers.append("maintenance plan registrou removed_worktrees diferente de none.")
    if budget_status != "ok":
        blockers.append(f"budget_status={budget_status} bloqueou o rehearsal.")
    if context_status != "ok":
        blockers.append(f"context_status={context_status} bloqueou o rehearsal.")
    if token_target_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"token_target_status={token_target_status} fora do nível aceito.")

    warnings.extend([str(item) for item in long_run_plan.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in plan_only_report.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in dry_run_report.get("warnings", []) if str(item).strip()])
    if sync_plan_status == "fast_forward_available":
        warnings.append("sync plan ainda requer fast-forward antes de qualquer live futuro.")

    final_status = "dry_run_only"
    final_decision = "dry_run_only"
    if blockers:
        final_status = "needs_review"
        final_decision = "needs_review"
    elif sync_plan_status != "already_current":
        final_status = "needs_review"
        final_decision = "needs_review"
    elif str(dry_run_report.get("final_decision", "")).strip() != "dry_run_only":
        final_status = "needs_review"
        final_decision = "needs_review"

    report_path = _report_path(repo, normalized_run_id)
    payload = {
        "ok": final_decision == "dry_run_only",
        "rehearsal_version": LONG_RUN_REHEARSAL_VERSION,
        "run_id": normalized_run_id,
        "target_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "mode": "dry-run",
        "allowed_to_execute_live": False,
        "executed_live": False,
        "required_manual_review": True,
        "long_run_plan_report": str(long_run_plan.get("report_path", "")).strip(),
        "maintenance_plan_report": str(maintenance_plan.get("report_path", "")).strip(),
        "cost_aware_plan_only_report": str(plan_only_report.get("report_path", "")).strip(),
        "cost_aware_dry_run_report": str(dry_run_report.get("report_path", "")).strip(),
        "budget_status": budget_status,
        "context_status": context_status,
        "token_target_status": token_target_status,
        "global_config_dependency": False,
        "readiness_status": readiness_status,
        "sync_plan_status": sync_plan_status,
        "final_status": final_status,
        "final_decision": final_decision,
        "next_gate_required": "manual_review_before_bounded_live_canary",
        "blockers": blockers,
        "warnings": warnings,
        "report_path": report_path.relative_to(repo).as_posix(),
        "cost_audit_report": str(cost_audit.get("report_path", "")).strip(),
        "generated_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def latest_valid_rehearsal_for_run(
    run_id: str,
    *,
    repo: Path | None = None,
    target_minutes: int | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    latest = latest_report("factory-long-run-rehearsals", repo=repo, run_id=normalized_run_id)
    if latest is None:
        return {"ok": False, "status": "missing", "reason": "rehearsal válido ausente para a run.", "report_path": ""}

    payload = latest.payload
    generated_at = str(payload.get("generated_at", "")).strip()
    if not generated_at:
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem generated_at.", "report_path": latest.relative_path}

    try:
        generated_dt = datetime.fromisoformat(generated_at)
    except ValueError:
        return {"ok": False, "status": "invalid", "reason": "rehearsal com generated_at inválido.", "report_path": latest.relative_path}

    now = datetime.now(generated_dt.tzinfo)
    if now - generated_dt > timedelta(hours=RECENT_REHEARSAL_HOURS):
        return {"ok": False, "status": "stale", "reason": f"rehearsal mais recente excedeu {RECENT_REHEARSAL_HOURS}h.", "report_path": latest.relative_path}
    if str(payload.get("final_decision", "")).strip() != "dry_run_only":
        return {"ok": False, "status": "needs_review", "reason": "rehearsal recente não terminou em dry_run_only.", "report_path": latest.relative_path}
    if bool(payload.get("allowed_to_execute_live", True)):
        return {"ok": False, "status": "invalid", "reason": "rehearsal não pode autorizar live diretamente.", "report_path": latest.relative_path}
    if bool(payload.get("executed_live", True)):
        return {"ok": False, "status": "invalid", "reason": "rehearsal não pode registrar executed_live=true.", "report_path": latest.relative_path}
    if str(payload.get("readiness_status", "")).strip() != "ready":
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem readiness ready.", "report_path": latest.relative_path}
    if str(payload.get("sync_plan_status", "")).strip() != "already_current":
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem sync plan already_current.", "report_path": latest.relative_path}
    if str(payload.get("budget_status", "")).strip() != "ok":
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem budget_status=ok.", "report_path": latest.relative_path}
    if str(payload.get("context_status", "")).strip() != "ok":
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem context_status=ok.", "report_path": latest.relative_path}
    if str(payload.get("token_target_status", "")).strip() not in {"ideal", "preferred_ok"}:
        return {"ok": False, "status": "invalid", "reason": "rehearsal sem token_target_status aceitável.", "report_path": latest.relative_path}
    if bool(payload.get("global_config_dependency", True)):
        return {"ok": False, "status": "invalid", "reason": "rehearsal depende de config global.", "report_path": latest.relative_path}
    if target_minutes is not None and int(payload.get("target_minutes", 0) or 0) != int(target_minutes):
        return {"ok": False, "status": "mismatch", "reason": "rehearsal recente não corresponde ao target_minutes exigido.", "report_path": latest.relative_path}
    if max_steps is not None and int(payload.get("max_steps", 0) or 0) != int(max_steps):
        return {"ok": False, "status": "mismatch", "reason": "rehearsal recente não corresponde ao max_steps exigido.", "report_path": latest.relative_path}

    return {
        "ok": True,
        "status": "valid",
        "reason": "",
        "report_path": latest.relative_path,
        "payload": payload,
    }
