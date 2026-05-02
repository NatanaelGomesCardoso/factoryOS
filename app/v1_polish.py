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

from app.report_index import latest_report
from app.task_runner import TaskRunnerError
from app.v1_audit import run_factoryos_v1_audit
from app.v1_readiness_gate import run_factoryos_v1_readiness_gate
from app.v1_reliability import run_factoryos_v1_reliability_check
from app.v1_security_review import run_factoryos_v1_security_review

POLISH_VERSION = "v0"
POLISH_REPORT_DIR = "final-v1-polish-consistency-pass"
PROOF_PATH = "reports/final-v1-polish-consistency-pass-v0-proof.txt"

MAIN_COMMANDS = [
    "factory-start",
    "factory-queue-start",
    "project-intake-create",
    "mvp-build-plan-create",
    "mvp-capsule-build-canary",
    "mvp-apply-plan-create",
    "project-workspace-scaffold",
    "mvp-evaluate",
    "mvp-delivery-package-create",
    "obsidian-project-sync",
    "project-pilot-runbook-create",
    "factoryos-v1-readiness-gate",
    "factoryos-v1-audit",
    "factoryos-v1-security-review",
    "factoryos-v1-reliability-check",
    "factoryos-v1-polish-check",
]

CRITICAL_REPORT_KINDS = [
    "factoryos-v1-readiness-gates",
    "factoryos-v1-audits",
    "security-safety-reviews",
    "reliability-hardening",
]

MAIN_DOCS = [
    "README.md",
    "WORKFLOW.md",
    "docs/OPERATING_MODEL.md",
    "docs/factoryos-v1-readiness-gate.md",
    "docs/factoryos-v1-audit.md",
    "docs/factoryos-v1-security-hardening.md",
    "docs/factoryos-v1-reliability-hardening.md",
    "docs/project-panel-dashboard.md",
]

PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|PLACEHOLDER|XXX)\b|placeholder", re.IGNORECASE)


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
        temp_path.unlink(missing_ok=True)


def _write_text_atomic(path: Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _report_path(repo: Path) -> Path:
    return repo / "reports" / POLISH_REPORT_DIR / f"{_timestamp()}.json"


def _subparser_commands() -> set[str]:
    import app.cli as cli

    parser = cli.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices.keys())
    return set()


def _check_command_names(repo: Path) -> dict[str, Any]:
    commands = _subparser_commands()
    missing = [command for command in MAIN_COMMANDS if command not in commands]
    external = {"bash", "git", "harness", "python", "python3"}
    legacy_or_profile_commands = {
        "factoryos-heavy-review",
        "factoryos-lite-default",
        "factoryos-mini-medium",
        "factoryos-standard-medium",
        "project-intake",
        "running",
    }
    unknown: list[dict[str, str]] = []
    pattern = re.compile(r"`([a-z][a-z0-9-]+)(?:\s+[^`]*)?`")
    doc_paths = [repo / path for path in MAIN_DOCS if path.endswith(".md")] + [repo / "WORKFLOW.md"]
    for doc_path in sorted(set(doc_paths)):
        if not doc_path.is_file():
            continue
        content = doc_path.read_text(encoding="utf-8")
        for command in pattern.findall(content):
            if command in commands or command in external or command in legacy_or_profile_commands or command.startswith("codex-"):
                continue
            if command.startswith(("factory", "mvp", "project", "obsidian", "report", "run", "bounded")):
                unknown.append({"doc": doc_path.relative_to(repo).as_posix(), "command": command})
    return {"ok": not missing and not unknown, "missing_commands": missing, "unknown_doc_commands": unknown[:50]}


def _check_reports(repo: Path) -> dict[str, Any]:
    latest = {}
    missing = []
    safety_missing = []
    for kind in CRITICAL_REPORT_KINDS:
        entry = latest_report(kind, repo=repo)
        latest[kind] = None if entry is None else entry.relative_path
        if entry is None:
            missing.append(kind)
            continue
        flags = {key: entry.payload.get(key) is True for key in ("no_push", "no_deploy", "no_paid_api", "no_secrets")}
        if not all(flags.values()):
            safety_missing.append({"kind": kind, "flags": flags})
    return {"ok": not missing and not safety_missing, "latest": latest, "missing": missing, "safety_missing": safety_missing}


def _check_json_commands() -> dict[str, Any]:
    import app.cli as cli

    commands = [
        ["mvp-template-list"],
        ["factoryos-v1-readiness-gate", "--dry-run"],
        ["factoryos-v1-audit", "--dry-run"],
        ["factoryos-v1-security-review", "--dry-run"],
        ["factoryos-v1-reliability-check", "--dry-run"],
    ]
    results = []
    parser = cli.build_parser()
    for command in commands:
        stdout_buffer = io.StringIO()
        try:
            args = parser.parse_args(command)
            with redirect_stdout(stdout_buffer):
                exit_code = args.func(args)
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


