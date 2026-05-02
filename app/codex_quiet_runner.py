from __future__ import annotations

import json
import hashlib
import os
import re
import secrets
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.output_budget import check_output_budget
from app.no_diff_prompt import prompt_has_no_diff_contract
from app.task_runner import TaskRunnerError
from app.token_usage import parse_token_usage_log

QUIET_RUNNER_VERSION = "v0"
QUIET_RUNS_DIR = "codex-quiet-runs"
QUIET_RUNNER_TERMINAL_VISIBLE_MAX_LINES = 20
QUIET_RUNNER_TERMINAL_VISIBLE_MAX_BYTES = 12000
QUIET_RUNNER_CAPTURED_LOG_WARNING_LINES = 120
QUIET_RUNNER_CAPTURED_LOG_WARNING_BYTES = 12000
QUIET_RUNNER_CAPTURED_LOG_HARD_LINES = 500
QUIET_RUNNER_CAPTURED_LOG_HARD_BYTES = 50000
QUIET_RUNNER_CAPTURED_LOG_TRUNCATE_BYTES = 12000
QUIET_RUNNER_CAPTURED_DIFF_LIKE_BLOCK_LIMIT = 50
QUIET_RUNNER_TIMEOUT_SECONDS = 600

_DIFF_LIKE_PATTERNS = (
    re.compile(r"^\s*diff --git\b"),
    re.compile(r"^\s*\+\+\+"),
    re.compile(r"^\s*---"),
    re.compile(r"^\s*@@"),
    re.compile(r"^\s*\+"),
    re.compile(r"^\s*-"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, *, max_length: int = 64) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    normalized = normalized[:max_length].strip("-")
    return normalized or "quiet-run"


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

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


def _validate_file(path: Path, *, kind: str) -> Path:
    if not path.exists():
        raise TaskRunnerError(f"{kind} inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"{kind} não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido em {kind}.")
    return path


def _validate_directory(path: Path, *, kind: str) -> Path:
    if not path.exists():
        raise TaskRunnerError(f"{kind} inexistente: {path}")
    if not path.is_dir():
        raise TaskRunnerError(f"{kind} não aponta para diretório: {path}")
    if path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido em {kind}.")
    return path


def _repo_relative_path(path: str | Path, *, repo: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo / candidate
    resolved = candidate.resolve(strict=False)
    try:
        return resolved.relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise TaskRunnerError(f"caminho fora do repositório: {path}") from exc


def _git_status_short(repo: Path) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "status",
            "--short",
            "--untracked-files=all",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise TaskRunnerError("não foi possível ler git status do repositório.")

    changed_files: list[str] = []
    for raw_line in (completed.stdout or "").splitlines():
        line = raw_line.rstrip()
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if not path_part:
            continue
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        changed_files.append(path_part)
    return changed_files


def _path_matches_allowed(path: str, allowed: str) -> bool:
    normalized_path = Path(path)
    normalized_allowed = Path(allowed)
    if normalized_path == normalized_allowed:
        return True
    try:
        normalized_path.relative_to(normalized_allowed)
        return True
    except ValueError:
        return False


def _normalize_allowed_paths(allowed_paths: list[str] | None, *, repo: Path) -> list[str]:
    normalized: list[str] = []
    for value in allowed_paths or []:
        if not str(value).strip():
            continue
        normalized.append(_repo_relative_path(value, repo=repo))
    return sorted(dict.fromkeys(normalized))


def _safety_flags(
    *,
    prompt_text: str,
    no_push: bool | None,
    no_deploy: bool | None,
    no_paid_api: bool | None,
    no_secrets: bool | None,
) -> dict[str, bool]:
    lowered = prompt_text.lower()
    secret_markers = (
        "token=",
        "api_key",
        "apikey",
        "secret=",
        "password=",
        "passwd=",
        "cookie=",
        "authorization:",
        "bearer ",
        ".env",
        "private key",
    )
    auto_no_secrets = not any(marker in lowered for marker in secret_markers)
    auto_no_push = "push" not in lowered
    auto_no_deploy = "deploy" not in lowered
    auto_no_paid_api = "paid api" not in lowered and "paid-api" not in lowered and "api paga" not in lowered
    return {
        "no_push": bool(auto_no_push if no_push is None else no_push),
        "no_deploy": bool(auto_no_deploy if no_deploy is None else no_deploy),
        "no_paid_api": bool(auto_no_paid_api if no_paid_api is None else no_paid_api),
        "no_secrets": bool(auto_no_secrets if no_secrets is None else no_secrets),
    }


def _channel_status(
    *,
    lines: int,
    bytes_count: int,
    diff_like_lines: int,
    max_lines: int,
    max_bytes: int,
    diff_like_block_limit: int | None = None,
    warn_on_diff_like: bool = False,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if lines > max_lines or bytes_count > max_bytes:
        return "blocked", warnings
    if diff_like_block_limit is not None and diff_like_lines > diff_like_block_limit:
        return "blocked", warnings
    if warn_on_diff_like and diff_like_lines > 0:
        warnings.append(f"captured log contains {diff_like_lines} diff-like line(s).")
    return ("warn" if warnings else "ok"), warnings


def _terminal_payload_metrics(payload: dict[str, Any]) -> dict[str, int]:
    payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return {
        "terminal_visible_lines": len(payload_text.splitlines()) if payload_text else 0,
        "terminal_visible_bytes": len(payload_text.encode("utf-8")),
        "terminal_diff_like_lines": count_diff_like_lines(payload_text),
    }


def _status_rank(status: str) -> int:
    return {"ok": 0, "warn": 1, "blocked": 2}.get(status, 2)


def _worst_budget_status(*statuses: str) -> str:
    return max(statuses, key=_status_rank)


def _overall_status_for_quiet_run(*, execution_status: str, budget_status: str, non_budget_blocked: bool) -> str:
    if execution_status == "timeout":
        return "timeout"
    if execution_status == "failed":
        return "failed"
    if execution_status == "succeeded":
        if non_budget_blocked:
            return "failed"
        if budget_status in {"warn", "blocked"}:
            return "succeeded_with_budget_warnings"
        return "succeeded"
    return "failed"


def _command_metadata(command: list[str]) -> dict[str, bool]:
    joined = " ".join(command)
    return {
        "command_contains_ignore_user_config": "--ignore-user-config" in command,
        "command_contains_ephemeral": "--ephemeral" in command,
        "command_contains_cd": "--cd" in command,
        "command_contains_model": "--model" in command,
        "command_contains_reasoning_effort": "model_reasoning_effort=" in joined,
        "command_contains_approval_policy": "approval_policy=" in joined,
        "command_contains_sandbox_mode": "sandbox_mode=" in joined,
    }


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def build_quiet_codex_command(
    *,
    cwd: str | Path,
    model: str,
    reasoning: str,
    sandbox: str,
    approval: str,
) -> list[str]:
    cwd_path = Path(cwd)
    return [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--cd",
        str(cwd_path),
        "--model",
        model,
        "-c",
        f"model_reasoning_effort={_toml_string(reasoning)}",
        "-c",
        f"approval_policy={_toml_string(approval)}",
        "-c",
        f"sandbox_mode={_toml_string(sandbox)}",
        "-",
    ]


def _log_paths(report_root: Path, timestamp: str, label: str) -> dict[str, Path]:
    base = report_root / f"{timestamp}-{label}"
    return {
        "stdout": base.with_suffix(".stdout.log"),
        "stderr": base.with_suffix(".stderr.log"),
        "combined": base.with_suffix(".combined.log"),
        "preview": base.with_suffix(".preview.log"),
        "report": base.with_suffix(".json"),
    }


def count_diff_like_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.lstrip()
        if any(pattern.match(stripped) for pattern in _DIFF_LIKE_PATTERNS):
            count += 1
    return count


def _analyze_log_text(text: str, *, log_path: Path, max_lines: int, max_bytes: int) -> dict[str, Any]:
    token_usage = parse_token_usage_log(log_path)
    output_budget_check = check_output_budget(log_path, max_lines=max_lines, max_bytes=max_bytes)
    return {
        "log_path": str(log_path),
        "output_lines": len(text.splitlines()) if text else 0,
        "output_bytes": len(text.encode("utf-8")),
        "diff_like_lines": count_diff_like_lines(text),
        "token_usage": token_usage,
        "output_budget_check": output_budget_check,
    }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text_from_stream(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _build_preview_text(text: str, *, max_bytes: int) -> tuple[str, bool]:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text, False

    preview = raw[:max_bytes].decode("utf-8", errors="replace")
    if preview and not preview.endswith("\n"):
        preview += "\n"
    preview += "...[truncated preview]\n"
    return preview, True


def _summary_lines(report: dict[str, Any]) -> list[str]:
    token_usage = report.get("token_usage", {})
    budget_check = report.get("output_budget_check", {})
    lines = [
        f"ok={str(report.get('ok', False)).lower()} executed={str(report.get('executed', False)).lower()} label={report.get('label', '')}",
        f"report_path={report.get('report_path', '')}",
        f"stdout_log_path={report.get('stdout_log_path', '')}",
        f"stderr_log_path={report.get('stderr_log_path', '')}",
        f"combined_log_path={report.get('combined_log_path', '')}",
        f"output_lines={report.get('output_lines', 0)} output_bytes={report.get('output_bytes', 0)} diff_like_lines={report.get('diff_like_lines', 0)}",
        f"tokens_used={token_usage.get('tokens_used')} input_tokens={token_usage.get('input_tokens')} cached_input_tokens={token_usage.get('cached_input_tokens')} output_tokens={token_usage.get('output_tokens')}",
        f"budget_status={budget_check.get('status', 'missing')} budget_ok={str(budget_check.get('ok', False)).lower()}",
    ]
    return [line for line in lines if line.strip()]


def run_codex_quiet_run(
    *,
    prompt_file: str | Path,
    cwd: str | Path,
    model: str,
    reasoning: str,
    sandbox: str,
    approval: str,
    label: str,
    allowed_paths: list[str] | None = None,
    no_push: bool | None = None,
    no_deploy: bool | None = None,
    no_paid_api: bool | None = None,
    no_secrets: bool | None = None,
    dry_run: bool = True,
    execute: bool = False,
    repo: Path | None = None,
    timeout_seconds: int = QUIET_RUNNER_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    repo = repo or repo_root()
    if execute and dry_run:
        raise TaskRunnerError("--dry-run e --execute são mutuamente exclusivos.")

    prompt_path = _validate_file(Path(prompt_file), kind="prompt file")
    cwd_path = _validate_directory(Path(cwd), kind="cwd")
    if not label.strip():
        raise TaskRunnerError("label não pode ficar vazio.")

    timestamp = _timestamp()
    safe_label = _slugify(label)
    report_root = repo / "reports" / QUIET_RUNS_DIR
    paths = _log_paths(report_root, timestamp, safe_label)

    command = build_quiet_codex_command(
        cwd=cwd_path,
        model=model,
        reasoning=reasoning,
        sandbox=sandbox,
        approval=approval,
    )
    command_metadata = _command_metadata(command)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    safety = _safety_flags(
        prompt_text=prompt_text,
        no_push=no_push,
        no_deploy=no_deploy,
        no_paid_api=no_paid_api,
        no_secrets=no_secrets,
    )
    normalized_allowed_paths = _normalize_allowed_paths(allowed_paths, repo=repo)
    git_status_before = _git_status_short(repo)
    started_at = _now_iso()
    started = time.monotonic()
    executed = bool(execute)
    exit_code: int | None = None
    stdout_text = ""
    stderr_text = ""
    execution_error_type: str | None = None
    execution_error_message: str | None = None
    prompt_has_contract = prompt_has_no_diff_contract(prompt_text)

    if executed:
        if os.environ.get("FACTORYOS_ENABLE_QUIET_CODEX") != "1":
            raise TaskRunnerError("execução quiet codex bloqueada; defina FACTORYOS_ENABLE_QUIET_CODEX=1.")

        try:
            completed = subprocess.run(
                command,
                cwd=cwd_path,
                input=prompt_text,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout_text = _text_from_stream(getattr(exc, "stdout", ""))
            stderr_text = _text_from_stream(getattr(exc, "stderr", ""))
            execution_error_type = "timeout"
            execution_error_message = f"execução quiet do Codex excedeu {timeout_seconds} segundos."
        except FileNotFoundError:
            exit_code = 127
            execution_error_type = "command_not_found"
            execution_error_message = "comando codex não encontrado no PATH."
        except subprocess.SubprocessError as exc:
            exit_code = 1
            execution_error_type = "execution_error"
            execution_error_message = str(exc) or "falha ao executar o Codex."
        else:
            exit_code = completed.returncode
            stdout_text = completed.stdout or ""
            stderr_text = completed.stderr or ""
            if exit_code not in (None, 0):
                execution_error_type = "nonzero_exit_code"
                execution_error_message = f"codex retornou exit code {exit_code}."
    else:
        _write_text_atomic(paths["stdout"], "")
        _write_text_atomic(paths["stderr"], "")
        _write_text_atomic(paths["combined"], "")

    combined_text = stdout_text + ("\n" if stdout_text and stderr_text else "") + stderr_text
    git_status_after = _git_status_short(repo)
    if executed:
        _write_text_atomic(paths["stdout"], stdout_text)
        _write_text_atomic(paths["stderr"], stderr_text)
        _write_text_atomic(paths["combined"], combined_text)

    analyzed = _analyze_log_text(
        combined_text,
        log_path=paths["combined"],
        max_lines=QUIET_RUNNER_CAPTURED_LOG_WARNING_LINES,
        max_bytes=QUIET_RUNNER_CAPTURED_LOG_WARNING_BYTES,
    )
    output_budget_check = analyzed["output_budget_check"]
    captured_log_lines = analyzed["output_lines"]
    captured_log_bytes = analyzed["output_bytes"]
    captured_log_diff_like_lines = analyzed["diff_like_lines"]
    captured_log_sha256 = _sha256_text(combined_text)
    preview_text, captured_log_truncated = _build_preview_text(
        combined_text,
        max_bytes=QUIET_RUNNER_CAPTURED_LOG_TRUNCATE_BYTES,
    )
    _write_text_atomic(paths["preview"], preview_text)
    captured_log_warnings: list[str] = []
    captured_log_status = "ok"
    if (
        captured_log_lines > QUIET_RUNNER_CAPTURED_LOG_HARD_LINES
        or captured_log_bytes > QUIET_RUNNER_CAPTURED_LOG_HARD_BYTES
    ):
        captured_log_status = "blocked"
        captured_log_warnings.append("captured log ultrapassou o limite duro de linhas ou bytes.")
    elif (
        captured_log_lines > QUIET_RUNNER_CAPTURED_LOG_WARNING_LINES
        or captured_log_bytes > QUIET_RUNNER_CAPTURED_LOG_WARNING_BYTES
        or output_budget_check.get("status") == "warn"
    ):
        captured_log_status = "warn"
        captured_log_warnings.append("captured log ultrapassou o budget de aviso de linhas ou bytes.")
    elif captured_log_truncated:
        captured_log_status = "warn"
        captured_log_warnings.append(
            f"captured log truncado em preview seguro de {QUIET_RUNNER_CAPTURED_LOG_TRUNCATE_BYTES} bytes."
        )
    if captured_log_diff_like_lines > QUIET_RUNNER_CAPTURED_DIFF_LIKE_BLOCK_LIMIT:
        captured_log_status = "blocked"
        captured_log_warnings.append(
            f"captured log ultrapassou o limite forte de diff-like lines ({QUIET_RUNNER_CAPTURED_DIFF_LIKE_BLOCK_LIMIT})."
        )
    elif captured_log_diff_like_lines > 0:
        captured_log_status = "warn"
        captured_log_warnings.append(
            f"captured log contém {captured_log_diff_like_lines} diff-like line(s); mantido em arquivo."
        )

    token_usage_warnings = analyzed["token_usage"].get("warnings", [])
    if isinstance(token_usage_warnings, list) and token_usage_warnings:
        captured_log_warnings.extend(str(item) for item in token_usage_warnings)
        if captured_log_status == "ok":
            captured_log_status = "warn"

    if not prompt_has_contract:
        captured_log_warnings.append("prompt sem no-diff-prompt-contract.")
        if captured_log_status == "ok":
            captured_log_status = "warn"

    if not all(safety.values()):
        captured_log_status = "blocked"
        if not safety["no_push"]:
            captured_log_warnings.append("safety flag no_push=false.")
        if not safety["no_deploy"]:
            captured_log_warnings.append("safety flag no_deploy=false.")
        if not safety["no_paid_api"]:
            captured_log_warnings.append("safety flag no_paid_api=false.")
        if not safety["no_secrets"]:
            captured_log_warnings.append("safety flag no_secrets=false.")

    runner_artifact_prefixes = ("reports/codex-quiet-runs/",)
    before_filtered = [
        path
        for path in git_status_before
        if not any(path.startswith(prefix) for prefix in runner_artifact_prefixes)
    ]
    after_filtered = [
        path
        for path in git_status_after
        if not any(path.startswith(prefix) for prefix in runner_artifact_prefixes)
    ]
    changed_files = sorted(set(after_filtered) - set(before_filtered))
    allowed_files = normalized_allowed_paths
    disallowed_files = [
        path for path in changed_files if allowed_files and not any(_path_matches_allowed(path, allowed) for allowed in allowed_files)
    ]
    changed_files_ok = True if not allowed_files else (bool(changed_files) and not disallowed_files)

    terminal_visible_payload = {
        "ok": True,
        "label": label,
        "quiet_runner_version": QUIET_RUNNER_VERSION,
        "executed": executed,
        "exit_code": exit_code,
        "report_path": str(paths["report"].relative_to(repo).as_posix()),
        "terminal_visible_lines": 0,
        "terminal_visible_bytes": 0,
        "terminal_diff_like_lines": 0,
    }
    terminal_metrics = _terminal_payload_metrics(terminal_visible_payload)
    terminal_ok = (
        terminal_metrics["terminal_visible_lines"] <= QUIET_RUNNER_TERMINAL_VISIBLE_MAX_LINES
        and terminal_metrics["terminal_visible_bytes"] <= QUIET_RUNNER_TERMINAL_VISIBLE_MAX_BYTES
        and terminal_metrics["terminal_diff_like_lines"] == 0
    )
    terminal_status = "ok" if terminal_ok else "blocked"
    terminal_visible_payload.update(terminal_metrics)
    terminal_summary = _summary_lines(
        {
            "ok": terminal_ok and (exit_code in (None, 0)) and execution_error_type is None,
            "executed": executed,
            "label": label,
            "report_path": str(paths["report"].relative_to(repo).as_posix()),
            "stdout_log_path": str(paths["stdout"].relative_to(repo).as_posix()),
            "stderr_log_path": str(paths["stderr"].relative_to(repo).as_posix()),
            "combined_log_path": str(paths["combined"].relative_to(repo).as_posix()),
            "output_lines": analyzed["output_lines"],
            "output_bytes": analyzed["output_bytes"],
            "diff_like_lines": analyzed["diff_like_lines"],
            "token_usage": analyzed["token_usage"],
            "output_budget_check": output_budget_check,
        }
    )

    execution_status = "succeeded"
    if execution_error_type == "timeout":
        execution_status = "timeout"
    elif execution_error_type is not None or exit_code not in (None, 0):
        execution_status = "failed"

    budget_status = _worst_budget_status(str(output_budget_check.get("status", "ok")), captured_log_status)
    budget_ok = budget_status != "blocked"

    non_budget_blocked = (not terminal_ok) or (not changed_files_ok) or (not all(safety.values()))

    overall_status = _overall_status_for_quiet_run(
        execution_status=execution_status,
        budget_status=budget_status,
        non_budget_blocked=non_budget_blocked,
    )

    ok = (
        execution_status == "succeeded"
        and terminal_ok
        and changed_files_ok
        and all(safety.values())
    )
    warnings = list(captured_log_warnings)

    report_path = paths["report"]
    report = {
        "ok": ok,
        "report_ok": ok,
        "execution_status": execution_status,
        "budget_status": budget_status,
        "budget_ok": budget_ok,
        "terminal_status": terminal_status,
        "overall_status": overall_status,
        "quiet_runner_version": QUIET_RUNNER_VERSION,
        "timeout": execution_error_type == "timeout",
        "timeout_seconds": timeout_seconds,
        "label": label,
        "safe_label": safe_label,
        "dry_run": bool(dry_run),
        "executed": executed,
        "exit_code": exit_code,
        "error_type": execution_error_type,
        "error_message": execution_error_message,
        "command": command,
        "command_metadata": command_metadata,
        **command_metadata,
        "model": model,
        "reasoning": reasoning,
        "sandbox": sandbox,
        "approval": approval,
        "prompt_file": str(prompt_path),
        "cwd": str(cwd_path),
        "prompt_lines": len(prompt_text.splitlines()) if prompt_text else 0,
        "prompt_bytes": len(prompt_text.encode("utf-8")),
        "git_status_before": git_status_before,
        "git_status_after": git_status_after,
        "changed_files": changed_files,
        "allowed_files": allowed_files,
        "disallowed_files": disallowed_files,
        "changed_files_ok": changed_files_ok,
        "no_push": safety["no_push"],
        "no_deploy": safety["no_deploy"],
        "no_paid_api": safety["no_paid_api"],
        "no_secrets": safety["no_secrets"],
        "stdout_log_path": str(paths["stdout"].relative_to(repo).as_posix()),
        "stderr_log_path": str(paths["stderr"].relative_to(repo).as_posix()),
        "combined_log_path": str(paths["combined"].relative_to(repo).as_posix()),
        "token_usage": analyzed["token_usage"],
        "output_budget_check": output_budget_check,
        "output_lines": analyzed["output_lines"],
        "output_bytes": analyzed["output_bytes"],
        "diff_like_lines": analyzed["diff_like_lines"],
        "diff_suppressed": True,
        "terminal_visible_budget": {
            "max_lines": QUIET_RUNNER_TERMINAL_VISIBLE_MAX_LINES,
            "max_bytes": QUIET_RUNNER_TERMINAL_VISIBLE_MAX_BYTES,
            "max_diff_like_lines": 0,
        },
        "terminal_visible_lines": terminal_metrics["terminal_visible_lines"],
        "terminal_visible_bytes": terminal_metrics["terminal_visible_bytes"],
        "terminal_diff_like_lines": terminal_metrics["terminal_diff_like_lines"],
        "terminal_ok": terminal_ok,
        "captured_log_budget": {
            "max_lines": QUIET_RUNNER_CAPTURED_LOG_WARNING_LINES,
            "max_bytes": QUIET_RUNNER_CAPTURED_LOG_WARNING_BYTES,
            "max_diff_like_lines_block": QUIET_RUNNER_CAPTURED_DIFF_LIKE_BLOCK_LIMIT,
        },
        "captured_log_warning_budget": {
            "lines": QUIET_RUNNER_CAPTURED_LOG_WARNING_LINES,
            "bytes": QUIET_RUNNER_CAPTURED_LOG_WARNING_BYTES,
        },
        "captured_log_hard_limit": {
            "lines": QUIET_RUNNER_CAPTURED_LOG_HARD_LINES,
            "bytes": QUIET_RUNNER_CAPTURED_LOG_HARD_BYTES,
        },
        "captured_log_truncation_policy": {
            "max_bytes": QUIET_RUNNER_CAPTURED_LOG_TRUNCATE_BYTES,
            "preview_path": str(paths["preview"].relative_to(repo).as_posix()),
        },
        "captured_log_status": captured_log_status,
        "captured_log_warnings": captured_log_warnings,
        "warnings": warnings,
        "captured_log_lines": captured_log_lines,
        "captured_log_bytes": captured_log_bytes,
        "captured_log_diff_like_lines": captured_log_diff_like_lines,
        "captured_log_truncated": captured_log_truncated,
        "captured_log_sha256": captured_log_sha256,
        "captured_log_full_path": str(paths["combined"].relative_to(repo).as_posix()),
        "captured_log_preview_path": str(paths["preview"].relative_to(repo).as_posix()),
        "prompt_has_no_diff_contract": prompt_has_contract,
        "terminal_summary_lines": len(terminal_summary),
        "global_config_dependency": False,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "generated_at": started_at,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
    _write_json_atomic(report_path, report)
    return {
        **report,
        "terminal_summary": terminal_summary,
    }


def compare_quiet_run_logs(log_a: str | Path, log_b: str | Path) -> dict[str, Any]:
    path_a = _validate_file(Path(log_a), kind="log")
    path_b = _validate_file(Path(log_b), kind="log")
    text_a = path_a.read_text(encoding="utf-8", errors="replace")
    text_b = path_b.read_text(encoding="utf-8", errors="replace")
    usage_a = parse_token_usage_log(path_a)
    usage_b = parse_token_usage_log(path_b)
    tokens_a = usage_a.get("tokens_used")
    tokens_b = usage_b.get("tokens_used")
    tokens_saved = None
    percent_saved = None
    if isinstance(tokens_a, int) and isinstance(tokens_b, int):
        tokens_saved = tokens_a - tokens_b
        if tokens_a > 0:
            percent_saved = round((tokens_saved / tokens_a) * 100, 2)

    return {
        "ok": True,
        "left_log": str(path_a),
        "right_log": str(path_b),
        "left": {
            "tokens_used": usage_a.get("tokens_used"),
            "input_tokens": usage_a.get("input_tokens"),
            "cached_input_tokens": usage_a.get("cached_input_tokens"),
            "output_tokens": usage_a.get("output_tokens"),
            "output_lines": len(text_a.splitlines()) if text_a else 0,
            "output_bytes": len(text_a.encode("utf-8")),
            "diff_like_lines": count_diff_like_lines(text_a),
        },
        "right": {
            "tokens_used": usage_b.get("tokens_used"),
            "input_tokens": usage_b.get("input_tokens"),
            "cached_input_tokens": usage_b.get("cached_input_tokens"),
            "output_tokens": usage_b.get("output_tokens"),
            "output_lines": len(text_b.splitlines()) if text_b else 0,
            "output_bytes": len(text_b.encode("utf-8")),
            "diff_like_lines": count_diff_like_lines(text_b),
        },
        "tokens_saved": tokens_saved,
        "percent_saved": percent_saved,
        "quiet_runner_version": QUIET_RUNNER_VERSION,
    }
