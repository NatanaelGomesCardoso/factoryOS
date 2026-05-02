from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

MVP_DELIVERY_PACKAGE_VERSION = "v0"
MVP_DELIVERY_PACKAGE_REPORT_DIR = "mvp-delivery-packages"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
}
EXCLUDED_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
EXCLUDED_SUFFIXES = {
    ".bak",
    ".env",
    ".key",
    ".log",
    ".pyc",
    ".p12",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".swp",
    ".tmp",
}


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


def _report_path(repo: Path, project_name: str) -> Path:
    filename = f"{_timestamp()}-{_slugify(project_name)}.json"
    return _unique_path(repo / "reports" / MVP_DELIVERY_PACKAGE_REPORT_DIR / filename)


def _resolve_workspace(repo: Path, workspace: str | Path) -> Path:
    candidate = Path(workspace)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (repo / candidate).resolve()
        try:
            resolved.relative_to(repo.resolve())
        except ValueError as exc:
            raise TaskRunnerError("workspace precisa ficar dentro do repo.") from exc

    if not resolved.exists():
        raise TaskRunnerError(f"workspace inexistente: {resolved}")
    if not resolved.is_dir():
        raise TaskRunnerError(f"workspace inválido: {resolved}")
    if resolved.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {resolved}")
    return resolved


def _is_excluded(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True
    lowered = path.name.lower()
    if lowered in EXCLUDED_EXACT_NAMES:
        return True
    return any(lowered.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def _collect_workspace_files(workspace: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        files.append(path)
    return files


def _build_package_file_lists(workspace: Path) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[str] = []
    excluded: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for path in _collect_workspace_files(workspace):
        relative = path.relative_to(workspace).as_posix()
        item = {"path": relative, "size_bytes": path.stat().st_size}
        if path.name.startswith(".") and path.name not in {".gitkeep"}:
            item["reason"] = "arquivo oculto excluído"
            excluded.append(item)
            continue
        if _is_excluded(path):
            item["reason"] = "padrão excluído"
            excluded.append(item)
            continue
        included.append(relative)
    return included, excluded, blocked


def run_mvp_delivery_package_create(
    *,
    project_name: str,
    workspace: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("mvp-delivery-package-create aceita somente --dry-run nesta sprint.")

    repo = repo or repo_root()
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")

    workspace_path = _resolve_workspace(repo, workspace)
    included_files, excluded_items, blocked_items = _build_package_file_lists(workspace_path)

    required_files = [
        "README.md",
        "PROJECT_STATE.md",
    ]
    required_present = {name: (workspace_path / name).is_file() for name in required_files}

    report_path = _report_path(repo, normalized_project)
    report = {
        "ok": True,
        "mvp_delivery_package_version": MVP_DELIVERY_PACKAGE_VERSION,
        "project_name": normalized_project,
        "workspace_path": str(workspace_path),
        "workspace_relative_path": workspace_path.relative_to(repo).as_posix() if workspace_path.is_relative_to(repo) else workspace_path.as_posix(),
        "dry_run": True,
        "package_created": False,
        "human_review_required": True,
        "package_name": f"{_slugify(normalized_project)}-mvp-delivery-package",
        "included_count": len(included_files),
        "excluded_count": len(excluded_items),
        "blocked_count": len(blocked_items),
        "required_files_present": required_present,
        "included_files": included_files,
        "excluded_items": excluded_items,
        "blocked_items": blocked_items,
        "excluded_patterns": {
            "dirs": sorted(EXCLUDED_DIRS),
            "exact_names": sorted(EXCLUDED_EXACT_NAMES),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
        },
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