def _check_v1_gates(repo: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    readiness = run_factoryos_v1_readiness_gate(dry_run=True, repo=repo)
    audit = run_factoryos_v1_audit(dry_run=True, repo=repo)
    security = run_factoryos_v1_security_review(dry_run=True, repo=repo)
    reliability = run_factoryos_v1_reliability_check(dry_run=True, repo=repo)
    checks["readiness"] = {"ok": readiness.get("readiness_decision") in {"ready_for_audit", "needs_review"}, "decision": readiness.get("readiness_decision"), "report_path": readiness.get("report_path")}
    checks["audit"] = {"ok": audit.get("audit_decision") in {"passed", "needs_review"}, "decision": audit.get("audit_decision"), "report_path": audit.get("report_path")}
    checks["security"] = {"ok": security.get("security_decision") in {"passed", "needs_review"}, "decision": security.get("security_decision"), "report_path": security.get("report_path")}
    checks["reliability"] = {"ok": reliability.get("reliability_decision") in {"passed", "needs_review"}, "decision": reliability.get("reliability_decision"), "report_path": reliability.get("report_path")}
    return {"ok": all(item["ok"] for item in checks.values()), "checks": checks}


def _check_docs(repo: Path) -> dict[str, Any]:
    missing = [path for path in MAIN_DOCS if not (repo / path).is_file()]
    findings = []
    for relative in MAIN_DOCS:
        path = repo / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for index, line in enumerate(content.splitlines(), start=1):
            if PLACEHOLDER_RE.search(line):
                findings.append({"path": relative, "line": index})
                break
    return {"ok": not missing and not findings, "missing": missing, "placeholder_findings": findings}


def _check_panel(repo: Path) -> dict[str, Any]:
    from app import web

    original_repo_root = web.repo_root
    try:
        web.repo_root = lambda: repo  # type: ignore[assignment]
        response = TestClient(web.create_app()).get("/")
        return {"ok": response.status_code == 200, "status_code": response.status_code}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "status_code": 0, "error": str(exc)}
    finally:
        web.repo_root = original_repo_root  # type: ignore[assignment]


def _check_git_diff(repo: Path) -> dict[str, Any]:
    completed = subprocess.run(["git", "-C", str(repo), "diff", "--check"], capture_output=True, text=True, check=False)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "output": (completed.stdout or completed.stderr).strip()}


def _check_warning_budget_contract() -> dict[str, Any]:
    from app.cli import cmd_codex_run_result_check

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "budget-blocked-success.json"
        path.write_text(json.dumps({"ok": True, "execution_status": "succeeded", "budget_status": "blocked", "exit_code": 0}, ensure_ascii=False) + "\n", encoding="utf-8")
        stdout_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer):
            exit_code = cmd_codex_run_result_check(argparse.Namespace(json=str(path)))
        payload = json.loads(stdout_buffer.getvalue())
    return {"ok": exit_code == 0 and payload.get("overall_status") == "succeeded_with_budget_warnings", "exit_code": exit_code, "overall_status": payload.get("overall_status")}


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "FactoryOS V1 final polish consistency pass V0 proof",
        f"report_path={report['report_path']}",
        f"polish_decision={report['polish_decision']}",
        f"blockers={','.join(report['blockers']) if report['blockers'] else 'none'}",
        f"warnings={','.join(report['warnings']) if report['warnings'] else 'none'}",
        "executed_live=false",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_factoryos_v1_polish_check(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-polish-check aceita somente --dry-run.")
    repo = repo or repo_root()
    checks = {
        "command_names": _check_command_names(repo),
        "critical_reports": _check_reports(repo),
        "json_commands": _check_json_commands(),
        "v1_gates": _check_v1_gates(repo),
        "docs": _check_docs(repo),
        "panel": _check_panel(repo),
        "git_diff_check": _check_git_diff(repo),
        "warning_budget_contract": _check_warning_budget_contract(),
    }
    blocker_keys = ["command_names", "critical_reports", "json_commands", "v1_gates", "panel", "git_diff_check", "warning_budget_contract"]
    warning_keys = ["docs"]
    blockers = [key for key in blocker_keys if not checks[key].get("ok")]
    warnings = [key for key in warning_keys if not checks[key].get("ok")]
    decision = "failed" if blockers else ("needs_review" if warnings else "passed")
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "factoryos_v1_polish_version": POLISH_VERSION,
        "dry_run": True,
        "executed_live": False,
        "polish_decision": decision,
        "blockers": blockers,
        "warnings": warnings,
        "fixed_items": [],
        "checks": checks,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "proof_path": PROOF_PATH,
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    _write_proof(repo, report)
    return report
