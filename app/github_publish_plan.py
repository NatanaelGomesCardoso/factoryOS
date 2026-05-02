from __future__ import annotations

import json
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.clean_export import DEFAULT_EXPORT_PATH, run_clean_public_export_plan, run_public_export_leak_review
from app.help_center import check_help_docs
from app.public_repo_readiness import run_public_repo_readiness_gate
from app.task_runner import TaskRunnerError

GITHUB_PUBLISH_PLAN_VERSION = "v0"
BACKUP_BRANCH = "backup/factoryos-full-history-v1"
BACKUP_TAG = "factoryos-v1-full-history"
PUBLISH_TARGET = "github-clean-export-v1"
PROOF_PATH = "reports/backup-branch-github-publish-plan-v0-proof.txt"
PLAN_REPORT_DIR = "reports/github-publish-plans"
ALLOWED_SPRINT_STATUS_PATHS = (
    "app/cli.py",
    "app/github_publish_plan.py",
    "github-backup-plan",
    "github-publish-plan",
    "github-release-checklist",
    "docs/github-backup-publish-plan.md",
    "specs/sprints/090-backup-branch-github-publish-plan-v0.json",
    "reports/clean-public-export-plan-v0.json",
    "reports/clean-public-v1-export-v0-proof.txt",
    "reports/final-public-repo-readiness-gate-v0.json",
    "reports/final-public-repo-readiness-gate-v0-proof.txt",
    "reports/public-export-leak-review-sanitization-v0-proof.txt",
    "reports/public-export-leak-reviews/",
    "reports/backup-branch-github-publish-plan-v0-proof.txt",
    "reports/github-publish-plans/",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


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


def _git_status_clean(repo: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return {"ok": False, "clean": False, "error": exc.__class__.__name__}
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    paths = [line[3:].strip() for line in lines if len(line) >= 4]
    external_paths = [
        path
        for path in paths
        if not any(path == allowed.rstrip("/") or path.startswith(allowed) for allowed in ALLOWED_SPRINT_STATUS_PATHS)
    ]
    return {
        "ok": completed.returncode == 0,
        "clean": completed.returncode == 0 and not external_paths,
        "dirty_count": len(lines),
        "external_dirty_count": len(external_paths),
        "allowed_sprint_dirty_count": len(paths) - len(external_paths),
        "ignored_allowed_sprint_paths": sorted(path for path in paths if path not in external_paths),
        "stderr_present": bool(completed.stderr.strip()),
    }


def _docs_exist(repo: Path) -> dict[str, Any]:
    required = {
        "github_backup_publish_plan": "docs/github-backup-publish-plan.md",
        "readme": "README.md",
        "commands": "docs/COMMANDS.md",
        "release_packaging": "docs/release-packaging-strategy.md",
        "clean_public_export": "docs/clean-public-v1-export.md",
        "public_readiness": "docs/final-public-repo-readiness-gate.md",
    }
    checks = {key: {"path": rel, "exists": (repo / rel).is_file()} for key, rel in required.items()}
    return {"ok": all(item["exists"] for item in checks.values()), "checks": checks}


def _manual_command(command: str, reason: str) -> dict[str, str]:
    return {
        "command": command,
        "mode": "preview_only",
        "manual_review_required": "true",
        "execute_now": "false",
        "reason": reason,
    }


def _common_payload(repo: Path, *, plan_type: str, commands_preview: list[dict[str, str]]) -> dict[str, Any]:
    report_rel_path = f"{PLAN_REPORT_DIR}/{_timestamp()}-{plan_type}.json"
    return {
        "ok": True,
        "github_publish_plan_version": GITHUB_PUBLISH_PLAN_VERSION,
        "plan_type": plan_type,
        "dry_run": True,
        "backup_branch": BACKUP_BRANCH,
        "backup_tag": BACKUP_TAG,
        "clean_export_path": DEFAULT_EXPORT_PATH.as_posix(),
        "publish_target": PUBLISH_TARGET,
        "safe_to_push": False,
        "safe_to_execute": False,
        "push_allowed": False,
        "human_review_required": True,
        "commands_preview": commands_preview,
        "blockers": [],
        "warnings": [
            "nao executar push, deploy, fetch, pull, rebase ou criacao remota nesta sprint",
            "publicar somente o export limpo apos revisao humana explicita",
        ],
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "created_at": _now_iso(),
        "repo": repo.as_posix(),
        "report_path": report_rel_path,
    }


def _persist_plan(repo: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _write_json_atomic(repo / str(payload["report_path"]), payload)
    _write_proof(repo, payload)
    return payload


def _write_proof(repo: Path, payload: dict[str, Any]) -> None:
    lines = [
        "Sprint 090 backup branch + GitHub publish plan V0 proof",
        f"plan_type={payload['plan_type']}",
        f"ok={str(payload['ok']).lower()}",
        f"dry_run={str(payload['dry_run']).lower()}",
        f"backup_branch={payload['backup_branch']}",
        f"backup_tag={payload['backup_tag']}",
        f"clean_export_path={payload['clean_export_path']}",
        f"publish_target={payload['publish_target']}",
        f"safe_to_push={str(payload['safe_to_push']).lower()}",
        f"push_allowed={str(payload['push_allowed']).lower()}",
        f"human_review_required={str(payload['human_review_required']).lower()}",
        f"blockers_count={len(payload['blockers'])}",
        f"warnings_count={len(payload['warnings'])}",
        f"report_path={payload['report_path']}",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def run_github_backup_plan(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("github-backup-plan V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    commands = [
        _manual_command(f"git branch {BACKUP_BRANCH}", "preservar historico completo local"),
        _manual_command(f"git tag {BACKUP_TAG}", "marcar snapshot completo local"),
    ]
    payload = _common_payload(repo, plan_type="backup", commands_preview=commands)
    payload.update(
        {
            "backup_mode": "local_only_full_history",
            "clean_export_required_before_public_push": True,
            "safe_to_execute": False,
            "execution_allowed": False,
        }
    )
    return _persist_plan(repo, payload)


def run_github_publish_plan(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("github-publish-plan V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    commands = [
        _manual_command("gh repo create <owner>/factoryos --private --source <FACTORYOS_CLEAN_EXPORT>", "criar repo somente apos revisao humana"),
        _manual_command("git remote add origin <git-url>", "configurar remoto apenas dentro do export limpo"),
        _manual_command("git push -u origin main", "push bloqueado ate autorizacao explicita"),
    ]
    payload = _common_payload(repo, plan_type="publish", commands_preview=commands)
    payload.update(
        {
            "remote_creation_plan": {
                "would_create_remote": False,
                "manual_review_required": True,
                "recommended_source": DEFAULT_EXPORT_PATH.as_posix(),
            },
            "publication_recommendation": "publicar somente o export limpo, nao o repo operacional completo",
            "warnings": [
                *payload["warnings"],
                "nao publicar branch com reports pesados como repo publico principal",
                "safe_to_push permanece false ate aprovacao explicita",
            ],
        }
    )
    return _persist_plan(repo, payload)


def run_github_release_checklist(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("github-release-checklist V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    git_status = _git_status_clean(repo)
    docs = _docs_exist(repo)
    help_docs = check_help_docs(dry_run=True)
    export_plan = run_clean_public_export_plan(dry_run=True, repo=repo)
    leak_review = run_public_export_leak_review(dry_run=True, repo=repo)
    readiness = run_public_repo_readiness_gate(dry_run=True, repo=repo)
    checks: dict[str, Any] = {
        "git_status_clean": git_status,
        "release_reports_ok": {"ok": readiness.get("ok") is True and leak_review.get("ok") is True},
        "suspected_secrets_zero": {"ok": int(leak_review.get("suspected_secrets_count", -1)) == 0, "count": leak_review.get("suspected_secrets_count")},
        "local_path_leaks_zero": {"ok": int(leak_review.get("local_path_leaks_count", -1)) == 0, "count": leak_review.get("local_path_leaks_count")},
        "docs_exist": docs,
        "readme_exists": {"ok": (repo / "README.md").is_file(), "path": "README.md"},
        "help_docs_ok": {"ok": help_docs.get("ok") is True, "panel_status": help_docs.get("panel_status"), "help_status": help_docs.get("help_status")},
        "export_readiness_ok": {
            "ok": readiness.get("readiness_decision") == "ready_for_human_review",
            "readiness_decision": readiness.get("readiness_decision"),
            "export_decision": readiness.get("export", {}).get("export_decision"),
        },
        "safe_to_push_false": {"ok": readiness.get("safe_to_push") is False},
        "human_review_required": {"ok": readiness.get("human_review_required") is True},
    }
    blockers = [key for key, value in checks.items() if not bool(value.get("ok"))]
    commands = [
        _manual_command("github-backup-plan --dry-run", "revisar backup local completo"),
        _manual_command("github-publish-plan --dry-run", "revisar publicacao GitHub sem execucao"),
        _manual_command("public-repo-readiness-gate --dry-run", "confirmar readiness antes de qualquer autorizacao"),
    ]
    payload = _common_payload(repo, plan_type="release-checklist", commands_preview=commands)
    payload.update(
        {
            "ok": not blockers,
            "release_checklist": "ok" if not blockers else "needs_review",
            "checks": checks,
            "blockers": blockers,
            "warnings": [
                *payload["warnings"],
                "checklist e plano nao autorizam push",
                "safe_to_push=false por contrato mesmo com readiness ok",
            ],
            "export": {
                "export_decision": export_plan.get("export_decision"),
                "suspected_secrets_count": export_plan.get("suspected_secrets_count"),
                "local_path_leaks_count": export_plan.get("local_path_leaks_count"),
                "readiness_decision": readiness.get("readiness_decision"),
            },
            "source_reports": {
                "export_plan": export_plan.get("report_path"),
                "leak_review": leak_review.get("report_path"),
                "public_readiness": readiness.get("json_report_path"),
            },
        }
    )
    return _persist_plan(repo, payload)
