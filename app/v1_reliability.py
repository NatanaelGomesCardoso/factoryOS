from __future__ import annotations

import argparse
import io
import json
import secrets
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.mvp_evaluator import run_mvp_evaluate
from app.project_pilot_runbook import run_project_pilot_runbook_create
from app.report_index import latest_report, list_reports
from app.task_runner import TaskRunnerError
from app.v1_readiness_gate import run_factoryos_v1_readiness_gate

RELIABILITY_VERSION = "v0"
RELIABILITY_REPORT_DIR = "reliability-hardening"
RELIABILITY_PROJECT = "demo-simple-web-mvp-safe-split"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
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


def _report_path(repo: Path) -> Path:
    return repo / "reports" / RELIABILITY_REPORT_DIR / f"{_timestamp()}.json"


def _check_json_command_payloads(repo: Path) -> dict[str, Any]:
    import app.cli as cli

    commands = [
        ["mvp-template-list"],
        ["report-list", "factoryos-v1-readiness-gates", "--limit", "1"],
        ["report-latest", "factoryos-v1-readiness-gates"],
    ]
    results: list[dict[str, Any]] = []
    for command in commands:
        stdout_buffer = io.StringIO()
        try:
            with redirect_stdout(stdout_buffer):
                exit_code = cli.build_parser().parse_args(command).func(cli.build_parser().parse_args(command))
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
        output = stdout_buffer.getvalue().strip()
        json_ok = False
        if output:
            try:
                json.loads(output)
                json_ok = True
            except json.JSONDecodeError:
                json_ok = False
        results.append({"command": " ".join(command), "exit_code": exit_code, "json_ok": json_ok})
    return {"ok": all(item["exit_code"] == 0 and item["json_ok"] for item in results), "results": results}


def _check_warning_budget_result() -> dict[str, Any]:
    from app.cli import cmd_codex_run_result_check

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "warning-budget.json"
        path.write_text(
            json.dumps(
                {"ok": True, "execution_status": "succeeded", "budget_status": "warn", "exit_code": 0},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        stdout_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))
        payload = json.loads(stdout_buffer.getvalue())
    return {
        "ok": exit_code == 0 and payload.get("overall_status") == "succeeded_with_budget_warnings",
        "exit_code": exit_code,
        "overall_status": payload.get("overall_status"),
    }


def _check_readiness(repo: Path) -> dict[str, Any]:
    try:
        report = run_factoryos_v1_readiness_gate(dry_run=True, repo=repo)
    except TaskRunnerError as exc:
        return {"ok": False, "error": str(exc)}
    decision = report.get("readiness_decision")
    return {"ok": decision in {"ready_for_audit", "needs_review"}, "readiness_decision": decision, "report_path": report.get("report_path")}


def _check_reports_index(repo: Path) -> dict[str, Any]:
    kind = "factoryos-v1-readiness-gates"
    latest = latest_report(kind, repo=repo)
    listed = list_reports(kind, repo=repo, limit=3)
    return {"ok": latest is not None and bool(listed), "latest": None if latest is None else latest.relative_path, "count": len(listed)}


def _check_panel(repo: Path) -> dict[str, Any]:
    from app import web

    original_repo_root = web.repo_root
    try:
        web.repo_root = lambda: repo  # type: ignore[assignment]
        response = TestClient(web.create_app()).get("/")
        return {"ok": response.status_code == 200, "status_code": response.status_code}
    except Exception as exc:  # pragma: no cover - defensive check behavior
        return {"ok": False, "error": str(exc)}
    finally:
        web.repo_root = original_repo_root  # type: ignore[assignment]


def _check_demo_commands(repo: Path) -> dict[str, Any]:
    workspace = repo / "workspaces" / "projects" / RELIABILITY_PROJECT
    results: dict[str, Any] = {}
    try:
        runbook = run_project_pilot_runbook_create(project_name=RELIABILITY_PROJECT, dry_run=True, repo=repo)
        results["pilot_runbook"] = {"ok": bool(runbook.get("ok")), "report_path": runbook.get("report_path")}
    except TaskRunnerError as exc:
        results["pilot_runbook"] = {"ok": False, "error": str(exc)}
    try:
        evaluator = run_mvp_evaluate(project_name=RELIABILITY_PROJECT, workspace=workspace, dry_run=True, repo=repo)
        results["mvp_evaluate"] = {"ok": evaluator.get("final_decision") in {"passed", "needs_review"}, "report_path": evaluator.get("report_path")}
    except TaskRunnerError as exc:
        results["mvp_evaluate"] = {"ok": False, "error": str(exc)}
    return {"ok": all(item.get("ok") for item in results.values()), "results": results}


def _check_controlled_errors() -> dict[str, Any]:
    try:
        run_factoryos_v1_readiness_gate(dry_run=False)
    except TaskRunnerError as exc:
        return {"ok": "dry-run" in str(exc), "error": str(exc)}
    return {"ok": False, "error": "dry_run=false não foi bloqueado"}


def run_factoryos_v1_reliability_check(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-reliability-check aceita somente --dry-run.")
    repo = repo or repo_root()
    checks = {
        "json_command_payloads": _check_json_command_payloads(repo),
        "warning_budget_result": _check_warning_budget_result(),
        "readiness_gate": _check_readiness(repo),
        "reports_index": _check_reports_index(repo),
        "panel": _check_panel(repo),
        "demo_commands": _check_demo_commands(repo),
        "controlled_errors": _check_controlled_errors(),
    }
    blockers = [key for key, value in checks.items() if not value.get("ok")]
    warnings: list[str] = []
    decision = "failed" if blockers else ("needs_review" if warnings else "passed")
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "reliability_version": RELIABILITY_VERSION,
        "dry_run": True,
        "executed_live": False,
        "reliability_decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "fixed_items": [],
        "checks": checks,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
