from __future__ import annotations

import json
import re
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.artifact_intake import run_artifact_intake_plan
from app.mvp_apply_plan import run_mvp_apply_plan_create
from app.mvp_delivery_package import run_mvp_delivery_package_create
from app.obsidian_sync import run_obsidian_project_sync
from app.report_retention import run_report_retention_cleanup_plan
from app.task_runner import TaskRunnerError

SECURITY_REVIEW_VERSION = "v0"
SECURITY_REVIEW_REPORT_DIR = "security-safety-reviews"
SECURITY_REVIEW_PROJECT = "demo-simple-web-mvp-safe-split"
SECRET_SCAN_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
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
    return repo / "reports" / SECURITY_REVIEW_REPORT_DIR / f"{_timestamp()}.json"


def _check_cli_safety(repo: Path) -> dict[str, Any]:
    source = (repo / "app" / "cli.py").read_text(encoding="utf-8")
    checks = {
        "dry_run_live_mutex": "--dry-run e --live" in source,
        "apply_dry_run_only": "aceita somente --dry-run" in source,
        "no_push_flag": "--no-push" in source,
        "no_deploy_flag": "--no-deploy" in source,
        "no_paid_api_flag": "--no-paid-api" in source,
        "no_secrets_flag": "--no-secrets" in source,
    }
    failed = [key for key, ok in checks.items() if not ok]
    return {"ok": not failed, "checks": checks, "failed": failed}


def _check_panel_viewer(repo: Path) -> dict[str, Any]:
    from app import web

    original_repo_root = web.repo_root
    try:
        web.repo_root = lambda: repo  # type: ignore[assignment]
        client = TestClient(web.create_app())
        root = client.get("/")
        traversal = client.get("/view/docs/..%2FREADME.md")
        hidden = client.get("/view/docs/.env")
        return {
            "ok": root.status_code == 200 and traversal.status_code in {400, 404} and hidden.status_code in {400, 404},
            "root_status_code": root.status_code,
            "traversal_status_code": traversal.status_code,
            "hidden_status_code": hidden.status_code,
            "read_only": True,
        }
    except Exception as exc:  # pragma: no cover - defensive review behavior
        return {"ok": False, "error": str(exc)}
    finally:
        web.repo_root = original_repo_root  # type: ignore[assignment]


def _check_artifact_intake_blocks(repo: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=repo / "reports") as tmp:
        source = Path(tmp) / "payload.exe"
        source.write_text("blocked", encoding="utf-8")
        try:
            run_artifact_intake_plan(project_name=SECURITY_REVIEW_PROJECT, source=source, dry_run=True, repo=repo)
        except TaskRunnerError as exc:
            return {"ok": True, "blocked": True, "error": str(exc)}
    return {"ok": False, "blocked": False, "error": "extensão perigosa foi aceita"}


def _check_delivery_exclusions(repo: Path) -> dict[str, Any]:
    workspace = repo / "workspaces" / "projects" / SECURITY_REVIEW_PROJECT
    try:
        report = run_mvp_delivery_package_create(project_name=SECURITY_REVIEW_PROJECT, workspace=workspace, dry_run=True, repo=repo)
    except TaskRunnerError as exc:
        return {"ok": False, "error": str(exc)}
    patterns = report.get("excluded_patterns", {})
    exact = set(patterns.get("exact_names", []))
    dirs = set(patterns.get("dirs", []))
    suffixes = set(patterns.get("suffixes", []))
    ok = ".env" in exact and "node_modules" in dirs and ".key" in suffixes and ".sqlite" in suffixes
    return {"ok": ok, "report_path": report.get("report_path"), "excluded_patterns": patterns}


def _check_obsidian_bounds(repo: Path) -> dict[str, Any]:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            vault_root = Path(tmp) / "10-Projetos" / "FactoryOS"
            report = run_obsidian_project_sync(
                project_name="FactoryOS",
                dry_run=True,
                write=False,
                repo=repo,
                vault_root=vault_root,
            )
    except TaskRunnerError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": bool(report.get("ok")) and report.get("written") is False, "report_path": report.get("report_path")}


def _check_retention_dry_run(repo: Path) -> dict[str, Any]:
    report = run_report_retention_cleanup_plan(repo=repo)
    return {
        "ok": report.get("safe_to_apply") is False and report.get("deleted_files") == [] and report.get("moved_files") == [],
        "report_path": report.get("report_path"),
        "safe_to_apply": report.get("safe_to_apply"),
        "deleted_files": report.get("deleted_files"),
        "moved_files": report.get("moved_files"),
    }


def _check_apply_gate(repo: Path) -> dict[str, Any]:
    latest_canary_dir = repo / "reports" / "mvp-capsule-build-canaries"
    candidates = sorted(latest_canary_dir.glob("*.json"), reverse=True) if latest_canary_dir.exists() else []
    for candidate in candidates:
        try:
            report = run_mvp_apply_plan_create(canary_report=candidate, dry_run=True, repo=repo)
        except TaskRunnerError:
            continue
        ok = report.get("human_review_required") is True and report.get("safe_to_apply") is False
        return {"ok": ok, "report_path": report.get("report_path"), "safe_to_apply": report.get("safe_to_apply")}
    return {"ok": False, "error": "nenhum canary válido para validar apply gate"}


def _check_backend_frontend_docs(repo: Path) -> dict[str, Any]:
    paths = [
        repo / "docs" / "backend-frontend-scaffold-split.md",
        repo / "workspaces" / "projects" / SECURITY_REVIEW_PROJECT / "backend" / "README.md",
        repo / "workspaces" / "projects" / SECURITY_REVIEW_PROJECT / "frontend" / "README.md",
    ]
    content = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file()).lower()
    checks = {
        "backend_mentions_rules": "regras críticas" in content or "regra crítica" in content,
        "frontend_mentions_no_secrets": "nenhum segredo no frontend" in content or "nunca secrets" in content,
    }
    failed = [key for key, ok in checks.items() if not ok]
    return {"ok": not failed, "checks": checks, "failed": failed}


def _scan_recent_docs_reports(repo: Path) -> dict[str, Any]:
    roots = [repo / "docs", repo / "reports"]
    findings: list[dict[str, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 256 * 1024:
                continue
            if path.suffix.lower() not in {".md", ".txt", ".json"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in SECRET_SCAN_PATTERNS:
                if pattern.search(content):
                    findings.append({"path": path.relative_to(repo).as_posix(), "pattern": pattern.pattern})
                    break
    return {"ok": not findings, "finding_count": len(findings), "findings": findings[:25]}


def run_factoryos_v1_security_review(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-v1-security-review aceita somente --dry-run.")
    repo = repo or repo_root()
    checks = {
        "cli_safety": _check_cli_safety(repo),
        "panel_viewer": _check_panel_viewer(repo),
        "artifact_intake_blocks": _check_artifact_intake_blocks(repo),
        "delivery_exclusions": _check_delivery_exclusions(repo),
        "obsidian_bounds": _check_obsidian_bounds(repo),
        "retention_dry_run": _check_retention_dry_run(repo),
        "apply_gate": _check_apply_gate(repo),
        "backend_frontend_docs": _check_backend_frontend_docs(repo),
        "recent_secret_scan": _scan_recent_docs_reports(repo),
    }
    blockers = [key for key, value in checks.items() if not value.get("ok")]
    warnings: list[str] = []
    decision = "failed" if blockers else ("needs_review" if warnings else "passed")
    report_path = _report_path(repo)
    report = {
        "ok": True,
        "security_review_version": SECURITY_REVIEW_VERSION,
        "dry_run": True,
        "executed_live": False,
        "security_decision": decision,
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
