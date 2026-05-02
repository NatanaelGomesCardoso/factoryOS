from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_handoff import (
    LIVE_CODEX_ENV,
    LIVE_CODEX_TIMEOUT_SECONDS,
    build_factoryos_codex_exec_command,
    load_latest_handoff_result,
    execute_live_codex,
)
from app.capsule_execution_policy import policy_for_run
from app.codex_context_router import context_pack_for_run
from app.codex_profile import codex_plan_for_run
from app.compact_execution_harness import compact_exec_handoff_metadata, infer_compact_exec_category
from app.controlled_loop import MAX_STEPS_LIMIT, run_controlled_loop
from app.execution_evaluator import evaluate_execution
from app.expanded_long_run_review_gate import load_latest_expanded_long_run_review_gate_result
from app.long_run_planner import run_factory_long_run_plan
from app.long_run_rehearsal import latest_valid_rehearsal_for_run
from app.output_budget import output_budget_contract_text
from app.maintenance_plan import run_factory_maintenance_plan
from app.report_index import latest_report
from app.routing_contracts import routing_contract_validation_payload
from app.run_workspace import run_workspace_readiness, run_workspace_sync_plan, show_run, workspace_status
from app.state_hygiene import factory_state_audit, factory_state_plan
from app.task_runner import TaskRunnerError, show_task
from app.token_usage import parse_token_usage_text

FACTORY_START_REPORTS_DIR = "factory-starts"
FACTORY_START_VERSION = "v0"
FACTORY_START_COST_AWARE_REPORTS_DIR = "cost-aware-factory-starts"
FACTORY_START_COST_AWARE_VERSION = "v0"
FACTORY_START_LIVE_CANARY_REPORTS_DIR = "factory-start-live-canary"
FACTORY_START_LIVE_CANARY_ALLOWED_FILES = (
    "reports/factory-start-live-canary/factory-start-canary-step-1.txt",
    "reports/factory-start-live-canary/factory-start-canary-step-2.txt",
)
FACTORY_START_LIVE_CANARY_MODEL = "gpt-5.4-mini"
FACTORY_START_LIVE_CANARY_REASONING = "medium"
MAX_LIVE_CANARY_STEPS = 2
BOUNDED_LONG_RUN_LIVE_CANARY_REPORTS_DIR = "bounded-long-run-live-canary"
BOUNDED_LONG_RUN_LIVE_CANARY_ALLOWED_FILES = (
    "reports/bounded-long-run-live-canary/step-1.txt",
    "reports/bounded-long-run-live-canary/step-2.txt",
    "reports/bounded-long-run-live-canary/step-3.txt",
)
BOUNDED_LONG_RUN_LIVE_CANARY_MODEL = "gpt-5.4-mini"
BOUNDED_LONG_RUN_LIVE_CANARY_REASONING = "low"
BOUNDED_LONG_RUN_LIVE_CANARY_MAX_STEPS = 3
BOUNDED_LONG_RUN_LIVE_CANARY_MAX_MINUTES = 15
EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR = "expanded-bounded-live-canary"
EXPANDED_BOUNDED_LIVE_CANARY_ALLOWED_FILES = (
    "reports/expanded-bounded-live-canary/step-1.txt",
    "reports/expanded-bounded-live-canary/step-2.txt",
    "reports/expanded-bounded-live-canary/step-3.txt",
    "reports/expanded-bounded-live-canary/step-4.txt",
    "reports/expanded-bounded-live-canary/step-5.txt",
    "reports/expanded-bounded-live-canary/step-6.txt",
)
EXPANDED_BOUNDED_LIVE_CANARY_MODEL = "gpt-5.4-mini"
EXPANDED_BOUNDED_LIVE_CANARY_REASONING = "low"
EXPANDED_BOUNDED_LIVE_CANARY_MAX_STEPS = 6
EXPANDED_BOUNDED_LIVE_CANARY_MAX_MINUTES = 30
EXPANDED_BOUNDED_LIVE_CANARY_ATTEMPTS_DIR = "attempts"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class LatestFactoryStartResult:
    available: bool
    factory_start_version: str
    mode: str
    start_id: str
    run_id: str
    status: str
    decision: str
    max_steps: int
    steps_completed: int
    executed_live: bool
    loop_report: str
    evaluation_report: str
    evaluation_decision: str
    final_decision: str
    final_status: str
    report_path: str
    view_path: str | None
    started_at: str
    finished_at: str
    reasons: list[str]


@dataclass(frozen=True, slots=True)
class LatestFactoryStartLiveCanaryResult:
    available: bool
    status: str
    mode: str
    max_steps: int
    steps_completed: int
    executed_live: bool
    canary_run_id: str
    canary_task_id: str
    report_path: str
    view_path: str | None
    workspace_path: str
    workspace_branch: str | None
    changed_files: list[str]
    canary_file: str
    codex_exit_code: int
    codex_exit_codes: list[int]
    stdout_path: str
    stderr_path: str
    master_head_before: str
    master_head_after: str
    workspace_head_before: str
    workspace_head_after: str
    allowed_files_changed: bool
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    created_at: str
    finished_at: str
    branch_commit: str | None
    decision: str
    evaluation_report: str
    evaluation_decision: str
    final_decision: str
    final_status: str


@dataclass(frozen=True, slots=True)
class LatestExpandedBoundedLiveCanaryResult:
    available: bool
    status: str
    mode: str
    max_steps: int
    max_minutes: int
    steps_completed: int
    executed_live: bool
    canary_run_id: str
    canary_task_id: str
    report_path: str
    view_path: str | None
    workspace_path: str
    workspace_branch: str | None
    changed_files: list[str]
    allowed_files: list[str]
    disallowed_files: list[str]
    codex_or_capsule_runs: list[dict[str, Any]]
    token_summary: dict[str, Any]
    codex_exit_codes: list[int]
    stdout_path: str
    stderr_path: str
    master_head_before: str
    master_head_after: str
    workspace_head_before: str
    workspace_head_after: str
    allowed_files_changed: bool
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    created_at: str
    finished_at: str
    branch_commit: str | None
    decision: str
    evaluation_report: str
    evaluation_decision: str
    final_decision: str
    final_status: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / FACTORY_START_REPORTS_DIR


def _live_canary_reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / FACTORY_START_LIVE_CANARY_REPORTS_DIR


def _bounded_live_canary_reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / BOUNDED_LONG_RUN_LIVE_CANARY_REPORTS_DIR


def _expanded_bounded_live_canary_reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR


def _safe_relative_path(value: str, *, prefix: str, suffix: str) -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {".", ".."} for part in candidate.parts):
        return False

    return candidate.as_posix().startswith(prefix) and candidate.suffix == suffix


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

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


def _git(repo: Path, *args: str) -> str:
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
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"git {' '.join(args)} falhou."
        raise TaskRunnerError(detail)

    return completed.stdout.strip()


