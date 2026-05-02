from __future__ import annotations

import argparse
import io
import json
import secrets
import subprocess
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.mvp_delivery_package import run_mvp_delivery_package_create
from app.mvp_evaluator import run_mvp_evaluate
from app.obsidian_sync import run_obsidian_project_sync
from app.report_index import latest_report, latest_report_for_project
from app.report_retention import run_report_retention_cleanup_plan
from app.task_runner import TaskRunnerError

READINESS_GATE_VERSION = "v0"
READINESS_GATE_REPORT_DIR = "factoryos-v1-readiness-gates"
READINESS_GATE_PROJECT = "demo-simple-web-mvp-safe-split"
READINESS_GATE_NOTE_PROJECT = "FactoryOS"


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
    return repo / "reports" / READINESS_GATE_REPORT_DIR / f"{_timestamp()}.json"


def _subparser_commands() -> set[str]:
    import app.cli as cli

    parser = cli.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices.keys())
    return set()


def _run_git_diff_check(repo: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), "diff", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0, (completed.stdout or completed.stderr or "").strip()


def _run_panel_check(repo: Path) -> dict[str, Any]:
    from app import web

    try:
        original_repo_root = web.repo_root
        web.repo_root = lambda: repo  # type: ignore[assignment]
        client = TestClient(web.create_app())
        response = client.get("/")
        return {
            "status_code": response.status_code,
            "ok": response.status_code == 200,
        }
    except Exception as exc:  # pragma: no cover - defensive gate behavior
        return {
            "status_code": 0,
            "ok": False,
            "error": str(exc),
        }
    finally:
        if "original_repo_root" in locals():
            web.repo_root = original_repo_root  # type: ignore[assignment]


