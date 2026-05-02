from __future__ import annotations

import hashlib
import json
import secrets
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_context_capsule import (
    CAPSULE_MANIFEST_NAME,
    capsule_manifest,
    inspect_capsule,
)
from app.codex_quiet_runner import run_codex_quiet_run
from app.task_runner import TaskRunnerError

CAPSULE_EXECUTION_REPORT_DIR = "capsule-executions"
CAPSULE_DIFF_REPORT_DIR = "capsule-diffs"
CAPSULE_EXPORT_PLAN_DIR = "capsule-export-plans"
CAPSULE_RUN_STATUS_DIR = "capsule-run-status"
CAPSULE_CANARY_DIR = "capsule-canary"
CAPSULE_APPLY_PLAN_DIR = "capsule-apply-plans"
CAPSULE_CANARY_FILE = "capsule-canary.txt"
CAPSULE_RUN_STATUS_VERSION = "v0"
CAPSULE_RUNTIME_ARTIFACT_PREFIXES = (".codex",)


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, *, max_length: int = 64) -> str:
    normalized = value.strip().lower()
    normalized = "".join(ch if ch.isalnum() else "-" for ch in normalized)
    normalized = "-".join(part for part in normalized.split("-") if part)
    return normalized[:max_length] or "capsule"


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


def _validate_capsule(capsule: str | Path, *, repo: Path) -> Path:
    capsule_path = Path(capsule)
    if not capsule_path.is_absolute():
        capsule_path = (repo / capsule_path).resolve()
    else:
        capsule_path = capsule_path.resolve()
    if not capsule_path.exists():
        raise TaskRunnerError(f"capsule inexistente: {capsule_path}")
    if not capsule_path.is_dir():
        raise TaskRunnerError(f"capsule não aponta para diretório: {capsule_path}")
    if capsule_path.is_symlink():
        raise TaskRunnerError("symlink não permitido para capsule.")
    if not (capsule_path / CAPSULE_MANIFEST_NAME).exists():
        raise TaskRunnerError("capsule sem manifest.")
    return capsule_path


def _validate_prompt(prompt_file: str | Path) -> Path:
    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        raise TaskRunnerError(f"prompt inexistente: {prompt_path}")
    if not prompt_path.is_file():
        raise TaskRunnerError(f"prompt não aponta para arquivo: {prompt_path}")
    if prompt_path.is_symlink():
        raise TaskRunnerError("symlink não permitido no prompt.")
    return prompt_path


def _capsule_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_EXECUTION_REPORT_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _diff_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_DIFF_REPORT_DIR / f"{_timestamp()}-{_slugify(label)}.diff")


