from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.long_run_expansion_policy import run_long_run_expansion_policy
from app.long_run_rehearsal import run_factory_long_run_rehearsal
from app.maintenance_plan import run_factory_maintenance_plan
from app.report_index import latest_report
from app.state_hygiene import factory_state_audit, factory_state_plan
from app.run_workspace import show_run
from app.task_runner import TaskRunnerError

EXPANDED_LONG_RUN_REHEARSAL_VERSION = "v0"
EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR = "expanded-long-run-rehearsals"
EXPANSION_POLICY_REPORTS_DIR = "long-run-expansion-policies"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TARGET_MINUTES_REQUIRED = 30
MAX_STEPS_REQUIRED = 6


@dataclass(frozen=True, slots=True)
class LatestExpandedLongRunRehearsalResult:
    available: bool
    expanded_rehearsal_version: str
    run_id: str
    target_minutes: int
    max_steps: int
    mode: str
    source_expansion_policy_report: str
    long_run_rehearsal_report: str
    maintenance_plan_report: str
    factory_state_audit_report: str
    factory_state_plan_report: str
    allowed_to_execute_live: bool
    executed_live: bool
    requires_review_gate: bool
    requires_new_sprint_for_live: bool
    global_config_dependency: bool
    token_target_status: str
    budget_status: str
    context_status: str
    final_decision: str
    blockers: list[str]
    warnings: list[str]
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    report_path: str
    view_path: str | None
    generated_at: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR


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
    if any(part in {".", ".."} for part in Path(normalized).parts):
        raise TaskRunnerError("id da run contém path traversal.")
    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise TaskRunnerError("id da run contém caracteres inválidos.")
    return normalized


def _validate_target_minutes(target_minutes: int) -> int:
    if target_minutes != TARGET_MINUTES_REQUIRED:
        raise TaskRunnerError(f"expanded rehearsal V0 exige target_minutes={TARGET_MINUTES_REQUIRED}.")
    return target_minutes


def _validate_max_steps(max_steps: int) -> int:
    if max_steps != MAX_STEPS_REQUIRED:
        raise TaskRunnerError(f"expanded rehearsal V0 exige max_steps={MAX_STEPS_REQUIRED}.")
    return max_steps


def _safe_relative_path(value: str, *, prefix: str, suffix: str) -> bool:
    if not value or Path(value).is_absolute():
        return False
    candidate = Path(value)
    if any(part in {".", ".."} for part in candidate.parts):
        return False
    return candidate.as_posix().startswith(prefix) and candidate.suffix == suffix


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.as_posix()}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")
    return payload


def _latest_policy_for_run(repo: Path, run_id: str) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report(EXPANSION_POLICY_REPORTS_DIR, repo=repo, run_id=run_id)
    if latest is None:
        latest = latest_report(EXPANSION_POLICY_REPORTS_DIR, repo=repo)
    if latest is None:
        return None
    payload = dict(latest.payload)
    if str(payload.get("decision", "")).strip() != "policy_ready_for_next_sprint":
        return None
    return latest.relative_path, payload


def _latest_state_audit(repo: Path) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report("factory-state-hygiene", repo=repo)
    if latest is None:
        return None
    payload = dict(latest.payload)
    if str(payload.get("kind", "")).strip() != "audit":
        return None
    return latest.relative_path, payload


def _latest_state_plan(repo: Path) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report("factory-state-hygiene", repo=repo)
    if latest is None:
        return None
    payload = dict(latest.payload)
    if str(payload.get("kind", "")).strip() != "plan":
        return None
    return latest.relative_path, payload


def _latest_cost_audit(repo: Path) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report("codex-cost-audits", repo=repo)
    if latest is None:
        return None
    return latest.relative_path, dict(latest.payload)


def _latest_maintenance_plan(repo: Path) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report("factory-maintenance-plans", repo=repo)
    if latest is None:
        return None
    return latest.relative_path, dict(latest.payload)


def _latest_report_for_run(repo: Path, run_id: str) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report(EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR, repo=repo, run_id=run_id)
    if latest is None:
        return None
    return latest.relative_path, dict(latest.payload)


