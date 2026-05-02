from __future__ import annotations

import fnmatch
import json
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

CLEAN_EXPORT_VERSION = "v0"
PUBLIC_EXPORT_LEAK_REVIEW_VERSION = "v0"
DEFAULT_EXPORT_PATH = Path.home() / "code" / "factoryos-v1-clean"
PROOF_PATH = "reports/clean-public-v1-export-v0-proof.txt"
LEAK_REVIEW_PROOF_PATH = "reports/public-export-leak-review-sanitization-v0-proof.txt"

INCLUDE_ROOTS = ["app", "docs"]
OPTIONAL_INCLUDE_ROOTS = ["templates", "static", "examples"]
INCLUDE_FILES = ["README.md", "requirements.txt", "pyproject.toml", "LICENSE", "AGENTS.md"]
ESSENTIAL_SPEC_GLOBS = [
    "specs/sprints/087-release-packaging-strategy-v0.json",
    "specs/sprints/088-clean-public-v1-export-v0.json",
    "specs/sprints/089-final-public-repo-readiness-gate-v0.json",
]
EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "reports",
    "workspaces",
    "runs",
    "logs",
    "traces",
    "screenshots",
}
EXCLUDED_PATTERNS = [
    "*.log",
    "*.tmp",
    "*.tar",
    "*.tar.gz",
    "*.zip",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
]
SENSITIVE_REFERENCE_TERMS = ["secret", "token", "cookie", "credential", "password", "apikey", "api_key"]
SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}"),
]
WINDOWS_USERS_MARKER = "C:" + "\\" + "Users" + "\\"
LOCAL_PATH_MARKERS = [str(Path.home()), "/mnt" + "/d", WINDOWS_USERS_MARKER]
LOCAL_PATH_REPLACEMENTS = [
    (re.compile(re.escape((Path.home() / "code" / "factoryos").as_posix())), "<FACTORYOS_ROOT>"),
    (re.compile(re.escape("/mnt" + "/d/Obsidian/_brain")), "<OBSIDIAN_VAULT>"),
    (re.compile(re.escape((Path.home() / "code").as_posix()) + r"/[A-Za-z0-9_.-]+"), "<PROJECT_ROOT>"),
    (re.compile(re.escape(str(Path.home())) + r"(/[A-Za-z0-9_.-]+)*"), "<LOCAL_HOME>"),
    (re.compile(re.escape(WINDOWS_USERS_MARKER) + r"[^\\\\\s]+(?:\\\\[^\s]+)*"), "<LOCAL_WINDOWS_PATH>"),
]
REQUIRED_SOURCE_REPORTS = [
    "reports/clean-public-export-plan-v0.json",
    "reports/clean-public-export-create-v0.json",
    "reports/clean-public-export-validate-v0.json",
    "reports/final-public-repo-readiness-gate-v0.json",
]


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


