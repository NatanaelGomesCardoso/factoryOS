from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.report_index import latest_report, latest_report_among
from app.run_workspace import finish_run, show_run
from app.task_runner import TaskRunnerError, finish_task, show_task

EXECUTION_EVALUATION_REPORTS_DIR = "execution-evaluations"
REPORT_ROOT_PREFIX = "reports/"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
REPORT_TIMESTAMP_PREFIX = re.compile(r"^\d{8}-\d{6}-(.+)$")


@dataclass(frozen=True, slots=True)
class LatestExecutionEvaluationResult:
    available: bool
    run_id: str
    source_report: str
    report_path: str
    view_path: str | None
    decision: str
    checks: dict[str, bool]
    reasons: list[str]
    created_at: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports"


def _evaluations_root(repo: Path | None = None) -> Path:
    return _reports_root(repo) / EXECUTION_EVALUATION_REPORTS_DIR


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{datetime.now().timestamp():.0f}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.as_posix()}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")

    return payload


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


def _safe_relative_report_path(value: str) -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {".", ".."} for part in candidate.parts):
        return False

    return candidate.as_posix().startswith(REPORT_ROOT_PREFIX) and candidate.suffix == ".json"


def _safe_path_from_report_input(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise TaskRunnerError("report path vazio.")
    if Path(normalized).is_absolute():
        raise TaskRunnerError("path absoluto não permitido em report.")
    candidate = Path(normalized)
    if any(part in {".", ".."} for part in candidate.parts):
        raise TaskRunnerError("path traversal não permitido em report.")
    if not candidate.as_posix().startswith(REPORT_ROOT_PREFIX):
        raise TaskRunnerError("report precisa ficar dentro de reports/.")
    if candidate.suffix != ".json":
        raise TaskRunnerError("report precisa terminar em .json.")
    return candidate.as_posix()


def _report_kind(payload: dict[str, Any], path: Path) -> str:
    if path.parent.name == "bounded-long-run-live-canary":
        return "bounded-long-run-live-canary"
    if path.parent.name == "factory-start-live-canary":
        return "factory-start-live-canary"
    if path.parent.name == "factory-starts":
        return "factory-start"
    if "canary_run_id" in payload or path.parent.name == "live-canary":
        return "live-canary"
    if "tick_id" in payload or path.parent.name == "factory-ticks":
        return "factory-tick"
    if "prompt_path" in payload or path.parent.name == "run-handoffs":
        return "run-handoff"
    if path.parent.name == "factory-loops":
        return "factory-loop"
    return "unknown"


def _payload_run_id(payload: dict[str, Any], kind: str) -> str:
    if kind in {"live-canary", "factory-start-live-canary", "bounded-long-run-live-canary"}:
        return str(payload.get("canary_run_id", "")).strip()
    return str(payload.get("run_id", "")).strip()


def _infer_run_id_from_report_path(report_path: str) -> str:
    stem = Path(report_path).stem
    match = REPORT_TIMESTAMP_PREFIX.fullmatch(stem)
    if match:
        return match.group(1)
    return stem


def _source_report_for_run(repo: Path, run_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    entry = latest_report_among(
        [
            "bounded-long-run-live-canary",
            "factory-start-live-canary",
            "factory-starts",
            "live-canary",
            "factory-loops",
            "factory-ticks",
            "run-handoffs",
        ],
        repo=repo,
        run_id=run_id,
    )
    if entry is None:
        return None, None
    return repo / entry.relative_path, dict(entry.payload)


def _local_validation_results() -> dict[str, bool]:
    python_files = sorted((repo_root() / "app").glob("*.py"))
    py_compile_ok = False
    compileall_ok = False
    panel_ok = False

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "py_compile", *[path.as_posix() for path in python_files]],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        py_compile_ok = completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        py_compile_ok = False

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "compileall", "app"],
            cwd=repo_root(),
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        compileall_ok = completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        compileall_ok = False

    try:
        from fastapi.testclient import TestClient

        from app.web import app

        with TestClient(app, base_url="http://127.0.0.1") as client:
            response = client.get("/")
            panel_ok = response.status_code == 200
    except Exception:
        panel_ok = False

    return {
        "python_compile_ok": py_compile_ok and compileall_ok,
        "panel_ok": panel_ok,
    }


