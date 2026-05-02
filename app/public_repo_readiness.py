from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.clean_export import run_clean_public_export_plan
from app.task_runner import TaskRunnerError

PUBLIC_REPO_READINESS_VERSION = "v0"
PROOF_PATH = "reports/final-public-repo-readiness-gate-v0-proof.txt"

REQUIRED_DOCS = {
    "help_center": "docs/README.md",
    "commands": "docs/COMMANDS.md",
    "install_run": "docs/GETTING_STARTED.md",
    "panel": "docs/LOCAL_PANEL.md",
    "security": "docs/SECURITY.md",
    "reversa": "docs/REVERSA.md",
    "cleanup_release": "docs/CLEANUP_AND_RELEASE.md",
    "release_packaging": "docs/release-packaging-strategy.md",
    "clean_export": "docs/clean-public-v1-export.md",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_text_atomic(path: Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink nao permitido: {path}")
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


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink nao permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _text_mentions(path: Path, needles: list[str]) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    return all(needle.lower() in text for needle in needles)


def _docs_checks(repo: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for key, rel in REQUIRED_DOCS.items():
        checks[key] = {
            "path": rel,
            "exists": (repo / rel).is_file(),
        }
    checks["readme"] = {"path": "README.md", "exists": (repo / "README.md").is_file()}
    checks["docs_dir"] = {"path": "docs", "exists": (repo / "docs").is_dir()}
    checks["help_center_documented"] = {
        "path": "docs/README.md",
        "exists": _text_mentions(repo / "docs/README.md", ["help", "center"]),
    }
    checks["commands_documented"] = {
        "path": "docs/COMMANDS.md",
        "exists": _text_mentions(repo / "docs/COMMANDS.md", ["release-packaging-strategy"]),
    }
    checks["github_push_default_blocked"] = {
        "path": "docs/release-packaging-strategy.md",
        "exists": _text_mentions(repo / "docs/release-packaging-strategy.md", ["push_allowed=false"]),
    }
    license_file = (repo / "LICENSE").is_file()
    license_declared = license_file or _text_mentions(repo / "README.md", ["license"])
    checks["license_status_declared"] = {
        "path": "LICENSE or README.md",
        "exists": license_declared,
    }
    return checks


def _missing_checks(checks: dict[str, Any]) -> list[str]:
    return [key for key, value in checks.items() if not bool(value.get("exists"))]


def _write_proof(repo: Path, payload: dict[str, Any]) -> None:
    lines = [
        "Sprint 089 final public repo readiness gate V0 proof",
        f"readiness_decision={payload['readiness_decision']}",
        f"safe_to_push={str(payload['safe_to_push']).lower()}",
        f"human_review_required={str(payload['human_review_required']).lower()}",
        f"missing_checks={payload['missing_checks_count']}",
        f"export_decision={payload['export']['export_decision']}",
        f"suspected_secrets_count={payload['export']['suspected_secrets_count']}",
        f"local_path_leaks_count={payload['export']['local_path_leaks_count']}",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_public_repo_readiness_gate(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("public-repo-readiness-gate V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    docs = _docs_checks(repo)
    missing = _missing_checks(docs)
    export = run_clean_public_export_plan(dry_run=True, repo=repo)
    export_unsafe = (
        export["export_decision"] == "failed"
        or export["suspected_secrets_count"] > 0
        or export["local_path_leaks_count"] > 0
    )
    if export["export_decision"] == "failed":
        readiness_decision = "failed"
    elif missing or export_unsafe:
        readiness_decision = "needs_review"
    else:
        readiness_decision = "ready_for_human_review"
    payload: dict[str, Any] = {
        "ok": readiness_decision != "failed",
        "public_repo_readiness_version": PUBLIC_REPO_READINESS_VERSION,
        "dry_run": True,
        "readiness_decision": readiness_decision,
        "safe_to_push": False,
        "safe_to_publish": False,
        "human_review_required": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "checks": docs,
        "missing_checks": missing,
        "missing_checks_count": len(missing),
        "export": {
            "export_decision": export["export_decision"],
            "export_path": export["export_path"],
            "included_count": export["included_count"],
            "excluded_count": export["excluded_count"],
            "suspected_secrets_count": export["suspected_secrets_count"],
            "local_path_leaks_count": export["local_path_leaks_count"],
            "reports_excluded": "reports" in export["excluded_roots"],
            "workspaces_excluded": "workspaces" in export["excluded_roots"],
            "env_excluded": ".env" in export["excluded_patterns"],
        },
        "github_policy": {
            "push_authorized_by_default": False,
            "remote_creation_allowed": False,
            "human_review_before_push": True,
        },
        "created_at": _now_iso(),
        "report_path": PROOF_PATH,
    }
    report_path = repo / "reports" / "final-public-repo-readiness-gate-v0.json"
    payload["json_report_path"] = report_path.relative_to(repo).as_posix()
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload
