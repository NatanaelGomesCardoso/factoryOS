from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

OUTPUT_BUDGET_CONTRACT_VERSION = "v0"
TOOL_STDOUT_BUDGET_CONTRACT_VERSION = "v0"
MAX_TERMINAL_LINES = 35
DEFAULT_MAX_BYTES = 12000
WARN_RATIO = 0.8


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

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


def output_budget_contract_lines() -> list[str]:
    return [
        "OUTPUT + TOOL STDOUT BUDGET CONTRACT",
        "",
        "- Terminal max 35 lines.",
        "- No full diffs.",
        "- No full worktree list.",
        "- No full task-list/run-list JSON.",
        "- No full reports list.",
        "- Redirect large command output to files in <TMP_DIR> or reports.",
        "- Print only compact metrics and report paths.",
        "- Write detailed evidence to reports/proofs.",
        "- Final answer must be COMPACT FINAL SUMMARY only.",
    ]


def output_budget_contract_text() -> str:
    return "\n".join(output_budget_contract_lines()) + "\n"


def output_budget_contract_summary() -> dict[str, Any]:
    return {
        "output_budget_contract_version": OUTPUT_BUDGET_CONTRACT_VERSION,
        "tool_stdout_budget_contract_version": TOOL_STDOUT_BUDGET_CONTRACT_VERSION,
        "max_terminal_lines": MAX_TERMINAL_LINES,
        "default_max_bytes": DEFAULT_MAX_BYTES,
        "large_stdout_policy": "redirect_large_stdout_to_files_and_print_only_compact_metrics",
        "token_usage_parser_available": True,
        "compact_summary_required": True,
    }


def check_output_budget(log_path: str | Path, *, max_lines: int, max_bytes: int) -> dict[str, Any]:
    path = Path(log_path)
    if not path.exists():
        raise TaskRunnerError(f"log inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"log não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError("symlink não permitido no log.")

    content = path.read_text(encoding="utf-8", errors="replace")
    output_lines = len(content.splitlines()) if content else 0
    output_bytes = len(content.encode("utf-8"))

    status = "ok"
    if output_lines > max_lines or output_bytes > max_bytes:
        status = "blocked"
    elif output_lines >= max(1, int(max_lines * WARN_RATIO)) or output_bytes >= max(1, int(max_bytes * WARN_RATIO)):
        status = "warn"

    return {
        "ok": status != "blocked",
        "output_lines": output_lines,
        "output_bytes": output_bytes,
        "max_lines": max_lines,
        "max_bytes": max_bytes,
        "status": status,
    }


def build_output_budget_report(
    *,
    log_path: str | Path,
    repo: Path,
    max_lines: int = MAX_TERMINAL_LINES,
    max_bytes: int = DEFAULT_MAX_BYTES,
    parser_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = parser_result or {}
    budget_check = check_output_budget(log_path, max_lines=max_lines, max_bytes=max_bytes)
    generated_at = _now_iso()
    report_dir = repo / "reports" / "token-economy"
    report_path = report_dir / f"{_timestamp()}.json"
    payload = {
        "ok": True,
        "generated_at": generated_at,
        "log_path": str(Path(log_path)),
        "report_path": report_path.relative_to(repo).as_posix(),
        "parser_result": parsed,
        "budget_check": budget_check,
        **output_budget_contract_summary(),
    }
    _write_json_atomic(report_path, payload)
    return payload