def _quiet_runner_contract_check(repo: Path) -> dict[str, Any]:
    try:
        from app.cli import cmd_codex_run_result_check

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quiet-runner-check.json"
            path.write_text(
                json.dumps(
                    {
                        "ok": True,
                        "execution_status": "succeeded",
                        "budget_status": "ok",
                        "overall_status": "succeeded",
                        "timeout": False,
                        "exit_code": 0,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))
        return {
            "ok": exit_code == 0,
            "exit_code": exit_code,
            "output": stdout_buffer.getvalue().strip(),
        }
    except Exception as exc:  # pragma: no cover - defensive gate behavior
        return {
            "ok": False,
            "exit_code": 2,
            "output": str(exc),
        }


def _workspace_report_checks(repo: Path) -> dict[str, Any]:
    workspace_path = repo / "workspaces/projects" / READINESS_GATE_PROJECT
    workspace_exists = workspace_path.is_dir()
    evaluator_report = latest_report_for_project("mvp-evaluations", project_name=READINESS_GATE_PROJECT, repo=repo)
    delivery_report = latest_report_for_project("mvp-delivery-packages", project_name=READINESS_GATE_PROJECT, repo=repo)
    obsidian_report = latest_report_for_project("obsidian-project-syncs", project_name=READINESS_GATE_NOTE_PROJECT, repo=repo)
    retention_report = latest_report("report-retention", repo=repo)
    pilot_report = latest_report_for_project("project-pilot-runbooks", project_name=READINESS_GATE_NOTE_PROJECT, repo=repo)
    return {
        "workspace_path": workspace_path.as_posix(),
        "workspace_exists": workspace_exists,
        "evaluator_report_path": evaluator_report.relative_path if evaluator_report else None,
        "delivery_report_path": delivery_report.relative_path if delivery_report else None,
        "obsidian_report_path": obsidian_report.relative_path if obsidian_report else None,
        "retention_report_path": retention_report.relative_path if retention_report else None,
        "pilot_report_path": pilot_report.relative_path if pilot_report else None,
    }


def _check_commands() -> dict[str, Any]:
    commands = _subparser_commands()
    required = [
        "project-pilot-runbook-create",
        "factoryos-v1-readiness-gate",
        "project-intake-create",
        "mvp-build-plan-create",
        "mvp-capsule-build-canary",
        "mvp-apply-plan-create",
        "project-workspace-scaffold",
        "mvp-evaluate",
        "mvp-delivery-package-create",
        "obsidian-project-sync",
        "report-retention-cleanup-plan",
        "run-workspace-readiness",
        "run-handoff",
        "run-execute",
        "codex-run-result-check",
    ]
    missing = [command for command in required if command not in commands]
    return {
        "commands": required,
        "missing_commands": missing,
        "ok": not missing,
    }


def _check_reports(repo: Path) -> dict[str, Any]:
    required_kinds = [
        "project-intakes",
        "mvp-build-plans",
        "mvp-capsule-build-canaries",
        "mvp-apply-plans",
        "project-workspaces",
        "mvp-evaluations",
        "mvp-delivery-packages",
        "obsidian-project-syncs",
        "report-retention",
        "project-pilot-runbooks",
    ]
    missing = [kind for kind in required_kinds if latest_report(kind, repo=repo) is None]
    return {
        "required_kinds": required_kinds,
        "missing_reports": missing,
        "ok": not missing,
    }


def _check_workspace_demo(repo: Path) -> dict[str, Any]:
    workspace_path = repo / "workspaces/projects" / READINESS_GATE_PROJECT
    workspace_exists = workspace_path.is_dir()
    readme_exists = (workspace_path / "README.md").is_file()
    state_exists = (workspace_path / "PROJECT_STATE.md").is_file()
    evaluator_ok = False
    evaluator_decision = None
    evaluator_report_path = None
    if workspace_exists:
        try:
            evaluator = run_mvp_evaluate(
                project_name=READINESS_GATE_PROJECT,
                workspace=workspace_path,
                dry_run=True,
                repo=repo,
            )
        except TaskRunnerError as exc:
            evaluator_decision = f"error: {exc}"
        else:
            evaluator_ok = evaluator.get("final_decision") != "failed"
            evaluator_decision = evaluator.get("final_decision")
            evaluator_report_path = evaluator.get("report_path")
    return {
        "workspace_path": workspace_path.as_posix(),
        "workspace_exists": workspace_exists,
        "readme_exists": readme_exists,
        "state_exists": state_exists,
        "evaluator_ok": evaluator_ok,
        "evaluator_decision": evaluator_decision,
        "evaluator_report_path": evaluator_report_path,
    }


def _run_support_checks(repo: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    try:
        checks["delivery_package"] = run_mvp_delivery_package_create(
            project_name=READINESS_GATE_PROJECT,
            workspace=repo / "workspaces/projects" / READINESS_GATE_PROJECT,
            dry_run=True,
            repo=repo,
        )
    except Exception as exc:  # pragma: no cover - defensive gate behavior
        checks["delivery_package"] = {"ok": False, "error": str(exc)}
    try:
        checks["retention"] = run_report_retention_cleanup_plan(repo=repo)
    except Exception as exc:  # pragma: no cover - defensive gate behavior
        checks["retention"] = {"ok": False, "error": str(exc)}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            vault_root = Path(tmp) / "10-Projetos" / "FactoryOS"
            checks["obsidian"] = run_obsidian_project_sync(
                project_name=READINESS_GATE_NOTE_PROJECT,
                dry_run=True,
                write=False,
                repo=repo,
                vault_root=vault_root,
            )
    except Exception as exc:  # pragma: no cover - defensive gate behavior
        checks["obsidian"] = {"ok": False, "error": str(exc)}
    checks["quiet_runner"] = _quiet_runner_contract_check(repo)
    checks["panel"] = _run_panel_check(repo)
    git_ok, git_output = _run_git_diff_check(repo)
    checks["git_diff_check"] = {"ok": git_ok, "output": git_output}
    return checks


def _decision_from_checks(*, command_ok: bool, report_ok: bool, workspace_ok: bool, support_ok: bool, panel_ok: bool, git_ok: bool) -> tuple[str, list[str], list[str]]:
    failed_checks: list[str] = []
    review_checks: list[str] = []
    if not command_ok:
        failed_checks.append("commands")
    if not report_ok:
        failed_checks.append("reports")
    if not workspace_ok:
        review_checks.append("workspace_demo")
    if not support_ok:
        review_checks.append("support_contracts")
    if not panel_ok:
        failed_checks.append("panel")
    if not git_ok:
        failed_checks.append("git_diff_check")
    if failed_checks:
        return "failed", failed_checks, review_checks
    if review_checks:
        return "needs_review", failed_checks, review_checks
    return "ready_for_audit", failed_checks, review_checks


def run_factoryos_v1_readiness_gate(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-readiness-gate aceita somente --dry-run nesta sprint.")

    command_checks = _check_commands()
    workspace_checks = _check_workspace_demo(repo)
    support_checks = _run_support_checks(repo)
    report_checks = _check_reports(repo)
    panel_ok = bool(support_checks["panel"]["ok"])
    git_ok = bool(support_checks["git_diff_check"]["ok"])
    support_ok = all(
        bool(support_checks[key]["ok"])
        for key in ("delivery_package", "retention", "obsidian", "quiet_runner")
    )
    readiness_decision, failed_checks, review_checks = _decision_from_checks(
        command_ok=command_checks["ok"],
        report_ok=report_checks["ok"],
        workspace_ok=workspace_checks["workspace_exists"] and workspace_checks["evaluator_ok"],
        support_ok=support_ok,
        panel_ok=panel_ok,
        git_ok=git_ok,
    )

    report_path = _report_path(repo)
    report = {
        "ok": True,
        "factoryos_v1_readiness_gate_version": READINESS_GATE_VERSION,
        "dry_run": True,
        "readiness_decision": readiness_decision,
        "human_review_required": readiness_decision != "ready_for_audit",
        "command_checks": command_checks,
        "report_checks": report_checks,
        "workspace_checks": workspace_checks,
        "support_checks": support_checks,
        "panel_check": support_checks["panel"],
        "git_diff_check": support_checks["git_diff_check"],
        "failed_checks": failed_checks,
        "review_checks": review_checks,
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