def _blocked_checks(local_validations: dict[str, bool]) -> dict[str, bool]:
    return {
        "json_valid": False,
        "executed_live_ok": False,
        "codex_exit_code_ok": False,
        "changed_files_ok": False,
        "allowed_files_changed_ok": False,
        "master_unchanged": False,
        "no_push": False,
        "no_deploy": False,
        "no_paid_api": False,
        "no_secrets": False,
        "readiness_ok": False,
        "sync_plan_ok": False,
        "python_compile_ok": local_validations["python_compile_ok"],
        "panel_ok": local_validations["panel_ok"],
    }


def _bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _build_checks(
    *,
    payload: dict[str, Any] | None,
    kind: str,
    report_exists: bool,
    local_validations: dict[str, bool],
) -> tuple[dict[str, bool], list[str], str]:
    checks = {
        "json_valid": False,
        "executed_live_ok": False,
        "codex_exit_code_ok": False,
        "changed_files_ok": False,
        "allowed_files_changed_ok": False,
        "master_unchanged": False,
        "no_push": False,
        "no_deploy": False,
        "no_paid_api": False,
        "no_secrets": False,
        "readiness_ok": False,
        "sync_plan_ok": False,
        "python_compile_ok": local_validations["python_compile_ok"],
        "panel_ok": local_validations["panel_ok"],
    }
    reasons: list[str] = []

    if not report_exists:
        reasons.append("report ausente.")
        return checks, reasons, "blocked"

    if payload is None:
        reasons.append("JSON inválido no report.")
        return checks, reasons, "blocked"

    checks["json_valid"] = True

    readiness_status = str(payload.get("readiness_status", "")).strip()
    sync_plan_status = str(payload.get("sync_plan_status", "")).strip()

    if readiness_status == "ready":
        checks["readiness_ok"] = True
    elif readiness_status:
        reasons.append(f"readiness_status inesperado: {readiness_status}.")

    if sync_plan_status == "already_current":
        checks["sync_plan_ok"] = True
    elif sync_plan_status:
        reasons.append(f"sync_plan_status inesperado: {sync_plan_status}.")

    if kind in {"live-canary", "factory-start-live-canary", "bounded-long-run-live-canary"}:
        executed_live = _bool(payload.get("executed_live"))
        if executed_live:
            checks["executed_live_ok"] = True
        else:
            reasons.append("executed_live precisa ser true para o live canary.")

        codex_exit_code = payload.get("codex_exit_code")
        codex_exit_codes = payload.get("codex_exit_codes")
        if isinstance(codex_exit_codes, list) and codex_exit_codes:
            normalized_codes = [int(item) for item in codex_exit_codes]
            if all(code == 0 for code in normalized_codes):
                checks["codex_exit_code_ok"] = True
            else:
                reasons.append("codex_exit_codes precisa conter apenas zeros.")
        elif isinstance(codex_exit_code, int) and codex_exit_code == 0:
            checks["codex_exit_code_ok"] = True
        else:
            reasons.append("codex_exit_code precisa ser 0.")

        changed_files = payload.get("changed_files")
        allowed_files = payload.get("allowed_files")
        canary_file = str(payload.get("canary_file", "")).strip()
        if isinstance(changed_files, list) and isinstance(allowed_files, list) and allowed_files:
            normalized_files = sorted(str(item) for item in changed_files)
            normalized_allowed = sorted(str(item) for item in allowed_files)
            if normalized_files == normalized_allowed:
                checks["changed_files_ok"] = True
            else:
                reasons.append("changed_files precisa corresponder exatamente aos arquivos permitidos.")
        elif isinstance(changed_files, list) and canary_file:
            normalized_files = [str(item) for item in changed_files]
            if normalized_files == [canary_file]:
                checks["changed_files_ok"] = True
            else:
                reasons.append("changed_files precisa conter somente o arquivo permitido.")
        else:
            reasons.append("changed_files ausente ou inválido.")

        if _bool(payload.get("allowed_files_changed")) and checks["changed_files_ok"]:
            checks["allowed_files_changed_ok"] = True
        else:
            reasons.append("allowed_files_changed precisa ser true.")

        master_before = str(payload.get("master_head_before", "")).strip()
        master_after = str(payload.get("master_head_after", "")).strip()
        if master_before and master_after and master_before == master_after:
            checks["master_unchanged"] = True
        else:
            reasons.append("master_head_before e master_head_after precisam ser iguais.")

        if _bool(payload.get("no_push")):
            checks["no_push"] = True
        else:
            reasons.append("no_push precisa ser true.")

        if _bool(payload.get("no_deploy")):
            checks["no_deploy"] = True
        else:
            reasons.append("no_deploy precisa ser true.")

        if _bool(payload.get("no_paid_api")):
            checks["no_paid_api"] = True
        else:
            reasons.append("no_paid_api precisa ser true.")

        if _bool(payload.get("no_secrets")):
            checks["no_secrets"] = True
        else:
            reasons.append("no_secrets precisa ser true.")

    elif kind == "factory-start":
        mode = str(payload.get("mode", "")).strip()
        executed_live = _bool(payload.get("executed_live"))
        if mode == "dry-run" and not executed_live:
            reasons.append("dry-run validado; evidência live ainda não existe.")
            return checks, reasons, "dry_run_only"
        reasons.append("factory-start sem evidência live suficiente para passed.")
        return checks, reasons, "needs_review"
    else:
        reasons.append("report não é um live canary concluído; revisão humana recomendada.")
        return checks, reasons, "needs_review"

    if (
        checks["executed_live_ok"]
        and checks["codex_exit_code_ok"]
        and checks["changed_files_ok"]
        and checks["allowed_files_changed_ok"]
        and checks["master_unchanged"]
        and checks["no_push"]
        and checks["no_deploy"]
        and checks["no_paid_api"]
        and checks["no_secrets"]
        and checks["readiness_ok"]
        and checks["sync_plan_ok"]
        and checks["python_compile_ok"]
        and checks["panel_ok"]
    ):
        return checks, reasons, "passed"

    if not checks["python_compile_ok"]:
        reasons.append("python_compile_ok precisa ser true.")
    if not checks["panel_ok"]:
        reasons.append("panel_ok precisa ser true.")

    if (
        not checks["executed_live_ok"]
        or not checks["codex_exit_code_ok"]
        or not checks["changed_files_ok"]
        or not checks["allowed_files_changed_ok"]
        or not checks["master_unchanged"]
        or not checks["no_push"]
        or not checks["no_deploy"]
        or not checks["no_paid_api"]
        or not checks["no_secrets"]
        or not checks["readiness_ok"]
        or not checks["sync_plan_ok"]
        or not checks["python_compile_ok"]
        or not checks["panel_ok"]
    ):
        return checks, reasons, "failed"

    return checks, reasons, "needs_review"


