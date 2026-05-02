from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

RELEASE_PACKAGING_VERSION = "v0"
PROOF_PATH = "reports/release-packaging-strategy-v0-proof.txt"


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


def _tracked_status(repo: Path) -> dict[str, Any]:
    head = (repo / ".git").is_dir()
    return {
        "git_repo_present": head,
        "current_branch": "preserve-current-history",
        "history_rewrite_allowed": False,
        "push_allowed": False,
    }


def _write_proof(repo: Path, payload: dict[str, Any]) -> None:
    lines = [
        "Sprint 087 release packaging strategy V0 proof",
        f"strategy_decision={payload['strategy_decision']}",
        f"backup_branch={payload['recommended_backup']['branch']}",
        f"backup_tag={payload['recommended_backup']['tag']}",
        f"export_path={payload['recommended_export']['path']}",
        f"human_review_required={str(payload['human_review_required']).lower()}",
        f"push_allowed={str(payload['push_allowed']).lower()}",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_release_packaging_strategy(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("release-packaging-strategy V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    branch_suffix = datetime.now().astimezone().strftime("%Y%m%d")
    payload: dict[str, Any] = {
        "ok": True,
        "release_packaging_strategy_version": RELEASE_PACKAGING_VERSION,
        "dry_run": True,
        "strategy_decision": "ready",
        "human_review_required": True,
        "push_allowed": False,
        "safe_to_publish": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "repository": repo.as_posix(),
        "git_state_policy": _tracked_status(repo),
        "recommended_backup": {
            "branch": f"backup/factoryos-pre-public-v1-{branch_suffix}",
            "tag": f"factoryos-pre-public-v1-{branch_suffix}",
            "mode": "local-only-before-any-public-export",
            "rules": [
                "nao reescrever historico",
                "nao apagar reports no branch atual",
                "nao fazer push sem autorizacao explicita",
            ],
        },
        "recommended_export": {
            "path": "<FACTORYOS_CLEAN_EXPORT>",
            "mode": "clean-copy-without-git-history",
            "overwrite_existing": False,
            "create_remote": False,
        },
        "include_paths": [
            "app/",
            "docs/",
            "specs/sprints/essential-public-sprints-only",
            "README.md",
            "requirements.txt",
            "AGENTS.md if scrubbed for public use",
        ],
        "exclude_paths": [
            "reports/",
            "workspaces/",
            "runs/",
            "logs/",
            ".venv/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            "traces/",
            "screenshots/",
            "backup tarballs",
            "capsules and codex run outputs",
        ],
        "forbidden_paths": [
            ".env",
            ".env.*",
            "*.pem",
            "*.key",
            "*token*",
            "*secret*",
            "<FACTORYOS_ROOT>/reports",
            "<FACTORYOS_ROOT>/workspaces",
        ],
        "secret_protection": {
            "scan_names": True,
            "scan_content_patterns": ["token", "secret", "api_key", "password", "BEGIN PRIVATE KEY"],
            "print_secret_values": False,
            "block_publish_on_suspected_secret": True,
        },
        "validation_plan": [
            "py_compile",
            "compileall app",
            "json.tool specs/sprints/087-release-packaging-strategy-v0.json",
            "release-packaging-strategy --dry-run",
            "git diff --check",
            "harness security-doctor --source-root <FACTORYOS_ROOT> --strict",
        ],
        "github_plan": [
            "criar backup local antes do export limpo",
            "criar export limpo sem .git e sem reports/workspaces",
            "validar export localmente",
            "revisao humana obrigatoria",
            "somente depois criar repo/remoto e push com autorizacao explicita",
        ],
        "created_at": _now_iso(),
        "report_path": PROOF_PATH,
    }
    _write_proof(repo, payload)
    _write_json_atomic(repo / "reports" / "release-packaging-strategy-v0.json", payload)
    return payload