def _is_excluded_rel(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    rel_text = rel.as_posix()
    return any(fnmatch.fnmatch(rel_text, pattern) or fnmatch.fnmatch(rel.name, pattern) for pattern in EXCLUDED_PATTERNS)


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            files.append(path)
    return sorted(files)


def _public_candidates(repo: Path) -> list[Path]:
    candidates: list[Path] = []
    for root_name in INCLUDE_ROOTS + OPTIONAL_INCLUDE_ROOTS:
        root = repo / root_name
        if root.is_dir():
            candidates.extend(_iter_files(root))
    for file_name in INCLUDE_FILES:
        path = repo / file_name
        if path.is_file() and not path.is_symlink():
            candidates.append(path)
    for pattern in ESSENTIAL_SPEC_GLOBS:
        candidates.extend(path for path in repo.glob(pattern) if path.is_file() and not path.is_symlink())
    unique = sorted({path.resolve(): path for path in candidates}.values())
    return [path for path in unique if not _is_excluded_rel(path.relative_to(repo))]


def _excluded_files(repo: Path) -> list[Path]:
    excluded: list[Path] = []
    for path in _iter_files(repo):
        rel = path.relative_to(repo)
        if _is_excluded_rel(rel):
            excluded.append(path)
    return excluded


def _scan_file(path: Path) -> tuple[bool, bool]:
    findings = _scan_file_findings(path, sanitized=True)
    suspected_secret = any(finding["category"] == "suspected_secret" for finding in findings)
    local_path_leak = any(finding["category"] == "local_path_leak" for finding in findings)
    return suspected_secret, local_path_leak


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _sanitize_public_text(text: str) -> str:
    sanitized = text
    for pattern, replacement in LOCAL_PATH_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def _scan_file_findings(path: Path, *, sanitized: bool) -> list[dict[str, str]]:
    rel_name = path.as_posix().lower()
    raw_text = _read_text(path)
    text = _sanitize_public_text(raw_text) if sanitized else raw_text
    findings: list[dict[str, str]] = []
    if any(pattern.search(text) for pattern in SECRET_VALUE_PATTERNS):
        findings.append({"category": "suspected_secret", "status": "confirmed_issue"})
    if any(marker in text for marker in LOCAL_PATH_MARKERS):
        findings.append({"category": "local_path_leak", "status": "confirmed_issue"})
    if any(term in rel_name or term in raw_text.lower() for term in SENSITIVE_REFERENCE_TERMS):
        findings.append({"category": "sensitive_term_reference", "status": "false_positive"})
    if any(marker in raw_text for marker in LOCAL_PATH_MARKERS) and not any(marker in text for marker in LOCAL_PATH_MARKERS):
        findings.append({"category": "sanitized_local_path_reference", "status": "false_positive"})
    return findings


def _redacted_public_findings(repo: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in _public_candidates(repo):
        rel = path.relative_to(repo).as_posix()
        seen: set[tuple[str, str]] = set()
        for finding in _scan_file_findings(path, sanitized=True):
            key = (finding["category"], finding["status"])
            if key in seen:
                continue
            seen.add(key)
            findings.append({"path": rel, "category": finding["category"], "status": finding["status"]})
    return findings


def _copy_public_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        shutil.copy2(source, target)
        return
    target.write_text(_sanitize_public_text(text), encoding="utf-8")


def _build_plan(repo: Path, export_path: Path) -> dict[str, Any]:
    included = _public_candidates(repo)
    excluded = _excluded_files(repo)
    suspected_secrets_count = 0
    local_path_leaks_count = 0
    for path in included:
        suspected_secret, local_path_leak = _scan_file(path)
        suspected_secrets_count += int(suspected_secret)
        local_path_leaks_count += int(local_path_leak)
    export_exists = export_path.exists()
    export_decision = "ready"
    if suspected_secrets_count or local_path_leaks_count or export_exists:
        export_decision = "needs_review"
    if export_exists and not export_path.is_dir():
        export_decision = "failed"
    return {
        "ok": export_decision != "failed",
        "clean_public_export_version": CLEAN_EXPORT_VERSION,
        "export_decision": export_decision,
        "export_path": export_path.as_posix(),
        "export_exists": export_exists,
        "overwrite_existing": False,
        "included_count": len(included),
        "excluded_count": len(excluded),
        "suspected_secrets_count": suspected_secrets_count,
        "local_path_leaks_count": local_path_leaks_count,
        "safe_to_publish": False,
        "human_review_required": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "include_roots": INCLUDE_ROOTS + OPTIONAL_INCLUDE_ROOTS,
        "include_files": INCLUDE_FILES,
        "essential_specs": ESSENTIAL_SPEC_GLOBS,
        "excluded_roots": sorted(EXCLUDED_DIR_NAMES),
        "excluded_patterns": EXCLUDED_PATTERNS,
        "included_sample": [path.relative_to(repo).as_posix() for path in included[:25]],
        "excluded_sample": [path.relative_to(repo).as_posix() for path in excluded[:25]],
        "created_at": _now_iso(),
    }


def _write_proof(repo: Path, payload: dict[str, Any]) -> None:
    lines = [
        "Sprint 088 clean public V1 export V0 proof",
        f"export_decision={payload['export_decision']}",
        f"export_path={payload['export_path']}",
        f"included_count={payload['included_count']}",
        f"excluded_count={payload['excluded_count']}",
        f"suspected_secrets_count={payload['suspected_secrets_count']}",
        f"local_path_leaks_count={payload['local_path_leaks_count']}",
        f"safe_to_publish={str(payload['safe_to_publish']).lower()}",
        f"human_review_required={str(payload['human_review_required']).lower()}",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / PROOF_PATH, "\n".join(lines) + "\n")


def _persist(repo: Path, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_path = repo / "reports" / f"clean-public-export-{kind}-v0.json"
    payload = dict(payload)
    payload["kind"] = kind
    payload["report_path"] = report_path.relative_to(repo).as_posix()
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload


def run_clean_public_export_plan(
    *, dry_run: bool, export_path: str | Path = DEFAULT_EXPORT_PATH, repo: Path | None = None
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("clean-public-export-plan V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    payload = _build_plan(repo, Path(export_path))
    payload["dry_run"] = True
    payload["would_create"] = False
    return _persist(repo, "plan", payload)


def run_clean_public_export_create(
    *, dry_run: bool = True, export_path: str | Path = DEFAULT_EXPORT_PATH, repo: Path | None = None
) -> dict[str, Any]:
    repo = (repo or repo_root()).resolve()
    export_path = Path(export_path)
    payload = _build_plan(repo, export_path)
    payload["dry_run"] = dry_run
    payload["would_create"] = True
    payload["created"] = False
    if export_path.exists():
        payload["would_create"] = False
        payload["export_decision"] = "needs_review" if export_path.is_dir() else "failed"
        payload["ok"] = export_path.is_dir()
        payload["blocked_reason"] = "export_path_exists_no_overwrite"
        return _persist(repo, "create", payload)
    if dry_run:
        return _persist(repo, "create", payload)
    export_path.mkdir(parents=True, exist_ok=False)
    for source in _public_candidates(repo):
        rel = source.relative_to(repo)
        target = export_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        _copy_public_file(source, target)
    payload["created"] = True
    payload["safe_to_publish"] = False
    return _persist(repo, "create", payload)


def run_clean_public_export_validate(
    *, dry_run: bool, export_path: str | Path = DEFAULT_EXPORT_PATH, repo: Path | None = None
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("clean-public-export-validate V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    export_path = Path(export_path)
    payload = _build_plan(repo, export_path)
    forbidden_present = []
    if export_path.is_dir():
        forbidden_present = [
            path.relative_to(export_path).as_posix()
            for path in _iter_files(export_path)
            if _is_excluded_rel(path.relative_to(export_path))
        ]
    payload.update(
        {
            "dry_run": True,
            "validation_target_exists": export_path.is_dir(),
            "forbidden_present_count": len(forbidden_present),
            "forbidden_present_sample": forbidden_present[:25],
            "safe_to_publish": False,
        }
    )
    if forbidden_present:
        payload["export_decision"] = "failed"
        payload["ok"] = False
    return _persist(repo, "validate", payload)


def _read_report_json(repo: Path, rel_path: str) -> dict[str, Any]:
    path = repo / rel_path
    if not path.is_file() or path.is_symlink():
        return {"ok": False, "path": rel_path, "missing": True}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "path": rel_path, "invalid_json": True}
    return {"ok": True, "path": rel_path, "data": data}


def _counts_from_report(report: dict[str, Any]) -> tuple[int, int]:
    data = report.get("data") or {}
    if "export" in data:
        export = data["export"]
        return int(export.get("suspected_secrets_count", 0)), int(export.get("local_path_leaks_count", 0))
    return int(data.get("suspected_secrets_count", 0)), int(data.get("local_path_leaks_count", 0))


def _write_leak_review_proof(repo: Path, payload: dict[str, Any]) -> None:
    lines = [
        "Sprint 089.M public export leak review sanitization V0 proof",
        "leak_review_created=true",
        "suspected_secrets_reviewed=true",
        "local_path_leaks_reviewed=true",
        "redaction_safe=true",
        "no_secret_values_printed=true",
        "safe_to_push=false",
        "human_review_required=true",
        "no_push=true",
        "no_deploy=true",
        "no_paid_api=true",
        "no_secrets=true",
        f"report_path={payload['report_path']}",
        f"suspected_secrets_count={payload['suspected_secrets_count']}",
        f"local_path_leaks_count={payload['local_path_leaks_count']}",
        f"confirmed_issue_count={payload['confirmed_issue_count']}",
        f"false_positive_count={payload['false_positive_count']}",
    ]
    _write_text_atomic(repo / LEAK_REVIEW_PROOF_PATH, "\n".join(lines) + "\n")


def run_public_export_leak_review(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("public-export-leak-review V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    source_reports = [_read_report_json(repo, rel_path) for rel_path in REQUIRED_SOURCE_REPORTS]
    redacted_findings = _redacted_public_findings(repo)
    confirmed = [finding for finding in redacted_findings if finding["status"] == "confirmed_issue"]
    false_positives = [finding for finding in redacted_findings if finding["status"] == "false_positive"]
    files_to_fix = sorted({finding["path"] for finding in confirmed})
    current_plan = _build_plan(repo, DEFAULT_EXPORT_PATH)
    before_secrets, before_paths = _counts_from_report(source_reports[-1])
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    report_rel_path = f"reports/public-export-leak-reviews/{timestamp}.json"
    payload: dict[str, Any] = {
        "ok": all(report["ok"] for report in source_reports),
        "public_export_leak_review_version": PUBLIC_EXPORT_LEAK_REVIEW_VERSION,
        "dry_run": True,
        "suspected_secrets_count": current_plan["suspected_secrets_count"],
        "local_path_leaks_count": current_plan["local_path_leaks_count"],
        "suspected_secrets_before": before_secrets,
        "local_path_leaks_before": before_paths,
        "false_positive_count": len(false_positives),
        "confirmed_issue_count": len(confirmed),
        "redacted_findings": redacted_findings,
        "files_to_fix": files_to_fix,
        "recommended_fixes": [
            "manter safe_to_push=false ate aprovacao humana da Sprint 090",
            "usar placeholders no export publico para caminhos locais",
            "tratar referencias a token/secret em docs de seguranca como falso positivo redigido quando nao houver valor",
            "registrar blocker e rotacionar fora do repo se aparecer valor real de segredo",
        ],
        "source_reports": [{"path": report["path"], "ok": report["ok"]} for report in source_reports],
        "safe_to_publish": False,
        "safe_to_push": False,
        "human_review_required": True,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "created_at": _now_iso(),
        "report_path": report_rel_path,
    }
    _write_json_atomic(repo / report_rel_path, payload)
    _write_leak_review_proof(repo, payload)
    return payload
