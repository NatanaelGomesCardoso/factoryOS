from __future__ import annotations

import argparse
import io
import json
import re
import secrets
import subprocess
import tempfile
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.mvp_evaluator import run_mvp_evaluate
from app.mvp_templates import list_templates, validate_template
from app.report_index import latest_report
from app.task_runner import TaskRunnerError
from app.v1_readiness_gate import run_factoryos_v1_readiness_gate

V1_AUDIT_VERSION = "v0"
V1_AUDIT_REPORT_DIR = "factoryos-v1-audits"
V1_AUDIT_PROJECT = "demo-simple-web-mvp-safe-split"

REQUIRED_COMMANDS = [
    "factory-start",
    "factory-queue-start",
    "project-intake-create",
    "mvp-build-plan-create",
    "mvp-capsule-build-canary",
    "mvp-apply-plan-create",
    "project-workspace-scaffold",
    "mvp-template-list",
    "mvp-evaluate",
    "project-pilot-runbook-create",
    "factoryos-v1-readiness-gate",
    "codex-run-result-check",
    "report-latest",
    "report-list",
]

REQUIRED_REPORT_KINDS = [
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
    "factoryos-v1-readiness-gates",
]

REQUIRED_DOCS_AND_SPECS = [
    "docs/reusable-mvp-templates.md",
    "docs/backend-frontend-scaffold-split.md",
    "docs/mvp-validation-evaluator.md",
    "docs/project-panel-dashboard.md",
    "docs/artifact-asset-intake.md",
    "docs/mvp-delivery-package.md",
    "docs/obsidian-project-memory-sync.md",
    "docs/report-retention-cleanup-policy-v1.md",
    "docs/first-project-pilot-runbook.md",
    "docs/factoryos-v1-readiness-gate.md",
    "specs/sprints/065-reusable-mvp-templates-v0.json",
    "specs/sprints/066-backend-frontend-scaffold-split-v0.json",
    "specs/sprints/067-mvp-validation-evaluator-v0.json",
    "specs/sprints/068-project-panel-dashboard-v0.json",
    "specs/sprints/069-artifact-asset-intake-v0.json",
    "specs/sprints/070-mvp-delivery-package-v0.json",
    "specs/sprints/071-obsidian-project-memory-sync-v0.json",
    "specs/sprints/072-report-retention-cleanup-policy-v1.json",
    "specs/sprints/073-first-project-pilot-runbook-v0.json",
    "specs/sprints/074-factoryos-v1-readiness-gate-v0.json",
]


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
    return repo / "reports" / V1_AUDIT_REPORT_DIR / f"{_timestamp()}.json"


def _subparser_commands() -> set[str]:
    import app.cli as cli

    parser = cli.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices.keys())
    return set()


def _check_commands() -> dict[str, Any]:
    commands = _subparser_commands()
    missing = [command for command in REQUIRED_COMMANDS if command not in commands]
    return {"ok": not missing, "required": REQUIRED_COMMANDS, "missing": missing}


def _check_reports(repo: Path) -> dict[str, Any]:
    missing = [kind for kind in REQUIRED_REPORT_KINDS if latest_report(kind, repo=repo) is None]
    latest = {
        kind: None if (entry := latest_report(kind, repo=repo)) is None else entry.relative_path
        for kind in REQUIRED_REPORT_KINDS
    }
    return {"ok": not missing, "required": REQUIRED_REPORT_KINDS, "missing": missing, "latest": latest}


def _check_templates() -> dict[str, Any]:
    template_ids = [template.template_id for template in list_templates()]
    validations = {template_id: validate_template(template_id).get("final_decision") for template_id in template_ids}
    failed = [template_id for template_id, decision in validations.items() if decision != "passed"]
    return {"ok": bool(template_ids) and not failed, "template_ids": template_ids, "validations": validations}


def _check_workspace_and_evaluator(repo: Path) -> dict[str, Any]:
    workspace = repo / "workspaces" / "projects" / V1_AUDIT_PROJECT
    result: dict[str, Any] = {
        "workspace_path": workspace.as_posix(),
        "workspace_exists": workspace.is_dir(),
        "readme_exists": (workspace / "README.md").is_file(),
        "project_state_exists": (workspace / "PROJECT_STATE.md").is_file(),
        "evaluator_decision": None,
        "evaluator_report_path": None,
        "ok": False,
    }
    if not workspace.is_dir():
        return result
    try:
        evaluator = run_mvp_evaluate(project_name=V1_AUDIT_PROJECT, workspace=workspace, dry_run=True, repo=repo)
    except TaskRunnerError as exc:
        result["error"] = str(exc)
    else:
        result["evaluator_decision"] = evaluator.get("final_decision")
        result["evaluator_report_path"] = evaluator.get("report_path")
        result["ok"] = evaluator.get("final_decision") in {"passed", "needs_review"}
    return result


def _check_readiness_gate(repo: Path) -> dict[str, Any]:
    try:
        report = run_factoryos_v1_readiness_gate(dry_run=True, repo=repo)
    except TaskRunnerError as exc:
        return {"ok": False, "error": str(exc)}
    decision = report.get("readiness_decision")
    return {
        "ok": decision in {"ready_for_audit", "needs_review"},
        "readiness_decision": decision,
        "report_path": report.get("report_path"),
    }


