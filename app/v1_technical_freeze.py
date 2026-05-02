from __future__ import annotations

import json
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.report_index import latest_report
from app.task_runner import TaskRunnerError
from app.v1_closure import POST_080_NEXT_STEPS, run_factoryos_v1_readiness_closure

TECHNICAL_FREEZE_VERSION = "v0"
TECHNICAL_FREEZE_REPORT_DIR = "factoryos-v1-technical-freeze"
PROOF_PATH = "reports/factoryos-v1-technical-freeze-v0-proof.txt"


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
    return repo / "reports" / TECHNICAL_FREEZE_REPORT_DIR / f"{_timestamp()}.json"


def _git_snapshot(repo: Path) -> dict[str, Any]:
    status = subprocess.run(["git", "-C", str(repo), "status", "--short", "--branch"], capture_output=True, text=True, check=False)
    diff_check = subprocess.run(["git", "-C", str(repo), "diff", "--check"], capture_output=True, text=True, check=False)
    lines = [line for line in status.stdout.splitlines() if line.strip()]
    dirty = [line for line in lines if not line.startswith("## ")]
    return {
        "ok": status.returncode == 0 and diff_check.returncode == 0,
        "branch_line": lines[0] if lines else "",
        "dirty_entries": dirty,
        "clean": status.returncode == 0 and not dirty,
        "diff_check_ok": diff_check.returncode == 0,
        "diff_check_output": (diff_check.stdout or diff_check.stderr).strip(),
    }


def _latest_closure(repo: Path) -> str | None:
    try:
        entry = latest_report("final-v1-readiness-closure", repo=repo)
    except TaskRunnerError:
        return None
    return None if entry is None else entry.relative_path


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "FactoryOS V1 technical freeze V0 proof",
        f"report_path={report['report_path']}",
        f"final_v1_status={report['final_v1_status']}",
        f"human_review_required={str(report['human_review_required']).lower()}",
        f"blockers={','.join(report['blockers']) if report['blockers'] else 'none'}",
        "visual_final_ready=false",
        "executed_live=false",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_factoryos_v1_technical_freeze(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-technical-freeze aceita somente --dry-run.")
    repo = repo or repo_root()
    closure = run_factoryos_v1_readiness_closure(dry_run=True, repo=repo)
    git = _git_snapshot(repo)
    closure_ok = closure.get("closure_decision") == "ready_for_technical_freeze" and closure.get("technical_freeze_allowed") is True
    blockers = [] if closure_ok else ["readiness_closure"]
    warnings = [] if git.get("clean") else ["git_dirty_after_report_generation"]
    final_v1_status = "technical_freeze_ready" if not blockers else "failed"
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "factoryos_v1_technical_freeze_version": TECHNICAL_FREEZE_VERSION,
        "dry_run": True,
        "executed_live": False,
        "final_v1_status": final_v1_status,
        "technical_freeze_ready": final_v1_status == "technical_freeze_ready",
        "visual_final_ready": False,
        "human_review_required": True,
        "blockers": blockers,
        "warnings": warnings,
        "fixed_items": [],
        "closure": {
            "ok": closure_ok,
            "closure_decision": closure.get("closure_decision"),
            "technical_freeze_allowed": closure.get("technical_freeze_allowed"),
            "human_review_required": closure.get("human_review_required"),
            "report_path": closure.get("report_path"),
            "latest_closure_report_before_freeze": _latest_closure(repo),
        },
        "git": git,
        "ready_for_next_steps": {
            "deep_hygiene": True,
            "ui_ux_polish": True,
            "final_gate": True,
            "github_backup_with_explicit_authorization": True,
        },
        "post_080_next_steps": POST_080_NEXT_STEPS,
        "explicit_non_actions": {
            "push_performed": False,
            "deploy_performed": False,
            "deep_cleanup_performed": False,
            "visual_final_claimed": False,
            "paid_api_used": False,
            "secrets_changed": False,
        },
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