def _export_plan_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_EXPORT_PLAN_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _run_status_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_RUN_STATUS_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _capsule_canary_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_CANARY_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _capsule_apply_report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CAPSULE_APPLY_PLAN_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _git_status_entries(capsule_path: Path) -> list[tuple[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(capsule_path), "status", "--porcelain=v1", "-uall"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise TaskRunnerError("não foi possível ler status da capsule.")
    entries: list[tuple[str, str]] = []
    for raw_line in completed.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        status = raw_line[:2]
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path and not any(path == prefix or path.startswith(f"{prefix}/") for prefix in CAPSULE_RUNTIME_ARTIFACT_PREFIXES):
            entries.append((status, path))
    return entries


def _git_diff_text(capsule_path: Path, status_entries: list[tuple[str, str]]) -> str:
    sections: list[str] = []
    for status, relative_path in status_entries:
        candidate = capsule_path / relative_path
        if status == "??":
            completed = subprocess.run(
                ["git", "-C", str(capsule_path), "diff", "--no-index", "--binary", "--", "/dev/null", relative_path],
                capture_output=True,
                text=True,
                check=False,
            )
            diff_text = completed.stdout or ""
        else:
            completed = subprocess.run(
                ["git", "-C", str(capsule_path), "diff", "--binary", "--no-ext-diff", "HEAD", "--", relative_path],
                capture_output=True,
                text=True,
                check=False,
            )
            diff_text = completed.stdout or ""

        if diff_text.strip():
            sections.append(diff_text.rstrip())
        elif candidate.exists():
            sections.append(f"diff --git a/{relative_path} b/{relative_path}\n")

    return "\n\n".join(section for section in sections if section.strip()).rstrip() + ("\n" if sections else "")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_relative_member(path: str, prefix: str) -> bool:
    candidate = Path(path)
    target = Path(prefix)
    if candidate == target:
        return True
    try:
        candidate.relative_to(target)
        return True
    except ValueError:
        return False


def _read_manifest(capsule_path: Path) -> dict[str, Any]:
    manifest = capsule_manifest(capsule_path)
    if not isinstance(manifest, dict):
        raise TaskRunnerError("manifest da capsule inválido.")
    return manifest


def run_codex_capsule_run(
    *,
    capsule: str | Path,
    prompt_file: str | Path,
    label: str,
    model: str,
    reasoning: str,
    sandbox: str,
    execute: bool,
    repo: Path | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    capsule_path = _validate_capsule(capsule, repo=repo)
    prompt_path = _validate_prompt(prompt_file)
    report_path = _capsule_report_path(repo, label)

    quiet_result = run_codex_quiet_run(
        prompt_file=prompt_path,
        cwd=capsule_path,
        model=model,
        reasoning=reasoning,
        sandbox=sandbox,
        approval="never" if execute else "on-request",
        label=label,
        dry_run=not execute,
        execute=execute,
        repo=repo,
        timeout_seconds=timeout_seconds,
        no_push=True,
        no_deploy=True,
        no_paid_api=True,
        no_secrets=True,
    )

    capsule_snapshot = inspect_capsule(capsule_path, repo=repo)
    status_entries = _git_status_entries(capsule_path) if execute else []
    diff_text = _git_diff_text(capsule_path, status_entries) if execute else ""

    diff_path = _diff_report_path(repo, label)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(diff_path, diff_text)

    changed_files = [path for status, path in status_entries if status]
    changed_files_count = len(changed_files)
    token_usage = quiet_result.get("token_usage", {})
    output_lines = int(quiet_result.get("output_lines", 0) or 0)
    output_bytes = int(quiet_result.get("output_bytes", 0) or 0)
    diff_bytes = len(diff_text.encode("utf-8"))

    report = {
        "ok": bool(quiet_result.get("ok", False)),
        "capsule_path": str(capsule_path),
        "prompt_file": str(prompt_path),
        "label": label,
        "model": model,
        "reasoning": reasoning,
        "sandbox": sandbox,
        "execute": bool(execute),
        "quiet_runner_report_path": quiet_result.get("report_path", ""),
        "quiet_runner_output_lines": output_lines,
        "quiet_runner_output_bytes": output_bytes,
        "token_usage": token_usage,
        "tokens_used": token_usage.get("tokens_used"),
        "input_tokens": token_usage.get("input_tokens"),
        "cached_input_tokens": token_usage.get("cached_input_tokens"),
        "output_tokens": token_usage.get("output_tokens"),
        "token_usage_parser_version": token_usage.get("parser_version"),
        "captured_log_status": quiet_result.get("captured_log_status"),
        "captured_log_warnings": quiet_result.get("captured_log_warnings", []),
        "captured_log_lines": quiet_result.get("captured_log_lines"),
        "captured_log_bytes": quiet_result.get("captured_log_bytes"),
        "changed_files": changed_files,
        "changed_files_count": changed_files_count,
        "diff_path": str(diff_path.relative_to(repo).as_posix()),
        "diff_bytes": diff_bytes,
        "diff_sha256": _sha256_text(diff_text),
        "capsule_snapshot": capsule_snapshot,
        "capsule_manifest": _read_manifest(capsule_path),
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report


def run_codex_capsule_diff(
    *,
    capsule: str | Path,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    capsule_path = _validate_capsule(capsule, repo=repo)
    manifest = _read_manifest(capsule_path)
    label = str(manifest.get("label", "capsule-diff"))

    status_entries = _git_status_entries(capsule_path)
    diff_text = _git_diff_text(capsule_path, status_entries)
    diff_path = _diff_report_path(repo, label)
    _write_text_atomic(diff_path, diff_text)

    report_path = repo / "reports" / CAPSULE_DIFF_REPORT_DIR / f"{_timestamp()}-{_slugify(label)}.json"

    changed_files = [path for _, path in status_entries]
    report = {
        "ok": True,
        "capsule_path": str(capsule_path),
        "changed_files": changed_files,
        "changed_files_count": len(changed_files),
        "diff_path": str(diff_path.relative_to(repo).as_posix()),
        "diff_bytes": len(diff_text.encode("utf-8")),
        "diff_sha256": _sha256_text(diff_text),
        "created_at": _now_iso(),
        "report_path": str(report_path.relative_to(repo).as_posix()),
    }
    _write_json_atomic(report_path, report)
    return report


def _plan_for_included_file(capsule_path: Path, source_root: Path, relative_path: str) -> dict[str, Any]:
    source_file = source_root / relative_path
    capsule_file = capsule_path / relative_path
    source_exists = source_file.exists() and source_file.is_file()
    capsule_exists = capsule_file.exists() and capsule_file.is_file()

    if source_exists and capsule_exists:
        source_bytes = source_file.read_bytes()
        capsule_bytes = capsule_file.read_bytes()
        if source_bytes == capsule_bytes:
            action = "noop"
        else:
            action = "update"
    elif capsule_exists and not source_exists:
        action = "create"
    elif source_exists and not capsule_exists:
        action = "delete"
    else:
        action = "missing"

    return {
        "path": relative_path,
        "source_exists": source_exists,
        "capsule_exists": capsule_exists,
        "action": action,
    }


def _plan_for_changed_file(capsule_path: Path, source_root: Path, relative_path: str) -> dict[str, Any]:
    return _plan_for_included_file(capsule_path, source_root, relative_path)


def run_codex_capsule_export_plan(
    *,
    capsule: str | Path,
    source_root: str | Path,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    capsule_path = _validate_capsule(capsule, repo=repo)
    source_root_path = Path(source_root)
    if not source_root_path.is_absolute():
        source_root_path = (repo / source_root_path).resolve()
    else:
        source_root_path = source_root_path.resolve()
    if not source_root_path.exists() or not source_root_path.is_dir():
        raise TaskRunnerError(f"source_root inválido: {source_root_path}")

    manifest = _read_manifest(capsule_path)
    included_files = [str(item) for item in manifest.get("included_files", []) if str(item).strip()]
    manifest_allowed = manifest.get("allowed_files", [])
    allowed_files = [str(item) for item in manifest_allowed if str(item).strip()]
    if not allowed_files:
        allowed_files = [*included_files, *[str(item) for item in manifest.get("allowed_write_paths", []) if str(item).strip()]]
    allowed_files = sorted(dict.fromkeys(allowed_files))
    allowed_set = set(allowed_files)
    status_entries = _git_status_entries(capsule_path)
    changed_files = [path for _, path in status_entries]
    disallowed_files = [path for path in changed_files if path not in allowed_set]

    plan_actions = [_plan_for_included_file(capsule_path, source_root_path, path) for path in included_files]
    changed_plan_actions = [item for item in plan_actions if item["action"] != "noop"]
    planned_paths = {str(item["path"]) for item in changed_plan_actions}
    for path in changed_files:
        if path in allowed_set and path not in planned_paths:
            changed_plan_actions.append(_plan_for_changed_file(capsule_path, source_root_path, path))
            planned_paths.add(path)

    report_path = _export_plan_report_path(repo, manifest.get("label", "capsule-export"))
    report = {
        "ok": True,
        "capsule_path": str(capsule_path),
        "source_root": str(source_root_path),
        "included_files": included_files,
        "candidate_files": changed_plan_actions,
        "candidate_files_count": len(changed_plan_actions),
        "disallowed_files": disallowed_files,
        "ignored_files": disallowed_files,
        "changed_files": changed_files,
        "changed_files_count": len(changed_files),
        "allowed_files": allowed_files,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
        "capsule_manifest": manifest,
    }
    _write_json_atomic(report_path, report)
    return report


def run_codex_capsule_apply(
    *,
    capsule: str | Path,
    source_root: str | Path,
    repo: Path | None = None,
    dry_run: bool,
    export_plan: str | Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("codex-capsule-apply aceita somente --dry-run nesta sprint.")

    repo = _repo_root(repo)
    if export_plan:
        export_plan_path = Path(export_plan)
        if not export_plan_path.is_absolute():
            export_plan_path = (repo / export_plan_path).resolve()
        plan = _load_json_report(export_plan_path, kind="export plan")
    else:
        plan = run_codex_capsule_export_plan(capsule=capsule, source_root=source_root, repo=repo)

    candidate_files = [item for item in plan.get("candidate_files", []) if isinstance(item, dict)]
    would_apply_files = [str(item.get("path", "")) for item in candidate_files if str(item.get("path", "")).strip()]
    disallowed_files = [str(item) for item in plan.get("disallowed_files", []) if str(item).strip()]
    changed_files = [str(item) for item in plan.get("changed_files", []) if str(item).strip()]
    allowed_files = [str(item) for item in plan.get("allowed_files", []) if str(item).strip()]
    safe_to_apply_later = bool(not disallowed_files and all(path in set(allowed_files) for path in would_apply_files))
    patch_path = _diff_report_path(repo, "capsule-apply-dry-run")
    _write_text_atomic(patch_path, "")
    report_path = _capsule_apply_report_path(repo, "capsule-apply-dry-run")
    report = {
        "ok": True,
        "apply_mode": "dry_run",
        "applied": False,
        "capsule_path": plan["capsule_path"],
        "source_root": plan["source_root"],
        "allowed_files": allowed_files,
        "disallowed_files": disallowed_files,
        "changed_files": changed_files,
        "would_apply_files": would_apply_files,
        "would_apply_count": len(would_apply_files),
        "ignored_files": disallowed_files,
        "safe_to_apply_later": safe_to_apply_later,
        "patch_path": str(patch_path.relative_to(repo).as_posix()),
        "plan_report_path": plan["report_path"],
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report


def _load_json_report(report_path: str | Path, *, kind: str) -> dict[str, Any]:
    path = Path(report_path)
    if not path.exists():
        raise TaskRunnerError(f"{kind} inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"{kind} não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido no {kind}.")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskRunnerError(f"{kind} inválido: {path}") from exc
    if not isinstance(loaded, dict):
        raise TaskRunnerError(f"{kind} precisa ser JSON object: {path}")
    return loaded


def _first_report_path(report: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(report.get(key, "")).strip()
        if value:
            return value
    return ""


def _status_warning(message: str, warnings: list[str]) -> None:
    if message not in warnings:
        warnings.append(message)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_codex_capsule_status(
    *,
    execution_report: str | Path,
    export_plan: str | Path,
    diff_report: str | Path,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    execution_report_path = Path(execution_report)
    if not execution_report_path.is_absolute():
        execution_report_path = (repo / execution_report_path).resolve()
    export_plan_path = Path(export_plan)
    if not export_plan_path.is_absolute():
        export_plan_path = (repo / export_plan_path).resolve()
    diff_report_path = Path(diff_report)
    if not diff_report_path.is_absolute():
        diff_report_path = (repo / diff_report_path).resolve()

    execution = _load_json_report(execution_report_path, kind="execution report")
    export_plan_payload = _load_json_report(export_plan_path, kind="export plan")
    diff_payload = _load_json_report(diff_report_path, kind="diff report")

    quiet_runner_path = _first_report_path(
        execution,
        (
            "quiet_runner_report_path",
            "quiet_runner_report",
            "captured_log_full_path",
        ),
    )
    quiet_runner_report: dict[str, Any] = {}
    if quiet_runner_path:
        quiet_runner_path = str((repo / quiet_runner_path).resolve()) if not Path(quiet_runner_path).is_absolute() else quiet_runner_path
        quiet_runner_report = _load_json_report(quiet_runner_path, kind="quiet runner report")

    exit_code = quiet_runner_report.get("exit_code")
    if exit_code is None:
        exit_code = execution.get("exit_code")
    exit_code = _safe_int(exit_code, default=-1)

    captured_log_status = str(
        execution.get("captured_log_status")
        or quiet_runner_report.get("captured_log_status")
        or ""
    ).strip() or "unknown"
    captured_log_diff_like_lines = _safe_int(
        quiet_runner_report.get("captured_log_diff_like_lines", execution.get("captured_log_diff_like_lines")),
        default=0,
    )

    execution_ok = exit_code == 0
    diff_ok = bool(diff_payload.get("ok", False))
    export_plan_ok = bool(export_plan_payload.get("ok", False))
    disallowed_files = [
        str(item)
        for item in export_plan_payload.get("disallowed_files", [])
        if str(item).strip()
    ]
    changed_files_count = _safe_int(
        export_plan_payload.get("changed_files_count", execution.get("changed_files_count", diff_payload.get("changed_files_count"))),
        default=0,
    )
    tokens_used = execution.get("tokens_used")
    if tokens_used is None:
        token_usage = quiet_runner_report.get("token_usage", {})
        if isinstance(token_usage, dict):
            tokens_used = token_usage.get("tokens_used")
    tokens_used = _safe_int(tokens_used, default=0)

    blockers: list[str] = []
    warnings: list[str] = []

    if exit_code != 0:
        blockers.append(f"exit_code={exit_code}")

    if not diff_ok:
        blockers.append("diff_report inválido ou ok=false.")

    if not export_plan_ok:
        blockers.append("export_plan ok=false.")

    if disallowed_files:
        blockers.append(f"disallowed_files={len(disallowed_files)}")

    if captured_log_status == "blocked":
        if exit_code == 0 and export_plan_ok and not disallowed_files and captured_log_diff_like_lines > 0:
            _status_warning(
                "captured_log_status=blocked apenas por diff-like lines capturadas.",
                warnings,
            )
        else:
            blockers.append("captured_log_status=blocked.")

    elif captured_log_status == "warn":
        _status_warning("captured_log_status=warn.", warnings)

    if bool(quiet_runner_report.get("captured_log_truncated")):
        _status_warning("captured_log_truncated=true.", warnings)

    for safety_flag in ("no_push", "no_deploy", "no_paid_api", "no_secrets"):
        value = quiet_runner_report.get(safety_flag)
        if value is False:
            _status_warning(f"{safety_flag}=false no quiet runner report.", warnings)

    if not quiet_runner_report:
        _status_warning("quiet runner report não foi encontrado.", warnings)

    status = "blocked"
    if not blockers:
        if execution_ok and export_plan_ok and diff_ok:
            if captured_log_status == "blocked" and captured_log_diff_like_lines > 0:
                status = "ok_with_captured_warnings"
            elif warnings:
                status = "ok_with_captured_warnings"
            else:
                status = "ok"

    report_path = _run_status_report_path(
        repo,
        str(execution.get("label", "")).strip() or execution_report_path.stem,
    )
    report = {
        "ok": status in {"ok", "ok_with_captured_warnings"},
        "capsule_run_status": status,
        "capsule_run_ok": status in {"ok", "ok_with_captured_warnings"},
        "capsule_run_decision": status,
        "execution_ok": execution_ok,
        "diff_ok": diff_ok,
        "export_plan_ok": export_plan_ok,
        "disallowed_files": disallowed_files,
        "changed_files_count": changed_files_count,
        "tokens_used": tokens_used,
        "blockers": blockers,
        "warnings": warnings,
        "captured_log_status": captured_log_status,
        "captured_log_diff_like_lines": captured_log_diff_like_lines,
        "quiet_runner_report_path": quiet_runner_path,
        "execution_report_path": str(execution_report_path),
        "export_plan_report_path": str(export_plan_path),
        "diff_report_path": str(diff_report_path),
        "capsule_run_status_version": CAPSULE_RUN_STATUS_VERSION,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
