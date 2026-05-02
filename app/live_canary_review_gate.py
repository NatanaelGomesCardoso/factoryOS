from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.report_index import latest_report
from app.task_runner import TaskRunnerError

REVIEW_GATE_VERSION = "v0"
REVIEW_GATE_REPORTS_DIR = "bounded-live-canary-reviews"
BOUNDED_LIVE_CANARY_REPORTS_DIR = "bounded-long-run-live-canary"
REVIEW_GATE_RECOMMENDED_TARGET_MINUTES = 30
REVIEW_GATE_RECOMMENDED_MAX_STEPS = 6
REVIEW_GATE_MAX_TARGET_MINUTES = 15
REVIEW_GATE_MAX_STEPS = 3


@dataclass(frozen=True, slots=True)
class LatestBoundedLiveCanaryReviewGateResult:
    available: bool
    review_gate_version: str
    run_id: str
    source_canary_report: str
    source_evaluation_report: str
    source_cost_audit_report: str
    source_maintenance_report: str
    report_path: str
    view_path: str | None
    approved_for_expansion_policy: bool
    allowed_to_execute_live: bool
    next_gate_requires_new_sprint: bool
    decision: str
    blockers: list[str]
    warnings: list[str]
    checks: dict[str, bool]
    recommended_next_gate: dict[str, Any]
    canary_decision: str
    evaluation_decision: str
    cost_audit_status: str
    target_minutes: int
    max_steps: int
    bwrap_path: str
    bwrap_version: str
    harness_global_doctor_status: str
    harness_doctor_status: str
    created_at: str
    finished_at: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / REVIEW_GATE_REPORTS_DIR


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


