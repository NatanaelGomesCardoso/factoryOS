from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.report_index import latest_report
from app.task_runner import TaskRunnerError

POLICY_VERSION = "v0"
POLICY_REPORTS_DIR = "long-run-expansion-policies"
REVIEW_GATE_REPORTS_DIR = "bounded-live-canary-reviews"
STATE_HYGIENE_REPORTS_DIR = "factory-state-hygiene"
MAINTENANCE_REPORTS_DIR = "factory-maintenance-plans"
TARGET_MINUTES_REQUIRED = 30
MAX_STEPS_REQUIRED = 6


@dataclass(frozen=True, slots=True)
class LatestLongRunExpansionPolicyResult:
    available: bool
    policy_version: str
    run_id: str
    source_review_report: str
    source_canary_report: str
    source_evaluation_report: str
    source_cost_audit_report: str
    source_maintenance_report: str
    source_state_audit_report: str
    source_state_plan_report: str
    report_path: str
    view_path: str | None
    current_level: str
    proposed_next_level: str
    target_minutes: int
    max_steps: int
    allowed_to_execute_live: bool
    requires_new_sprint: bool
    requires_manual_review: bool
    required_gates: list[str]
    acceptance_criteria: list[str]
    levels: list[dict[str, Any]]
    decision: str
    blockers: list[str]
    warnings: list[str]
    checks: dict[str, bool]
    created_at: str
    finished_at: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / POLICY_REPORTS_DIR


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{datetime.now().timestamp():.0f}.tmp")
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
    return normalized


def _validate_target_minutes(target_minutes: int) -> int:
    if target_minutes != TARGET_MINUTES_REQUIRED:
        raise TaskRunnerError(f"policy de expansão V0 exige target_minutes={TARGET_MINUTES_REQUIRED}.")
    return target_minutes


def _validate_max_steps(max_steps: int) -> int:
    if max_steps != MAX_STEPS_REQUIRED:
        raise TaskRunnerError(f"policy de expansão V0 exige max_steps={MAX_STEPS_REQUIRED}.")
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


def _latest_report_for_suffix(repo: Path, directory: str, suffix: str) -> tuple[str, dict[str, Any]] | None:
    root = repo / "reports" / directory
    if not root.exists():
        return None
    candidates = [path for path in root.glob(f"*{suffix}.json") if path.is_file() and not path.is_symlink()]
    if not candidates:
        return None
    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    return latest.relative_to(repo).as_posix(), _load_json_file(latest)


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


def _latest_review_gate(repo: Path, run_id: str) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report(REVIEW_GATE_REPORTS_DIR, repo=repo, run_id=run_id)
    if latest is None:
        return None
    return latest.relative_path, dict(latest.payload)


def _no_mutation_artifact(value: Any) -> bool:
    if value is None or value == "none" or value == "":
        return True
    if isinstance(value, list):
        return not value
    return False


def _level_payload(name: str, status: str, summary: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
    }


