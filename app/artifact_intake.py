from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

ARTIFACT_INTAKE_VERSION = "v0"
ARTIFACT_INTAKE_REPORT_DIR = "artifact-intakes"

BLOCKED_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
BLOCKED_SUFFIXES = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".jar",
    ".key",
    ".msi",
    ".p12",
    ".pfx",
    ".ps1",
    ".so",
    ".sh",
    ".token",
}

IMAGE_SUFFIXES = {".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".tif", ".tiff", ".webp"}
DOCUMENT_SUFFIXES = {".csv", ".doc", ".docx", ".json", ".md", ".pdf", ".rtf", ".txt", ".xls", ".xlsx", ".yaml", ".yml"}
PROMPT_SUFFIXES = {".prompt", ".prompt.md"}
BRIEF_SUFFIXES = {".brief", ".brief.md"}


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


def _report_path(repo: Path, project_name: str, operation: str) -> Path:
    filename = f"{_timestamp()}-{operation}-{_slugify(project_name)}.json"
    return _unique_path(repo / "reports" / ARTIFACT_INTAKE_REPORT_DIR / filename)


def _resolve_source_path(repo: Path, source: str | Path) -> tuple[Path, str]:
    candidate = Path(source)
    if not str(source).strip():
        raise TaskRunnerError("source não pode ficar vazio.")

    if candidate.is_absolute():
        resolved = candidate.resolve()
        scope = "external"
    else:
        resolved = (repo / candidate).resolve()
        scope = "repo"
        try:
            resolved.relative_to(repo.resolve())
        except ValueError as exc:
            raise TaskRunnerError("path traversal não permitido fora do repo.") from exc

    if not resolved.exists():
        raise TaskRunnerError(f"source inexistente: {resolved}")
    if resolved.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {resolved}")
    return resolved, scope


def _is_blocked(path: Path) -> bool:
    lowered = path.name.lower()
    if lowered in BLOCKED_EXACT_NAMES:
        return True
    return any(lowered.endswith(suffix) for suffix in BLOCKED_SUFFIXES)


def _classify(path: Path) -> str:
    lowered = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in DOCUMENT_SUFFIXES:
        return "document"
    if any(lowered.endswith(item) for item in PROMPT_SUFFIXES) or "prompt" in lowered:
        return "prompt"
    if any(lowered.endswith(item) for item in BRIEF_SUFFIXES) or "brief" in lowered:
        return "brief"
    return "unknown"


def _collect_entries(source_path: Path) -> list[Path]:
    if source_path.is_file():
        return [source_path]
    if source_path.is_dir():
        return [path for path in sorted(source_path.rglob("*")) if path.is_file()]
    raise TaskRunnerError(f"source inválido: {source_path}")


def _build_items(entries: list[Path], root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for path in entries:
        relative = path.relative_to(root).as_posix() if root in path.parents or path == root else path.as_posix()
        item = {
            "path": relative,
            "kind": _classify(path),
            "size_bytes": path.stat().st_size,
        }
        if _is_blocked(path):
            item["reason"] = "extensão ou nome bloqueado"
            blocked.append(item)
            continue
        accepted.append(item)
    return accepted, blocked


def _build_report(
    *,
    project_name: str,
    source: str | Path,
    dry_run: bool,
    operation: str,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("artifact-intake aceita somente --dry-run nesta sprint.")

    repo = repo or repo_root()
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")

    source_path, source_scope = _resolve_source_path(repo, source)
    entries = _collect_entries(source_path)
    accepted_items, blocked_items = _build_items(entries, source_path if source_path.is_dir() else source_path.parent)
    if blocked_items:
        blocked_names = ", ".join(item["path"] for item in blocked_items[:5])
        raise TaskRunnerError(f"source contém itens bloqueados: {blocked_names}")

    source_type_counts: dict[str, int] = {}
    for item in accepted_items:
        source_type_counts[item["kind"]] = source_type_counts.get(item["kind"], 0) + 1

    report_path = _report_path(repo, normalized_project, operation)
    report = {
        "ok": True,
        "artifact_intake_version": ARTIFACT_INTAKE_VERSION,
        "operation": operation,
        "project_name": normalized_project,
        "source_path": str(source_path),
        "source_scope": source_scope,
        "source_kind": "directory" if source_path.is_dir() else "file",
        "dry_run": True,
        "registered": False,
        "registration_requested": operation == "register",
        "plan_created": True,
        "accepted_count": len(accepted_items),
        "blocked_count": 0,
        "accepted_items": accepted_items,
        "blocked_items": blocked_items,
        "source_type_counts": source_type_counts,
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


def run_artifact_intake_plan(
    *,
    project_name: str,
    source: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    return _build_report(project_name=project_name, source=source, dry_run=dry_run, operation="plan", repo=repo)


def run_artifact_intake_register(
    *,
    project_name: str,
    source: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    return _build_report(project_name=project_name, source=source, dry_run=dry_run, operation="register", repo=repo)
