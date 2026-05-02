from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_handoff import run_execute, run_handoff
from app.run_workspace import run_workspace_readiness, run_workspace_sync_plan, show_run
from app.task_runner import TaskRunnerError

TICK_REPORTS_DIR = "factory-ticks"
TICK_STATUSES = {"passed", "blocked", "failed", "dry_run_only"}


@dataclass(frozen=True, slots=True)
class LatestFactoryTickResult:
    available: bool
    tick_id: str
    run_id: str
    task_id: str
    mode: str
    status: str
    started_at: str
    finished_at: str
    readiness_status: str | None
    sync_plan_status: str | None
    handoff_report_path: str
    tick_report_path: str
    view_path: str | None
    executed_live: bool
    decision_can_continue_to_live_future: bool
    decision_next_recommended_action: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / TICK_REPORTS_DIR


def _safe_relative_path(value: str, *, prefix: str, suffix: str) -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {".", ".."} for part in candidate.parts):
        return False

    return candidate.as_posix().startswith(prefix) and candidate.suffix == suffix


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink nao permitido: {path.name}")

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


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON invalido em {path.name}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")

    return payload


def _generate_tick_id(run_id: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{run_id}-{secrets.token_hex(3)}"


def _validate_tick_report(payload: dict[str, Any], *, expected_report_path: str) -> None:
    required_fields = {
        "ok",
        "mode",
        "tick_id",
        "run_id",
        "task_id",
        "started_at",
        "finished_at",
        "status",
        "readiness_status",
        "sync_plan_status",
        "handoff_report_path",
        "tick_report_path",
        "executed_live",
        "decision",
    }
    missing = required_fields - payload.keys()
    if missing:
        raise TaskRunnerError(f"tick report incompleto; faltam: {', '.join(sorted(missing))}")

    if payload.get("tick_report_path") != expected_report_path:
        raise TaskRunnerError("tick report_path nao corresponde ao arquivo gerado.")

    if payload.get("status") not in TICK_STATUSES:
        raise TaskRunnerError("status do tick invalido.")

    decision = payload.get("decision")
    if not isinstance(decision, dict):
        raise TaskRunnerError("decision do tick precisa ser um objeto.")


def _validate_run_execute_report(payload: dict[str, Any], *, expected_run_id: str, expected_report_path: str) -> None:
    if str(payload.get("run_id", "")).strip() != expected_run_id:
        raise TaskRunnerError("run_execute retornou run_id inesperado.")
    if payload.get("mode") != "dry-run":
        raise TaskRunnerError("run_execute precisa permanecer em dry-run.")
    if payload.get("executed") is not False:
        raise TaskRunnerError("run_execute nao pode executar live nesta sprint.")
    if payload.get("live_enabled") is not False:
        raise TaskRunnerError("run_execute nao pode habilitar live nesta sprint.")
    if str(payload.get("report_path", "")).strip() != expected_report_path:
        raise TaskRunnerError("report_path do run_execute nao bate com o esperado.")


def _empty_reason_text(reasons: list[str], fallback: str) -> str:
    return "; ".join(reasons) if reasons else fallback


def _blocked_report(
    *,
    tick_id: str,
    run: dict[str, Any],
    started_at: str,
    finished_at: str,
    readiness_status: str | None,
    sync_plan_status: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "dry-run",
        "tick_id": tick_id,
        "run_id": run["id"],
        "task_id": run["task_id"],
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "blocked",
        "readiness_status": readiness_status,
        "sync_plan_status": sync_plan_status,
        "handoff_report_path": "",
        "tick_report_path": "",
        "executed_live": False,
        "decision": {
            "can_continue_to_live_future": False,
            "next_recommended_action": reason,
        },
    }


def _failed_report(
    *,
    tick_id: str,
    run: dict[str, Any],
    started_at: str,
    finished_at: str,
    readiness_status: str | None,
    sync_plan_status: str | None,
    handoff_report_path: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "dry-run",
        "tick_id": tick_id,
        "run_id": run["id"],
        "task_id": run["task_id"],
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "failed",
        "readiness_status": readiness_status,
        "sync_plan_status": sync_plan_status,
        "handoff_report_path": handoff_report_path,
        "tick_report_path": "",
        "executed_live": False,
        "decision": {
            "can_continue_to_live_future": False,
            "next_recommended_action": reason,
        },
    }


def _success_report(
    *,
    tick_id: str,
    run: dict[str, Any],
    started_at: str,
    finished_at: str,
    readiness_status: str | None,
    sync_plan_status: str | None,
    handoff_report_path: str,
    tick_report_path: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "dry-run",
        "tick_id": tick_id,
        "run_id": run["id"],
        "task_id": run["task_id"],
        "started_at": started_at,
        "finished_at": finished_at,
        "status": "dry_run_only",
        "readiness_status": readiness_status,
        "sync_plan_status": sync_plan_status,
        "handoff_report_path": handoff_report_path,
        "tick_report_path": tick_report_path,
        "executed_live": False,
        "decision": {
            "can_continue_to_live_future": True,
            "next_recommended_action": "implement live canary in a future sprint",
        },
    }


def _load_running_run(run_id: str, *, repo: Path) -> dict[str, Any]:
    run_result = show_run(run_id, repo=repo)
    run = run_result["run"]
    if run.get("status") != "running":
        raise TaskRunnerError("run precisa estar em running para factory-tick.")
    return run


def _extract_status_and_reasons(result: dict[str, Any], key: str) -> tuple[str | None, list[str]]:
    section = result.get(key, {})
    if not isinstance(section, dict):
        return None, []

    status = section.get("status")
    status_text = str(status).strip() if isinstance(status, str) and status.strip() else None

    reasons_value = section.get("reasons", [])
    reasons = [str(item) for item in reasons_value] if isinstance(reasons_value, list) else []
    return status_text, reasons


def run_factory_tick(
    run_id: str,
    *,
    dry_run: bool = True,
    live: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    if live:
        raise TaskRunnerError("live mode is out of scope for Factory Tick V0")

    repo = repo or repo_root()
    run = _load_running_run(run_id, repo=repo)
    started_at = _now_iso()
    tick_id = _generate_tick_id(str(run["id"]))
    tick_report_path = _reports_root(repo) / f"{tick_id}.json"

    readiness = run_workspace_readiness(str(run["id"]), repo=repo)
    readiness_status, readiness_reasons = _extract_status_and_reasons(readiness, "workspace")
    if readiness_status != "ready":
        finished_at = _now_iso()
        report = _blocked_report(
            tick_id=tick_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            readiness_status=readiness_status,
            sync_plan_status=None,
            reason=f"readiness precisa ser ready antes do tick: {_empty_reason_text(readiness_reasons, 'workspace nao esta pronto.')}",
        )
        report["tick_report_path"] = tick_report_path.relative_to(repo).as_posix()
        _write_json_atomic(tick_report_path, report)
        _validate_tick_report(report, expected_report_path=report["tick_report_path"])
        return report

    sync_plan = run_workspace_sync_plan(str(run["id"]), repo=repo)
    sync_plan_status, sync_plan_reasons = _extract_status_and_reasons(sync_plan, "plan")
    if sync_plan_status != "already_current":
        finished_at = _now_iso()
        report = _blocked_report(
            tick_id=tick_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            readiness_status=readiness_status,
            sync_plan_status=sync_plan_status,
            reason=f"sync plan precisa ser already_current antes do tick: {_empty_reason_text(sync_plan_reasons, 'workspace nao esta sincronizado.')}",
        )
        report["tick_report_path"] = tick_report_path.relative_to(repo).as_posix()
        _write_json_atomic(tick_report_path, report)
        _validate_tick_report(report, expected_report_path=report["tick_report_path"])
        return report

    try:
        handoff = run_handoff(str(run["id"]), repo=repo)
        handoff_report_path = str(handoff.get("report_path", "")).strip()
        if not handoff_report_path:
            raise TaskRunnerError("run_handoff nao retornou report_path.")
        if not _safe_relative_path(handoff_report_path, prefix="reports/run-handoffs/", suffix=".json"):
            raise TaskRunnerError("report_path do handoff fora do formato permitido.")

        executed = run_execute(str(run["id"]), live=False, repo=repo)
        if executed.get("executed") is not False:
            raise TaskRunnerError("run_execute nao permaneceu em dry-run.")

        executed_report_path = str(executed.get("report_path", "")).strip()
        if executed_report_path != handoff_report_path:
            raise TaskRunnerError("run_execute nao reutilizou o report_path esperado.")

        executed_report_file = repo / executed_report_path
        if not executed_report_file.exists():
            raise TaskRunnerError("report do run_execute nao foi gravado.")

        final_report = _load_json_file(executed_report_file)
        _validate_run_execute_report(
            final_report,
            expected_run_id=str(run["id"]),
            expected_report_path=executed_report_path,
        )

    except TaskRunnerError as exc:
        finished_at = _now_iso()
        report = _failed_report(
            tick_id=tick_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            readiness_status=readiness_status,
            sync_plan_status=sync_plan_status,
            handoff_report_path=str(locals().get("handoff_report_path", "")).strip(),
            reason=f"factory tick falhou: {exc}",
        )
        report["tick_report_path"] = tick_report_path.relative_to(repo).as_posix()
        _write_json_atomic(tick_report_path, report)
        _validate_tick_report(report, expected_report_path=report["tick_report_path"])
        return report

    finished_at = _now_iso()
    report = _success_report(
        tick_id=tick_id,
        run=run,
        started_at=started_at,
        finished_at=finished_at,
        readiness_status=readiness_status,
        sync_plan_status=sync_plan_status,
        handoff_report_path=handoff_report_path,
        tick_report_path=tick_report_path.relative_to(repo).as_posix(),
    )
    _write_json_atomic(tick_report_path, report)
    _validate_tick_report(report, expected_report_path=report["tick_report_path"])
    return report


def load_latest_factory_tick_result(repo: Path) -> LatestFactoryTickResult:
    reports_dir = _reports_root(repo)
    candidates = sorted(
        reports_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for latest in candidates:
        try:
            payload = _load_json_file(latest)
        except Exception:
            continue

        tick_id = str(payload.get("tick_id", "")).strip()
        run_id = str(payload.get("run_id", "")).strip()
        task_id = str(payload.get("task_id", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        status = str(payload.get("status", "")).strip()
        started_at = str(payload.get("started_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        readiness_status = payload.get("readiness_status")
        sync_plan_status = payload.get("sync_plan_status")
        handoff_report_path = str(payload.get("handoff_report_path", "")).strip()
        tick_report_path = str(payload.get("tick_report_path", "")).strip()
        executed_live = bool(payload.get("executed_live", False))
        decision = payload.get("decision", {})

        if not all([tick_id, run_id, task_id, mode, status, started_at, finished_at, tick_report_path]):
            continue

        actual_report_path = latest.relative_to(repo).as_posix()
        if tick_report_path != actual_report_path:
            continue

        if not _safe_relative_path(tick_report_path, prefix=f"reports/{TICK_REPORTS_DIR}/", suffix=".json"):
            continue

        if handoff_report_path and not _safe_relative_path(
            handoff_report_path,
            prefix="reports/run-handoffs/",
            suffix=".json",
        ):
            continue

        if not isinstance(decision, dict):
            continue

        if readiness_status is not None and not isinstance(readiness_status, str):
            continue

        if sync_plan_status is not None and not isinstance(sync_plan_status, str):
            continue

        next_action = str(decision.get("next_recommended_action", "")).strip()

        return LatestFactoryTickResult(
            available=True,
            tick_id=tick_id,
            run_id=run_id,
            task_id=task_id,
            mode=mode,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            readiness_status=str(readiness_status).strip() if isinstance(readiness_status, str) and readiness_status.strip() else None,
            sync_plan_status=str(sync_plan_status).strip() if isinstance(sync_plan_status, str) and sync_plan_status.strip() else None,
            handoff_report_path=handoff_report_path,
            tick_report_path=tick_report_path,
            view_path=latest.relative_to(repo / "reports").as_posix(),
            executed_live=executed_live,
            decision_can_continue_to_live_future=bool(decision.get("can_continue_to_live_future", False)),
            decision_next_recommended_action=next_action or "Revisar o ultimo Factory Tick.",
        )

    return LatestFactoryTickResult(
        available=False,
        tick_id="",
        run_id="",
        task_id="",
        mode="unknown",
        status="blocked",
        started_at="",
        finished_at="",
        readiness_status=None,
        sync_plan_status=None,
        handoff_report_path="",
        tick_report_path="",
        view_path=None,
        executed_live=False,
        decision_can_continue_to_live_future=False,
        decision_next_recommended_action="Nenhum Factory Tick valido encontrado em reports/factory-ticks/.",
    )