def run_expanded_long_run_rehearsal(
    run_id: str,
    *,
    target_minutes: int = 30,
    max_steps: int = 6,
    dry_run: bool = True,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    validated_target_minutes = _validate_target_minutes(target_minutes)
    validated_max_steps = _validate_max_steps(max_steps)

    if not dry_run:
        raise TaskRunnerError("Expanded Long Run Rehearsal V0 aceita somente --dry-run.")

    run_payload = dict(show_run(normalized_run_id, repo=repo)["run"])
    if str(run_payload.get("status", "")).strip() != "running":
        raise TaskRunnerError("run precisa estar em running para o rehearsal expandido.")

    policy = _latest_policy_for_run(repo, normalized_run_id)
    if policy is None:
        raise TaskRunnerError("policy de expansão aprovada ausente para a run informada.")

    policy_payload = policy[1]
    policy_decision = str(policy_payload.get("decision", "")).strip()
    policy_ok = bool(policy_payload.get("ok", False))
    policy_allowed_live = bool(policy_payload.get("allowed_to_execute_live", True))
    policy_requires_new_sprint = bool(policy_payload.get("requires_new_sprint", False))

    if policy_decision != "policy_ready_for_next_sprint" or not policy_ok:
        raise TaskRunnerError("policy de expansão ainda não está pronta para o rehearsal expandido.")
    if policy_allowed_live:
        raise TaskRunnerError("policy de expansão não pode permitir live nesta etapa.")
    if not policy_requires_new_sprint:
        raise TaskRunnerError("policy de expansão precisa exigir nova sprint.")

    long_run_rehearsal = run_factory_long_run_rehearsal(
        run_id=normalized_run_id,
        target_minutes=validated_target_minutes,
        max_steps=validated_max_steps,
        dry_run=True,
        repo=repo,
    )
    maintenance_plan = run_factory_maintenance_plan(repo=repo)
    state_audit = factory_state_audit(repo=repo)
    state_plan = factory_state_plan(repo=repo)
    cost_audit = _latest_cost_audit(repo)

    rehearsal_budget_status = str(long_run_rehearsal.get("budget_status", "")).strip() or "blocked"
    rehearsal_context_status = str(long_run_rehearsal.get("context_status", "")).strip() or "blocked"
    rehearsal_token_status = str(long_run_rehearsal.get("token_target_status", "")).strip() or "missing"
    rehearsal_readiness_status = str(long_run_rehearsal.get("readiness_status", "")).strip() or "unknown"
    rehearsal_sync_plan_status = str(long_run_rehearsal.get("sync_plan_status", "")).strip() or "unknown"
    rehearsal_final_decision = str(long_run_rehearsal.get("final_decision", "")).strip()
    rehearsal_allowed_live = bool(long_run_rehearsal.get("allowed_to_execute_live", True))
    rehearsal_executed_live = bool(long_run_rehearsal.get("executed_live", True))
    rehearsal_global_config_dependency = bool(long_run_rehearsal.get("global_config_dependency", True))

    cost_status = str(cost_audit[1].get("classification", {}).get("status", "")).strip() if cost_audit else ""
    maintenance_deleted_files = maintenance_plan.get("deleted_files", "none")
    maintenance_removed_worktrees = maintenance_plan.get("removed_worktrees", "none")
    state_audit_payload = state_audit
    state_plan_payload = state_plan

    blockers: list[str] = []
    warnings: list[str] = []

    if not long_run_rehearsal.get("ok", False):
        blockers.extend([str(item) for item in long_run_rehearsal.get("blockers", []) if str(item).strip()])
    if rehearsal_final_decision != "dry_run_only":
        blockers.append("rehearsal anterior não terminou em dry_run_only.")
    if rehearsal_allowed_live:
        blockers.append("rehearsal expandido não pode autorizar live.")
    if rehearsal_executed_live:
        blockers.append("rehearsal expandido registrou executed_live=true.")
    if rehearsal_budget_status != "ok":
        blockers.append(f"budget_status={rehearsal_budget_status} bloqueou o rehearsal expandido.")
    if rehearsal_context_status != "ok":
        blockers.append(f"context_status={rehearsal_context_status} bloqueou o rehearsal expandido.")
    if rehearsal_token_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"token_target_status={rehearsal_token_status} fora do nível aceito.")
    if rehearsal_readiness_status != "ready":
        blockers.append(f"readiness_status={rehearsal_readiness_status} bloqueou o rehearsal expandido.")
    if rehearsal_sync_plan_status != "already_current":
        blockers.append(f"sync_plan_status={rehearsal_sync_plan_status} bloqueou o rehearsal expandido.")
    if rehearsal_global_config_dependency:
        blockers.append("rehearsal expandido depende de config global.")
    if cost_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"cost_audit_status={cost_status or 'missing'} fora do nível aceito.")

    state_audit_stats = state_audit_payload.get("stats", {}) if state_audit_payload else {}
    state_plan_stats = state_plan_payload.get("stats", {}) if state_plan_payload else {}
    if int(state_audit_stats.get("running_tasks_count", 1) or 1) != 0:
        warnings.append("factory-state-audit ainda mostra running_tasks_count diferente de zero; revisão final ainda pendente.")
    if int(state_audit_stats.get("running_runs_count", 1) or 1) != 0:
        warnings.append("factory-state-audit ainda mostra running_runs_count diferente de zero; revisão final ainda pendente.")
    if int(state_plan_stats.get("safe_to_close_count", 1) or 1) != 0:
        warnings.append("factory-state-plan ainda mostra safe_to_close_count diferente de zero; revisão final ainda pendente.")
    if int(state_plan_stats.get("needs_review_count", 1) or 1) != 0:
        warnings.append("factory-state-plan ainda mostra needs_review_count diferente de zero; revisão final ainda pendente.")
    if int(state_plan_stats.get("blocked_count", 1) or 1) != 0:
        warnings.append("factory-state-plan ainda mostra blocked_count diferente de zero; revisão final ainda pendente.")
    if str(maintenance_deleted_files) != "none":
        blockers.append("maintenance plan registrou deleted_files.")
    if str(maintenance_removed_worktrees) != "none":
        blockers.append("maintenance plan registrou removed_worktrees.")

    if policy is None:
        blockers.append("policy de expansão ausente.")

    if policy is not None and str(policy_payload.get("target_minutes", 0) or 0) != str(TARGET_MINUTES_REQUIRED):
        blockers.append("policy de expansão não corresponde a target_minutes=30.")
    if policy is not None and str(policy_payload.get("max_steps", 0) or 0) != str(MAX_STEPS_REQUIRED):
        blockers.append("policy de expansão não corresponde a max_steps=6.")

    warnings.extend([str(item) for item in long_run_rehearsal.get("warnings", []) if str(item).strip()])
    if cost_audit is None:
        warnings.append("cost audit não encontrado no momento do rehearsal expandido.")
    if state_audit is None:
        warnings.append("factory-state-audit não encontrado no momento do rehearsal expandido.")
    if state_plan is None:
        warnings.append("factory-state-plan não encontrado no momento do rehearsal expandido.")
    if policy is None:
        warnings.append("policy de expansão não encontrada no momento do rehearsal expandido.")

    final_decision = "expanded_rehearsal_ready_for_review"
    final_status = final_decision
    if blockers:
        final_decision = "blocked" if any("ausente" in item or "invalid" in item or "não corresponde" in item for item in blockers) else "needs_review"
        final_status = final_decision

    report_path = _reports_root(repo) / f"{_timestamp()}-{normalized_run_id}.json"
    payload = {
        "ok": final_decision == "expanded_rehearsal_ready_for_review",
        "expanded_rehearsal_version": EXPANDED_LONG_RUN_REHEARSAL_VERSION,
        "run_id": normalized_run_id,
        "target_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "mode": "dry-run",
        "source_expansion_policy_report": policy[0] if policy is not None else "",
        "long_run_rehearsal_report": str(long_run_rehearsal.get("report_path", "")).strip(),
        "maintenance_plan_report": str(maintenance_plan.get("report_path", "")).strip(),
        "factory_state_audit_report": str(state_audit.get("report_path", "")).strip() if state_audit else "",
        "factory_state_plan_report": str(state_plan.get("report_path", "")).strip() if state_plan else "",
        "allowed_to_execute_live": False,
        "executed_live": False,
        "requires_review_gate": True,
        "requires_new_sprint_for_live": True,
        "global_config_dependency": False,
        "token_target_status": rehearsal_token_status,
        "budget_status": rehearsal_budget_status,
        "context_status": rehearsal_context_status,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "final_decision": final_decision,
        "final_status": final_status,
        "blockers": blockers,
        "warnings": warnings,
        "report_path": report_path.relative_to(repo).as_posix(),
        "generated_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def load_latest_expanded_long_run_rehearsal_result(repo: Path) -> LatestExpandedLongRunRehearsalResult:
    latest = latest_report(EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR, repo=repo)
    if latest is None:
        return LatestExpandedLongRunRehearsalResult(
            available=False,
            expanded_rehearsal_version=EXPANDED_LONG_RUN_REHEARSAL_VERSION,
            run_id="",
            target_minutes=0,
            max_steps=0,
            mode="",
            source_expansion_policy_report="",
            long_run_rehearsal_report="",
            maintenance_plan_report="",
            factory_state_audit_report="",
            factory_state_plan_report="",
            allowed_to_execute_live=False,
            executed_live=False,
            requires_review_gate=True,
            requires_new_sprint_for_live=True,
            global_config_dependency=False,
            token_target_status="",
            budget_status="",
            context_status="",
            final_decision="unknown",
            blockers=[],
            warnings=[],
            no_push=False,
            no_deploy=False,
            no_paid_api=False,
            no_secrets=False,
            report_path="",
            view_path=None,
            generated_at="",
        )

    payload = latest.payload
    report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
    run_id = str(payload.get("run_id", "")).strip()
    if (
        report_path
        and run_id
        and _safe_relative_path(
            report_path,
            prefix=f"reports/{EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR}/",
            suffix=".json",
        )
    ):
        return LatestExpandedLongRunRehearsalResult(
            available=True,
            expanded_rehearsal_version=str(payload.get("expanded_rehearsal_version", EXPANDED_LONG_RUN_REHEARSAL_VERSION)).strip()
            or EXPANDED_LONG_RUN_REHEARSAL_VERSION,
            run_id=run_id,
            target_minutes=int(payload.get("target_minutes", 0) or 0),
            max_steps=int(payload.get("max_steps", 0) or 0),
            mode=str(payload.get("mode", "")).strip(),
            source_expansion_policy_report=str(payload.get("source_expansion_policy_report", "")).strip(),
            long_run_rehearsal_report=str(payload.get("long_run_rehearsal_report", "")).strip(),
            maintenance_plan_report=str(payload.get("maintenance_plan_report", "")).strip(),
            factory_state_audit_report=str(payload.get("factory_state_audit_report", "")).strip(),
            factory_state_plan_report=str(payload.get("factory_state_plan_report", "")).strip(),
            allowed_to_execute_live=bool(payload.get("allowed_to_execute_live", False)),
            executed_live=bool(payload.get("executed_live", False)),
            requires_review_gate=bool(payload.get("requires_review_gate", True)),
            requires_new_sprint_for_live=bool(payload.get("requires_new_sprint_for_live", True)),
            global_config_dependency=bool(payload.get("global_config_dependency", False)),
            token_target_status=str(payload.get("token_target_status", "")).strip(),
            budget_status=str(payload.get("budget_status", "")).strip(),
            context_status=str(payload.get("context_status", "")).strip(),
            final_decision=str(payload.get("final_decision", "")).strip() or "unknown",
            blockers=[str(item) for item in payload.get("blockers", []) if str(item).strip()],
            warnings=[str(item) for item in payload.get("warnings", []) if str(item).strip()],
            no_push=bool(payload.get("no_push", False)),
            no_deploy=bool(payload.get("no_deploy", False)),
            no_paid_api=bool(payload.get("no_paid_api", False)),
            no_secrets=bool(payload.get("no_secrets", False)),
            report_path=report_path,
            view_path=latest.view_path,
            generated_at=str(payload.get("generated_at", "")).strip(),
        )

    return LatestExpandedLongRunRehearsalResult(
        available=False,
        expanded_rehearsal_version=EXPANDED_LONG_RUN_REHEARSAL_VERSION,
        run_id="",
        target_minutes=0,
        max_steps=0,
        mode="",
        source_expansion_policy_report="",
        long_run_rehearsal_report="",
        maintenance_plan_report="",
        factory_state_audit_report="",
        factory_state_plan_report="",
        allowed_to_execute_live=False,
        executed_live=False,
        requires_review_gate=True,
        requires_new_sprint_for_live=True,
        global_config_dependency=False,
        token_target_status="",
        budget_status="",
        context_status="",
        final_decision="unknown",
        blockers=[],
        warnings=[],
        no_push=False,
        no_deploy=False,
        no_paid_api=False,
        no_secrets=False,
        report_path="",
        view_path=None,
        generated_at="",
    )
