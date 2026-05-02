from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.execution_evaluator import evaluate_execution
from app.factory_tick import run_factory_tick
from app.run_workspace import list_runs, run_workspace_readiness, run_workspace_sync_plan, show_run
from app.state_hygiene import factory_state_snapshot
from app.task_runner import TaskRunnerError

CONTROLLED_LOOP_REPORTS_DIR = "factory-loops"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_STEPS_LIMIT = 3


@dataclass(frozen=True, slots=True)
class LatestControlledLoopResult:
    available: bool
    loop_version: str
    loop_id: str
    run_id: str
    task_id: str
    mode: str
    status: str
    decision: str
    auto_selected: bool
    eligible_runs_count: int
    hygiene: dict[str, int]
    max_steps: int
    steps_executed: int
    started_at: str
    finished_at: str
    readiness_status: str | None
    sync_plan_status: str | None
    factory_tick_report: str
    evaluation_report: str
    executed_live: bool
    closed: bool
    reasons: list[str]
    view_path: str | None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / CONTROLLED_LOOP_REPORTS_DIR


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


def _loop_id(run_id: str, *, started_at: str) -> str:
    timestamp = datetime.fromisoformat(started_at).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{run_id}-{secrets.token_hex(3)}"


def _loop_report_path(repo: Path, loop_id: str) -> Path:
    return _reports_root(repo) / f"{loop_id}.json"


def _load_running_runs(repo: Path) -> list[dict[str, Any]]:
    run_groups = list_runs(repo=repo)["groups"]
    running_group = next(
        (group for group in run_groups if group["status"] == "running"),
        {"runs": []},
    )
    runs = running_group.get("runs", [])
    return [run for run in runs if isinstance(run, dict)]


def _single_run_context(run_id: str, repo: Path) -> dict[str, Any]:
    run_result = show_run(run_id, repo=repo)
    run = run_result["run"]
    if not isinstance(run, dict):
        raise TaskRunnerError("run inválida.")
    return run


def _build_selection_review(
    *,
    started_at: str,
    reason: str,
    candidates: list[dict[str, Any]],
    loop_version: str,
    auto_selected: bool,
    eligible_runs_count: int,
    hygiene: dict[str, int],
) -> dict[str, Any]:
    return {
        "ok": True,
        "loop_version": loop_version,
        "mode": "dry-run",
        "loop_id": _loop_id("unresolved", started_at=started_at),
        "run_id": "",
        "task_id": "",
        "auto_selected": auto_selected,
        "eligible_runs_count": eligible_runs_count,
        "hygiene": hygiene,
        "max_steps": 1,
        "steps_executed": 0,
        "started_at": started_at,
        "finished_at": _now_iso(),
        "status": "needs_review",
        "decision": "needs_review",
        "readiness_status": "",
        "sync_plan_status": "",
        "factory_tick_report": "",
        "evaluation_report": "",
        "executed_live": False,
        "closed": False,
        "reasons": [reason],
        "candidates": candidates[:3],
    }


def _build_report(
    *,
    loop_version: str,
    loop_id: str,
    run: dict[str, Any],
    started_at: str,
    finished_at: str,
    auto_selected: bool,
    eligible_runs_count: int,
    hygiene: dict[str, int],
    max_steps: int,
    steps_executed: int,
    status: str,
    decision: str,
    readiness_status: str | None,
    sync_plan_status: str | None,
    factory_tick_report: str,
    evaluation_report: str,
    reasons: list[str],
    executed_live: bool = False,
    closed: bool = False,
) -> dict[str, Any]:
    return {
        "ok": True,
        "loop_version": loop_version,
        "mode": "dry-run",
        "loop_id": loop_id,
        "run_id": str(run["id"]),
        "task_id": str(run["task_id"]),
        "auto_selected": auto_selected,
        "eligible_runs_count": eligible_runs_count,
        "hygiene": hygiene,
        "max_steps": max_steps,
        "steps_executed": steps_executed,
        "started_at": started_at,
        "finished_at": finished_at,
        "status": status,
        "decision": decision,
        "readiness_status": readiness_status or "",
        "sync_plan_status": sync_plan_status or "",
        "factory_tick_report": factory_tick_report,
        "evaluation_report": evaluation_report,
        "executed_live": executed_live,
        "closed": closed,
        "reasons": reasons,
    }


