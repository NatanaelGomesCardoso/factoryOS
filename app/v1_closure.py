from __future__ import annotations

import json
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.mvp_evaluator import run_mvp_evaluate
from app.report_index import latest_report
from app.task_runner import TaskRunnerError
from app.v1_audit import run_factoryos_v1_audit
from app.v1_polish import run_factoryos_v1_polish_check
from app.v1_readiness_gate import READINESS_GATE_PROJECT, run_factoryos_v1_readiness_gate
from app.v1_reliability import run_factoryos_v1_reliability_check
from app.v1_security_review import run_factoryos_v1_security_review

CLOSURE_VERSION = "v0"
CLOSURE_REPORT_DIR = "final-v1-readiness-closure"
PROOF_PATH = "reports/final-v1-readiness-closure-v0-proof.txt"

POST_080_NEXT_STEPS = [
    "deep hygiene",
    "UI/UX polish",
    "final gate",
    "GitHub backup com autorização explícita",
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
    return repo / "reports" / CLOSURE_REPORT_DIR / f"{_timestamp()}.json"


def _git_status(repo: Path) -> dict[str, Any]:
    branch = subprocess.run(["git", "-C", str(repo), "status", "--short", "--branch"], capture_output=True, text=True, check=False)
    diff_check = subprocess.run(["git", "-C", str(repo), "diff", "--check"], capture_output=True, text=True, check=False)
    lines = [line for line in branch.stdout.splitlines() if line.strip()]
    dirty = [line for line in lines if not line.startswith("## ")]
    return {
        "ok": branch.returncode == 0 and diff_check.returncode == 0,
        "branch_line": lines[0] if lines else "",
        "dirty_entries": dirty,
        "clean": branch.returncode == 0 and not dirty,
        "diff_check_ok": diff_check.returncode == 0,
        "diff_check_output": (diff_check.stdout or diff_check.stderr).strip(),
    }


def _panel_status(repo: Path) -> dict[str, Any]:
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


def _demo_project_status(repo: Path) -> dict[str, Any]:
    workspace = repo / "workspaces" / "projects" / READINESS_GATE_PROJECT
    status: dict[str, Any] = {
        "ok": False,
        "project": READINESS_GATE_PROJECT,
        "workspace_path": workspace.as_posix(),
        "workspace_exists": workspace.is_dir(),
        "readme_exists": (workspace / "README.md").is_file(),
        "project_state_exists": (workspace / "PROJECT_STATE.md").is_file(),
        "evaluator_decision": None,
        "evaluator_report_path": None,
    }
    if not workspace.is_dir():
        return status
    try:
        evaluator = run_mvp_evaluate(project_name=READINESS_GATE_PROJECT, workspace=workspace, dry_run=True, repo=repo)
    except TaskRunnerError as exc:
        status["error"] = str(exc)
    else:
        status["evaluator_decision"] = evaluator.get("final_decision")
        status["evaluator_report_path"] = evaluator.get("report_path")
        status["ok"] = evaluator.get("final_decision") in {"passed", "needs_review"}
    return status


def _latest_support_reports(repo: Path) -> dict[str, str | None]:
    kinds = {
        "readiness": "factoryos-v1-readiness-gates",
        "audit": "factoryos-v1-audits",
        "security": "security-safety-reviews",
        "reliability": "reliability-hardening",
        "polish": "final-v1-polish-consistency-pass",
    }
    latest: dict[str, str | None] = {}
    for label, kind in kinds.items():
        try:
            entry = latest_report(kind, repo=repo)
        except TaskRunnerError:
            entry = None
        latest[label] = None if entry is None else entry.relative_path
    return latest


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "FactoryOS V1 readiness closure V0 proof",
        f"report_path={report['report_path']}",
        f"closure_decision={report['closure_decision']}",
        f"technical_freeze_allowed={str(report['technical_freeze_allowed']).lower()}",
        f"human_review_required={str(report['human_review_required']).lower()}",
        f"blockers={','.join(report['blockers']) if report['blockers'] else 'none'}",
        "executed_live=false",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_factoryos_v1_readiness_closure(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-readiness-closure aceita somente --dry-run.")
    repo = repo or repo_root()
    readiness = run_factoryos_v1_readiness_gate(dry_run=True, repo=repo)
    audit = run_factoryos_v1_audit(dry_run=True, repo=repo)
    security = run_factoryos_v1_security_review(dry_run=True, repo=repo)
    reliability = run_factoryos_v1_reliability_check(dry_run=True, repo=repo)
    polish = run_factoryos_v1_polish_check(dry_run=True, repo=repo)
    git = _git_status(repo)
    panel = _panel_status(repo)
    demo = _demo_project_status(repo)
    checks = {
        "readiness": {"ok": readiness.get("readiness_decision") in {"ready_for_audit", "needs_review"}, "decision": readiness.get("readiness_decision"), "report_path": readiness.get("report_path")},
        "audit": {"ok": audit.get("audit_decision") in {"passed", "needs_review"}, "decision": audit.get("audit_decision"), "report_path": audit.get("report_path")},
        "security": {"ok": security.get("security_decision") in {"passed", "needs_review"}, "decision": security.get("security_decision"), "report_path": security.get("report_path")},
        "reliability": {"ok": reliability.get("reliability_decision") in {"passed", "needs_review"}, "decision": reliability.get("reliability_decision"), "report_path": reliability.get("report_path")},
        "polish": {"ok": polish.get("polish_decision") in {"passed", "needs_review"}, "decision": polish.get("polish_decision"), "report_path": polish.get("report_path")},
        "git": git,
        "panel": panel,
        "demo_project": demo,
    }
    blocker_keys = ["readiness", "audit", "security", "reliability", "polish", "panel", "demo_project"]
    blockers = [key for key in blocker_keys if not checks[key].get("ok")]
    warnings = [] if git.get("clean") else ["git_dirty_after_report_generation"]
    closure_decision = "failed" if blockers else "ready_for_technical_freeze"
    technical_freeze_allowed = not blockers
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "factoryos_v1_readiness_closure_version": CLOSURE_VERSION,
        "dry_run": True,
        "executed_live": False,
        "closure_decision": closure_decision,
        "human_review_required": True,
        "technical_freeze_allowed": technical_freeze_allowed,
        "blockers": blockers,
        "warnings": warnings,
        "fixed_items": [],
        "checks": checks,
        "latest_support_reports": _latest_support_reports(repo),
        "post_080_next_steps": POST_080_NEXT_STEPS,
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