def _check_panel(repo: Path) -> dict[str, Any]:
    from app import web

    original_repo_root = web.repo_root
    try:
        web.repo_root = lambda: repo  # type: ignore[assignment]
        response = TestClient(web.create_app()).get("/")
        return {"ok": response.status_code == 200, "status_code": response.status_code}
    except Exception as exc:  # pragma: no cover - defensive audit behavior
        return {"ok": False, "status_code": 0, "error": str(exc)}
    finally:
        web.repo_root = original_repo_root  # type: ignore[assignment]


def _check_quiet_runner_result_check() -> dict[str, Any]:
    from app.cli import cmd_codex_run_result_check

    scenarios = {
        "success": {"ok": True, "execution_status": "succeeded", "budget_status": "ok", "exit_code": 0},
        "warning_budget": {
            "ok": True,
            "execution_status": "succeeded",
            "budget_status": "warn",
            "exit_code": 0,
        },
    }
    results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for name, payload in scenarios.items():
            path = tmp_path / f"{name}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            stdout_buffer = io.StringIO()
            with redirect_stdout(stdout_buffer):
                exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))
            results[name] = {"exit_code": exit_code, "output": stdout_buffer.getvalue().strip()}
    ok = results["success"]["exit_code"] == 0 and results["warning_budget"]["exit_code"] == 0
    return {"ok": ok, "scenarios": results}


def _check_docs_and_specs(repo: Path) -> dict[str, Any]:
    missing = [path for path in REQUIRED_DOCS_AND_SPECS if not (repo / path).is_file()]
    return {"ok": not missing, "required": REQUIRED_DOCS_AND_SPECS, "missing": missing}


def _check_doc_command_names(repo: Path) -> dict[str, Any]:
    commands = _subparser_commands()
    external_commands = {"bash", "git", "harness", "python", "python3"}
    unknown: list[dict[str, str]] = []
    pattern = re.compile(r"^\s*-\s*`([a-z][a-z0-9-]+)\s+[^`]+`", re.MULTILINE)
    for doc_path in sorted((repo / "docs").glob("*.md")):
        content = doc_path.read_text(encoding="utf-8")
        for command in pattern.findall(content):
            if command in commands or command in external_commands or command.startswith("codex-"):
                continue
            unknown.append({"doc": doc_path.relative_to(repo).as_posix(), "command": command})
    return {"ok": not unknown, "unknown_commands": unknown[:50], "unknown_count": len(unknown)}


def _check_safety_defaults(repo: Path) -> dict[str, Any]:
    cli_source = (repo / "app" / "cli.py").read_text(encoding="utf-8")
    checks = {
        "dry_run_live_mutex_present": "--dry-run e --live" in cli_source,
        "push_flag_is_opt_in": "--no-push" in cli_source,
        "deploy_flag_is_opt_in": "--no-deploy" in cli_source,
        "paid_api_flag_is_opt_in": "--no-paid-api" in cli_source,
        "secrets_flag_is_opt_in": "--no-secrets" in cli_source,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return {"ok": not failed, "checks": checks, "failed": failed}


def _run_git_diff_check(repo: Path) -> dict[str, Any]:
    completed = subprocess.run(["git", "-C", str(repo), "diff", "--check"], capture_output=True, text=True, check=False)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "output": (completed.stdout or completed.stderr).strip()}


def run_factoryos_v1_audit(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-audit aceita somente --dry-run.")

    repo = repo or repo_root()
    checks = {
        "commands": _check_commands(),
        "reports": _check_reports(repo),
        "templates": _check_templates(),
        "workspace_evaluator": _check_workspace_and_evaluator(repo),
        "readiness_gate": _check_readiness_gate(repo),
        "panel": _check_panel(repo),
        "quiet_runner_result_check": _check_quiet_runner_result_check(),
        "docs_specs": _check_docs_and_specs(repo),
        "doc_command_names": _check_doc_command_names(repo),
        "safety_defaults": _check_safety_defaults(repo),
        "git_diff_check": _run_git_diff_check(repo),
    }
    blocker_keys = ["commands", "templates", "readiness_gate", "panel", "quiet_runner_result_check", "docs_specs", "git_diff_check"]
    warning_keys = ["reports", "workspace_evaluator", "doc_command_names", "safety_defaults"]
    blockers = [key for key in blocker_keys if not checks[key].get("ok")]
    warnings = [key for key in warning_keys if not checks[key].get("ok")]
    if blockers:
        decision = "failed"
    elif warnings:
        decision = "needs_review"
    else:
        decision = "passed"
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "factoryos_v1_audit_version": V1_AUDIT_VERSION,
        "dry_run": True,
        "executed_live": False,
        "audit_decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "suggested_fixes": [
            "corrigir comandos/docs ausentes antes das sprints finais",
            "manter reports novos em diretórios indexados",
        ] if decision != "passed" else [],
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
