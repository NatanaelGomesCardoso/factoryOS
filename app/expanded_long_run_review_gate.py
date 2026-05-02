from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.expanded_long_run_rehearsal import EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR
from app.maintenance_plan import run_factory_maintenance_plan
from app.report_index import latest_report
from app.task_runner import TaskRunnerError

EXPANDED_LONG_RUN_REVIEW_GATE_VERSION = "v0"
EXPANDED_LONG_RUN_REVIEW_REPORTS_DIR = "expanded-long-run-reviews"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TARGET_MINUTES_REQUIRED = 30
MAX_STEPS_REQUIRED = 6


@dataclass(frozen=True, slots=True)
class LatestExpandedLongRunReviewGateResult:
    available: bool
    expanded_review_gate_version: str
    run_id: str
    source_expanded_rehearsal_report: str
    approved_for_expanded_live_sprint: bool
    allowed_to_execute_live: bool
    next_gate_requires_new_sprint: bool
    recommended_next_sprint: dict[str, Any]
    decision: str
    blockers: list[str]
    warnings: list[str]
    target_minutes: int
    max_steps: int
    allowed_no_push: bool
    allowed_no_deploy: bool
    allowed_no_paid_api: bool
    allowed_no_secrets: bool
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
    return (repo or repo_root()) / "reports" / EXPANDED_LONG_RUN_REVIEW_REPORTS_DIR


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


def _latest_rehearsal_for_run(repo: Path, run_id: str) -> tuple[str, dict[str, Any]] | None:
    latest = latest_report(EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR, repo=repo, run_id=run_id)
    if latest is None:
        return None
    return latest.relative_path, dict(latest.payload)


def _required_true_or_absent(payload: dict[str, Any], key: str, warnings: list[str]) -> bool:
    if key not in payload:
        warnings.append(f"{key} ausente no rehearsal expandido; revisão conservadora aplicada.")
        return True
    return bool(payload.get(key, False))