def run_long_run_expansion_policy(
    run_id: str,
    *,
    target_minutes: int,
    max_steps: int,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    validated_target_minutes = _validate_target_minutes(target_minutes)
    validated_max_steps = _validate_max_steps(max_steps)

    review = _latest_review_gate(repo, normalized_run_id)
    maintenance = _latest_maintenance_plan(repo)
    cost_audit = _latest_cost_audit(repo)
    state_audit = _latest_report_for_suffix(repo, STATE_HYGIENE_REPORTS_DIR, "-audit")
    state_plan = _latest_report_for_suffix(repo, STATE_HYGIENE_REPORTS_DIR, "-plan")

    if review is None:
        raise TaskRunnerError("review gate aprovado ausente para a run informada.")

    review_payload = review[1]
    review_approved = bool(review_payload.get("approved_for_expansion_policy", False))
    review_allowed_live = bool(review_payload.get("allowed_to_execute_live", True))
    review_decision = str(review_payload.get("decision", "")).strip()
    review_canary_report = str(review_payload.get("source_canary_report", "")).strip()
    review_evaluation_report = str(review_payload.get("source_evaluation_report", "")).strip()

    maintenance_payload = maintenance[1] if maintenance is not None else {}
    cost_audit_payload = cost_audit[1] if cost_audit is not None else {}
    state_audit_payload = state_audit[1] if state_audit is not None else {}
    state_plan_payload = state_plan[1] if state_plan is not None else {}

    cost_status = str(cost_audit_payload.get("classification", {}).get("status", "")).strip()
    deleted_files = maintenance_payload.get("deleted_files", [])
    removed_worktrees = maintenance_payload.get("removed_worktrees", [])
    running_tasks_count = int(state_audit_payload.get("stats", {}).get("running_tasks_count", 0) or 0)
    running_runs_count = int(state_audit_payload.get("stats", {}).get("running_runs_count", 0) or 0)
    safe_to_close_count = int(state_plan_payload.get("stats", {}).get("safe_to_close_count", 0) or 0)
    needs_review_count = int(state_plan_payload.get("stats", {}).get("needs_review_count", 0) or 0)
    blocked_count = int(state_plan_payload.get("stats", {}).get("blocked_count", 0) or 0)

    checks = {
        "review_gate_available": True,
        "review_gate_approved": review_approved is True,
        "review_gate_live_blocked": review_allowed_live is False,
        "review_gate_decision_ready": review_decision == "approved_for_expansion_policy",
        "cost_audit_ok": cost_status in {"ideal", "preferred_ok"},
        "maintenance_deleted_files_empty": _no_mutation_artifact(deleted_files),
        "maintenance_removed_worktrees_empty": _no_mutation_artifact(removed_worktrees),
        "state_audit_clean": running_tasks_count == 0 and running_runs_count == 0,
        "state_plan_clean": safe_to_close_count == 0 and needs_review_count == 0 and blocked_count == 0,
        "target_minutes_30": validated_target_minutes == TARGET_MINUTES_REQUIRED,
        "max_steps_6": validated_max_steps == MAX_STEPS_REQUIRED,
    }

    blockers: list[str] = []
    warnings: list[str] = []

    if review is None:
        blockers.append("review gate aprovado ausente.")
    if not review_approved:
        blockers.append("review gate não aprovou expansão.")
    if review_allowed_live:
        blockers.append("review gate ainda permite live, o que é proibido nesta policy.")
    if cost_audit is None:
        blockers.append("cost audit ausente.")
    if maintenance is None:
        blockers.append("maintenance plan ausente.")
    if state_audit is None:
        blockers.append("factory-state-audit ausente.")
    if state_plan is None:
        blockers.append("factory-state-plan ausente.")
    if not _no_mutation_artifact(deleted_files):
        blockers.append("maintenance plan registrou deleted_files não vazios.")
    if not _no_mutation_artifact(removed_worktrees):
        blockers.append("maintenance plan registrou removed_worktrees não vazios.")
    if running_tasks_count != 0 or running_runs_count != 0:
        blockers.append("factory-state-audit ainda mostra itens running.")
    if safe_to_close_count != 0 or needs_review_count != 0 or blocked_count != 0:
        blockers.append("factory-state-plan ainda aponta itens para fechar ou revisar.")
    if cost_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"cost_audit_status={cost_status or 'missing'} fora do nível aceito.")
    if not checks["target_minutes_30"] or not checks["max_steps_6"]:
        blockers.append("parâmetros do próximo gate não correspondem a 30m/6 steps.")

    if cost_audit is None:
        warnings.append("cost audit não encontrado no momento da policy.")
    if maintenance is None:
        warnings.append("maintenance plan não encontrado no momento da policy.")

    approved = all(checks.values())
    if approved:
        decision = "policy_ready_for_next_sprint"
    elif blockers:
        decision = "blocked"
    else:
        decision = "needs_review"

    current_level = "level_1_bounded_live_canary_15m_3steps_passed"
    proposed_next_level = "level_2_expanded_bounded_live_30m_6steps"
    required_gates = [
        "bounded_live_canary_review_gate_v0_approved",
        "factory_maintenance_plan_clean",
        "factory_state_audit_clean",
        "factory_state_plan_clean",
        "codex_cost_audit_ideal_or_preferred_ok",
        "manual_review_before_next_sprint",
    ]
    acceptance_criteria = [
        "review gate aprovado para expansão futura",
        "allowed_to_execute_live permanece false",
        "requires_new_sprint permanece true",
        "target_minutes=30",
        "max_steps=6",
        "maintenance/state/cost audit sem bloqueios",
        "revisão manual obrigatória antes da próxima sprint",
    ]
    levels = [
        _level_payload(
            "level_0_dry_run_rehearsal",
            "passed",
            "Rehearsal dry-run já consolidado pela Sprint 034.",
        ),
        _level_payload(
            "level_1_bounded_live_canary_15m_3steps",
            "passed",
            "Bounded live canary da Sprint 035 aprovado e revisado.",
        ),
        _level_payload(
            "level_2_expanded_bounded_live_30m_6steps",
            "proposed",
            "Ainda bloqueado; depende de nova sprint e revisão manual adicional.",
        ),
    ]

    report_path = _reports_root(repo) / f"{_timestamp()}-{normalized_run_id}.json"
    payload = {
        "ok": approved,
        "policy_version": POLICY_VERSION,
        "run_id": normalized_run_id,
        "source_review_report": review[0],
        "source_canary_report": review_canary_report,
        "source_evaluation_report": review_evaluation_report,
        "source_cost_audit_report": cost_audit[0] if cost_audit is not None else "",
        "source_maintenance_report": maintenance[0] if maintenance is not None else "",
        "source_state_audit_report": state_audit[0] if state_audit is not None else "",
        "source_state_plan_report": state_plan[0] if state_plan is not None else "",
        "current_level": current_level,
        "proposed_next_level": proposed_next_level,
        "target_minutes": validated_target_minutes,
        "max_steps": validated_max_steps,
        "allowed_to_execute_live": False,
        "requires_new_sprint": True,
        "requires_manual_review": True,
        "required_gates": required_gates,
        "acceptance_criteria": acceptance_criteria,
        "levels": levels,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "decision": decision,
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
        "report_path": report_path.relative_to(repo).as_posix(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def load_latest_long_run_expansion_policy_result(repo: Path) -> LatestLongRunExpansionPolicyResult:
    latest = latest_report(POLICY_REPORTS_DIR, repo=repo)
    if latest is None:
        return LatestLongRunExpansionPolicyResult(
            available=False,
            policy_version=POLICY_VERSION,
            run_id="",
            source_review_report="",
            source_canary_report="",
            source_evaluation_report="",
            source_cost_audit_report="",
            source_maintenance_report="",
            source_state_audit_report="",
            source_state_plan_report="",
            report_path="",
            view_path=None,
            current_level="",
            proposed_next_level="",
            target_minutes=0,
            max_steps=0,
            allowed_to_execute_live=False,
            requires_new_sprint=True,
            requires_manual_review=True,
            required_gates=[],
            acceptance_criteria=[],
            levels=[],
            decision="unknown",
            blockers=[],
            warnings=[],
            checks={},
            created_at="",
            finished_at="",
        )

    payload = latest.payload
    report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
    run_id = str(payload.get("run_id", "")).strip()
    levels = payload.get("levels", [])
    checks = payload.get("checks", {})
    if (
        report_path
        and run_id
        and isinstance(levels, list)
        and isinstance(checks, dict)
        and _safe_relative_path(report_path, prefix=f"reports/{POLICY_REPORTS_DIR}/", suffix=".json")
    ):
        return LatestLongRunExpansionPolicyResult(
            available=True,
            policy_version=str(payload.get("policy_version", POLICY_VERSION)).strip() or POLICY_VERSION,
            run_id=run_id,
            source_review_report=str(payload.get("source_review_report", "")).strip(),
            source_canary_report=str(payload.get("source_canary_report", "")).strip(),
            source_evaluation_report=str(payload.get("source_evaluation_report", "")).strip(),
            source_cost_audit_report=str(payload.get("source_cost_audit_report", "")).strip(),
            source_maintenance_report=str(payload.get("source_maintenance_report", "")).strip(),
            source_state_audit_report=str(payload.get("source_state_audit_report", "")).strip(),
            source_state_plan_report=str(payload.get("source_state_plan_report", "")).strip(),
            report_path=report_path,
            view_path=latest.view_path,
            current_level=str(payload.get("current_level", "")).strip(),
            proposed_next_level=str(payload.get("proposed_next_level", "")).strip(),
            target_minutes=int(payload.get("target_minutes", 0) or 0),
            max_steps=int(payload.get("max_steps", 0) or 0),
            allowed_to_execute_live=bool(payload.get("allowed_to_execute_live", False)),
            requires_new_sprint=bool(payload.get("requires_new_sprint", True)),
            requires_manual_review=bool(payload.get("requires_manual_review", True)),
            required_gates=[str(item) for item in payload.get("required_gates", []) if str(item).strip()],
            acceptance_criteria=[str(item) for item in payload.get("acceptance_criteria", []) if str(item).strip()],
            levels=[{str(key): value for key, value in level.items()} for level in levels],
            decision=str(payload.get("decision", "")).strip() or "unknown",
            blockers=[str(item) for item in payload.get("blockers", []) if str(item).strip()],
            warnings=[str(item) for item in payload.get("warnings", []) if str(item).strip()],
            checks={str(key): bool(value) for key, value in checks.items()},
            created_at=str(payload.get("created_at", "")).strip(),
            finished_at=str(payload.get("finished_at", "")).strip(),
        )

    return LatestLongRunExpansionPolicyResult(
        available=False,
        policy_version=POLICY_VERSION,
        run_id="",
        source_review_report="",
        source_canary_report="",
        source_evaluation_report="",
        source_cost_audit_report="",
        source_maintenance_report="",
        source_state_audit_report="",
        source_state_plan_report="",
        report_path="",
        view_path=None,
        current_level="",
        proposed_next_level="",
        target_minutes=0,
        max_steps=0,
        allowed_to_execute_live=False,
        requires_new_sprint=True,
        requires_manual_review=True,
        required_gates=[],
        acceptance_criteria=[],
        levels=[],
        decision="unknown",
        blockers=["latest policy report inválido ou fora do formato esperado."],
        warnings=[],
        checks={},
        created_at="",
        finished_at="",
    )