def _extract_run_id(payload: dict[str, Any]) -> str:
    for key in ("run_id", "canary_run_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise TaskRunnerError("report não contém run_id válido.")


def _run_command(command: list[str], *, timeout_seconds: int = 120) -> tuple[str, str, int]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except OSError:
        return "", "", 127
    except subprocess.TimeoutExpired as exc:
        return exc.stdout or "", exc.stderr or "", 124
    return completed.stdout.strip(), completed.stderr.strip(), completed.returncode


def _system_status(repo: Path) -> dict[str, Any]:
    bwrap_path = shutil.which("bwrap") or ""
    bwrap_version = ""
    bwrap_ok = False
    if bwrap_path:
        stdout, stderr, returncode = _run_command(["bwrap", "--version"], timeout_seconds=20)
        bwrap_version = stdout or stderr
        bwrap_ok = returncode == 0 and bool(bwrap_version)

    harness_root = repo.parent / "harness"
    _, _, global_code = _run_command(["harness", "global-doctor", "--strict"], timeout_seconds=180)
    _, _, doctor_code = _run_command(
        ["harness", "doctor", "--source-root", harness_root.as_posix(), "--strict"],
        timeout_seconds=180,
    )

    return {
        "bwrap_path": bwrap_path,
        "bwrap_version": bwrap_version,
        "bwrap_ok": bwrap_ok,
        "harness_global_doctor_status": "passed" if global_code == 0 else "failed",
        "harness_doctor_status": "passed" if doctor_code == 0 else "failed",
    }


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


def _no_mutation_artifact(value: Any) -> bool:
    if value is None or value == "none" or value == "":
        return True
    if isinstance(value, list):
        return not value
    return False


def _load_source_report(
    *,
    repo: Path,
    run_id: str | None,
    report: str | None,
) -> tuple[str, str, dict[str, Any]]:
    normalized_run_id = _validate_run_id(run_id) if run_id else None

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
        if not candidate.as_posix().startswith(f"reports/{BOUNDED_LIVE_CANARY_REPORTS_DIR}/"):
            raise TaskRunnerError("report precisa apontar para reports/bounded-long-run-live-canary/.")

        report_path = repo / candidate
        if not report_path.exists():
            raise TaskRunnerError("report informado não existe.")

        payload = _load_json_file(report_path)
        report_run_id = _extract_run_id(payload)
        if normalized_run_id is None:
            normalized_run_id = report_run_id
        elif normalized_run_id != report_run_id:
            raise TaskRunnerError("run_id não corresponde ao report informado.")
        return normalized_run_id, candidate.as_posix(), payload

    if normalized_run_id is None:
        raise TaskRunnerError("informe --run-id ou --report.")

    latest = latest_report(BOUNDED_LIVE_CANARY_REPORTS_DIR, repo=repo, run_id=normalized_run_id)
    if latest is None:
        raise TaskRunnerError("bounded live canary report ausente para a run informada.")
    return normalized_run_id, latest.relative_path, dict(latest.payload)


def run_bounded_live_canary_review_gate(
    run_id: str | None = None,
    *,
    report: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id, source_canary_report, canary = _load_source_report(repo=repo, run_id=run_id, report=report)

    evaluation = latest_report("execution-evaluations", repo=repo, run_id=normalized_run_id)
    maintenance = _latest_maintenance_plan(repo)
    cost_audit = _latest_cost_audit(repo)
    system_status = _system_status(repo)

    canary_version = str(canary.get("canary_version", "")).strip()
    target_minutes = int(canary.get("target_minutes", 0) or 0)
    max_steps = int(canary.get("max_steps", 0) or 0)
    steps_completed = int(canary.get("steps_completed", 0) or 0)
    codex_exit_codes = canary.get("codex_exit_codes", [])
    changed_files = canary.get("changed_files", [])
    disallowed_files = canary.get("disallowed_files", [])
    master_head_before = str(canary.get("master_head_before", "")).strip()
    master_head_after = str(canary.get("master_head_after", "")).strip()
    workspace_head_before = str(canary.get("workspace_head_before", "")).strip()
    workspace_head_after = str(canary.get("workspace_head_after", "")).strip()
    global_config_dependency = bool(canary.get("global_config_dependency", True))
    final_decision = str(canary.get("final_decision", "")).strip()
    executed_live = bool(canary.get("executed_live", False))
    no_push = bool(canary.get("no_push", False))
    no_deploy = bool(canary.get("no_deploy", False))
    no_paid_api = bool(canary.get("no_paid_api", False))
    no_secrets = bool(canary.get("no_secrets", False))
    allowed_files_changed = bool(canary.get("allowed_files_changed", False))
    canary_decision = str(canary.get("decision", "")).strip()
    source_evaluation_report = evaluation.relative_path if evaluation is not None else ""
    evaluation_payload = dict(evaluation.payload) if evaluation is not None else {}
    evaluation_decision = str(evaluation_payload.get("decision", "")).strip()
    cost_audit_payload = cost_audit[1] if cost_audit is not None else {}
    cost_audit_status = str(cost_audit_payload.get("classification", {}).get("status", "")).strip()
    source_cost_audit_report = cost_audit[0] if cost_audit is not None else ""
    source_maintenance_report = maintenance[0] if maintenance is not None else ""
    maintenance_payload = maintenance[1] if maintenance is not None else {}
    deleted_files = maintenance_payload.get("deleted_files", [])
    removed_worktrees = maintenance_payload.get("removed_worktrees", [])

    checks = {
        "report_exists": bool(source_canary_report),
        "evaluation_report_exists": bool(source_evaluation_report),
        "canary_version_v0": canary_version == "v0",
        "executed_live_true": executed_live is True,
        "steps_completed_3": steps_completed == 3,
        "codex_exit_codes_all_zero": isinstance(codex_exit_codes, list) and all(int(code) == 0 for code in codex_exit_codes),
        "changed_files_allowed": isinstance(changed_files, list) and allowed_files_changed is True,
        "disallowed_files_empty": isinstance(disallowed_files, list) and not disallowed_files,
        "master_intact": master_head_before == master_head_after,
        "workspace_intact": workspace_head_before == workspace_head_after,
        "global_config_dependency_false": global_config_dependency is False,
        "no_push": no_push is True,
        "no_deploy": no_deploy is True,
        "no_paid_api": no_paid_api is True,
        "no_secrets": no_secrets is True,
        "final_decision_passed": final_decision == "passed",
        "evaluation_decision_passed": evaluation_decision == "passed",
        "target_minutes_le_15": target_minutes <= REVIEW_GATE_MAX_TARGET_MINUTES,
        "max_steps_le_3": max_steps <= REVIEW_GATE_MAX_STEPS,
        "cost_audit_ok": cost_audit_status in {"ideal", "preferred_ok"},
        "bwrap_ok": bool(system_status["bwrap_ok"]),
        "harness_global_doctor_ok": system_status["harness_global_doctor_status"] == "passed",
        "harness_doctor_ok": system_status["harness_doctor_status"] == "passed",
        "deleted_files_empty": _no_mutation_artifact(deleted_files),
        "removed_worktrees_empty": _no_mutation_artifact(removed_worktrees),
    }

    blockers = [f"{key}=false" for key, ok in checks.items() if not ok]
    warnings: list[str] = []
    if maintenance is None:
        warnings.append("maintenance plan não encontrado.")
    if cost_audit is None:
        warnings.append("cost audit não encontrado.")

    approved = all(checks.values())
    decision = "approved_for_expansion_policy" if approved else "blocked"
    if not approved and (evaluation is None or cost_audit is None or not source_canary_report):
        decision = "needs_review"

    created_at = _now_iso()
    report_path = _reports_root(repo) / f"{_timestamp()}-{normalized_run_id}.json"
    payload = {
        "ok": approved,
        "review_gate_version": REVIEW_GATE_VERSION,
        "run_id": normalized_run_id,
        "source_canary_report": source_canary_report,
        "source_evaluation_report": source_evaluation_report,
        "source_cost_audit_report": source_cost_audit_report,
        "source_maintenance_report": source_maintenance_report,
        "checks": checks,
        "approved_for_expansion_policy": approved,
        "allowed_to_execute_live": False,
        "next_gate_requires_new_sprint": True,
        "recommended_next_gate": {
            "target_minutes": REVIEW_GATE_RECOMMENDED_TARGET_MINUTES,
            "max_steps": REVIEW_GATE_RECOMMENDED_MAX_STEPS,
            "mode": "bounded_live_canary_expansion",
        },
        "decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "canary_decision": canary_decision,
        "evaluation_decision": evaluation_decision,
        "cost_audit_status": cost_audit_status or "missing",
        "target_minutes": target_minutes,
        "max_steps": max_steps,
        "bwrap_path": system_status["bwrap_path"],
        "bwrap_version": system_status["bwrap_version"],
        "harness_global_doctor_status": system_status["harness_global_doctor_status"],
        "harness_doctor_status": system_status["harness_doctor_status"],
        "created_at": created_at,
        "finished_at": _now_iso(),
        "report_path": report_path.relative_to(repo).as_posix(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def load_latest_bounded_live_canary_review_gate_result(repo: Path) -> LatestBoundedLiveCanaryReviewGateResult:
    latest = latest_report(REVIEW_GATE_REPORTS_DIR, repo=repo)
    if latest is None:
        return LatestBoundedLiveCanaryReviewGateResult(
            available=False,
            review_gate_version=REVIEW_GATE_VERSION,
            run_id="",
            source_canary_report="",
            source_evaluation_report="",
            source_cost_audit_report="",
            source_maintenance_report="",
            report_path="",
            view_path=None,
            approved_for_expansion_policy=False,
            allowed_to_execute_live=False,
            next_gate_requires_new_sprint=True,
            decision="unknown",
            blockers=[],
            warnings=[],
            checks={},
            recommended_next_gate={
                "target_minutes": REVIEW_GATE_RECOMMENDED_TARGET_MINUTES,
                "max_steps": REVIEW_GATE_RECOMMENDED_MAX_STEPS,
                "mode": "bounded_live_canary_expansion",
            },
            canary_decision="unknown",
            evaluation_decision="unknown",
            cost_audit_status="missing",
            target_minutes=0,
            max_steps=0,
            bwrap_path="",
            bwrap_version="",
            harness_global_doctor_status="unknown",
            harness_doctor_status="unknown",
            created_at="",
            finished_at="",
        )

    payload = latest.payload
    report_path = str(payload.get("report_path", "")).strip() or latest.relative_path
    run_id = str(payload.get("run_id", "")).strip()
    checks = payload.get("checks", {})
    recommended_next_gate = payload.get("recommended_next_gate", {})
    if (
        report_path
        and run_id
        and isinstance(checks, dict)
        and isinstance(recommended_next_gate, dict)
        and _safe_relative_path(report_path, prefix=f"reports/{REVIEW_GATE_REPORTS_DIR}/", suffix=".json")
    ):
        return LatestBoundedLiveCanaryReviewGateResult(
            available=True,
            review_gate_version=str(payload.get("review_gate_version", REVIEW_GATE_VERSION)).strip() or REVIEW_GATE_VERSION,
            run_id=run_id,
            source_canary_report=str(payload.get("source_canary_report", "")).strip(),
            source_evaluation_report=str(payload.get("source_evaluation_report", "")).strip(),
            source_cost_audit_report=str(payload.get("source_cost_audit_report", "")).strip(),
            source_maintenance_report=str(payload.get("source_maintenance_report", "")).strip(),
            report_path=report_path,
            view_path=latest.view_path,
            approved_for_expansion_policy=bool(payload.get("approved_for_expansion_policy", False)),
            allowed_to_execute_live=bool(payload.get("allowed_to_execute_live", False)),
            next_gate_requires_new_sprint=bool(payload.get("next_gate_requires_new_sprint", True)),
            decision=str(payload.get("decision", "")).strip() or "unknown",
            blockers=[str(item) for item in payload.get("blockers", []) if str(item).strip()],
            warnings=[str(item) for item in payload.get("warnings", []) if str(item).strip()],
            checks={str(key): bool(value) for key, value in checks.items()},
            recommended_next_gate={str(key): value for key, value in recommended_next_gate.items()},
            canary_decision=str(payload.get("canary_decision", "")).strip(),
            evaluation_decision=str(payload.get("evaluation_decision", "")).strip(),
            cost_audit_status=str(payload.get("cost_audit_status", "")).strip(),
            target_minutes=int(payload.get("target_minutes", 0) or 0),
            max_steps=int(payload.get("max_steps", 0) or 0),
            bwrap_path=str(payload.get("bwrap_path", "")).strip(),
            bwrap_version=str(payload.get("bwrap_version", "")).strip(),
            harness_global_doctor_status=str(payload.get("harness_global_doctor_status", "")).strip(),
            harness_doctor_status=str(payload.get("harness_doctor_status", "")).strip(),
            created_at=str(payload.get("created_at", "")).strip(),
            finished_at=str(payload.get("finished_at", "")).strip(),
        )

    return LatestBoundedLiveCanaryReviewGateResult(
        available=False,
        review_gate_version=REVIEW_GATE_VERSION,
        run_id="",
        source_canary_report="",
        source_evaluation_report="",
        source_cost_audit_report="",
        source_maintenance_report="",
        report_path="",
        view_path=None,
        approved_for_expansion_policy=False,
        allowed_to_execute_live=False,
        next_gate_requires_new_sprint=True,
        decision="unknown",
        blockers=["latest review gate report inválido ou fora do formato esperado."],
        warnings=[],
        checks={},
        recommended_next_gate={
            "target_minutes": REVIEW_GATE_RECOMMENDED_TARGET_MINUTES,
            "max_steps": REVIEW_GATE_RECOMMENDED_MAX_STEPS,
            "mode": "bounded_live_canary_expansion",
        },
        canary_decision="unknown",
        evaluation_decision="unknown",
        cost_audit_status="missing",
        target_minutes=0,
        max_steps=0,
        bwrap_path="",
        bwrap_version="",
        harness_global_doctor_status="unknown",
        harness_doctor_status="unknown",
        created_at="",
        finished_at="",
    )
