from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.memory_digest import latest_memory_digest
from app.task_runner import TaskRunnerError

CAPSULES_DIR = "workspaces/codex-capsules"
CAPSULE_REPORTS_DIR = "codex-context-capsules"
CAPSULE_VERSION = "v0"
CAPSULE_MANIFEST_NAME = "CAPSULE_MANIFEST.json"
CAPSULE_AGENTS_NAME = "AGENTS.md"
CAPSULE_DEFAULT_LIMIT_BYTES = 256 * 1024
CAPSULE_MODES = {"standard", "ultra_slim", "ultra_slim_min"}

DEFAULT_EXCLUDED_PATTERNS = (
    ".git/",
    ".venv/",
    "workspaces/",
    "node_modules/",
    "reports/",
    "logs/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    "*.log",
    "*.tmp",
    ".DS_Store",
)

SECRET_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
SECRET_SUFFIXES = {".key", ".pem", ".token"}


@dataclass(frozen=True, slots=True)
class CapsuleFileCopy:
    source_path: str
    capsule_path: str
    size_bytes: int
    included: bool
    reason: str | None = None


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, *, max_length: int = 64) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    normalized = normalized[:max_length].strip("-")
    return normalized or "capsule"


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


def _write_compact_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def _safe_relative_path(value: str) -> bool:
    candidate = Path(value)
    return bool(value) and not candidate.is_absolute() and not any(part in {"..", "."} for part in candidate.parts)


def _is_secret_path(relative_path: str) -> bool:
    name = Path(relative_path).name.lower()
    return name in SECRET_EXACT_NAMES or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES)


def _is_excluded_path(relative_path: str) -> bool:
    normalized = Path(relative_path).as_posix()
    return (
        not _safe_relative_path(normalized)
        or _is_secret_path(normalized)
        or any(normalized == pattern.rstrip("/") or normalized.startswith(pattern) for pattern in DEFAULT_EXCLUDED_PATTERNS)
        or normalized.endswith(".stdout.log")
        or normalized.endswith(".stderr.log")
        or normalized.endswith(".combined.log")
        or normalized.endswith(".preview.log")
    )


def _resolve_under_root(root: Path, relative_or_absolute: str | Path) -> tuple[Path, str]:
    candidate = Path(relative_or_absolute)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve(strict=False)
    root_resolved = root.resolve()
    try:
        relative = candidate.relative_to(root_resolved).as_posix()
    except ValueError as exc:
        raise TaskRunnerError(f"caminho fora do root permitido: {relative_or_absolute}") from exc
    return candidate, relative


def _ensure_source_file(source_root: Path, include_path: str | Path) -> tuple[Path, str]:
    candidate, relative = _resolve_under_root(source_root, include_path)
    if _is_excluded_path(relative):
        raise TaskRunnerError(f"arquivo incluído bloqueado por exclusão: {relative}")
    if not candidate.exists():
        raise TaskRunnerError(f"arquivo incluído inexistente: {relative}")
    if candidate.is_symlink():
        raise TaskRunnerError(f"symlink não permitido no include: {relative}")
    if not candidate.is_file():
        raise TaskRunnerError(f"include precisa ser arquivo: {relative}")
    return candidate, relative


def _file_size(path: Path) -> int:
    if not path.exists() or not path.is_file() or path.is_symlink():
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _copy_file(source_path: Path, capsule_path: Path) -> None:
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, capsule_path)


def _agents_text(label: str, source_root: Path, *, capsule_mode: str = "standard") -> str:
    if capsule_mode == "ultra_slim_min":
        return "FactoryOS capsule. Write only allowed files. No secrets.\n"

    if capsule_mode == "ultra_slim":
        return f"# AGENTS\nFactoryOS ultra-slim. Arquivos locais. Saida compacta. label={label}\n"

    return "\n".join(
        [
            "# AGENTS",
            "",
            "Contexto mínimo da cápsula FactoryOS.",
            "",
            "Regras locais:",
            "- usar somente o contexto copiado para esta cápsula;",
            "- não expor segredos, tokens, cookies ou credenciais;",
            "- não fazer push, pull, fetch, rebase ou deploy;",
            "- não depender de reports grandes;",
            "- manter saídas compactas e focadas.",
            "",
            f"- label: `{label}`",
            f"- source_root: `{source_root}`",
        ]
    ).strip() + "\n"


def _capsule_root(repo: Path, label: str) -> Path:
    return _unique_path(repo / CAPSULES_DIR / f"{_timestamp()}-{_slugify(label)}")


