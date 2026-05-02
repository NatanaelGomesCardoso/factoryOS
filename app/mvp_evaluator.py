from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.mvp_templates import get_template
from app.project_workspace import load_project_state
from app.task_runner import TaskRunnerError

MVP_EVALUATOR_VERSION = "v0"
MVP_EVALUATIONS_DIR = "mvp-evaluations"
MAX_SECRET_SCAN_BYTES = 256 * 1024

PROHIBITED_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
PROHIBITED_SUFFIXES = {".pem", ".key", ".token", ".p12", ".pfx"}
SECRET_PATTERNS = [
    re.compile(r"(?i)\bapi[_-]?key\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bsecret\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\btoken\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bpassword\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bpasswd\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bprivate[_-]?key\b\s*[:=]\s*\S+"),
]


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "project"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return path.with_name(f"{path.name}-{secrets.token_hex(3)}")


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _report_path(repo: Path, project_name: str) -> Path:
    return _unique_path(repo / "reports" / MVP_EVALUATIONS_DIR / f"{_timestamp()}-{_slugify(project_name)}.json")


def _resolve_workspace(repo: Path, workspace: str | Path) -> Path:
    candidate = Path(workspace)
    if not candidate.is_absolute():
        candidate = (repo / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise TaskRunnerError(f"workspace inexistente: {candidate}")
    if not candidate.is_dir() or candidate.is_symlink():
        raise TaskRunnerError(f"workspace inválido: {candidate}")
    try:
        candidate.relative_to(repo.resolve())
    except ValueError as exc:
        raise TaskRunnerError("workspace precisa ficar dentro do repo.") from exc
    return candidate


def _is_prohibited_file(path: Path) -> bool:
    lowered = path.name.lower()
    if lowered in PROHIBITED_EXACT_NAMES:
        return True
    return any(lowered.endswith(suffix) for suffix in PROHIBITED_SUFFIXES)


def _is_textual(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py"}


def _scan_for_secrets(workspace: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in sorted(item for item in workspace.rglob("*") if item.is_file() and not item.is_symlink()):
        if path.stat().st_size > MAX_SECRET_SCAN_BYTES:
            continue
        if not _is_textual(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append({
                    "path": path.relative_to(workspace).as_posix(),
                    "pattern": pattern.pattern,
                })
                break
    return findings


def _walk_prohibited_files(workspace: Path) -> list[str]:
    prohibited: list[str] = []
    for path in sorted(item for item in workspace.rglob("*") if item.is_file() and not item.is_symlink()):
        if _is_prohibited_file(path):
            prohibited.append(path.relative_to(workspace).as_posix())
    return prohibited


def _bool_from_state(state: dict[str, str], key: str) -> bool:
    return state.get(key, "").strip().lower() == "true"


def run_mvp_evaluate(
    *,
    project_name: str,
    workspace: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("mvp-evaluate aceita somente --dry-run nesta sprint.")

    repo = _repo_root(repo)
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")

    workspace_path = _resolve_workspace(repo, workspace)
    state = load_project_state(workspace_path)
    template_id = state.get("template_id") or "simple-web-mvp"
    template = get_template(template_id)
    project_state_name = state.get("project_name") or workspace_path.name
    project_kind = state.get("kind") or template.kind

    readme_exists = (workspace_path / "README.md").is_file()
    state_exists = (workspace_path / "PROJECT_STATE.md").is_file()
    backend_exists = (workspace_path / "backend").is_dir()
    frontend_exists = (workspace_path / "frontend").is_dir()
    docs_exists = (workspace_path / "docs").is_dir()
    reports_exists = (workspace_path / "reports").is_dir()
    backend_readme_exists = (workspace_path / "backend" / "README.md").is_file()
    frontend_readme_exists = (workspace_path / "frontend" / "README.md").is_file()

    required_backend = template.backend_required
    required_frontend = template.frontend_required

    prohibited_files = _walk_prohibited_files(workspace_path)
    secret_findings = _scan_for_secrets(workspace_path)

    checks = {
        "project_name_matches_state": project_state_name == normalized_project,
        "readme_exists": readme_exists,
        "project_state_exists": state_exists,
        "docs_exists": docs_exists,
        "reports_exists": reports_exists,
        "backend_exists": backend_exists if required_backend else True,
        "frontend_exists": frontend_exists if required_frontend else True,
        "backend_readme_exists": backend_readme_exists,
        "frontend_readme_exists": frontend_readme_exists,
        "separation_documented": backend_readme_exists and frontend_readme_exists,
        "no_push": _bool_from_state(state, "no_push"),
        "no_deploy": _bool_from_state(state, "no_deploy"),
        "no_paid_api": _bool_from_state(state, "no_paid_api"),
        "no_secrets": _bool_from_state(state, "no_secrets"),
        "no_prohibited_files": not prohibited_files,
        "no_obvious_secrets": not secret_findings,
    }

    failed_checks = [name for name, ok in checks.items() if not ok and name in {"project_name_matches_state", "readme_exists", "project_state_exists", "docs_exists", "reports_exists", "backend_exists", "frontend_exists", "separation_documented", "no_push", "no_deploy", "no_paid_api", "no_secrets", "no_prohibited_files", "no_obvious_secrets"}]
    review_checks = [name for name, ok in checks.items() if not ok and name in {"backend_readme_exists", "frontend_readme_exists"}]

    if failed_checks:
        final_decision = "failed"
    elif review_checks:
        final_decision = "needs_review"
    else:
        final_decision = "passed"

    report_path = _report_path(repo, normalized_project)
    report = {
        "ok": True,
        "mvp_evaluator_version": MVP_EVALUATOR_VERSION,
        "project_name": normalized_project,
        "workspace_path": str(workspace_path),
        "workspace_relative_path": workspace_path.relative_to(repo).as_posix(),
        "template_id": template.template_id,
        "template_name": template.name,
        "project_kind": project_kind,
        "dry_run": True,
        "executed_live": False,
        "checks": checks,
        "failed_checks": failed_checks,
        "review_checks": review_checks,
        "warnings": [],
        "prohibited_files": prohibited_files,
        "secret_findings": secret_findings,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "final_decision": final_decision,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