def _git_optional(repo: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout.strip()


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


def _validate_max_steps(max_steps: int) -> int:
    if max_steps < 1:
        raise TaskRunnerError("max_steps precisa ser pelo menos 1.")
    if max_steps > MAX_STEPS_LIMIT:
        raise TaskRunnerError(f"max_steps precisa ser no máximo {MAX_STEPS_LIMIT}.")
    return max_steps


def _validate_live_canary_max_steps(max_steps: int) -> int:
    validated = _validate_max_steps(max_steps)
    if validated > MAX_LIVE_CANARY_STEPS:
        raise TaskRunnerError(f"live canary multi-step exige max_steps no máximo {MAX_LIVE_CANARY_STEPS}.")
    return validated


def _validate_bounded_live_canary_max_steps(max_steps: int) -> int:
    validated = _validate_max_steps(max_steps)
    if validated > BOUNDED_LONG_RUN_LIVE_CANARY_MAX_STEPS:
        raise TaskRunnerError(
            f"bounded long run live canary exige max_steps no máximo {BOUNDED_LONG_RUN_LIVE_CANARY_MAX_STEPS}."
        )
    return validated


def _validate_bounded_live_canary_target_minutes(target_minutes: int) -> int:
    if target_minutes < 1 or target_minutes > BOUNDED_LONG_RUN_LIVE_CANARY_MAX_MINUTES:
        raise TaskRunnerError(
            f"bounded long run live canary exige target_minutes entre 1 e {BOUNDED_LONG_RUN_LIVE_CANARY_MAX_MINUTES}."
        )
    return target_minutes


def _validate_expanded_bounded_live_canary_max_steps(max_steps: int) -> int:
    if max_steps < 1:
        raise TaskRunnerError("max_steps precisa ser pelo menos 1.")
    if max_steps > EXPANDED_BOUNDED_LIVE_CANARY_MAX_STEPS:
        raise TaskRunnerError(
            f"expanded bounded live canary exige max_steps no máximo {EXPANDED_BOUNDED_LIVE_CANARY_MAX_STEPS}."
        )
    return max_steps


def _validate_expanded_bounded_live_canary_target_minutes(target_minutes: int) -> int:
    if target_minutes < 1 or target_minutes > EXPANDED_BOUNDED_LIVE_CANARY_MAX_MINUTES:
        raise TaskRunnerError(
            f"expanded bounded live canary exige target_minutes entre 1 e {EXPANDED_BOUNDED_LIVE_CANARY_MAX_MINUTES}."
        )
    return target_minutes


def _expanded_bounded_live_canary_gate_result(run_id: str, *, repo: Path) -> dict[str, Any]:
    review_gate = load_latest_expanded_long_run_review_gate_result(repo)
    if not review_gate.available or review_gate.run_id != run_id:
        raise TaskRunnerError("expanded bounded live canary bloqueado por review gate ausente para a run.")
    if not review_gate.approved_for_expanded_live_sprint:
        raise TaskRunnerError("expanded bounded live canary bloqueado por review gate não aprovado.")
    return {
        "report_path": review_gate.report_path,
        "decision": review_gate.decision,
        "approved_for_expanded_live_sprint": review_gate.approved_for_expanded_live_sprint,
        "allowed_to_execute_live": review_gate.allowed_to_execute_live,
        "recommended_next_gate": review_gate.recommended_next_sprint,
        "max_steps": int(review_gate.max_steps),
        "target_minutes": int(review_gate.target_minutes),
    }


def _expanded_bounded_live_canary_workspace_snapshot(
    validation: dict[str, Any],
    *,
    run_id: str,
    repo: Path,
) -> dict[str, Any]:
    workspace = validation.get("workspace")
    if isinstance(workspace, dict):
        return workspace

    readiness = validation.get("readiness")
    if isinstance(readiness, dict):
        readiness_workspace = readiness.get("workspace")
        if isinstance(readiness_workspace, dict):
            return readiness_workspace

    try:
        return workspace_status(run_id, repo=repo)["workspace"]
    except (KeyError, TaskRunnerError) as exc:
        raise TaskRunnerError("expanded live canary blocked: workspace snapshot ausente.") from exc


def _normalize_expanded_canary_validation(
    validation: dict[str, Any],
    *,
    run_id: str,
    repo: Path,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "warnings": [],
        "blockers": [],
        "workspace": {},
        "readiness": {},
        "sync_plan": {},
        "run": validation.get("run") if isinstance(validation.get("run"), dict) else {},
        "review_gate": validation.get("review_gate") if isinstance(validation.get("review_gate"), dict) else {},
        "rehearsal": validation.get("rehearsal") if isinstance(validation.get("rehearsal"), dict) else {},
        "cost_audit": validation.get("cost_audit") if isinstance(validation.get("cost_audit"), dict) else {},
        "max_steps": int(validation["max_steps"]),
        "target_minutes": int(validation["target_minutes"]),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
    }

    run = normalized["run"]
    if not run:
        normalized["blockers"].append("run snapshot ausente.")
        normalized["warnings"].append("run ausente na validação expandida; usando fallback vazio.")

    try:
        workspace = _expanded_bounded_live_canary_workspace_snapshot(validation, run_id=run_id, repo=repo)
    except TaskRunnerError as exc:
        normalized["blockers"].append(str(exc))
        workspace = {}
    if workspace:
        normalized["workspace"] = workspace
    else:
        normalized["warnings"].append("workspace snapshot ausente na validação expandida.")

    try:
        readiness = run_workspace_readiness(run_id, repo=repo).get("workspace", {})
    except TaskRunnerError as exc:
        readiness = {}
        normalized["warnings"].append(f"readiness snapshot indisponível: {exc}")
    if isinstance(readiness, dict) and readiness:
        normalized["readiness"] = readiness
    else:
        normalized["warnings"].append("readiness snapshot ausente na validação expandida.")
        normalized["blockers"].append("expanded live canary blocked: readiness snapshot ausente.")

    try:
        sync_plan = run_workspace_sync_plan(run_id, repo=repo).get("plan", {})
    except TaskRunnerError as exc:
        sync_plan = {}
        normalized["warnings"].append(f"sync plan indisponível: {exc}")
    if isinstance(sync_plan, dict) and sync_plan:
        normalized["sync_plan"] = sync_plan
    else:
        normalized["warnings"].append("sync_plan snapshot ausente na validação expandida.")

    normalized["master_head_before"] = normalized["readiness"].get("main_head") if isinstance(normalized["readiness"], dict) else None
    normalized["workspace_head_before"] = normalized["readiness"].get("workspace_head") if isinstance(normalized["readiness"], dict) else None
    normalized["workspace_branch"] = normalized["workspace"].get("branch") if isinstance(normalized["workspace"], dict) else None
    normalized["workspace_path"] = str(run.get("workspace_path", "")) if isinstance(run, dict) else ""
    normalized["readiness_status"] = normalized["readiness"].get("status") if isinstance(normalized["readiness"], dict) else None
    normalized["sync_plan_status"] = normalized["sync_plan"].get("status") if isinstance(normalized["sync_plan"], dict) else None
    normalized["safety_flags"] = {
        "bounded": True,
        "canary": True,
        "cost_aware": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
    }
    return normalized


def validate_expanded_bounded_live_canary_request(
    run_id: str,
    *,
    max_steps: int,
    target_minutes: int,
    bounded: bool,
    canary: bool,
    cost_aware: bool,
    no_push: bool,
    no_deploy: bool,
    no_paid_api: bool,
    no_secrets: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    if not bounded:
        raise TaskRunnerError("expanded bounded live canary exige --bounded.")
    if not canary:
        raise TaskRunnerError("expanded bounded live canary exige --canary.")
    if not cost_aware:
        raise TaskRunnerError("expanded bounded live canary exige --cost-aware.")
    if not no_push:
        raise TaskRunnerError("expanded bounded live canary exige --no-push.")
    if not no_deploy:
        raise TaskRunnerError("expanded bounded live canary exige --no-deploy.")
    if not no_paid_api:
        raise TaskRunnerError("expanded bounded live canary exige --no-paid-api.")
    if not no_secrets:
        raise TaskRunnerError("expanded bounded live canary exige --no-secrets.")

    validated_max_steps = _validate_expanded_bounded_live_canary_max_steps(max_steps)
    validated_target_minutes = _validate_expanded_bounded_live_canary_target_minutes(target_minutes)
    gate_result = _expanded_bounded_live_canary_gate_result(normalized_run_id, repo=repo)
    if gate_result["max_steps"] != EXPANDED_BOUNDED_LIVE_CANARY_MAX_STEPS:
        raise TaskRunnerError("expanded bounded live canary bloqueado por revisão fora do nível expandido esperado.")
    if gate_result["target_minutes"] != EXPANDED_BOUNDED_LIVE_CANARY_MAX_MINUTES:
        raise TaskRunnerError("expanded bounded live canary bloqueado por target_minutes fora do nível expandido esperado.")
    rehearsal = latest_valid_rehearsal_for_run(
        normalized_run_id,
        repo=repo,
        target_minutes=validated_target_minutes,
        max_steps=validated_max_steps,
    )
    if not rehearsal["ok"]:
        raise TaskRunnerError(f"expanded bounded live canary bloqueado: {rehearsal['reason']}")

    cost_audit = _latest_cost_audit_summary(repo)
    if str(cost_audit.get("status", "")).strip() not in {"ideal", "preferred_ok"}:
        raise TaskRunnerError("expanded bounded live canary bloqueado por codex cost audit fora do nível aceito.")
    run_result = show_run(normalized_run_id, repo=repo)
    run = run_result["run"]
    workspace = workspace_status(normalized_run_id, repo=repo)["workspace"]

    return {
        "run": run,
        "workspace": workspace,
        "max_steps": validated_max_steps,
        "target_minutes": validated_target_minutes,
        "rehearsal": rehearsal,
        "review_gate": gate_result,
        "cost_audit": cost_audit,
    }


def _start_id(run_token: str, *, started_at: str) -> str:
    timestamp = datetime.fromisoformat(started_at).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{run_token}-{secrets.token_hex(3)}"


def _report_path(repo: Path, start_id: str) -> Path:
    return _reports_root(repo) / f"{start_id}.json"


def _cost_aware_reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / FACTORY_START_COST_AWARE_REPORTS_DIR


def _cost_aware_report_path(repo: Path, run_id: str) -> Path:
    return _cost_aware_reports_root(repo) / f"{_timestamp()}-{run_id}.json"


def _live_canary_report_path(repo: Path, run_id: str, *, created_at: str) -> Path:
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d-%H%M%S")
    return _live_canary_reports_root(repo) / f"{timestamp}-{run_id}.json"


def _bounded_live_canary_report_path(repo: Path, run_id: str, *, created_at: str) -> Path:
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d-%H%M%S")
    return _bounded_live_canary_reports_root(repo) / f"{timestamp}-{run_id}.json"


def _expanded_bounded_live_canary_report_path(repo: Path, run_id: str, *, created_at: str) -> Path:
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d-%H%M%S")
    return _expanded_bounded_live_canary_reports_root(repo) / f"{timestamp}-{run_id}.json"


def _expanded_bounded_live_canary_attempt_dir(report_path: Path, attempt_id: str) -> Path:
    return report_path.parent / EXPANDED_BOUNDED_LIVE_CANARY_ATTEMPTS_DIR / attempt_id


def _expanded_bounded_live_canary_attempt_step_path(report_path: Path, attempt_id: str, step: int) -> Path:
    return _expanded_bounded_live_canary_attempt_dir(report_path, attempt_id) / f"step-{step}.txt"


def _expanded_bounded_live_canary_step_relpath(report_path: Path, attempt_id: str, step: int) -> str:
    return _expanded_bounded_live_canary_attempt_step_path(report_path, attempt_id, step).relative_to(report_path.parent.parent.parent).as_posix()


def _attempt_changed_files(changed_files: list[str], *, attempt_id: str) -> list[str]:
    attempt_prefix = (
        f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/"
        f"{EXPANDED_BOUNDED_LIVE_CANARY_ATTEMPTS_DIR}/{attempt_id}/"
    )
    return sorted([path for path in changed_files if path.startswith(attempt_prefix)])


def _ignored_old_expanded_canary_step_files(changed_files: list[str], *, attempt_id: str) -> list[str]:
    current_attempt_prefix = (
        f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/"
        f"{EXPANDED_BOUNDED_LIVE_CANARY_ATTEMPTS_DIR}/{attempt_id}/"
    )
    attempts_prefix = (
        f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/"
        f"{EXPANDED_BOUNDED_LIVE_CANARY_ATTEMPTS_DIR}/"
    )
    legacy_step_prefix = f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/step-"
    ignored: list[str] = []
    for path in changed_files:
        if path.startswith(attempts_prefix) and not path.startswith(current_attempt_prefix):
            ignored.append(path)
        elif path.startswith(legacy_step_prefix) and path.endswith(".txt"):
            ignored.append(path)
    return sorted(ignored)


def _expanded_bounded_live_canary_expected_content_matches(content: str, *, run_id: str, step: int) -> bool:
    required_lines = {
        "FactoryOS expanded bounded live canary completed",
        f"run_id={run_id}",
        f"step={step}",
        "bounded=true",
        "canary=true",
        "cost_aware=true",
        "no push",
        "no deploy",
        "no paid API",
        "no secrets",
    }
    return required_lines.issubset(set(content.splitlines()))


def _compact_execution_fields(
    *,
    context_category: str,
    model: str | None = None,
    reasoning: str | None = None,
    sandbox: str | None = None,
    approval: str | None = None,
    live: bool = False,
    quiet_runner_used: bool = False,
    quiet_runner_reason: str | None = None,
) -> dict[str, Any]:
    metadata = compact_exec_handoff_metadata(
        context_category=context_category,
        model=model,
        reasoning=reasoning,
        sandbox=sandbox,
        approval=approval,
        live=live,
    )
    metadata["quiet_runner_used"] = quiet_runner_used
    metadata["quiet_runner_reason"] = quiet_runner_reason or "quiet runner não utilizado neste fluxo."
    metadata["compact_exec_category"] = infer_compact_exec_category(
        context_category=context_category,
        live=live,
        factory_start=context_category in {"factory_start", "live_canary"},
    )
    return metadata


def _consolidate_factory_start_decision(
    *,
    status: str,
    executed_live: bool,
    evaluation_decision: str,
) -> tuple[str, str]:
    normalized_status = status.strip() or "blocked"
    normalized_evaluation = evaluation_decision.strip()

    if not normalized_evaluation:
        if executed_live:
            return normalized_status, normalized_status
        if normalized_status in {"passed", "dry_run_only", "needs_review", "blocked", "failed"}:
            return normalized_status, normalized_status
        return "needs_review", "needs_review"

    if executed_live:
        if normalized_status == "passed" and normalized_evaluation == "passed":
            return "passed", "passed"
        if normalized_evaluation in {"failed", "blocked", "needs_review"}:
            return normalized_evaluation, normalized_evaluation
        return normalized_status, normalized_status

    if normalized_evaluation in {"dry_run_only", "needs_review", "blocked", "failed"}:
        return normalized_evaluation, normalized_evaluation
    return "needs_review", "needs_review"


def _attach_evaluation(report: dict[str, Any], *, repo: Path) -> dict[str, Any]:
    evaluation = evaluate_execution(report_path=str(report["report_path"]), repo=repo)
    report["evaluation_report"] = str(evaluation.get("report_path", "")).strip()
    report["evaluation_decision"] = str(evaluation.get("decision", "")).strip()
    final_decision, final_status = _consolidate_factory_start_decision(
        status=str(report.get("status", "")).strip(),
        executed_live=bool(report.get("executed_live")),
        evaluation_decision=str(report.get("evaluation_decision", "")).strip(),
    )
    report["final_decision"] = final_decision
    report["final_status"] = final_status
    report["decision"] = final_decision
    return report


def _latest_cost_audit_summary(repo: Path) -> dict[str, Any]:
    latest = latest_report("codex-cost-audits", repo=repo)
    if latest is None:
        return {
            "available": False,
            "status": "missing",
            "report_path": "",
            "raw_global_tokens": None,
            "factoryos_forced_lean_tokens": None,
            "factoryos_repo_aware_tokens": None,
        }

    payload = latest.payload
    cases = {str(item.get("name")): item for item in payload.get("cases", []) if isinstance(item, dict)}
    classification = payload.get("classification", {})
    return {
        "available": True,
        "status": str(classification.get("status", "")).strip() or "missing",
        "report_path": latest.relative_path,
        "raw_global_tokens": cases.get("raw_global_minimal", {}).get("tokens_used"),
        "factoryos_forced_lean_tokens": cases.get("factoryos_forced_lean", {}).get("tokens_used"),
        "factoryos_repo_aware_tokens": cases.get("factoryos_repo_aware", {}).get("tokens_used"),
    }


def _maintenance_blockers(maintenance_plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if maintenance_plan.get("deleted_files") != "none":
        blockers.append("maintenance plan registrou deleted_files diferente de none.")
    if maintenance_plan.get("removed_worktrees") != "none":
        blockers.append("maintenance plan registrou removed_worktrees diferente de none.")
    return blockers


def _cost_aware_common(
    *,
    repo: Path,
    run_id: str,
    max_steps: int,
    target_minutes: int,
) -> dict[str, Any]:
    run = show_run(run_id, repo=repo)["run"]
    task = show_task(str(run["task_id"]), repo=repo)["task"]
    routing_contract = routing_contract_validation_payload(task=task, run=run)
    codex_plan = codex_plan_for_run(run_id, max_steps=max_steps, repo=repo)
    context_pack = context_pack_for_run(run_id, repo=repo)
    capsule_policy = policy_for_run(run_id, repo=repo)
    long_run_plan = run_factory_long_run_plan(
        run_id=run_id,
        target_minutes=target_minutes,
        max_steps=max_steps,
        repo=repo,
    )
    maintenance_plan = run_factory_maintenance_plan(repo=repo)
    cost_audit = _latest_cost_audit_summary(repo)
    latest_handoff = load_latest_handoff_result(repo)

    budget_status = str(codex_plan.get("budget_status", "blocked")).strip() or "blocked"
    context_status = str(context_pack.get("context_status", "blocked")).strip() or "blocked"
    token_target_status = str(cost_audit.get("status", "missing")).strip() or "missing"

    blockers: list[str] = []
    warnings: list[str] = []

    if not bool(routing_contract.get("valid", False)):
        blockers.extend([str(item) for item in routing_contract.get("reasons", []) if str(item).strip()])
    if budget_status != "ok":
        blockers.extend([str(item) for item in codex_plan.get("reasons", []) if str(item).strip()])
    if context_status != "ok":
        blockers.extend([str(item) for item in context_pack.get("reasons", []) if str(item).strip()])
    if not bool(long_run_plan.get("ok", False)):
        blockers.extend([str(item) for item in long_run_plan.get("blockers", []) if str(item).strip()])
    blockers.extend(_maintenance_blockers(maintenance_plan))
    if token_target_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"token_target_status={token_target_status} fora do nível aceito para cost-aware start.")

    warnings.extend([str(item) for item in routing_contract.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in codex_plan.get("warnings", []) if str(item).strip()])
    warnings.extend([str(item) for item in context_pack.get("warnings", []) if str(item).strip()])

    return {
        "run": run,
        "task": task,
        "routing_contract": routing_contract.get("routing_contract", {}),
        "routing_contract_validation": routing_contract,
        "codex_plan": codex_plan,
        "context_pack": context_pack,
        "capsule_execution_policy": capsule_policy,
        "long_run_plan": long_run_plan,
        "maintenance_plan": maintenance_plan,
        "cost_audit": cost_audit,
        "budget_status": budget_status,
        "context_status": context_status,
        "token_target_status": token_target_status,
        "blockers": blockers,
        "warnings": warnings,
        "global_config_dependency": False,
        "latest_handoff_report": latest_handoff.report_path if latest_handoff.available else "",
    }


def _write_cost_aware_report(
    *,
    repo: Path,
    run_id: str,
    mode: str,
    plan_only: bool,
    max_steps: int,
    target_minutes: int,
    common: dict[str, Any],
    final_status: str,
    final_decision: str,
    executed_live: bool,
    dry_run_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_path = _cost_aware_report_path(repo, run_id)
    payload = {
        "ok": final_status not in {"blocked", "failed"},
        "factory_start_version": FACTORY_START_VERSION,
        "cost_aware_version": FACTORY_START_COST_AWARE_VERSION,
        "run_id": run_id,
        "mode": mode,
        "plan_only": plan_only,
        "cost_aware": True,
        "routing_contract": common["routing_contract"],
        "codex_plan": common["codex_plan"],
        "context_pack": common["context_pack"],
        "long_run_plan_report": common["long_run_plan"].get("report_path", ""),
        "maintenance_plan_report": common["maintenance_plan"].get("report_path", ""),
        "budget_status": common["budget_status"],
        "context_status": common["context_status"],
        "token_target_status": common["token_target_status"],
        "global_config_dependency": False,
        "allowed_to_execute_live": False,
        "executed_live": executed_live,
        "final_status": final_status,
        "final_decision": final_decision,
        "blockers": common["blockers"],
        "warnings": common["warnings"],
        "next_gate_required": (
            "manual_review_before_future_live" if final_status in {"plan_only", "dry_run_only"}
            else "resolve_blockers_before_next_attempt"
        ),
        "target_minutes": target_minutes,
        "max_steps": max_steps,
        "routing_contract_validation": common["routing_contract_validation"],
        "cost_audit_report": common["cost_audit"].get("report_path", ""),
        "latest_handoff_report": common.get("latest_handoff_report", ""),
        "dry_run_report": "" if dry_run_report is None else dry_run_report.get("report_path", ""),
        "capsule_execution_policy": common["capsule_execution_policy"],
        "execution_mode_recommendation": common["capsule_execution_policy"]["execution_mode_recommendation"],
        "capsule_recommended": common["capsule_execution_policy"]["capsule_recommended"],
        "capsule_policy_decision": common["capsule_execution_policy"]["capsule_policy_decision"],
        "expected_savings_percent": common["capsule_execution_policy"]["expected_savings_percent"],
        "full_repo_required_reason": common["capsule_execution_policy"]["full_repo_required_reason"],
        "timeout_recovery_policy": common["capsule_execution_policy"]["timeout_recovery_policy"],
        "allowed_to_execute_live": common["capsule_execution_policy"]["allowed_to_execute_live"],
        "recommended_command_kind": common["capsule_execution_policy"]["recommended_command_kind"],
        **_compact_execution_fields(
            context_category="factory_start",
            model=str(common["codex_plan"].get("model", "")).strip() or None,
            reasoning=str(common["codex_plan"].get("reasoning_effort", "")).strip() or None,
            sandbox=str(common["codex_plan"].get("sandbox_mode", "")).strip() or None,
            approval=str(common["codex_plan"].get("approval_policy", "")).strip() or None,
            live=executed_live,
            quiet_runner_used=False,
            quiet_runner_reason="Factory Start cost-aware mantém o fluxo legado nesta sprint.",
        ),
        "report_path": report_path.relative_to(repo).as_posix(),
        "generated_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def _parse_changed_files_from_status(output: str) -> list[str]:
    changed: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip()
        if "->" in candidate:
            candidate = candidate.split("->", 1)[1].strip()
        if candidate:
            changed.append(candidate)
    return sorted(set(changed))


def _current_changed_files(repo: Path) -> list[str]:
    status_output = _git_optional(repo, "status", "--short", "--untracked-files=all") or ""
    if not status_output.strip():
        return []
    return _parse_changed_files_from_status(status_output)


def _build_live_canary_prompt(
    *,
    run_id: str,
    timestamp: str,
    step: int,
    max_steps: int,
    allowed_file: str,
) -> str:
    lines = [
        "Você está rodando dentro de um worktree isolado do FactoryOS.",
        "Execute um canário bounded de um único passo.",
        f"Passo atual: {step} de {max_steps}.",
        "Faça apenas isto:",
        f"- criar apenas {allowed_file}",
        "- escrever exatamente estes campos em texto simples:",
        "  FactoryOS bounded multi-step live canary completed",
        f"  run_id={run_id}",
        f"  step={step}",
        f"  timestamp={timestamp}",
        "  no deploy",
        "  no push",
        "  no paid API",
        "  no secrets",
        "- não editar nenhum outro arquivo",
        "- não instalar dependências",
        "- não usar rede",
        "- não usar API paga",
        "- não ler nem escrever secrets",
        "- não alterar config global",
        "- não fazer push",
        "- não fazer deploy",
        "- não fazer merge, rebase, fetch ou pull",
        "- não tocar em produção",
        "- ao final, mostrar git status --short",
        "",
        output_budget_contract_text().strip(),
    ]
    return "\n".join(lines) + "\n"


def _build_live_canary_command(workspace_path: str) -> list[str]:
    codex_plan = {
        "budget_status": "ok",
        "model": FACTORY_START_LIVE_CANARY_MODEL,
        "reasoning_effort": FACTORY_START_LIVE_CANARY_REASONING,
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "live": True,
    }
    return build_factoryos_codex_exec_command(
        codex_plan=codex_plan,
        context_pack={"context_status": "ok", "category": "factory_start_live_canary"},
        workspace_path=workspace_path,
        live=True,
        automated=True,
    )


def _build_bounded_live_canary_prompt(
    *,
    run_id: str,
    timestamp: str,
    step: int,
    allowed_file: str,
) -> str:
    lines = [
        "Você está em um worktree isolado do FactoryOS.",
        "Faça apenas isto:",
        f"- criar {allowed_file};",
        "- escrever run_id, step, timestamp, no deploy, no push, no paid API, no secrets, global_config_dependency=false;",
        "- não editar nenhum outro arquivo;",
        "- não instalar dependências;",
        "- não usar rede;",
        "- não usar API paga;",
        "- não ler nem escrever secrets;",
        "- não fazer deploy;",
        "- não alterar config global;",
        "- não fazer push;",
        "- ao final, mostrar git status --short e git log --oneline -3.",
        "",
        f"run_id: {run_id}",
        f"step: {step}",
        f"timestamp: {timestamp}",
        "",
        output_budget_contract_text().strip(),
    ]
    return "\n".join(lines) + "\n"


def _build_bounded_live_canary_command(workspace_path: str) -> list[str]:
    codex_plan = {
        "budget_status": "ok",
        "model": BOUNDED_LONG_RUN_LIVE_CANARY_MODEL,
        "reasoning_effort": BOUNDED_LONG_RUN_LIVE_CANARY_REASONING,
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "live": True,
    }
    return build_factoryos_codex_exec_command(
        codex_plan=codex_plan,
        context_pack={"context_status": "ok", "category": "bounded_long_run_live_canary"},
        workspace_path=workspace_path,
        live=True,
        automated=True,
    )


def _build_expanded_bounded_live_canary_prompt(
    *,
    run_id: str,
    timestamp: str,
    step: int,
    max_steps: int,
    allowed_file: str,
) -> str:
    lines = [
        "Você está em um worktree isolado do FactoryOS.",
        "Execute um canário bounded expandido, com um passo por execução.",
        f"Passo atual: {step} de {max_steps}.",
        "Faça apenas isto:",
        f"- criar apenas {allowed_file}",
        "- escrever exatamente estes campos em texto simples:",
        "  FactoryOS expanded bounded live canary completed",
        f"  run_id={run_id}",
        f"  step={step}",
        f"  timestamp={timestamp}",
        "  bounded=true",
        "  canary=true",
        "  cost_aware=true",
        "  no push",
        "  no deploy",
        "  no paid API",
        "  no secrets",
        "- não editar nenhum outro arquivo",
        "- não instalar dependências",
        "- não usar rede",
        "- não usar API paga",
        "- não ler nem escrever secrets",
        "- não alterar config global",
        "- não fazer push",
        "- não fazer deploy",
        "- não fazer merge, rebase, fetch ou pull",
        "- ao final, mostrar git status --short e git log --oneline -3",
        "",
        output_budget_contract_text().strip(),
    ]
    return "\n".join(lines) + "\n"


def _build_expanded_bounded_live_canary_command(workspace_path: str) -> list[str]:
    codex_plan = {
        "budget_status": "ok",
        "model": EXPANDED_BOUNDED_LIVE_CANARY_MODEL,
        "reasoning_effort": EXPANDED_BOUNDED_LIVE_CANARY_REASONING,
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "live": True,
    }
    return build_factoryos_codex_exec_command(
        codex_plan=codex_plan,
        context_pack={"context_status": "ok", "category": "expanded_bounded_live_canary"},
        workspace_path=workspace_path,
        live=True,
        automated=True,
    )


def _validate_live_canary_preconditions(run_id: str, *, repo: Path) -> dict[str, Any]:
    run = show_run(run_id, repo=repo)["run"]
    if run.get("status") != "running":
        raise TaskRunnerError("live canary requires run status running.")

    workspace_snapshot = workspace_status(run_id, repo=repo)["workspace"]
    if workspace_snapshot.get("kind") != "git_worktree" or not workspace_snapshot.get("is_worktree"):
        raise TaskRunnerError("live canary requires a git worktree workspace.")

    readiness = run_workspace_readiness(run_id, repo=repo)["workspace"]
    if readiness.get("status") != "ready":
        reasons = readiness.get("reasons", [])
        reason_text = "; ".join(str(item) for item in reasons) if isinstance(reasons, list) else "workspace não está ready."
        raise TaskRunnerError(f"live canary blocked: {reason_text}")

    sync_plan = run_workspace_sync_plan(run_id, repo=repo)["plan"]
    if sync_plan.get("status") != "already_current":
        reasons = sync_plan.get("reasons", [])
        reason_text = "; ".join(str(item) for item in reasons) if isinstance(reasons, list) else "sync plan não está already_current."
        raise TaskRunnerError(f"live canary blocked: {reason_text}")

    return {
        "run": run,
        "workspace": workspace_snapshot,
        "readiness": readiness,
        "sync_plan": sync_plan,
    }


def _validate_bounded_live_canary_preconditions(
    run_id: str,
    *,
    repo: Path,
    max_steps: int,
    target_minutes: int,
) -> dict[str, Any]:
    if os.environ.get(LIVE_CODEX_ENV) != "1":
        raise TaskRunnerError(f"live canary bloqueado; defina {LIVE_CODEX_ENV}=1 para permitir execução.")

    rehearsal = latest_valid_rehearsal_for_run(
        run_id,
        repo=repo,
        target_minutes=target_minutes,
        max_steps=max_steps,
    )
    if not rehearsal["ok"]:
        raise TaskRunnerError(f"bounded live canary bloqueado: {rehearsal['reason']}")

    validation = _validate_live_canary_preconditions(run_id, repo=repo)
    cost_audit = _latest_cost_audit_summary(repo)
    if str(cost_audit.get("status", "")).strip() not in {"ideal", "preferred_ok"}:
        raise TaskRunnerError("bounded live canary bloqueado por codex cost audit fora do nível aceito.")

    common = _cost_aware_common(
        repo=repo,
        run_id=run_id,
        max_steps=max_steps,
        target_minutes=target_minutes,
    )
    if common["budget_status"] != "ok":
        raise TaskRunnerError(f"bounded live canary bloqueado por budget_status={common['budget_status']}.")
    if common["context_status"] != "ok":
        raise TaskRunnerError(f"bounded live canary bloqueado por context_status={common['context_status']}.")
    if common["global_config_dependency"]:
        raise TaskRunnerError("bounded live canary bloqueado por dependência de config global.")

    return {
        **validation,
        "rehearsal": rehearsal,
        "cost_audit": cost_audit,
        "common": common,
    }


def _validate_expanded_bounded_live_canary_preconditions(
    run_id: str,
    *,
    repo: Path,
    max_steps: int,
    target_minutes: int,
) -> dict[str, Any]:
    if os.environ.get(LIVE_CODEX_ENV) != "1":
        raise TaskRunnerError(f"live canary bloqueado; defina {LIVE_CODEX_ENV}=1 para permitir execução.")

    return validate_expanded_bounded_live_canary_request(
        run_id,
        max_steps=max_steps,
        target_minutes=target_minutes,
        bounded=True,
        canary=True,
        cost_aware=True,
        no_push=True,
        no_deploy=True,
        no_paid_api=True,
        no_secrets=True,
        repo=repo,
    )


def _extract_hygiene_summary(
    *,
    audit_result: dict[str, Any],
    plan_result: dict[str, Any],
    loop_result: dict[str, Any],
) -> dict[str, int]:
    loop_hygiene = loop_result.get("hygiene", {})
    if isinstance(loop_hygiene, dict) and loop_hygiene:
        return {
            "running_tasks_count": int(loop_hygiene.get("running_tasks_count", 0)),
            "running_runs_count": int(loop_hygiene.get("running_runs_count", 0)),
            "safe_to_close_count": int(loop_hygiene.get("safe_to_close_count", 0)),
            "needs_review_count": int(loop_hygiene.get("needs_review_count", 0)),
            "blocked_count": int(loop_hygiene.get("blocked_count", 0)),
        }

    audit_stats = audit_result.get("stats", {})
    plan_stats = plan_result.get("stats", {})
    return {
        "running_tasks_count": int(audit_stats.get("running_tasks_count", 0)),
        "running_runs_count": int(audit_stats.get("running_runs_count", 0)),
        "safe_to_close_count": int(plan_stats.get("safe_to_close_count", 0)),
        "needs_review_count": int(plan_stats.get("needs_review_count", 0)),
        "blocked_count": int(plan_stats.get("blocked_count", 0)),
    }


def _loop_report_path_from_result(loop_result: dict[str, Any]) -> str:
    report_path = str(loop_result.get("report_path", "")).strip()
    if report_path:
        return report_path

    loop_id = str(loop_result.get("loop_id", "")).strip()
    if loop_id:
        return f"reports/factory-loops/{loop_id}.json"
    return ""


def _summarize_dry_run_steps(steps: list[dict[str, Any]]) -> tuple[str, str]:
    if not steps:
        return "blocked", "blocked"

    decisions = [str(step.get("decision", "")).strip() or "blocked" for step in steps]
    if "failed" in decisions:
        return "failed", "failed"
    if "blocked" in decisions:
        return "blocked", "blocked"
    if "needs_review" in decisions:
        return "needs_review", "needs_review"
    if all(decision == "dry_run_only" for decision in decisions):
        return "dry_run_only", "dry_run_only"
    return "needs_review", "needs_review"


def _run_factory_start_dry_run(
    run_id: str | None,
    *,
    max_steps: int,
    evaluate: bool,
    repo: Path,
) -> dict[str, Any]:
    validated_max_steps = _validate_max_steps(max_steps)
    normalized_run_id = _validate_run_id(run_id) if run_id is not None else None
    started_at = _now_iso()

    audit_result = factory_state_audit(repo=repo)
    plan_result = factory_state_plan(repo=repo)

    steps: list[dict[str, Any]] = []
    selected_run_id = ""
    last_loop_report = ""
    auto_selected = False
    eligible_runs_count = 0
    final_reasons: list[str] = []
    last_loop_result: dict[str, Any] = {}

    for step_number in range(1, validated_max_steps + 1):
        loop_result = run_controlled_loop(
            run_id=normalized_run_id,
            max_steps=1,
            dry_run=True,
            live=False,
            repo=repo,
        )
        last_loop_result = loop_result
        selected_run_id = selected_run_id or str(loop_result.get("run_id", "")).strip()
        auto_selected = auto_selected or bool(loop_result.get("auto_selected", False))
        eligible_runs_count = max(eligible_runs_count, int(loop_result.get("eligible_runs_count", 0)))
        last_loop_report = _loop_report_path_from_result(loop_result)

        step_status = str(loop_result.get("status", "blocked")).strip() or "blocked"
        step_decision = str(loop_result.get("decision", step_status)).strip() or step_status
        step_reasons = [str(item) for item in loop_result.get("reasons", []) if str(item).strip()]
        step_entry = {
            "step": step_number,
            "loop_report": last_loop_report,
            "status": step_status,
            "decision": step_decision,
            "executed_live": False,
            "reasons": step_reasons,
        }
        steps.append(step_entry)

        for reason in step_reasons:
            final_reasons.append(f"step {step_number}: {reason}")

        if step_decision != "dry_run_only":
            break

    run_token = selected_run_id or (normalized_run_id or "unresolved")
    start_id = _start_id(run_token, started_at=started_at)
    report_path = _report_path(repo, start_id)
    status, decision = _summarize_dry_run_steps(steps)
    if not final_reasons and status == "dry_run_only":
        final_reasons.append("multi-step dry-run executado; live continua bloqueado.")

    report = {
        "ok": all(bool(step.get("status")) for step in steps),
        "factory_start_version": FACTORY_START_VERSION,
        "mode": "dry-run",
        "start_id": start_id,
        "run_id": selected_run_id,
        "max_steps": validated_max_steps,
        "steps_requested": validated_max_steps,
        "steps_completed": len(steps),
        "status": status,
        "decision": decision,
        "loop_report": last_loop_report,
        "steps": steps,
        "hygiene_summary": _extract_hygiene_summary(
            audit_result=audit_result,
            plan_result=plan_result,
            loop_result=last_loop_result,
        ),
        "executed_live": False,
        "started_at": started_at,
        "finished_at": _now_iso(),
        "reasons": final_reasons,
        "audit_report": str(audit_result.get("report_path", "")).strip(),
        "plan_report": str(plan_result.get("report_path", "")).strip(),
        "auto_selected": auto_selected,
        "eligible_runs_count": eligible_runs_count,
        **_compact_execution_fields(
            context_category="factory_start",
            model=str(last_loop_result.get("model", "")).strip() or None,
            reasoning=str(last_loop_result.get("reasoning_effort", "")).strip() or None,
            sandbox="workspace-write",
            approval="on-request",
            live=False,
            quiet_runner_used=False,
            quiet_runner_reason="Dry-run não executa Codex; quiet runner recomendado para canários simples futuros.",
        ),
        "report_path": report_path.relative_to(repo).as_posix(),
        "evaluation_report": "",
        "evaluation_decision": "",
        "final_decision": decision,
        "final_status": status,
    }
    _write_json_atomic(report_path, report)
    if evaluate:
        report = _attach_evaluation(report, repo=repo)
        _write_json_atomic(report_path, report)
    return report


def _step_sidecar_path(report_path: Path, *, step: int, suffix: str) -> Path:
    return report_path.with_name(f"{report_path.stem}.step-{step}.{suffix}.txt")


def _run_live_canary_step(
    *,
    repo: Path,
    workspace_path: Path,
    command: list[str],
    report_path: Path,
    run_id: str,
    step: int,
    max_steps: int,
    allowed_file: str,
) -> tuple[dict[str, Any], str, str]:
    before_files = set(_current_changed_files(workspace_path))
    workspace_head_before = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    started_at = _now_iso()
    prompt = _build_live_canary_prompt(
        run_id=run_id,
        timestamp=started_at,
        step=step,
        max_steps=max_steps,
        allowed_file=allowed_file,
    )

    execution_error: str | None = None
    try:
        execution = execute_live_codex(
            command,
            cwd=repo,
            input_text=prompt,
            timeout_seconds=LIVE_CODEX_TIMEOUT_SECONDS,
        )
    except TaskRunnerError as exc:
        execution = None
        execution_error = str(exc)

    finished_at = _now_iso()
    stdout_text = execution.stdout if execution is not None else ""
    stderr_text = execution.stderr if execution is not None else (execution_error or "")
    stdout_path = _step_sidecar_path(report_path, step=step, suffix="stdout")
    stderr_path = _step_sidecar_path(report_path, step=step, suffix="stderr")
    _write_text_atomic(stdout_path, stdout_text)
    _write_text_atomic(stderr_path, stderr_text)

    after_files = set(_current_changed_files(workspace_path))
    workspace_head_after = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    changed_files = sorted(after_files - before_files)
    codex_exit_code = execution.returncode if execution is not None else 1
    status = "passed"
    reason = ""

    if codex_exit_code != 0:
        status = "failed"
        reason = f"codex exitou com código {codex_exit_code}."
    elif changed_files != [allowed_file]:
        status = "failed"
        reason = "alteração fora do arquivo permitido ou sem alteração registrada no step."

    step_result = {
        "step": step,
        "status": status,
        "decision": status,
        "executed_live": True,
        "allowed_file": allowed_file,
        "changed_files": changed_files,
        "codex_exit_code": codex_exit_code,
        "stdout_path": stdout_path.relative_to(repo).as_posix(),
        "stderr_path": stderr_path.relative_to(repo).as_posix(),
        "workspace_head_before": workspace_head_before,
        "workspace_head_after": workspace_head_after,
        "started_at": started_at,
        "finished_at": finished_at,
        "reason": reason,
    }
    return step_result, stdout_text, stderr_text


def _run_bounded_live_canary_step(
    *,
    repo: Path,
    workspace_path: Path,
    command: list[str],
    report_path: Path,
    run_id: str,
    step: int,
    allowed_file: str,
) -> tuple[dict[str, Any], str, str]:
    before_files = set(_current_changed_files(workspace_path))
    workspace_head_before = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    started_at = _now_iso()
    prompt = _build_bounded_live_canary_prompt(
        run_id=run_id,
        timestamp=started_at,
        step=step,
        allowed_file=allowed_file,
    )

    execution_error: str | None = None
    try:
        execution = execute_live_codex(
            command,
            cwd=repo,
            input_text=prompt,
            timeout_seconds=LIVE_CODEX_TIMEOUT_SECONDS,
        )
    except TaskRunnerError as exc:
        execution = None
        execution_error = str(exc)

    finished_at = _now_iso()
    stdout_text = execution.stdout if execution is not None else ""
    stderr_text = execution.stderr if execution is not None else (execution_error or "")
    stdout_path = _step_sidecar_path(report_path, step=step, suffix="stdout")
    stderr_path = _step_sidecar_path(report_path, step=step, suffix="stderr")
    _write_text_atomic(stdout_path, stdout_text)
    _write_text_atomic(stderr_path, stderr_text)

    after_files = set(_current_changed_files(workspace_path))
    workspace_head_after = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    changed_files = sorted(after_files - before_files)
    codex_exit_code = execution.returncode if execution is not None else 1
    status = "passed"
    reason = ""

    if codex_exit_code != 0:
        status = "failed"
        reason = f"codex exitou com código {codex_exit_code}."
    elif changed_files != [allowed_file]:
        status = "failed"
        reason = "alteração fora do arquivo permitido ou sem alteração registrada no step."

    step_result = {
        "step": step,
        "status": status,
        "decision": status,
        "executed_live": True,
        "allowed_file": allowed_file,
        "changed_files": changed_files,
        "codex_exit_code": codex_exit_code,
        "stdout_path": stdout_path.relative_to(repo).as_posix(),
        "stderr_path": stderr_path.relative_to(repo).as_posix(),
        "workspace_head_before": workspace_head_before,
        "workspace_head_after": workspace_head_after,
        "started_at": started_at,
        "finished_at": finished_at,
        "reason": reason,
    }
    return step_result, stdout_text, stderr_text


def _run_expanded_bounded_live_canary_step(
    *,
    repo: Path,
    workspace_path: Path,
    command: list[str],
    report_path: Path,
    attempt_id: str,
    run_id: str,
    step: int,
    max_steps: int,
    allowed_file: str,
) -> tuple[dict[str, Any], str, str]:
    before_files = set(_current_changed_files(workspace_path))
    workspace_head_before = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    started_at = _now_iso()
    prompt = _build_expanded_bounded_live_canary_prompt(
        run_id=run_id,
        timestamp=started_at,
        step=step,
        max_steps=max_steps,
        allowed_file=allowed_file,
    )

    execution_error: str | None = None
    try:
        execution = execute_live_codex(
            command,
            cwd=repo,
            input_text=prompt,
            timeout_seconds=LIVE_CODEX_TIMEOUT_SECONDS,
        )
    except TaskRunnerError as exc:
        execution = None
        execution_error = str(exc)

    finished_at = _now_iso()
    stdout_text = execution.stdout if execution is not None else ""
    stderr_text = execution.stderr if execution is not None else (execution_error or "")
    after_files = set(_current_changed_files(workspace_path))
    workspace_head_after = _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    changed_files = sorted(after_files - before_files)
    attempt_changed_files = _attempt_changed_files(changed_files, attempt_id=attempt_id)
    disallowed_step_files = sorted(path for path in changed_files if path not in {allowed_file})
    codex_exit_code = execution.returncode if execution is not None else 1
    status = "passed"
    reason = ""
    expected_step_file = allowed_file
    expected_step_path = workspace_path / expected_step_file
    expected_file_exists = expected_step_path.exists() and expected_step_path.is_file() and not expected_step_path.is_symlink()
    expected_content_matches = False
    if expected_file_exists:
        expected_content_matches = _expanded_bounded_live_canary_expected_content_matches(
            expected_step_path.read_text(encoding="utf-8", errors="replace"),
            run_id=run_id,
            step=step,
        )

    if codex_exit_code != 0:
        status = "failed"
        reason = f"codex exitou com código {codex_exit_code}."
    elif not expected_file_exists:
        status = "failed"
        reason = "arquivo esperado do step não foi criado."
    elif not expected_content_matches:
        status = "failed"
        reason = "arquivo esperado do step não contém o conteúdo obrigatório."
    elif expected_step_file not in attempt_changed_files:
        status = "failed"
        reason = "arquivo esperado do step não está na whitelist da tentativa."
    elif len(attempt_changed_files) != 1 or disallowed_step_files:
        status = "failed"
        reason = "há arquivos fora da whitelist da tentativa atual."

    step_result = {
        "step": step,
        "status": status,
        "decision": status,
        "executed_live": True,
        "attempt_id": attempt_id,
        "allowed_file": allowed_file,
        "expected_step_file": expected_step_file,
        "expected_file_exists": expected_file_exists,
        "expected_content_matches": expected_content_matches,
        "changed_files": attempt_changed_files,
        "global_changed_files": changed_files,
        "disallowed_files": disallowed_step_files,
        "codex_exit_code": codex_exit_code,
        "stdout_path": "",
        "stderr_path": "",
        "workspace_head_before": workspace_head_before,
        "workspace_head_after": workspace_head_after,
        "started_at": started_at,
        "finished_at": finished_at,
        "reason": reason,
    }
    return step_result, stdout_text, stderr_text


def run_factory_start_live_canary(
    run_id: str | None,
    *,
    max_steps: int,
    canary: bool,
    evaluate: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not canary:
        raise TaskRunnerError("live canary multi-step exige --canary.")
    if not evaluate:
        raise TaskRunnerError("live canary multi-step exige --evaluate.")
    if run_id is None:
        raise TaskRunnerError("live canary multi-step exige --run-id explícito.")
    normalized_run_id = _validate_run_id(run_id)
    validated_max_steps = _validate_live_canary_max_steps(max_steps)
    if os.environ.get(LIVE_CODEX_ENV) != "1":
        raise TaskRunnerError(f"live canary bloqueado; defina {LIVE_CODEX_ENV}=1 para permitir execução.")

    repo = repo or repo_root()
    validation = _validate_live_canary_preconditions(normalized_run_id, repo=repo)
    run = validation["run"]
    workspace_snapshot = validation["workspace"]

    workspace_path = repo / str(run["workspace_path"])
    workspace_branch = workspace_snapshot.get("branch")
    master_head_before = _git(repo, "rev-parse", "HEAD")
    workspace_head_before = workspace_snapshot.get("workspace_head") or _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    created_at = _now_iso()
    report_path = _live_canary_report_path(repo, normalized_run_id, created_at=created_at)
    command = _build_live_canary_command(str(workspace_path))
    allowed_files = list(FACTORY_START_LIVE_CANARY_ALLOWED_FILES[:validated_max_steps])

    steps: list[dict[str, Any]] = []
    stdout_blocks: list[str] = []
    stderr_blocks: list[str] = []
    for step_number, allowed_file in enumerate(allowed_files, start=1):
        step_result, stdout_text, stderr_text = _run_live_canary_step(
            repo=repo,
            workspace_path=workspace_path,
            command=command,
            report_path=report_path,
            run_id=normalized_run_id,
            step=step_number,
            max_steps=validated_max_steps,
            allowed_file=allowed_file,
        )
        steps.append(step_result)
        stdout_blocks.append(f"== step {step_number} ==\n{stdout_text}".rstrip() + "\n")
        stderr_blocks.append(f"== step {step_number} ==\n{stderr_text}".rstrip() + "\n")
        if step_result["status"] != "passed":
            break

    stdout_path = report_path.with_suffix(".stdout.txt")
    stderr_path = report_path.with_suffix(".stderr.txt")
    _write_text_atomic(stdout_path, "".join(stdout_blocks))
    _write_text_atomic(stderr_path, "".join(stderr_blocks))

    master_head_after = _git(repo, "rev-parse", "HEAD")
    workspace_after = workspace_status(normalized_run_id, repo=repo)["workspace"]
    workspace_head_after = workspace_after.get("workspace_head") or ""
    finished_at = _now_iso()
    try:
        duration_seconds = max(
            0.0,
            (
                datetime.fromisoformat(finished_at)
                - datetime.fromisoformat(created_at)
            ).total_seconds(),
        )
    except ValueError:
        duration_seconds = None
    changed_files = _current_changed_files(workspace_path)
    allowed_files_changed = bool(changed_files) and set(changed_files).issubset(set(allowed_files))
    codex_exit_codes = [int(step["codex_exit_code"]) for step in steps]
    codex_exit_code = 0 if steps and all(code == 0 for code in codex_exit_codes) else next(
        (code for code in codex_exit_codes if code != 0),
        1,
    )
    status = "passed"
    reason = ""

    if not steps:
        status = "failed"
        reason = "nenhum step live foi executado."
    elif any(step["status"] != "passed" for step in steps):
        status = "failed"
        failed_step = next(step for step in steps if step["status"] != "passed")
        reason = str(failed_step.get("reason", "")).strip() or "step live falhou."
    elif len(steps) != validated_max_steps:
        status = "failed"
        reason = "nem todos os steps solicitados foram concluídos."
    elif master_head_after != master_head_before:
        status = "failed"
        reason = "master foi alterado durante o live canary."
    elif sorted(changed_files) != sorted(allowed_files):
        status = "failed"
        reason = "changed_files final não corresponde exatamente aos arquivos canary permitidos."

    branch_commit = workspace_head_after if workspace_head_after and workspace_head_after != workspace_head_before else None
    report = {
        "ok": status == "passed",
        "factory_start_version": FACTORY_START_VERSION,
        "mode": "live-canary",
        "status": status,
        "decision": status,
        "reason": reason,
        "executed_live": True,
        "canary_run_id": normalized_run_id,
        "canary_task_id": run["task_id"],
        "run_id": normalized_run_id,
        "task_id": run["task_id"],
        "max_steps": validated_max_steps,
        "steps_requested": validated_max_steps,
        "steps_completed": len(steps),
        "steps": steps,
        "workspace_path": run["workspace_path"],
        "workspace_branch": workspace_branch,
        "master_head_before": master_head_before,
        "master_head_after": master_head_after,
        "workspace_head_before": str(workspace_head_before),
        "workspace_head_after": str(workspace_head_after),
        "allowed_files": allowed_files,
        "allowed_files_changed": allowed_files_changed,
        "changed_files": changed_files,
        "canary_file": allowed_files[0],
        "codex_exit_code": codex_exit_code,
        "codex_exit_codes": codex_exit_codes,
        "stdout_path": stdout_path.relative_to(repo).as_posix(),
        "stderr_path": stderr_path.relative_to(repo).as_posix(),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "created_at": created_at,
        "finished_at": _now_iso(),
        "branch_commit": branch_commit,
        "readiness_status": validation["readiness"].get("status"),
        "sync_plan_status": validation["sync_plan"].get("status"),
        "codex_command": command,
        "uses_ignore_user_config": "--ignore-user-config" in command,
        "uses_ephemeral": "--ephemeral" in command,
        "approval_policy": "never",
        "sandbox_mode": "workspace-write",
        "source_of_truth": "codex_plan",
        "global_config_dependency": False,
        "report_path": report_path.relative_to(repo).as_posix(),
        "evaluation_report": "",
        "evaluation_decision": "",
        "final_decision": status,
        "final_status": status,
    }
    _write_json_atomic(report_path, report)
    report = _attach_evaluation(report, repo=repo)
    _write_json_atomic(report_path, report)
    return report


def run_bounded_long_run_live_canary(
    run_id: str,
    *,
    max_steps: int,
    target_minutes: int,
    canary: bool,
    evaluate: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not canary:
        raise TaskRunnerError("bounded long run live canary exige --canary.")
    if not evaluate:
        raise TaskRunnerError("bounded long run live canary exige --evaluate.")

    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    validated_max_steps = _validate_bounded_live_canary_max_steps(max_steps)
    validated_target_minutes = _validate_bounded_live_canary_target_minutes(target_minutes)
    validation = _validate_bounded_live_canary_preconditions(
        normalized_run_id,
        repo=repo,
        max_steps=validated_max_steps,
        target_minutes=validated_target_minutes,
    )
    run = validation["run"]
    workspace_snapshot = validation["workspace"]
    workspace_path = repo / str(run["workspace_path"])
    workspace_branch = workspace_snapshot.get("branch")
    master_head_before = _git(repo, "rev-parse", "HEAD")
    workspace_head_before = workspace_snapshot.get("workspace_head") or _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    created_at = _now_iso()
    report_path = _bounded_live_canary_report_path(repo, normalized_run_id, created_at=created_at)
    command = _build_bounded_live_canary_command(str(workspace_path))
    allowed_files = list(BOUNDED_LONG_RUN_LIVE_CANARY_ALLOWED_FILES[:validated_max_steps])

    steps: list[dict[str, Any]] = []
    stdout_blocks: list[str] = []
    stderr_blocks: list[str] = []
    for step_number, allowed_file in enumerate(allowed_files, start=1):
        step_result, stdout_text, stderr_text = _run_bounded_live_canary_step(
            repo=repo,
            workspace_path=workspace_path,
            command=command,
            report_path=report_path,
            run_id=normalized_run_id,
            step=step_number,
            allowed_file=allowed_file,
        )
        steps.append(step_result)
        stdout_blocks.append(f"== step {step_number} ==\n{stdout_text}".rstrip() + "\n")
        stderr_blocks.append(f"== step {step_number} ==\n{stderr_text}".rstrip() + "\n")
        if step_result["status"] != "passed":
            break

    stdout_path = report_path.with_suffix(".stdout.txt")
    stderr_path = report_path.with_suffix(".stderr.txt")
    _write_text_atomic(stdout_path, "".join(stdout_blocks))
    _write_text_atomic(stderr_path, "".join(stderr_blocks))

    master_head_after = _git(repo, "rev-parse", "HEAD")
    workspace_after = workspace_status(normalized_run_id, repo=repo)["workspace"]
    workspace_head_after = workspace_after.get("workspace_head") or ""
    changed_files = _current_changed_files(workspace_path)
    disallowed_files = sorted(set(changed_files) - set(allowed_files))
    allowed_files_changed = not disallowed_files and sorted(changed_files) == sorted(allowed_files)
    codex_exit_codes = [int(step["codex_exit_code"]) for step in steps]
    final_decision = "passed"
    blockers: list[str] = []
    warnings: list[str] = []

    if len(steps) != validated_max_steps:
        final_decision = "failed"
        blockers.append("nem todos os steps solicitados foram concluídos.")
    if any(code != 0 for code in codex_exit_codes):
        final_decision = "failed"
        blockers.append("codex_exit_codes contém falhas.")
    if disallowed_files:
        final_decision = "failed"
        blockers.append("arquivos fora da whitelist foram alterados.")
    if sorted(changed_files) != sorted(allowed_files):
        final_decision = "failed"
        blockers.append("changed_files final não corresponde exatamente aos arquivos permitidos.")
    if master_head_before != master_head_after:
        final_decision = "failed"
        blockers.append("master foi alterado durante o live canary.")

    report = {
        "ok": final_decision == "passed",
        "canary_version": "v0",
        "factory_start_version": FACTORY_START_VERSION,
        "mode": "bounded-live-canary",
        "status": final_decision,
        "decision": final_decision,
        "run_id": normalized_run_id,
        "canary_run_id": normalized_run_id,
        "canary_task_id": run["task_id"],
        "task_id": run["task_id"],
        "target_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "steps_completed": len(steps),
        "executed_live": True,
        "codex_exit_codes": codex_exit_codes,
        "changed_files": changed_files,
        "allowed_files": allowed_files,
        "allowed_files_changed": allowed_files_changed,
        "disallowed_files": disallowed_files,
        "master_head_before": master_head_before,
        "master_head_after": master_head_after,
        "workspace_head_before": str(workspace_head_before),
        "workspace_head_after": str(workspace_head_after),
        "workspace_path": run["workspace_path"],
        "workspace_branch": workspace_branch,
        "global_config_dependency": False,
        "cost_audit_report": validation["cost_audit"].get("report_path", ""),
        "rehearsal_report": validation["rehearsal"].get("report_path", ""),
        "evaluation_report": "",
        "evaluation_decision": "",
        "final_decision": final_decision,
        "final_status": final_decision,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "blockers": blockers,
        "warnings": warnings,
        **_compact_execution_fields(
            context_category="live_canary",
            model=FACTORY_START_LIVE_CANARY_MODEL,
            reasoning=FACTORY_START_LIVE_CANARY_REASONING,
            sandbox="workspace-write",
            approval="never",
            live=True,
            quiet_runner_used=False,
            quiet_runner_reason="Live canary V0 ainda usa o fluxo legado; quiet runner fica recomendado para canários simples futuros.",
        ),
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": created_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "readiness_status": validation["readiness"].get("status"),
        "sync_plan_status": validation["sync_plan"].get("status"),
        "codex_command": command,
        "uses_ignore_user_config": "--ignore-user-config" in command,
        "uses_ephemeral": "--ephemeral" in command,
        "approval_policy": "never",
        "sandbox_mode": "workspace-write",
    }
    _write_json_atomic(report_path, report)
    report = _attach_evaluation(report, repo=repo)
    if report.get("final_decision") != "passed":
        report["ok"] = False
    _write_json_atomic(report_path, report)
    return report


def run_expanded_bounded_live_canary(
    run_id: str,
    *,
    max_steps: int,
    target_minutes: int,
    bounded: bool,
    canary: bool,
    cost_aware: bool,
    no_push: bool,
    no_deploy: bool,
    no_paid_api: bool,
    no_secrets: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    validation = validate_expanded_bounded_live_canary_request(
        normalized_run_id,
        max_steps=max_steps,
        target_minutes=target_minutes,
        bounded=bounded,
        canary=canary,
        cost_aware=cost_aware,
        no_push=no_push,
        no_deploy=no_deploy,
        no_paid_api=no_paid_api,
        no_secrets=no_secrets,
        repo=repo,
    )
    normalized_validation = _normalize_expanded_canary_validation(
        validation,
        run_id=normalized_run_id,
        repo=repo,
    )
    validated_max_steps = int(normalized_validation["max_steps"])
    validated_target_minutes = int(normalized_validation["target_minutes"])
    run = normalized_validation["run"]
    workspace_snapshot = normalized_validation["workspace"]
    workspace_path = repo / str(run["workspace_path"])
    workspace_branch = workspace_snapshot.get("branch")
    master_head_before = _git(repo, "rev-parse", "HEAD")
    workspace_head_before = workspace_snapshot.get("workspace_head") or _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    created_at = _now_iso()
    report_path = _expanded_bounded_live_canary_report_path(repo, normalized_run_id, created_at=created_at)
    attempt_id = f"{normalized_run_id}-{datetime.fromisoformat(created_at).strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}"
    command = _build_expanded_bounded_live_canary_command(str(workspace_path))
    if normalized_validation["blockers"]:
        finished_at = _now_iso()
        report = {
            "ok": False,
            "factory_start_version": FACTORY_START_VERSION,
            "canary_version": "v0",
            "mode": "expanded-bounded-live-canary",
            "status": "blocked",
            "decision": "blocked",
            "run_id": normalized_run_id,
            "canary_run_id": normalized_run_id,
            "canary_task_id": run["task_id"],
            "task_id": run["task_id"],
            "target_minutes": validated_target_minutes,
            "max_minutes": validated_target_minutes,
            "max_steps": validated_max_steps,
            "steps_completed": 0,
            "executed_live": False,
            "codex_exit_codes": [],
            "codex_or_capsule_runs": [],
            "token_summary": {},
            "changed_files": [],
            "allowed_files": [],
            "allowed_files_changed": False,
            "disallowed_files": [],
            "master_head_before": master_head_before,
            "master_head_after": master_head_before,
            "workspace_head_before": str(workspace_head_before),
            "workspace_head_after": str(workspace_head_before),
            "workspace_path": run["workspace_path"],
            "workspace_branch": workspace_branch,
            "global_config_dependency": False,
            "cost_audit_report": normalized_validation["cost_audit"].get("report_path", ""),
            "rehearsal_report": normalized_validation["rehearsal"].get("report_path", ""),
            "review_gate_report": normalized_validation["review_gate"].get("report_path", ""),
            "evaluation_report": "",
            "evaluation_decision": "",
            "final_decision": "blocked",
            "final_status": "blocked",
            "no_push": True,
            "no_deploy": True,
            "no_paid_api": True,
            "no_secrets": True,
            "blockers": list(normalized_validation["blockers"]),
            "warnings": list(normalized_validation["warnings"]),
            **_compact_execution_fields(
                context_category="expanded_bounded_live_canary",
                model=EXPANDED_BOUNDED_LIVE_CANARY_MODEL,
                reasoning=EXPANDED_BOUNDED_LIVE_CANARY_REASONING,
                sandbox="workspace-write",
                approval="never",
                live=False,
                quiet_runner_used=False,
                quiet_runner_reason="Canário expandido bloqueado antes da execução por normalização estrutural.",
            ),
            "report_path": report_path.relative_to(repo).as_posix(),
            "created_at": created_at,
            "finished_at": finished_at,
            "duration_seconds": 0.0,
            "readiness_status": normalized_validation["readiness_status"],
            "sync_plan_status": normalized_validation["sync_plan_status"],
            "codex_command": command,
            "uses_ignore_user_config": "--ignore-user-config" in command,
            "uses_ephemeral": "--ephemeral" in command,
            "approval_policy": "never",
            "sandbox_mode": "workspace-write",
        }
        _write_json_atomic(report_path, report)
        return report
    attempt_allowed_files = [
        _expanded_bounded_live_canary_step_relpath(report_path, attempt_id, step_number)
        for step_number in range(1, validated_max_steps + 1)
    ]
    attempt_dir = _expanded_bounded_live_canary_attempt_dir(report_path, attempt_id).relative_to(repo).as_posix()
    initial_global_changed_files = _current_changed_files(workspace_path)
    initial_ignored_old_step_files = _ignored_old_expanded_canary_step_files(
        initial_global_changed_files,
        attempt_id=attempt_id,
    )
    deadline_seconds = float(validated_target_minutes * 60)
    started_monotonic = time.monotonic()
    deadline_exceeded = False

    steps: list[dict[str, Any]] = []
    stdout_blocks: list[str] = []
    stderr_blocks: list[str] = []
    for step_number in range(1, validated_max_steps + 1):
        allowed_file = attempt_allowed_files[step_number - 1]
        if time.monotonic() - started_monotonic > deadline_seconds:
            deadline_exceeded = True
            steps.append({
                "step": step_number,
                "status": "failed",
                "decision": "failed",
                "executed_live": False,
                "allowed_file": allowed_file,
                "changed_files": [],
                "codex_exit_code": 124,
                "stdout_path": "",
                "stderr_path": "",
                "workspace_head_before": "",
                "workspace_head_after": "",
                "started_at": _now_iso(),
                "finished_at": _now_iso(),
                "reason": "tempo máximo do canário expandido excedido antes do step.",
            })
            break
        step_result, stdout_text, stderr_text = _run_expanded_bounded_live_canary_step(
            repo=repo,
            workspace_path=workspace_path,
            command=command,
            report_path=report_path,
            attempt_id=attempt_id,
            run_id=normalized_run_id,
            step=step_number,
            max_steps=validated_max_steps,
            allowed_file=allowed_file,
        )
        steps.append(step_result)
        stdout_blocks.append(f"== step {step_number} ==\n{stdout_text}".rstrip() + "\n")
        stderr_blocks.append(f"== step {step_number} ==\n{stderr_text}".rstrip() + "\n")
        if step_result["status"] != "passed":
            break
        if time.monotonic() - started_monotonic > deadline_seconds:
            deadline_exceeded = True
            break

    stdout_path = report_path.with_suffix(".stdout.txt")
    stderr_path = report_path.with_suffix(".stderr.txt")
    _write_text_atomic(stdout_path, "".join(stdout_blocks))
    _write_text_atomic(stderr_path, "".join(stderr_blocks))

    master_head_after = _git(repo, "rev-parse", "HEAD")
    workspace_after = workspace_status(normalized_run_id, repo=repo)["workspace"]
    workspace_head_after = workspace_after.get("workspace_head") or ""
    global_changed_files = _current_changed_files(workspace_path)
    new_global_changed_files = sorted(set(global_changed_files) - set(initial_global_changed_files))
    attempt_changed_files = _attempt_changed_files(global_changed_files, attempt_id=attempt_id)
    ignored_old_step_files = _ignored_old_expanded_canary_step_files(global_changed_files, attempt_id=attempt_id)
    disallowed_files = sorted(path for path in new_global_changed_files if path not in set(attempt_allowed_files))
    allowed_files_changed = not disallowed_files and sorted(attempt_changed_files) == sorted(attempt_allowed_files)
    codex_exit_codes = [int(step["codex_exit_code"]) for step in steps]
    token_summary = parse_token_usage_text("\n".join(stdout_blocks + stderr_blocks))
    token_summary_ok = token_summary.get("tokens_used") is not None and int(token_summary["tokens_used"]) <= 50000
    final_decision = "passed"
    blockers: list[str] = []
    warnings: list[str] = list(normalized_validation["warnings"])
    if initial_ignored_old_step_files or ignored_old_step_files:
        warnings.append("arquivos de step antigos foram ignorados para isolar a tentativa atual.")

    if normalized_validation["blockers"]:
        final_decision = "blocked"
        blockers.extend(normalized_validation["blockers"])

    if len(steps) != validated_max_steps:
        final_decision = "failed"
        blockers.append("nem todos os steps solicitados foram concluídos.")
    if any(code != 0 for code in codex_exit_codes):
        final_decision = "failed"
        blockers.append("codex_exit_codes contém falhas.")
    if disallowed_files:
        final_decision = "failed"
        blockers.append("arquivos fora da whitelist foram alterados.")
    if sorted(attempt_changed_files) != sorted(attempt_allowed_files):
        final_decision = "failed"
        blockers.append("changed_files final da tentativa não corresponde exatamente aos arquivos permitidos.")
    if master_head_before != master_head_after:
        final_decision = "failed"
        blockers.append("master foi alterado durante o live canary.")
    if deadline_exceeded:
        final_decision = "failed"
        blockers.append("tempo máximo do canário expandido excedido.")
    if not token_summary_ok:
        final_decision = "needs_review" if final_decision == "passed" else final_decision
        warnings.append("token_summary ausente ou acima do limite razoável.")

    if final_decision == "blocked":
        warnings.append("execução live não iniciada por bloqueio estrutural.")

    finished_at = _now_iso()
    try:
        duration_seconds = max(
            0.0,
            (
                datetime.fromisoformat(finished_at)
                - datetime.fromisoformat(created_at)
            ).total_seconds(),
        )
    except ValueError:
        duration_seconds = None

    report = {
        "ok": final_decision == "passed",
        "factory_start_version": FACTORY_START_VERSION,
        "canary_version": "v0",
        "mode": "expanded-bounded-live-canary",
        "status": final_decision,
        "decision": final_decision,
        "run_id": normalized_run_id,
        "canary_run_id": normalized_run_id,
        "canary_task_id": run["task_id"],
        "task_id": run["task_id"],
        "target_minutes": validated_target_minutes,
        "max_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "attempt_id": attempt_id,
        "attempt_dir": attempt_dir,
        "steps_completed": len(steps),
        "executed_live": final_decision == "passed",
        "codex_exit_codes": codex_exit_codes,
        "codex_or_capsule_runs": steps,
        "token_summary": token_summary,
        "changed_files": attempt_changed_files,
        "allowed_files": attempt_allowed_files,
        "allowed_files_changed": allowed_files_changed,
        "disallowed_files": disallowed_files,
        "global_changed_files": global_changed_files,
        "ignored_old_step_files": ignored_old_step_files,
        "master_head_before": master_head_before,
        "master_head_after": master_head_after,
        "workspace_head_before": str(workspace_head_before),
        "workspace_head_after": str(workspace_head_after),
        "workspace_path": run["workspace_path"],
        "workspace_branch": workspace_branch,
        "global_config_dependency": False,
        "cost_audit_report": normalized_validation["cost_audit"].get("report_path", ""),
        "rehearsal_report": normalized_validation["rehearsal"].get("report_path", ""),
        "review_gate_report": normalized_validation["review_gate"].get("report_path", ""),
        "evaluation_report": "",
        "evaluation_decision": "",
        "final_decision": final_decision,
        "final_status": final_decision,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "blockers": blockers,
        "warnings": warnings,
        **_compact_execution_fields(
            context_category="expanded_bounded_live_canary",
            model=EXPANDED_BOUNDED_LIVE_CANARY_MODEL,
            reasoning=EXPANDED_BOUNDED_LIVE_CANARY_REASONING,
            sandbox="workspace-write",
            approval="never",
            live=True,
            quiet_runner_used=False,
            quiet_runner_reason="Canário expandido continua seguindo o fluxo legado até a 058.",
        ),
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": created_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "readiness_status": normalized_validation["readiness_status"],
        "sync_plan_status": normalized_validation["sync_plan_status"],
        "codex_command": command,
        "uses_ignore_user_config": "--ignore-user-config" in command,
        "uses_ephemeral": "--ephemeral" in command,
        "approval_policy": "never",
        "sandbox_mode": "workspace-write",
    }
    _write_json_atomic(report_path, report)

    from app.post_expansion_evaluator import evaluate_post_expansion_canary_report

    if report["final_decision"] != "blocked":
        evaluation = evaluate_post_expansion_canary_report(report_path=str(report_path.relative_to(repo).as_posix()), repo=repo)
        report["evaluation_report"] = str(evaluation.get("report_path", "")).strip()
        report["evaluation_decision"] = str(evaluation.get("decision", "")).strip()
        if report["evaluation_decision"] and report["evaluation_decision"] != "passed":
            report["final_decision"] = report["evaluation_decision"]
            report["final_status"] = report["evaluation_decision"]
            report["decision"] = report["evaluation_decision"]
            report["ok"] = False
        _write_json_atomic(report_path, report)
    return report


def run_factory_start(
    run_id: str | None = None,
    *,
    max_steps: int = 1,
    target_minutes: int = 30,
    dry_run: bool = True,
    live: bool = False,
    plan_only: bool = False,
    cost_aware: bool = False,
    canary: bool = False,
    evaluate: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    if cost_aware:
        if run_id is None:
            raise TaskRunnerError("Cost-Aware Factory Start V0 exige --run-id explícito.")
        normalized_run_id = _validate_run_id(run_id)
        if live:
            return run_bounded_long_run_live_canary(
                normalized_run_id,
                max_steps=max_steps,
                target_minutes=target_minutes,
                canary=canary,
                evaluate=evaluate,
                repo=repo,
            )
        common = _cost_aware_common(
            repo=repo,
            run_id=normalized_run_id,
            max_steps=max_steps,
            target_minutes=target_minutes,
        )
        if plan_only:
            final_status = "blocked" if common["blockers"] else "plan_only"
            final_decision = "blocked" if common["blockers"] else "plan_only"
            return _write_cost_aware_report(
                repo=repo,
                run_id=normalized_run_id,
                mode="plan-only",
                plan_only=True,
                max_steps=max_steps,
                target_minutes=target_minutes,
                common=common,
                final_status=final_status,
                final_decision=final_decision,
                executed_live=False,
            )
        if not dry_run:
            raise TaskRunnerError("Cost-Aware Factory Start V0 exige --dry-run ou --plan-only.")
        if common["blockers"]:
            return _write_cost_aware_report(
                repo=repo,
                run_id=normalized_run_id,
                mode="dry-run",
                plan_only=False,
                max_steps=max_steps,
                target_minutes=target_minutes,
                common=common,
                final_status="blocked",
                final_decision="blocked",
                executed_live=False,
            )
        dry_run_result = _run_factory_start_dry_run(
            normalized_run_id,
            max_steps=max_steps,
            evaluate=evaluate,
            repo=repo,
        )
        dry_run_decision = str(dry_run_result.get("final_decision", "")).strip() or str(dry_run_result.get("decision", "needs_review")).strip()
        if dry_run_decision == "dry_run_only":
            final_status = "dry_run_only"
            final_decision = "dry_run_only"
        else:
            final_status = "needs_review"
            final_decision = "needs_review"
        return _write_cost_aware_report(
            repo=repo,
            run_id=normalized_run_id,
            mode="dry-run",
            plan_only=False,
            max_steps=max_steps,
            target_minutes=target_minutes,
            common=common,
            final_status=final_status,
            final_decision=final_decision,
            executed_live=False,
            dry_run_report=dry_run_result,
        )

    if live:
        raise TaskRunnerError("Factory Start live canary V0 exige --cost-aware.")
    if not dry_run:
        raise TaskRunnerError("Factory Start V0 aceita apenas dry-run ou live canary nesta sprint.")

    return _run_factory_start_dry_run(
        run_id,
        max_steps=max_steps,
        evaluate=evaluate,
        repo=repo,
    )


def load_latest_factory_start_result(repo: Path) -> LatestFactoryStartResult:
    latest = latest_report("factory-starts", repo=repo)
    if latest is not None:
        payload = latest.payload
        factory_start_version = str(payload.get("factory_start_version", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        start_id = str(payload.get("start_id", "")).strip()
        run_id = str(payload.get("run_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        decision = str(payload.get("decision", "")).strip()
        loop_report = str(payload.get("loop_report", "")).strip()
        report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
        started_at = str(payload.get("started_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        reasons = payload.get("reasons", [])

        if (
            all([factory_start_version, mode, start_id, status, decision, report_path, started_at, finished_at])
            and isinstance(reasons, list)
            and _safe_relative_path(
                report_path,
                prefix=f"reports/{FACTORY_START_REPORTS_DIR}/",
                suffix=".json",
            )
            and (
                not loop_report
                or _safe_relative_path(loop_report, prefix="reports/factory-loops/", suffix=".json")
            )
        ):
            return LatestFactoryStartResult(
                available=True,
                factory_start_version=factory_start_version,
                mode=mode,
                start_id=start_id,
                run_id=run_id,
                status=status,
                decision=decision,
                max_steps=int(payload.get("max_steps", 1)),
                steps_completed=int(payload.get("steps_completed", 0)),
                executed_live=bool(payload.get("executed_live", False)),
                loop_report=loop_report,
                evaluation_report=str(payload.get("evaluation_report", "")).strip(),
                evaluation_decision=str(payload.get("evaluation_decision", "")).strip(),
                final_decision=str(payload.get("final_decision", "")).strip() or decision,
                final_status=str(payload.get("final_status", "")).strip() or status,
                report_path=report_path,
                view_path=latest.view_path,
                started_at=started_at,
                finished_at=finished_at,
                reasons=[str(item) for item in reasons],
            )

    return LatestFactoryStartResult(
        available=False,
        factory_start_version=FACTORY_START_VERSION,
        mode="unknown",
        start_id="",
        run_id="",
        status="unknown",
        decision="unknown",
        max_steps=1,
        steps_completed=0,
        executed_live=False,
        loop_report="",
        evaluation_report="",
        evaluation_decision="",
        final_decision="unknown",
        final_status="unknown",
        report_path="",
        view_path=None,
        started_at="",
        finished_at="",
        reasons=["Nenhum Factory Start válido encontrado em reports/factory-starts/."],
    )


def load_latest_factory_start_live_canary_result(repo: Path) -> LatestFactoryStartLiveCanaryResult:
    latest = latest_report("factory-start-live-canary", repo=repo)
    if latest is not None:
        payload = latest.payload
        report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
        canary_run_id = str(payload.get("canary_run_id", "")).strip()
        canary_task_id = str(payload.get("canary_task_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        workspace_path = str(payload.get("workspace_path", "")).strip()
        canary_file = str(payload.get("canary_file", "")).strip()
        stdout_path = str(payload.get("stdout_path", "")).strip()
        stderr_path = str(payload.get("stderr_path", "")).strip()
        master_head_before = str(payload.get("master_head_before", "")).strip()
        master_head_after = str(payload.get("master_head_after", "")).strip()
        workspace_head_before = str(payload.get("workspace_head_before", "")).strip()
        workspace_head_after = str(payload.get("workspace_head_after", "")).strip()
        created_at = str(payload.get("created_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        changed_files = payload.get("changed_files", [])
        codex_exit_codes = payload.get("codex_exit_codes", [])

        if (
            all([
                report_path,
                canary_run_id,
                canary_task_id,
                status,
                mode,
                workspace_path,
                canary_file,
                stdout_path,
                stderr_path,
                master_head_before,
                master_head_after,
                workspace_head_before,
                workspace_head_after,
                created_at,
                finished_at,
            ])
            and isinstance(changed_files, list)
            and isinstance(codex_exit_codes, list)
            and _safe_relative_path(
                report_path,
                prefix=f"reports/{FACTORY_START_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".json",
            )
            and _safe_relative_path(
                stdout_path,
                prefix=f"reports/{FACTORY_START_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".txt",
            )
            and _safe_relative_path(
                stderr_path,
                prefix=f"reports/{FACTORY_START_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".txt",
            )
        ):
            return LatestFactoryStartLiveCanaryResult(
                available=True,
                status=status,
                mode=mode,
                max_steps=int(payload.get("max_steps", 1)),
                steps_completed=int(payload.get("steps_completed", 0)),
                executed_live=bool(payload.get("executed_live", False)),
                canary_run_id=canary_run_id,
                canary_task_id=canary_task_id,
                report_path=report_path,
                view_path=latest.view_path,
                workspace_path=workspace_path,
                workspace_branch=str(payload.get("workspace_branch", "")).strip() or None,
                changed_files=[str(item) for item in changed_files],
                canary_file=canary_file,
                codex_exit_code=int(payload.get("codex_exit_code", -1)),
                codex_exit_codes=[int(item) for item in codex_exit_codes],
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                master_head_before=master_head_before,
                master_head_after=master_head_after,
                workspace_head_before=workspace_head_before,
                workspace_head_after=workspace_head_after,
                allowed_files_changed=bool(payload.get("allowed_files_changed", False)),
                no_push=bool(payload.get("no_push", False)),
                no_deploy=bool(payload.get("no_deploy", False)),
                no_paid_api=bool(payload.get("no_paid_api", False)),
                no_secrets=bool(payload.get("no_secrets", False)),
                created_at=created_at,
                finished_at=finished_at,
                branch_commit=str(payload.get("branch_commit", "")).strip() or None,
                decision=str(payload.get("decision", "")).strip() or status,
                evaluation_report=str(payload.get("evaluation_report", "")).strip(),
                evaluation_decision=str(payload.get("evaluation_decision", "")).strip(),
                final_decision=str(payload.get("final_decision", "")).strip() or str(payload.get("decision", "")).strip() or status,
                final_status=str(payload.get("final_status", "")).strip() or status,
            )

    return LatestFactoryStartLiveCanaryResult(
        available=False,
        status="unknown",
        mode="unknown",
        max_steps=1,
        steps_completed=0,
        executed_live=False,
        canary_run_id="",
        canary_task_id="",
        report_path="",
        view_path=None,
        workspace_path="",
        workspace_branch=None,
        changed_files=[],
        canary_file=FACTORY_START_LIVE_CANARY_ALLOWED_FILES[0],
        codex_exit_code=-1,
        codex_exit_codes=[],
        stdout_path="",
        stderr_path="",
        master_head_before="",
        master_head_after="",
        workspace_head_before="",
        workspace_head_after="",
        allowed_files_changed=False,
        no_push=False,
        no_deploy=False,
        no_paid_api=False,
        no_secrets=False,
        created_at="",
        finished_at="",
        branch_commit=None,
        decision="unknown",
        evaluation_report="",
        evaluation_decision="",
        final_decision="unknown",
        final_status="unknown",
    )


def load_latest_expanded_bounded_live_canary_result(repo: Path) -> LatestExpandedBoundedLiveCanaryResult:
    latest = latest_report(EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR, repo=repo)
    if latest is not None:
        payload = latest.payload
        report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
        canary_run_id = str(payload.get("canary_run_id", "")).strip()
        canary_task_id = str(payload.get("canary_task_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        workspace_path = str(payload.get("workspace_path", "")).strip()
        stdout_path = str(payload.get("stdout_path", "")).strip()
        stderr_path = str(payload.get("stderr_path", "")).strip()
        master_head_before = str(payload.get("master_head_before", "")).strip()
        master_head_after = str(payload.get("master_head_after", "")).strip()
        workspace_head_before = str(payload.get("workspace_head_before", "")).strip()
        workspace_head_after = str(payload.get("workspace_head_after", "")).strip()
        created_at = str(payload.get("created_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        changed_files = payload.get("changed_files", [])
        allowed_files = payload.get("allowed_files", [])
        disallowed_files = payload.get("disallowed_files", [])
        codex_or_capsule_runs = payload.get("codex_or_capsule_runs", [])
        token_summary = payload.get("token_summary", {})
        codex_exit_codes = payload.get("codex_exit_codes", [])

        if (
            all([
                report_path,
                canary_run_id,
                canary_task_id,
                status,
                mode,
                workspace_path,
                stdout_path,
                stderr_path,
                master_head_before,
                master_head_after,
                workspace_head_before,
                workspace_head_after,
                created_at,
                finished_at,
            ])
            and isinstance(changed_files, list)
            and isinstance(allowed_files, list)
            and isinstance(disallowed_files, list)
            and isinstance(codex_or_capsule_runs, list)
            and isinstance(token_summary, dict)
            and isinstance(codex_exit_codes, list)
            and _safe_relative_path(
                report_path,
                prefix=f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".json",
            )
            and _safe_relative_path(
                stdout_path,
                prefix=f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".txt",
            )
            and _safe_relative_path(
                stderr_path,
                prefix=f"reports/{EXPANDED_BOUNDED_LIVE_CANARY_REPORTS_DIR}/",
                suffix=".txt",
            )
        ):
            return LatestExpandedBoundedLiveCanaryResult(
                available=True,
                status=status,
                mode=mode,
                max_steps=int(payload.get("max_steps", 0) or 0),
                max_minutes=int(payload.get("max_minutes", 0) or 0),
                steps_completed=int(payload.get("steps_completed", 0) or 0),
                executed_live=bool(payload.get("executed_live", False)),
                canary_run_id=canary_run_id,
                canary_task_id=canary_task_id,
                report_path=report_path,
                view_path=latest.view_path,
                workspace_path=workspace_path,
                workspace_branch=str(payload.get("workspace_branch", "")).strip() or None,
                changed_files=[str(item) for item in changed_files],
                allowed_files=[str(item) for item in allowed_files],
                disallowed_files=[str(item) for item in disallowed_files],
                codex_or_capsule_runs=[dict(item) for item in codex_or_capsule_runs if isinstance(item, dict)],
                token_summary={str(key): value for key, value in token_summary.items()},
                codex_exit_codes=[int(item) for item in codex_exit_codes],
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                master_head_before=master_head_before,
                master_head_after=master_head_after,
                workspace_head_before=workspace_head_before,
                workspace_head_after=workspace_head_after,
                allowed_files_changed=bool(payload.get("allowed_files_changed", False)),
                no_push=bool(payload.get("no_push", False)),
                no_deploy=bool(payload.get("no_deploy", False)),
                no_paid_api=bool(payload.get("no_paid_api", False)),
                no_secrets=bool(payload.get("no_secrets", False)),
                created_at=created_at,
                finished_at=finished_at,
                branch_commit=str(payload.get("branch_commit", "")).strip() or None,
                decision=str(payload.get("decision", "")).strip() or status,
                evaluation_report=str(payload.get("evaluation_report", "")).strip(),
                evaluation_decision=str(payload.get("evaluation_decision", "")).strip(),
                final_decision=str(payload.get("final_decision", "")).strip() or str(payload.get("decision", "")).strip() or status,
                final_status=str(payload.get("final_status", "")).strip() or status,
            )

    return LatestExpandedBoundedLiveCanaryResult(
        available=False,
        status="unknown",
        mode="unknown",
        max_steps=0,
        max_minutes=0,
        steps_completed=0,
        executed_live=False,
        canary_run_id="",
        canary_task_id="",
        report_path="",
        view_path=None,
        workspace_path="",
        workspace_branch=None,
        changed_files=[],
        allowed_files=list(EXPANDED_BOUNDED_LIVE_CANARY_ALLOWED_FILES),
        disallowed_files=[],
        codex_or_capsule_runs=[],
        token_summary={},
        codex_exit_codes=[],
        stdout_path="",
        stderr_path="",
        master_head_before="",
        master_head_after="",
        workspace_head_before="",
        workspace_head_after="",
        allowed_files_changed=False,
        no_push=False,
        no_deploy=False,
        no_paid_api=False,
        no_secrets=False,
        created_at="",
        finished_at="",
        branch_commit=None,
        decision="unknown",
        evaluation_report="",
        evaluation_decision="unknown",
        final_decision="unknown",
        final_status="unknown",
    )
