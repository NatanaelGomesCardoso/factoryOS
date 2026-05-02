from __future__ import annotations

import json
import os
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

AUDIT_VERSION = "v0"
AUDIT_REPORT_DIR = "deep-hygiene-audits"
FACTORYOS_ROOT = Path("<FACTORYOS_ROOT>")
CODE_ROOT = Path("<CODE_ROOT>")
HOME_ROOT = Path.home()
TMP_ROOT = Path("<TMP_DIR>")
HARNESS_ROOT = Path("<HARNESS_ROOT>")
OBSIDIAN_ROOT = Path("<OBSIDIAN_VAULT>")
TMP_PREFIXES = (
    "factoryos-",
    "codex-runs",
    "expanded-bounded-live-canary",
    "quiet-runner",
    "capsule-",
    "mvp-",
    "s0",
)
SENSITIVE_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
SENSITIVE_SUFFIXES = (".key", ".pem", ".token", ".secret")
SAFE_INTERNAL_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SAFE_INTERNAL_SUFFIXES = (".pyc", ".pyo", ".tmp", ".bak", ".old", ".log")
GENERATED_DIR_NAMES = {
    "dist",
    "build",
    "htmlcov",
    ".coverage",
}


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
    return repo / "reports" / AUDIT_REPORT_DIR / f"{_timestamp()}.json"


def _contains_git(path: Path) -> bool:
    if path.name == ".git":
        return True
    if path.is_dir() and (path / ".git").exists():
        return True
    return any(part == ".git" for part in path.parts)


def _contains_obsidian(path: Path) -> bool:
    text = path.as_posix()
    return text.startswith(OBSIDIAN_ROOT.as_posix()) or "/Obsidian/" in text


def _is_sensitive(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered in SENSITIVE_EXACT_NAMES or any(lowered.endswith(suffix) for suffix in SENSITIVE_SUFFIXES)


def _size_bytes(path: Path) -> int:
    try:
        if path.is_file() or path.is_symlink():
            return path.stat().st_size
        total = 0
        for root, dirs, files in os.walk(path):
            dirs[:] = [item for item in dirs if item != ".git"]
            for file_name in files:
                try:
                    total += (Path(root) / file_name).stat().st_size
                except OSError:
                    continue
            if total > 512 * 1024 * 1024:
                break
        return total
    except OSError:
        return 0


def _git_tracked_paths(repo: Path) -> set[str]:
    result = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _is_tracked(path: Path, repo: Path, tracked: set[str]) -> bool:
    try:
        rel = path.relative_to(repo).as_posix()
    except ValueError:
        return False
    if rel in tracked:
        return True
    if path.is_dir():
        prefix = rel.rstrip("/") + "/"
        return any(item.startswith(prefix) for item in tracked)
    return False


def _candidate(path: Path, *, root: str, category: str, classification: str, reason: str) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "root": root,
        "category": category,
        "classification": classification,
        "reason": reason,
        "size_bytes": _size_bytes(path),
        "contains_git": _contains_git(path),
        "sensitive_name": _is_sensitive(path),
        "exists": path.exists(),
    }


def _safe_internal_candidate(path: Path, repo: Path, tracked: set[str]) -> bool:
    if not path.exists():
        return False
    if repo not in path.resolve().parents and path.resolve() != repo:
        return False
    if _contains_git(path) or _contains_obsidian(path) or _is_sensitive(path):
        return False
    if _is_tracked(path, repo, tracked):
        return False
    if path.name in SAFE_INTERNAL_DIR_NAMES:
        return True
    if path.name in GENERATED_DIR_NAMES:
        return True
    if path.is_file() and path.name.endswith(SAFE_INTERNAL_SUFFIXES):
        return True
    return False


def _scan_factoryos(repo: Path) -> list[dict[str, Any]]:
    tracked = _git_tracked_paths(repo)
    candidates: list[dict[str, Any]] = []
    ignored_dirs = {".git", ".venv", "node_modules"}
    for root, dirs, files in os.walk(repo):
        current = Path(root)
        dirs[:] = [item for item in dirs if item not in ignored_dirs]
        for dir_name in list(dirs):
            path = current / dir_name
            if dir_name in SAFE_INTERNAL_DIR_NAMES:
                classification = "safe_delete_candidate" if _safe_internal_candidate(path, repo, tracked) else "needs_review"
                candidates.append(_candidate(path, root="factoryos", category="cache", classification=classification, reason="cache/runtime interno"))
                dirs.remove(dir_name)
            elif dir_name in GENERATED_DIR_NAMES:
                classification = "safe_delete_candidate" if _safe_internal_candidate(path, repo, tracked) else "needs_review"
                candidates.append(_candidate(path, root="factoryos", category="generated_validation_dir", classification=classification, reason="diretório gerado por validação/build"))
        for file_name in files:
            path = current / file_name
            if file_name.startswith("."):
                continue
            if file_name.endswith(SAFE_INTERNAL_SUFFIXES):
                classification = "safe_delete_candidate" if _safe_internal_candidate(path, repo, tracked) else "needs_review"
                candidates.append(_candidate(path, root="factoryos", category="runtime_or_temp_file", classification=classification, reason="arquivo runtime/cache/temp interno"))
            elif current == repo / "reports" and path.stat().st_size >= 1_000_000:
                candidates.append(_candidate(path, root="factoryos", category="large_report", classification="needs_review", reason="report grande sem prova suficiente para apagar"))
    return candidates