def _evaluation_report_path(repo: Path, run_id: str, *, created_at: str) -> Path:
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d-%H%M%S")
    return _evaluations_root(repo) / f"{timestamp}-{run_id}.json"


def _load_source_report(report: Path) -> tuple[dict[str, Any] | None, str]:
    if not report.exists():
        return None, "missing"

    if not report.is_file() or report.is_symlink():
        raise TaskRunnerError("report inválido.")

    payload = _load_json_file(report)
    return payload, "present"


def _evaluate_from_payload(
    *,
    repo: Path,
    run_id: str,
    source_report: Path,
    payload: dict[str, Any] | None,
    kind: str,
    created_at: str,
    local_validations: dict[str, bool],
) -> dict[str, Any]:
    checks, reasons, decision = _build_checks(
        payload=payload,
        kind=kind,
        report_exists=source_report.exists(),
        local_validations=local_validations,
    )
    report = {
        "ok": True,
        "run_id": run_id,
        "source_report": source_report.relative_to(repo).as_posix() if source_report.exists() else "",
        "decision": decision,
        "checks": checks,
        "reasons": reasons,
        "created_at": created_at,
    }
    evaluation_path = _evaluation_report_path(repo, run_id, created_at=created_at)
    report["report_path"] = evaluation_path.relative_to(repo).as_posix()
    _write_json_atomic(evaluation_path, report)
    return report


def evaluate_execution(
    *,
    run_id: str | None = None,
    report_path: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    created_at = _now_iso()
    local_validations = _local_validation_results()

    if (run_id is None and report_path is None) or (run_id is not None and report_path is not None):
        raise TaskRunnerError("informe exatamente um de --run-id ou --report.")

    if run_id is not None:
        normalized_run_id = _validate_run_id(run_id)
        try:
            show_run(normalized_run_id, repo=repo)
        except TaskRunnerError as exc:
            report = {
                "ok": True,
                "run_id": normalized_run_id,
                "source_report": "",
                "decision": "blocked",
                "checks": _blocked_checks(local_validations),
                "reasons": [str(exc)],
                "created_at": created_at,
            }
            evaluation_path = _evaluation_report_path(repo, normalized_run_id, created_at=created_at)
            report["report_path"] = evaluation_path.relative_to(repo).as_posix()
            _write_json_atomic(evaluation_path, report)
            return report

        source_report_path, payload = _source_report_for_run(repo, normalized_run_id)
        if source_report_path is None:
            report = {
                "ok": True,
                "run_id": normalized_run_id,
                "source_report": "",
                "decision": "blocked",
                "checks": _blocked_checks(local_validations),
                "reasons": ["nenhum report relacionado encontrado."],
                "created_at": created_at,
            }
            evaluation_path = _evaluation_report_path(repo, normalized_run_id, created_at=created_at)
            report["report_path"] = evaluation_path.relative_to(repo).as_posix()
            _write_json_atomic(evaluation_path, report)
            return report

        kind = _report_kind(payload or {}, source_report_path)
        source_run_id = _payload_run_id(payload or {}, kind) or normalized_run_id
        if payload is None:
            report = {
                "ok": True,
                "run_id": source_run_id,
                "source_report": source_report_path.relative_to(repo).as_posix(),
                "decision": "blocked",
                "checks": _blocked_checks(local_validations),
                "reasons": ["payload do report ausente."],
                "created_at": created_at,
            }
            evaluation_path = _evaluation_report_path(repo, source_run_id, created_at=created_at)
            report["report_path"] = evaluation_path.relative_to(repo).as_posix()
            _write_json_atomic(evaluation_path, report)
            return report
        report = _evaluate_from_payload(
            repo=repo,
            run_id=source_run_id,
            source_report=source_report_path,
            payload=payload,
            kind=kind,
            created_at=created_at,
            local_validations=local_validations,
        )
        return report

    safe_report_path = _safe_path_from_report_input(report_path or "")
    source_report = repo / safe_report_path
    payload = None
    try:
        payload, _ = _load_source_report(source_report)
    except TaskRunnerError as exc:
        report = {
            "ok": True,
            "run_id": _infer_run_id_from_report_path(safe_report_path),
            "source_report": safe_report_path,
            "decision": "blocked",
            "checks": {
                "json_valid": False,
                "executed_live_ok": False,
                "codex_exit_code_ok": False,
                "changed_files_ok": False,
                "allowed_files_changed_ok": False,
                "master_unchanged": False,
                "no_push": False,
                "no_deploy": False,
                "no_paid_api": False,
                "no_secrets": False,
                "readiness_ok": False,
                "sync_plan_ok": False,
                "python_compile_ok": False,
                "panel_ok": False,
            },
            "reasons": [str(exc)],
            "created_at": created_at,
        }
        run_id_for_report = _infer_run_id_from_report_path(safe_report_path)
        evaluation_path = _evaluation_report_path(repo, run_id_for_report, created_at=created_at)
        report["report_path"] = evaluation_path.relative_to(repo).as_posix()
        _write_json_atomic(evaluation_path, report)
        return report

    if payload is None:
        run_id_for_report = _infer_run_id_from_report_path(safe_report_path)
        report = {
            "ok": True,
            "run_id": run_id_for_report,
            "source_report": safe_report_path,
            "decision": "blocked",
            "checks": _blocked_checks(local_validations),
            "reasons": ["report ausente."],
            "created_at": created_at,
        }
        evaluation_path = _evaluation_report_path(repo, run_id_for_report, created_at=created_at)
        report["report_path"] = evaluation_path.relative_to(repo).as_posix()
        _write_json_atomic(evaluation_path, report)
        return report

    kind = _report_kind(payload or {}, source_report)
    run_id_value = _payload_run_id(payload or {}, kind) or _infer_run_id_from_report_path(safe_report_path)

    try:
        show_run(run_id_value, repo=repo)
    except TaskRunnerError as exc:
        report = {
            "ok": True,
            "run_id": run_id_value,
            "source_report": safe_report_path,
            "decision": "blocked",
            "checks": _blocked_checks(local_validations),
            "reasons": [str(exc)],
            "created_at": created_at,
        }
        evaluation_path = _evaluation_report_path(repo, run_id_value, created_at=created_at)
        report["report_path"] = evaluation_path.relative_to(repo).as_posix()
        _write_json_atomic(evaluation_path, report)
        return report

    report = _evaluate_from_payload(
        repo=repo,
        run_id=run_id_value,
        source_report=source_report,
        payload=payload,
        kind=kind,
        created_at=created_at,
        local_validations=local_validations,
    )
    return report


def execution_close_if_passed(
    *,
    run_id: str,
    dry_run: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_run_id = _validate_run_id(run_id)
    evaluation = evaluate_execution(run_id=normalized_run_id, repo=repo)

    response: dict[str, Any] = {
        "ok": True,
        "run_id": normalized_run_id,
        "dry_run": dry_run,
        "evaluation": evaluation,
        "closed": False,
        "close_reason": "",
    }

    if evaluation.get("decision") != "passed":
        response["close_reason"] = "evaluation não passou."
        return response

    if dry_run:
        response["close_reason"] = "dry-run solicitado."
        return response

    run_result = show_run(normalized_run_id, repo=repo)
    run = run_result["run"]
    task_result = show_task(str(run["task_id"]), repo=repo)
    task = task_result["task"]

    if run.get("status") != "running" or task.get("status") != "running":
        response["close_reason"] = "run/task não estão ambos em running."
        return response

    try:
        finished_task = finish_task(str(task["id"]), repo=repo)
        finished_run = finish_run(normalized_run_id, repo=repo)
    except TaskRunnerError as exc:
        response["close_reason"] = f"falha ao fechar run/task: {exc}"
        return response

    response["closed"] = True
    response["close_reason"] = "run e task movidas para done."
    response["task_result"] = finished_task
    response["run_result"] = finished_run
    return response


def load_latest_execution_evaluation(repo: Path) -> LatestExecutionEvaluationResult:
    latest = latest_report("execution-evaluations", repo=repo)
    if latest is not None:
        payload = latest.payload
        run_id = str(payload.get("run_id", "")).strip()
        source_report = str(payload.get("source_report", "")).strip()
        decision = str(payload.get("decision", "")).strip()
        checks = payload.get("checks", {})
        reasons = payload.get("reasons", [])
        created_at = str(payload.get("created_at", "")).strip()

        if run_id and decision and created_at and isinstance(checks, dict) and isinstance(reasons, list):
            if not source_report or _safe_relative_report_path(source_report):
                return LatestExecutionEvaluationResult(
                    available=True,
                    run_id=run_id,
                    source_report=source_report,
                    report_path=latest.relative_path,
                    view_path=latest.view_path,
                    decision=decision,
                    checks={str(key): bool(value) for key, value in checks.items()},
                    reasons=[str(item) for item in reasons],
                    created_at=created_at,
                )

    return LatestExecutionEvaluationResult(
        available=False,
        run_id="",
        source_report="",
        report_path="",
        view_path=None,
        decision="not_available",
        checks={},
        reasons=[],
        created_at="",
    )