def _manifest_path(capsule_root: Path) -> Path:
    return capsule_root / CAPSULE_MANIFEST_NAME


def _report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_REPORTS_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _latest_digest_snapshot(source_root: Path, *, use_latest_digest: bool) -> dict[str, Any]:
    if not use_latest_digest:
        return {
            "available": False,
            "json_path": "",
            "md_path": "",
            "source_json_path": "",
            "source_md_path": "",
            "size_bytes": 0,
            "warnings": [],
        }

    digest = latest_memory_digest(source_root)
    if not digest.get("available"):
        return {
            "available": False,
            "json_path": "",
            "md_path": "",
            "source_json_path": "",
            "source_md_path": "",
            "size_bytes": 0,
            "warnings": [str(item) for item in digest.get("warnings", []) if str(item).strip()],
        }

    json_path = str(digest.get("digest_path_json", "")).strip()
    md_path = str(digest.get("digest_path_md", "")).strip()
    source_json_path, source_json_relative = _resolve_under_root(source_root, json_path)
    source_md_path, source_md_relative = _resolve_under_root(source_root, md_path)
    return {
        "available": True,
        "json_path": source_json_relative,
        "md_path": source_md_relative,
        "source_json_path": str(source_json_path),
        "source_md_path": str(source_md_path),
        "size_bytes": _file_size(source_json_path) + _file_size(source_md_path),
        "warnings": [str(item) for item in digest.get("warnings", []) if str(item).strip()],
    }


def _build_manifest_payload(
    *,
    repo: Path,
    capsule_root: Path,
    source_root: Path,
    label: str,
    included_files: list[str],
    allowed_write_paths: list[str],
    capsule_mode: str,
    latest_digest_path: str,
    total_bytes: int,
    max_context_bytes: int,
    report_path: Path,
) -> dict[str, Any]:
    if capsule_mode == "ultra_slim_min":
        allowed_files = sorted(dict.fromkeys([*included_files, *allowed_write_paths]))
        return {
            "capsule_version": CAPSULE_VERSION,
            "source_root": str(source_root),
            "label": label,
            "capsule_mode": capsule_mode,
            "included_files": included_files,
            "allowed_write_paths": allowed_write_paths,
            "allowed_files": allowed_files,
            "total_bytes": total_bytes,
            "max_context_bytes": max_context_bytes,
            "report_path": str(report_path.relative_to(repo).as_posix()),
        }

    return {
        "capsule_version": CAPSULE_VERSION,
        "source_root": str(source_root),
        "label": label,
        "capsule_mode": capsule_mode,
        "included_files": included_files,
        "allowed_write_paths": allowed_write_paths,
        "allowed_files": sorted(dict.fromkeys([*included_files, *allowed_write_paths])),
        "excluded_patterns": list(DEFAULT_EXCLUDED_PATTERNS),
        "latest_digest_path": latest_digest_path,
        "total_bytes": total_bytes,
        "max_context_bytes": max_context_bytes,
        "created_at": _now_iso(),
        "report_path": str(report_path.relative_to(repo).as_posix()),
    }


def _manifest_bytes(payload: dict[str, Any], *, compact: bool = False) -> int:
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    return len(text.encode("utf-8")) + 1