def _scan_tmp() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not TMP_ROOT.exists():
        return candidates
    for path in sorted(TMP_ROOT.iterdir(), key=lambda item: item.name):
        if not any(path.name.startswith(prefix) for prefix in TMP_PREFIXES):
            continue
        classification = "needs_review"
        if path.name.startswith("factoryos-cleanup-fixture"):
            classification = "factoryos_related_candidate"
        candidates.append(_candidate(path, root="<TMP_DIR>", category="tmp_prefixed_artifact", classification=classification, reason="prefixo temporário relacionado a FactoryOS/Codex; auditoria não apaga <TMP_DIR>"))
    return candidates


def _classify_home_underscore(path: Path) -> str:
    if _contains_obsidian(path) or _is_sensitive(path):
        return "unsafe_to_touch"
    if _contains_git(path):
        return "unknown_needs_review"
    lowered = path.name.lower()
    if "factoryos" in lowered or "codex" in lowered or "capsule" in lowered:
        return "factoryos_related_candidate"
    return "unknown_needs_review"


def _scan_home_underscores() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not HOME_ROOT.exists():
        return candidates
    for path in sorted(HOME_ROOT.iterdir(), key=lambda item: item.name):
        if not path.name.startswith("_"):
            continue
        classification = _classify_home_underscore(path)
        candidates.append(_candidate(path, root=str(HOME_ROOT), category="external_underscore", classification=classification, reason="pasta externa iniciada com '_' exige revisão humana"))
    return candidates


def _scan_code_root() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not CODE_ROOT.exists():
        return candidates
    for path in sorted(CODE_ROOT.iterdir(), key=lambda item: item.name):
        if path == FACTORYOS_ROOT:
            continue
        if path == HARNESS_ROOT:
            candidates.append(_candidate(path, root="<CODE_ROOT>", category="protected_root", classification="unsafe_to_touch", reason="harness protegido"))
        elif path.name.startswith("_"):
            candidates.append(_candidate(path, root="<CODE_ROOT>", category="external_underscore", classification="unknown_needs_review", reason="pasta em <CODE_ROOT> iniciada com '_' pode ser outro projeto"))
        elif path.is_dir() and (path / ".git").exists():
            candidates.append(_candidate(path, root="<CODE_ROOT>", category="other_git_repo", classification="unsafe_to_touch", reason="outro repositório Git protegido"))
    return candidates


def _split_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    safe = [item for item in candidates if item["classification"] == "safe_delete_candidate"]
    unsafe = [item for item in candidates if item["classification"] == "unsafe_to_touch"]
    review = [item for item in candidates if item["classification"] in {"needs_review", "unknown_needs_review", "factoryos_related_candidate"}]
    external_underscore = [item for item in candidates if item["category"] == "external_underscore"]
    return safe, review, unsafe, external_underscore


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "Sprint 080.M deep project hygiene audit V0 proof",
        f"report_path={report['report_path']}",
        f"include_external={str(report['include_external']).lower()}",
        f"safe_to_apply={str(report['safe_to_apply']).lower()}",
        f"safe_delete_candidates={len(report['safe_delete_candidates'])}",
        f"needs_review_candidates={len(report['needs_review_candidates'])}",
        f"external_underscore_candidates={len(report['external_underscore_candidates'])}",
        "deleted_files=0",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / "reports" / "deep-project-hygiene-external-artifact-cleanup-audit-v0-proof.txt", "\n".join(lines) + "\n")


def run_deep_hygiene_audit(*, dry_run: bool, include_external: bool = False, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-deep-hygiene-audit aceita somente --dry-run na V0.")
    repo = (repo or repo_root()).resolve()
    candidates = _scan_factoryos(repo)
    scanned_roots = [repo.as_posix()]
    protected_roots = [HARNESS_ROOT.as_posix(), OBSIDIAN_ROOT.as_posix()]
    if include_external:
        candidates.extend(_scan_tmp())
        candidates.extend(_scan_home_underscores())
        candidates.extend(_scan_code_root())
        scanned_roots.extend([TMP_ROOT.as_posix(), HOME_ROOT.as_posix(), CODE_ROOT.as_posix()])
    safe, review, unsafe, external_underscore = _split_candidates(candidates)
    report_path = _report_path(repo)
    human_review_required = bool(review or unsafe or external_underscore)
    payload = {
        "ok": True,
        "deep_hygiene_audit_version": AUDIT_VERSION,
        "dry_run": True,
        "include_external": include_external,
        "scanned_roots": scanned_roots,
        "protected_roots": protected_roots,
        "candidates": candidates,
        "safe_delete_candidates": safe,
        "needs_review_candidates": review,
        "unsafe_candidates": unsafe,
        "external_underscore_candidates": external_underscore,
        "total_bytes_candidate": sum(int(item.get("size_bytes", 0)) for item in candidates),
        "human_review_required": human_review_required,
        "safe_to_apply": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload
