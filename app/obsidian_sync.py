from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.project_workspace import discover_project_workspaces
from app.report_index import latest_report
from app.task_runner import TaskRunnerError

OBSIDIAN_SYNC_VERSION = "v0"
OBSIDIAN_SYNC_REPORT_DIR = "obsidian-project-syncs"
ALLOWED_VAULT_ROOT = Path("<OBSIDIAN_VAULT>/10-Projetos/FactoryOS")
SECRET_PATTERNS = (
    re.compile(r"(?i)\bapi[_-]?key\b"),
    re.compile(r"(?i)\bsecret\b"),
    re.compile(r"(?i)\btoken\b"),
    re.compile(r"(?i)\bpassword\b"),
    re.compile(r"(?i)\bprivate[_-]?key\b"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def _report_path(repo: Path, project_name: str) -> Path:
    filename = f"{_timestamp()}-{_slugify(project_name)}.json"
    return _unique_path(repo / "reports" / OBSIDIAN_SYNC_REPORT_DIR / filename)


def _note_path(project_name: str, vault_root: Path | None = None) -> Path:
    root = (vault_root or ALLOWED_VAULT_ROOT).resolve()
    return root / f"{project_name.strip()} - Estado atual.md"


def _load_project_snapshot(project_name: str, repo: Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "project_name": project_name,
        "workspace": None,
        "latest_reports": [],
        "workspace_status": None,
    }
    for project in discover_project_workspaces(repo):
        if str(project.get("project_name", "")).strip() == project_name:
            snapshot["workspace"] = {
                "path": project.get("workspace_path"),
                "relative_path": project.get("workspace_relative_path"),
                "status": project.get("status"),
                "notes": project.get("notes", []),
            }
            break
    report_kinds = [
        "artifact-intakes",
        "mvp-delivery-packages",
        "project-pilot-runbooks",
        "factoryos-v1-readiness-gates",
        "obsidian-project-syncs",
        "report-retention",
    ]
    snapshot["latest_reports"] = [
        {
            "kind": kind,
            "report_path": entry.relative_path,
        }
        for kind in report_kinds
        if (entry := latest_report(kind, repo=repo)) is not None
    ]
    return snapshot


def _build_note_content(project_name: str, repo: Path) -> str:
    snapshot = _load_project_snapshot(project_name, repo)
    workspace = snapshot.get("workspace") or {}
    workspace_path = workspace.get("path") or "desconhecido"
    workspace_status = workspace.get("status") or "unknown"
    notes = workspace.get("notes") or []
    latest_reports = snapshot.get("latest_reports") or []
    content = "\n".join(
        [
            f"# {project_name} - Estado atual",
            "",
            "Memória curta operacional do projeto.",
            "",
            "## Estado",
            f"- workspace: `{workspace_path}`",
            f"- status: `{workspace_status}`",
            f"- no_push=true",
            f"- no_deploy=true",
            f"- no_paid_api=true",
            f"- no_secrets=true",
            "",
            "## Observações",
            *(f"- {note}" for note in notes[:5]),
            "",
            "## Reports recentes",
            *(f"- `{item['kind']}`: `{item['report_path']}`" for item in latest_reports),
            "",
            "## Próximo passo",
            "- manter a sequência controlada das sprints operacionais.",
        ]
    ).strip() + "\n"
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise TaskRunnerError("conteúdo de Obsidian contém padrão sensível.")
    return content


def run_obsidian_project_sync(
    *,
    project_name: str,
    dry_run: bool,
    write: bool,
    repo: Path | None = None,
    vault_root: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")
    if dry_run and write:
        raise TaskRunnerError("--dry-run e --write são mutuamente exclusivos.")
    if not dry_run and not write:
        dry_run = True

    root = (vault_root or ALLOWED_VAULT_ROOT).resolve()
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise TaskRunnerError("vault root symlink não permitido.")

    note_path = _note_path(normalized_project, vault_root=root)
    if root not in note_path.resolve().parents and note_path.resolve() != root:
        raise TaskRunnerError("nota fora do vault permitido.")

    content = _build_note_content(normalized_project, repo)
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    written = False
    if write and not dry_run:
        _write_text_atomic(note_path, content)
        written = True

    report_path = _report_path(repo, normalized_project)
    report = {
        "ok": True,
        "obsidian_sync_version": OBSIDIAN_SYNC_VERSION,
        "project_name": normalized_project,
        "note_path": str(note_path),
        "vault_root": str(root),
        "dry_run": bool(dry_run),
        "write_requested": bool(write),
        "written": written,
        "human_review_required": bool(write),
        "content_sha256": content_hash,
        "content_length": len(content),
        "content_preview": content[:320],
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