def _initial_commit(capsule_root: Path) -> str:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(capsule_root),
            "-c",
            "user.name=FactoryOS",
            "-c",
            "user.email=factoryos@local",
            "commit",
            "-m",
            "init capsule",
            "--allow-empty",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise TaskRunnerError(f"falha ao inicializar commit da cápsula: {completed.stderr.strip() or completed.stdout.strip()}")

    sha = subprocess.run(
        ["git", "-C", str(capsule_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if sha.returncode != 0:
        raise TaskRunnerError("commit inicial da cápsula sem HEAD válido.")
    return sha.stdout.strip()


def _git_init(capsule_root: Path, *, capsule_mode: str) -> None:
    command = ["git", "-C", str(capsule_root)]
    if capsule_mode in {"ultra_slim", "ultra_slim_min"}:
        template_dir = capsule_root / ".factoryos-empty-git-template"
        template_dir.mkdir(parents=True, exist_ok=True)
        command.extend(["-c", f"init.templateDir={template_dir}"])
    command.extend(["init", "-q"])
    subprocess.run(command, check=True, capture_output=True, text=True)
    if capsule_mode in {"ultra_slim", "ultra_slim_min"}:
        shutil.rmtree(capsule_root / ".factoryos-empty-git-template", ignore_errors=True)


def _count_files_and_bytes(capsule_root: Path) -> tuple[int, int]:
    files_count = 0
    total_bytes = 0
    for root, dirs, files in os.walk(capsule_root):
        dirs[:] = [item for item in dirs if item != ".git"]
        for filename in files:
            path = Path(root) / filename
            if path.is_symlink() or not path.is_file():
                continue
            files_count += 1
            total_bytes += _file_size(path)
    return files_count, total_bytes


def _tree_bytes(root_path: Path, *, include_git: bool = True) -> int:
    total_bytes = 0
    for root, dirs, files in os.walk(root_path):
        if not include_git:
            dirs[:] = [item for item in dirs if item != ".git"]
        for filename in files:
            path = Path(root) / filename
            if path.is_symlink() or not path.is_file():
                continue
            total_bytes += _file_size(path)
    return total_bytes


def _git_hooks_bytes(capsule_root: Path) -> int:
    hooks_root = capsule_root / ".git" / "hooks"
    if not hooks_root.exists() or not hooks_root.is_dir():
        return 0
    return _tree_bytes(hooks_root, include_git=True)


def create_capsule(
    *,
    label: str,
    source_root: str | Path,
    include_paths: list[str],
    use_latest_digest: bool,
    max_context_bytes: int,
    capsule_mode: str = "standard",
    allowed_write_paths: list[str] | None = None,
    allow_empty_context: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    source_root_path = Path(source_root)
    if not source_root_path.is_absolute():
        source_root_path = (repo / source_root_path).resolve()
    else:
        source_root_path = source_root_path.resolve()
    if not source_root_path.exists():
        raise TaskRunnerError(f"source_root inexistente: {source_root_path}")
    if not source_root_path.is_dir():
        raise TaskRunnerError(f"source_root não aponta para diretório: {source_root_path}")
    if source_root_path.is_symlink():
        raise TaskRunnerError("source_root não pode ser symlink.")

    normalized_mode = str(capsule_mode).strip() or "standard"
    if normalized_mode not in CAPSULE_MODES:
        allowed = ", ".join(sorted(CAPSULE_MODES))
        raise TaskRunnerError(f"capsule_mode inválido: {normalized_mode}. Permitidos: {allowed}.")

    normalized_allowed_writes: list[str] = []
    for value in allowed_write_paths or []:
        normalized = Path(str(value).strip()).as_posix()
        if not _safe_relative_path(normalized) or _is_secret_path(normalized):
            raise TaskRunnerError(f"allowed_write_path inválido: {value}")
        if normalized not in normalized_allowed_writes:
            normalized_allowed_writes.append(normalized)

    if not include_paths and not allow_empty_context:
        raise TaskRunnerError("informe ao menos um include.")

    report_path = _report_path(repo, label)
    capsule_root = _capsule_root(repo, label)
    capsule_root.mkdir(parents=True, exist_ok=True)

    planned_copies: list[tuple[Path, str]] = []
    included_files: list[str] = []
    seen_files: set[str] = set()
    excluded_files: list[dict[str, str]] = []

    for include_path in include_paths:
        source_file, relative = _ensure_source_file(source_root_path, include_path)
        if relative in seen_files:
            continue
        planned_copies.append((source_file, relative))
        included_files.append(relative)
        seen_files.add(relative)

    digest_snapshot = _latest_digest_snapshot(source_root_path, use_latest_digest=use_latest_digest)
    if digest_snapshot["available"]:
        for digest_path in (digest_snapshot["source_json_path"], digest_snapshot["source_md_path"]):
            source_file, relative = _ensure_source_file(source_root_path, digest_path)
            if relative in seen_files:
                continue
            planned_copies.append((source_file, relative))
            if relative not in seen_files:
                included_files.append(relative)
                seen_files.add(relative)

    agents_text = _agents_text(label, source_root_path, capsule_mode=normalized_mode)
    temp_manifest_payload = _build_manifest_payload(
        repo=repo,
        capsule_root=capsule_root,
        source_root=source_root_path,
        label=label,
        included_files=included_files,
        allowed_write_paths=normalized_allowed_writes,
        capsule_mode=normalized_mode,
        latest_digest_path=digest_snapshot["json_path"] if digest_snapshot["available"] else "",
        total_bytes=0,
        max_context_bytes=max_context_bytes,
        report_path=report_path,
    )

    planned_bytes = sum(_file_size(source_file) for source_file, _ in planned_copies)
    planned_bytes += len(agents_text.encode("utf-8"))
    compact_manifest = normalized_mode in {"ultra_slim", "ultra_slim_min"}
    planned_bytes += _manifest_bytes(temp_manifest_payload, compact=compact_manifest)
    manifest_total_bytes = planned_bytes
    while True:
        manifest_payload = _build_manifest_payload(
            repo=repo,
            capsule_root=capsule_root,
            source_root=source_root_path,
            label=label,
            included_files=included_files,
            allowed_write_paths=normalized_allowed_writes,
            capsule_mode=normalized_mode,
            latest_digest_path=digest_snapshot["json_path"] if digest_snapshot["available"] else "",
            total_bytes=manifest_total_bytes,
            max_context_bytes=max_context_bytes,
            report_path=report_path,
        )
        next_total = sum(_file_size(source_file) for source_file, _ in planned_copies)
        next_total += len(agents_text.encode("utf-8"))
        next_total += _manifest_bytes(manifest_payload, compact=compact_manifest)
        if next_total == manifest_total_bytes:
            break
        manifest_total_bytes = next_total

    if manifest_total_bytes > max_context_bytes:
        raise TaskRunnerError(
            f"capsule excede max_context_bytes: total_bytes={manifest_total_bytes} max_context_bytes={max_context_bytes}."
        )

    capsule_root.mkdir(parents=True, exist_ok=True)
    _git_init(capsule_root, capsule_mode=normalized_mode)

    _write_text_atomic(capsule_root / CAPSULE_AGENTS_NAME, agents_text)
    for source_file, relative in planned_copies:
        capsule_path = capsule_root / relative
        _copy_file(source_file, capsule_path)
    if compact_manifest:
        _write_compact_json_atomic(_manifest_path(capsule_root), manifest_payload)
    else:
        _write_json_atomic(_manifest_path(capsule_root), manifest_payload)

    subprocess.run(
        ["git", "-C", str(capsule_root), "add", "-A"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit_sha = _initial_commit(capsule_root)
    files_count, total_bytes = _count_files_and_bytes(capsule_root)
    agents_bytes = _file_size(capsule_root / CAPSULE_AGENTS_NAME)
    manifest_bytes = _file_size(_manifest_path(capsule_root))
    capsule_total_bytes = _tree_bytes(capsule_root, include_git=True)
    capsule_non_git_bytes = _tree_bytes(capsule_root, include_git=False)
    capsule_git_hooks_bytes = _git_hooks_bytes(capsule_root)

    report = {
        "ok": True,
        "capsule_version": CAPSULE_VERSION,
        "label": label,
        "capsule_mode": normalized_mode,
        "capsule_path": str(capsule_root),
        "source_root": str(source_root_path),
        "included_files": included_files,
        "allowed_write_paths": normalized_allowed_writes,
        "allowed_files": sorted(dict.fromkeys([*included_files, *normalized_allowed_writes])),
        "excluded_files": excluded_files,
        "excluded_patterns": list(DEFAULT_EXCLUDED_PATTERNS),
        "latest_digest_path": digest_snapshot["json_path"] if digest_snapshot["available"] else "",
        "latest_digest_md_path": digest_snapshot["md_path"] if digest_snapshot["available"] else "",
        "manifest_path": str(_manifest_path(capsule_root)),
        "agents_path": str(capsule_root / CAPSULE_AGENTS_NAME),
        "git_commit": commit_sha,
        "has_git": True,
        "has_agents": True,
        "has_manifest": True,
        "files_count": files_count,
        "total_bytes": total_bytes,
        "agents_bytes": agents_bytes,
        "manifest_bytes": manifest_bytes,
        "capsule_total_bytes": capsule_total_bytes,
        "capsule_non_git_bytes": capsule_non_git_bytes,
        "capsule_git_hooks_bytes": capsule_git_hooks_bytes,
        "max_context_bytes": max_context_bytes,
        "created_at": _now_iso(),
        "report_path": str(report_path.relative_to(repo).as_posix()),
    }
    _write_json_atomic(report_path, report)
    return report


def list_capsules(*, limit: int = 10, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    capsules_root = repo / CAPSULES_DIR
    if not capsules_root.exists():
        return {"ok": True, "capsules": [], "capsules_root": str(capsules_root), "limit": limit}

    entries: list[tuple[str, Path, dict[str, Any]]] = []
    for capsule_path in capsules_root.iterdir():
        if not capsule_path.is_dir() or capsule_path.is_symlink():
            continue
        manifest_path = capsule_path / CAPSULE_MANIFEST_NAME
        if not manifest_path.exists() or manifest_path.is_symlink():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(manifest, dict):
            continue
        created_at = str(manifest.get("created_at", "")).strip()
        if not created_at:
            created_at = datetime.fromtimestamp(capsule_path.stat().st_mtime).isoformat()
        entries.append((created_at, capsule_path, manifest))

    entries.sort(key=lambda item: item[0], reverse=True)
    capsules: list[dict[str, Any]] = []
    for _, capsule_path, manifest in entries[: max(limit, 0)]:
        files_count, total_bytes = _count_files_and_bytes(capsule_path)
        capsules.append(
            {
                "capsule_path": str(capsule_path),
                "label": str(manifest.get("label", "")),
                "created_at": manifest.get("created_at"),
                "files_count": files_count,
                "total_bytes": total_bytes,
                "latest_digest_path": manifest.get("latest_digest_path", ""),
                "has_git": (capsule_path / ".git").exists(),
                "has_agents": (capsule_path / CAPSULE_AGENTS_NAME).exists(),
                "has_manifest": True,
            }
        )

    return {"ok": True, "capsules": capsules, "capsules_root": str(capsules_root), "limit": limit}


def inspect_capsule(capsule_path: str | Path, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    capsule_root = Path(capsule_path)
    if not capsule_root.is_absolute():
        capsule_root = (repo / capsule_root).resolve()
    else:
        capsule_root = capsule_root.resolve()
    if not capsule_root.exists():
        raise TaskRunnerError(f"capsule inexistente: {capsule_root}")
    if not capsule_root.is_dir():
        raise TaskRunnerError(f"capsule não aponta para diretório: {capsule_root}")
    if capsule_root.is_symlink():
        raise TaskRunnerError("symlink não permitido para capsule.")

    manifest_path = capsule_root / CAPSULE_MANIFEST_NAME
    has_manifest = manifest_path.exists() and not manifest_path.is_symlink()
    manifest: dict[str, Any] = {}
    if has_manifest:
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskRunnerError("manifest da capsule inválido.") from exc
        if isinstance(loaded, dict):
            manifest = loaded
        else:
            raise TaskRunnerError("manifest da capsule precisa ser JSON object.")

    files_count, total_bytes = _count_files_and_bytes(capsule_root)
    has_git = (capsule_root / ".git").exists()
    has_agents = (capsule_root / CAPSULE_AGENTS_NAME).exists()
    excluded_patterns = list(manifest.get("excluded_patterns", DEFAULT_EXCLUDED_PATTERNS))
    max_context_bytes = int(manifest.get("max_context_bytes", 0) or 0)

    return {
        "ok": bool(has_git and has_agents and has_manifest and (not max_context_bytes or total_bytes <= max_context_bytes)),
        "capsule_path": str(capsule_root),
        "files_count": files_count,
        "total_bytes": total_bytes,
        "has_git": has_git,
        "has_agents": has_agents,
        "has_manifest": has_manifest,
        "excluded_patterns": excluded_patterns,
        "manifest_path": str(manifest_path),
        "label": manifest.get("label", ""),
        "created_at": manifest.get("created_at", ""),
        "latest_digest_path": manifest.get("latest_digest_path", ""),
        "max_context_bytes": max_context_bytes,
        "report_path": manifest.get("report_path", ""),
    }


def capsule_manifest(capsule_path: str | Path, *, repo: Path | None = None) -> dict[str, Any]:
    capsule_root = Path(capsule_path)
    if not capsule_root.is_absolute():
        capsule_root = (_repo_root(repo) / capsule_root).resolve()
    else:
        capsule_root = capsule_root.resolve()
    manifest_path = capsule_root / CAPSULE_MANIFEST_NAME
    if not manifest_path.exists():
        raise TaskRunnerError(f"manifest inexistente: {manifest_path}")
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TaskRunnerError("manifest da capsule precisa ser JSON object.")
    return loaded


def capsule_digest_paths(source_root: str | Path, *, repo: Path | None = None) -> dict[str, Any]:
    source_root_path = Path(source_root)
    if not source_root_path.is_absolute():
        source_root_path = (_repo_root(repo) / source_root_path).resolve()
    else:
        source_root_path = source_root_path.resolve()
    digest = latest_memory_digest(source_root_path)
    return {
        "ok": True,
        "available": bool(digest.get("available")),
        "digest_path_json": digest.get("digest_path_json", ""),
        "digest_path_md": digest.get("digest_path_md", ""),
        "summary": digest.get("summary", ""),
        "warnings": digest.get("warnings", []),
    }