def _run_selection_snapshot(repo: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    running_runs = _load_running_runs(repo)
    eligible_runs: list[dict[str, Any]] = []
    run_snapshots: list[dict[str, Any]] = []

    for run in running_runs:
        run_id = str(run.get("id", "")).strip()
        task_id = str(run.get("task_id", "")).strip()
        workspace_path = str(run.get("workspace_path", "")).strip()
        readiness_status = ""
        sync_plan_status = ""
        reasons: list[str] = []

        try:
            readiness = run_workspace_readiness(run_id, repo=repo)["workspace"]
        except TaskRunnerError as exc:
            reasons.append(f"readiness error: {exc}")
        else:
            readiness_status = str(readiness.get("status", "")).strip()
            reasons.extend(
                [str(item) for item in readiness.get("reasons", []) if str(item).strip()]
            )

        if readiness_status == "ready":
            try:
                sync_plan = run_workspace_sync_plan(run_id, repo=repo)["plan"]
            except TaskRunnerError as exc:
                reasons.append(f"sync plan error: {exc}")
            else:
                sync_plan_status = str(sync_plan.get("status", "")).strip()
                reasons.extend(
                    [str(item) for item in sync_plan.get("reasons", []) if str(item).strip()]
                )

        run_snapshot = {
            "run_id": run_id,
            "task_id": task_id,
            "workspace_path": workspace_path,
            "readiness_status": readiness_status,
            "sync_plan_status": sync_plan_status,
            "reasons": reasons[:3],
        }
        run_snapshots.append(run_snapshot)

        if readiness_status == "ready" and sync_plan_status == "already_current":
            eligible_runs.append(run)

    return eligible_runs, run_snapshots


def _select_run(
    run_id: str | None,
    *,
    repo: Path,
    started_at: str,
    loop_version: str,
    hygiene: dict[str, int],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    eligible_runs, run_snapshots = _run_selection_snapshot(repo)
    selection_meta = {
        "auto_selected": False,
        "eligible_runs_count": len(eligible_runs),
        "hygiene": hygiene,
    }

    if run_id is not None:
        normalized_run_id = _validate_run_id(run_id)
        try:
            run = _single_run_context(normalized_run_id, repo)
        except TaskRunnerError as exc:
            return None, {
                "ok": True,
                "loop_version": loop_version,
                "mode": "dry-run",
                "loop_id": _loop_id(normalized_run_id, started_at=started_at),
                "run_id": normalized_run_id,
                "task_id": "",
                "auto_selected": False,
                "eligible_runs_count": len(eligible_runs),
                "hygiene": hygiene,
                "max_steps": 1,
                "steps_executed": 0,
                "started_at": started_at,
                "finished_at": _now_iso(),
                "status": "blocked",
                "decision": "blocked",
                "readiness_status": "",
                "sync_plan_status": "",
                "factory_tick_report": "",
                "evaluation_report": "",
                "executed_live": False,
                "closed": False,
                "reasons": [str(exc)],
            }, selection_meta

        return run, None, selection_meta

    if not run_snapshots:
        return None, {
            "ok": True,
            "loop_version": loop_version,
            "mode": "dry-run",
            "loop_id": _loop_id("no-running", started_at=started_at),
            "run_id": "",
            "task_id": "",
            "auto_selected": False,
            "eligible_runs_count": 0,
            "hygiene": hygiene,
            "max_steps": 1,
            "steps_executed": 0,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "status": "blocked",
            "decision": "blocked",
            "readiness_status": "",
            "sync_plan_status": "",
            "factory_tick_report": "",
            "evaluation_report": "",
            "executed_live": False,
            "closed": False,
            "reasons": ["nenhuma run running disponível para seleção automática segura."],
        }, selection_meta

    if not eligible_runs:
        return None, {
            "ok": True,
            "loop_version": loop_version,
            "mode": "dry-run",
            "loop_id": _loop_id("no-eligible", started_at=started_at),
            "run_id": "",
            "task_id": "",
            "auto_selected": False,
            "eligible_runs_count": 0,
            "hygiene": hygiene,
            "max_steps": 1,
            "steps_executed": 0,
            "started_at": started_at,
            "finished_at": _now_iso(),
            "status": "blocked",
            "decision": "blocked",
            "readiness_status": "",
            "sync_plan_status": "",
            "factory_tick_report": "",
            "evaluation_report": "",
            "executed_live": False,
            "closed": False,
            "reasons": ["nenhuma run running elegível com readiness=ready e sync_plan=already_current."],
            "candidates": run_snapshots[:3],
        }, selection_meta

    if len(eligible_runs) > 1:
        return None, _build_selection_review(
            started_at=started_at,
            reason="mais de uma run running elegível encontrada; passe --run-id explicitamente.",
            candidates=run_snapshots[:3],
            loop_version=loop_version,
            auto_selected=False,
            eligible_runs_count=len(eligible_runs),
            hygiene=hygiene,
        ), selection_meta

    selection_meta["auto_selected"] = True
    return eligible_runs[0], None, selection_meta


def run_controlled_loop(
    run_id: str | None = None,
    *,
    max_steps: int = 1,
    dry_run: bool = True,
    live: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    loop_version = "v1"
    if live:
        raise TaskRunnerError("live mode continua bloqueado no Controlled Execution Loop V1")

    _validate_max_steps(max_steps)
    repo = repo or repo_root()
    started_at = _now_iso()
    hygiene = factory_state_snapshot(repo=repo)

    selected_run, prebuilt_report, selection_meta = _select_run(
        run_id,
        repo=repo,
        started_at=started_at,
        loop_version=loop_version,
        hygiene=hygiene,
    )
    if prebuilt_report is not None:
        prebuilt_loop_id = str(prebuilt_report["loop_id"])
        prebuilt_report_path = _loop_report_path(repo, prebuilt_loop_id)
        prebuilt_report["report_path"] = prebuilt_report_path.relative_to(repo).as_posix()
        _write_json_atomic(prebuilt_report_path, prebuilt_report)
        return prebuilt_report

    assert selected_run is not None
    run = selected_run
    normalized_run_id = str(run["id"])
    loop_id = _loop_id(normalized_run_id, started_at=started_at)
    report_path = _loop_report_path(repo, loop_id)

    if run.get("status") != "running":
        finished_at = _now_iso()
        report = _build_report(
            loop_version=loop_version,
            loop_id=loop_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            auto_selected=selection_meta["auto_selected"],
            eligible_runs_count=selection_meta["eligible_runs_count"],
            hygiene=hygiene,
            max_steps=max_steps,
            steps_executed=0,
            status="needs_review",
            decision="needs_review",
            readiness_status="",
            sync_plan_status="",
            factory_tick_report="",
            evaluation_report="",
            reasons=[
                f"run precisa estar em running para o loop; status atual: {run.get('status', 'desconhecido')}"
            ],
        )
        _write_json_atomic(report_path, report)
        return report

    readiness = run_workspace_readiness(normalized_run_id, repo=repo)["workspace"]
    readiness_status = str(readiness.get("status", "")).strip() or None
    readiness_reasons = [str(item) for item in readiness.get("reasons", []) if str(item).strip()]
    if readiness_status != "ready":
        finished_at = _now_iso()
        report = _build_report(
            loop_version=loop_version,
            loop_id=loop_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            auto_selected=selection_meta["auto_selected"],
            eligible_runs_count=selection_meta["eligible_runs_count"],
            hygiene=hygiene,
            max_steps=max_steps,
            steps_executed=0,
            status="blocked",
            decision="blocked",
            readiness_status=readiness_status,
            sync_plan_status=None,
            factory_tick_report="",
            evaluation_report="",
            reasons=["readiness precisa ser ready antes do loop.", *readiness_reasons],
        )
        _write_json_atomic(report_path, report)
        return report

    sync_plan = run_workspace_sync_plan(normalized_run_id, repo=repo)["plan"]
    sync_plan_status = str(sync_plan.get("status", "")).strip() or None
    sync_plan_reasons = [str(item) for item in sync_plan.get("reasons", []) if str(item).strip()]
    if sync_plan_status != "already_current":
        finished_at = _now_iso()
        report = _build_report(
            loop_version=loop_version,
            loop_id=loop_id,
            run=run,
            started_at=started_at,
            finished_at=finished_at,
            auto_selected=selection_meta["auto_selected"],
            eligible_runs_count=selection_meta["eligible_runs_count"],
            hygiene=hygiene,
            max_steps=max_steps,
            steps_executed=0,
            status="blocked",
            decision="blocked",
            readiness_status=readiness_status,
            sync_plan_status=sync_plan_status,
            factory_tick_report="",
            evaluation_report="",
            reasons=["sync plan precisa ser already_current antes do loop.", *sync_plan_reasons],
        )
        _write_json_atomic(report_path, report)
        return report

    tick = run_factory_tick(normalized_run_id, dry_run=dry_run, live=False, repo=repo)
    factory_tick_report = str(tick.get("tick_report_path", "")).strip()
    tick_status = str(tick.get("status", "")).strip()

    evaluation_report_path = ""
    evaluation_reasons: list[str] = []
    evaluation_status = "needs_review"
    if factory_tick_report:
        try:
            evaluation = evaluate_execution(report_path=factory_tick_report, repo=repo)
        except TaskRunnerError as exc:
            evaluation_reasons = [f"evaluation falhou: {exc}"]
        else:
            evaluation_reasons = [str(item) for item in evaluation.get("reasons", []) if str(item).strip()]
            evaluation_created_at = str(evaluation.get("created_at", "")).strip()
            evaluation_run_id = str(evaluation.get("run_id", normalized_run_id)).strip()
            if evaluation_created_at:
                timestamp = datetime.fromisoformat(evaluation_created_at).strftime("%Y%m%d-%H%M%S")
                evaluation_report_path = f"reports/execution-evaluations/{timestamp}-{evaluation_run_id}.json"
            evaluation_status = str(evaluation.get("decision", "")).strip() or "needs_review"

    finished_at = _now_iso()
    status = "dry_run_only"
    decision = "dry_run_only"
    if tick_status == "failed":
        status = "failed"
        decision = "failed"
    elif tick_status == "blocked":
        status = "blocked"
        decision = "blocked"
    elif evaluation_status == "failed":
        status = "failed"
        decision = "failed"

    report = _build_report(
        loop_version=loop_version,
        loop_id=loop_id,
        run=run,
        started_at=started_at,
        finished_at=finished_at,
        auto_selected=selection_meta["auto_selected"],
        eligible_runs_count=selection_meta["eligible_runs_count"],
        hygiene=hygiene,
        max_steps=max_steps,
        steps_executed=1,
        status=status,
        decision=decision,
        readiness_status=readiness_status,
        sync_plan_status=sync_plan_status,
        factory_tick_report=factory_tick_report,
        evaluation_report=evaluation_report_path,
        reasons=["dry-run executado; live continua bloqueado."] if status == "dry_run_only" else ["dry-run falhou ou foi bloqueado.", *evaluation_reasons],
    )
    report["report_path"] = report_path.relative_to(repo).as_posix()
    _write_json_atomic(report_path, report)
    return report


def load_latest_controlled_loop_result(repo: Path) -> LatestControlledLoopResult:
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

        loop_version = str(payload.get("loop_version", "v0")).strip() or "v0"
        loop_id = str(payload.get("loop_id", "")).strip()
        run_id = str(payload.get("run_id", "")).strip()
        task_id = str(payload.get("task_id", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        status = str(payload.get("status", "")).strip()
        decision = str(payload.get("decision", "")).strip()
        auto_selected = bool(payload.get("auto_selected", False))
        eligible_runs_count = int(payload.get("eligible_runs_count", 0))
        hygiene = payload.get("hygiene", {})
        started_at = str(payload.get("started_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        readiness_status = payload.get("readiness_status")
        sync_plan_status = payload.get("sync_plan_status")
        factory_tick_report = str(payload.get("factory_tick_report", "")).strip()
        evaluation_report = str(payload.get("evaluation_report", "")).strip()
        reasons = payload.get("reasons", [])

        if not all([loop_id, mode, status, decision, started_at, finished_at]):
            continue

        actual_report_path = latest.relative_to(repo).as_posix()
        if not _safe_relative_path(
            actual_report_path,
            prefix=f"reports/{CONTROLLED_LOOP_REPORTS_DIR}/",
            suffix=".json",
        ):
            continue

        if not isinstance(reasons, list):
            continue

        if readiness_status is not None and not isinstance(readiness_status, str):
            continue
        if sync_plan_status is not None and not isinstance(sync_plan_status, str):
            continue
        if factory_tick_report and not _safe_relative_path(
            factory_tick_report,
            prefix="reports/factory-ticks/",
            suffix=".json",
        ):
            continue
        if evaluation_report and not _safe_relative_path(
            evaluation_report,
            prefix="reports/execution-evaluations/",
            suffix=".json",
        ):
            continue

        if not isinstance(hygiene, dict):
            continue

        return LatestControlledLoopResult(
            available=True,
            loop_version=loop_version,
            loop_id=loop_id,
            run_id=run_id,
            task_id=task_id,
            mode=mode,
            status=status,
            decision=decision,
            auto_selected=auto_selected,
            eligible_runs_count=eligible_runs_count,
            hygiene={
                "running_tasks_count": int(hygiene.get("running_tasks_count", 0)),
                "running_runs_count": int(hygiene.get("running_runs_count", 0)),
                "safe_to_close_count": int(hygiene.get("safe_to_close_count", 0)),
                "needs_review_count": int(hygiene.get("needs_review_count", 0)),
                "blocked_count": int(hygiene.get("blocked_count", 0)),
            },
            max_steps=int(payload.get("max_steps", 1)),
            steps_executed=int(payload.get("steps_executed", 0)),
            started_at=started_at,
            finished_at=finished_at,
            readiness_status=str(readiness_status).strip() if isinstance(readiness_status, str) and readiness_status.strip() else None,
            sync_plan_status=str(sync_plan_status).strip() if isinstance(sync_plan_status, str) and sync_plan_status.strip() else None,
            factory_tick_report=factory_tick_report,
            evaluation_report=evaluation_report,
            executed_live=bool(payload.get("executed_live", False)),
            closed=bool(payload.get("closed", False)),
            reasons=[str(item) for item in reasons],
            view_path=latest.relative_to(repo / "reports").as_posix(),
        )

    return LatestControlledLoopResult(
        available=False,
        loop_version="unknown",
        loop_id="",
        run_id="",
        task_id="",
        mode="unknown",
        status="blocked",
        decision="blocked",
        auto_selected=False,
        eligible_runs_count=0,
        hygiene={},
        max_steps=1,
        steps_executed=0,
        started_at="",
        finished_at="",
        readiness_status=None,
        sync_plan_status=None,
        factory_tick_report="",
        evaluation_report="",
        executed_live=False,
        closed=False,
        reasons=["Nenhum Controlled Loop válido encontrado em reports/factory-loops/."],
        view_path=None,
    )