def run_expanded_long_run_review_gate(
    run_id: str | None = None,
    *,
    report: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    warnings: list[str] = []

    if bool(run_id) == bool(report):
        raise TaskRunnerError("informe exatamente um de --run-id ou --report.")

    if report is not None:
        normalized_report = report.strip()
        if not normalized_report:
            raise TaskRunnerError("report path vazio.")
        if Path(normalized_report).is_absolute():
            raise TaskRunnerError("path absoluto não permitido no report.")
        candidate = Path(normalized_report)
        if any(part in {".", ".."} for part in candidate.parts):
            raise TaskRunnerError("path traversal não permitido no report.")
        if candidate.suffix != ".json":
            raise TaskRunnerError("report precisa terminar em .json.")
        if not candidate.as_posix().startswith(f"reports/{EXPANDED_LONG_RUN_REVIEW_REPORTS_DIR}/"):
            raise TaskRunnerError("report precisa apontar para reports/expanded-long-run-reviews/.")
        report_path = repo / candidate
        if not report_path.exists():
            raise TaskRunnerError("report informado não existe.")
        payload = _load_json_file(report_path)
        run_id_value = str(payload.get("run_id", "")).strip()
        if not run_id_value:
            raise TaskRunnerError("report não contém run_id válido.")
        normalized_run_id = _validate_run_id(run_id_value)
        source_expanded_rehearsal_report = str(payload.get("source_expanded_rehearsal_report", "")).strip()
        if not source_expanded_rehearsal_report:
            raise TaskRunnerError("report não contém rehearsal de origem.")
        if not _safe_relative_path(
            source_expanded_rehearsal_report,
            prefix=f"reports/{EXPANDED_LONG_RUN_REHEARSAL_REPORTS_DIR}/",
            suffix=".json",
        ):
            raise TaskRunnerError("report de rehearsal de origem inválido.")
        rehearsal_path = repo / source_expanded_rehearsal_report
        if not rehearsal_path.exists():
            raise TaskRunnerError("report de rehearsal de origem não existe.")
        rehearsal = _load_json_file(rehearsal_path)
    else:
        normalized_run_id = _validate_run_id(run_id or "")
        rehearsal_match = _latest_rehearsal_for_run(repo, normalized_run_id)
        if rehearsal_match is None:
            raise TaskRunnerError("expanded rehearsal ausente para a run informada.")
        source_expanded_rehearsal_report, rehearsal = rehearsal_match

    if str(rehearsal.get("expanded_rehearsal_version", "")).strip() != "v0":
        raise TaskRunnerError("expanded rehearsal inválido para review gate V0.")
    if str(rehearsal.get("mode", "")).strip() != "dry-run":
        raise TaskRunnerError("review gate exige rehearsal em dry-run.")
    if int(rehearsal.get("target_minutes", 0) or 0) != TARGET_MINUTES_REQUIRED:
        raise TaskRunnerError("expanded rehearsal precisa ter target_minutes=30.")
    if int(rehearsal.get("max_steps", 0) or 0) != MAX_STEPS_REQUIRED:
        raise TaskRunnerError("expanded rehearsal precisa ter max_steps=6.")

    allowed_to_execute_live = bool(rehearsal.get("allowed_to_execute_live", True))
    executed_live = bool(rehearsal.get("executed_live", True))
    requires_review_gate = bool(rehearsal.get("requires_review_gate", False))
    requires_new_sprint_for_live = bool(rehearsal.get("requires_new_sprint_for_live", False))
    global_config_dependency = bool(rehearsal.get("global_config_dependency", True))
    token_target_status = str(rehearsal.get("token_target_status", "")).strip()
    budget_status = str(rehearsal.get("budget_status", "")).strip()
    context_status = str(rehearsal.get("context_status", "")).strip()
    final_decision = str(rehearsal.get("final_decision", "")).strip()
    blockers: list[str] = []

    maintenance = run_factory_maintenance_plan(repo=repo)
    maintenance_path = str(maintenance.get("report_path", "")).strip()
    maintenance_payload = _load_json_file(repo / maintenance_path) if maintenance_path else {}
    state_audit_path = str(maintenance.get("factory_state_audit_report", "")).strip()
    state_plan_path = str(maintenance.get("factory_state_plan_report", "")).strip()
    state_audit_payload = _load_json_file(repo / state_audit_path) if state_audit_path else {}
    state_plan_payload = _load_json_file(repo / state_plan_path) if state_plan_path else {}

    maintenance_deleted_files = maintenance_payload.get("deleted_files", [])
    maintenance_removed_worktrees = maintenance_payload.get("removed_worktrees", [])
    state_audit_stats = state_audit_payload.get("stats", {}) if isinstance(state_audit_payload, dict) else {}
    state_plan_stats = state_plan_payload.get("stats", {}) if isinstance(state_plan_payload, dict) else {}

    if str(rehearsal.get("source_expansion_policy_report", "")).strip() == "":
        blockers.append("policy de expansão ausente no rehearsal expandido.")
    if final_decision != "expanded_rehearsal_ready_for_review":
        blockers.append("rehearsal expandido não terminou pronto para review.")
    if allowed_to_execute_live:
        blockers.append("rehearsal expandido não pode autorizar live.")
    if executed_live:
        blockers.append("rehearsal expandido não pode registrar executed_live=true.")
    if not requires_review_gate:
        blockers.append("rehearsal expandido precisa exigir review gate.")
    if not requires_new_sprint_for_live:
        blockers.append("rehearsal expandido precisa exigir nova sprint.")
    if global_config_dependency:
        blockers.append("rehearsal expandido depende de config global.")
    if token_target_status not in {"ideal", "preferred_ok"}:
        blockers.append(f"token_target_status={token_target_status or 'missing'} fora do nível aceito.")
    if budget_status != "ok":
        blockers.append(f"budget_status={budget_status or 'missing'} fora do nível aceito.")
    if context_status != "ok":
        blockers.append(f"context_status={context_status or 'missing'} fora do nível aceito.")
    if int(state_audit_stats.get("running_tasks_count", 0) or 0) != 0:
        blockers.append("factory-state-audit mostra running_tasks_count diferente de zero.")
    if int(state_audit_stats.get("running_runs_count", 0) or 0) != 0:
        blockers.append("factory-state-audit mostra running_runs_count diferente de zero.")
    if int(state_plan_stats.get("safe_to_close_count", 0) or 0) != 0:
        blockers.append("factory-state-plan mostra safe_to_close_count diferente de zero.")
    if int(state_plan_stats.get("needs_review_count", 0) or 0) != 0:
        blockers.append("factory-state-plan mostra needs_review_count diferente de zero.")
    if int(state_plan_stats.get("blocked_count", 0) or 0) != 0:
        blockers.append("factory-state-plan mostra blocked_count diferente de zero.")
    if str(maintenance_deleted_files) != "none":
        blockers.append("maintenance plan registrou deleted_files.")
    if str(maintenance_removed_worktrees) != "none":
        blockers.append("maintenance plan registrou removed_worktrees.")

    no_push = _required_true_or_absent(rehearsal, "no_push", warnings)
    no_deploy = _required_true_or_absent(rehearsal, "no_deploy", warnings)
    no_paid_api = _required_true_or_absent(rehearsal, "no_paid_api", warnings)
    no_secrets = _required_true_or_absent(rehearsal, "no_secrets", warnings)
    if not no_push:
        blockers.append("rehearsal expandido registrou no_push=false.")
    if not no_deploy:
        blockers.append("rehearsal expandido registrou no_deploy=false.")
    if not no_paid_api:
        blockers.append("rehearsal expandido registrou no_paid_api=false.")
    if not no_secrets:
        blockers.append("rehearsal expandido registrou no_secrets=false.")

    decision = "approved_for_expanded_live_sprint"
    if blockers:
        decision = "blocked" if any("ausente" in item or "invál" in item or "missing" in item or "não terminou" in item for item in blockers) else "needs_review"

    report_path = _reports_root(repo) / f"{_timestamp()}-{normalized_run_id}.json"
    payload = {
        "ok": decision == "approved_for_expanded_live_sprint",
        "expanded_review_gate_version": EXPANDED_LONG_RUN_REVIEW_GATE_VERSION,
        "run_id": normalized_run_id,
        "source_expanded_rehearsal_report": source_expanded_rehearsal_report,
        "source_maintenance_report": maintenance_path,
        "source_state_audit_report": state_audit_path,
        "source_state_plan_report": state_plan_path,
        "approved_for_expanded_live_sprint": decision == "approved_for_expanded_live_sprint",
        "allowed_to_execute_live": False,
        "next_gate_requires_new_sprint": True,
        "recommended_next_sprint": {
            "title": "Expanded Bounded Live Canary 30m 6 Steps V0",
            "target_minutes": TARGET_MINUTES_REQUIRED,
            "max_steps": MAX_STEPS_REQUIRED,
            "mode": "bounded_live_canary_expansion",
        },
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "target_minutes": TARGET_MINUTES_REQUIRED,
        "max_steps": MAX_STEPS_REQUIRED,
        "allowed_no_push": bool(no_push),
        "allowed_no_deploy": bool(no_deploy),
        "allowed_no_paid_api": bool(no_paid_api),
        "allowed_no_secrets": bool(no_secrets),
        "report_path": report_path.relative_to(repo).as_posix(),
        "generated_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def load_latest_expanded_long_run_review_gate_result(repo: Path) -> LatestExpandedLongRunReviewGateResult:
    latest = latest_report(EXPANDED_LONG_RUN_REVIEW_REPORTS_DIR, repo=repo)
    if latest is None:
        return LatestExpandedLongRunReviewGateResult(
            available=False,
            expanded_review_gate_version=EXPANDED_LONG_RUN_REVIEW_GATE_VERSION,
            run_id="",
            source_expanded_rehearsal_report="",
            approved_for_expanded_live_sprint=False,
            allowed_to_execute_live=False,
            next_gate_requires_new_sprint=True,
            recommended_next_sprint={},
            decision="unknown",
            blockers=[],
            warnings=[],
            target_minutes=0,
            max_steps=0,
            allowed_no_push=False,
            allowed_no_deploy=False,
            allowed_no_paid_api=False,
            allowed_no_secrets=False,
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
            prefix=f"reports/{EXPANDED_LONG_RUN_REVIEW_REPORTS_DIR}/",
            suffix=".json",
        )
    ):
        return LatestExpandedLongRunReviewGateResult(
            available=True,
            expanded_review_gate_version=str(payload.get("expanded_review_gate_version", EXPANDED_LONG_RUN_REVIEW_GATE_VERSION)).strip()
            or EXPANDED_LONG_RUN_REVIEW_GATE_VERSION,
            run_id=run_id,
            source_expanded_rehearsal_report=str(payload.get("source_expanded_rehearsal_report", "")).strip(),
            approved_for_expanded_live_sprint=bool(payload.get("approved_for_expanded_live_sprint", False)),
            allowed_to_execute_live=bool(payload.get("allowed_to_execute_live", False)),
            next_gate_requires_new_sprint=bool(payload.get("next_gate_requires_new_sprint", True)),
            recommended_next_sprint={str(key): value for key, value in dict(payload.get("recommended_next_sprint", {})).items()},
            decision=str(payload.get("decision", "")).strip() or "unknown",
            blockers=[str(item) for item in payload.get("blockers", []) if str(item).strip()],
            warnings=[str(item) for item in payload.get("warnings", []) if str(item).strip()],
            target_minutes=int(payload.get("target_minutes", 0) or 0),
            max_steps=int(payload.get("max_steps", 0) or 0),
            allowed_no_push=bool(payload.get("allowed_no_push", False)),
            allowed_no_deploy=bool(payload.get("allowed_no_deploy", False)),
            allowed_no_paid_api=bool(payload.get("allowed_no_paid_api", False)),
            allowed_no_secrets=bool(payload.get("allowed_no_secrets", False)),
            report_path=report_path,
            view_path=latest.view_path,
            generated_at=str(payload.get("generated_at", "")).strip(),
        )

    return LatestExpandedLongRunReviewGateResult(
        available=False,
        expanded_review_gate_version=EXPANDED_LONG_RUN_REVIEW_GATE_VERSION,
        run_id="",
        source_expanded_rehearsal_report="",
        approved_for_expanded_live_sprint=False,
        allowed_to_execute_live=False,
        next_gate_requires_new_sprint=True,
        recommended_next_sprint={},
        decision="unknown",
        blockers=[],
        warnings=[],
        target_minutes=0,
        max_steps=0,
        allowed_no_push=False,
        allowed_no_deploy=False,
        allowed_no_paid_api=False,
        allowed_no_secrets=False,
        report_path="",
        view_path=None,
        generated_at="",
    )
