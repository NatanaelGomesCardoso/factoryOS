from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_quiet_runner import QUIET_RUNNER_VERSION, count_diff_like_lines
from app.output_budget import check_output_budget
from app.task_runner import TaskRunnerError
from app.token_usage import parse_token_usage_log

COMPACT_EXECUTION_HARNESS_VERSION = "v0"
COMPACT_EXECUTION_REPORTS_DIR = "compact-execution"
COMPACT_EXECUTION_MODES = {"terminal", "captured"}

COMPACT_EXECUTION_BUDGETS: dict[str, dict[str, Any]] = {
    "docs_only": {
        "max_terminal_lines": 12,
        "max_output_bytes": 6000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4-mini",
        "reasoning_hint": "low",
    },
    "code_small": {
        "max_terminal_lines": 20,
        "max_output_bytes": 9000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4-mini",
        "reasoning_hint": "low",
    },
    "code_medium": {
        "max_terminal_lines": 24,
        "max_output_bytes": 12000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4-mini",
        "reasoning_hint": "medium",
    },
    "live_canary": {
        "max_terminal_lines": 20,
        "max_output_bytes": 12000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4-mini",
        "reasoning_hint": "low",
    },
    "security_review": {
        "max_terminal_lines": 30,
        "max_output_bytes": 15000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4",
        "reasoning_hint": "medium",
    },
    "factory_start": {
        "max_terminal_lines": 20,
        "max_output_bytes": 12000,
        "max_diff_like_lines_terminal": 0,
        "preferred_runner": "codex-quiet-run",
        "model_hint": "gpt-5.4-mini",
        "reasoning_hint": "low",
    },
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def _normalize_category(category: str | None) -> str:
    normalized = (category or "").strip()
    if not normalized:
        return "code_medium"
    if normalized in COMPACT_EXECUTION_BUDGETS:
        return normalized
    if "live_canary" in normalized or "canary" in normalized:
        return "live_canary"
    if "security" in normalized:
        return "security_review"
    if "doc" in normalized or "prd" in normalized or "spec" in normalized:
        return "docs_only"
    if "factory_start" in normalized or "factory start" in normalized:
        return "factory_start"
    if "code_small" in normalized:
        return "code_small"
    return "code_medium"


def compact_exec_budget_for_category(category: str | None = None) -> dict[str, Any]:
    normalized = _normalize_category(category)
    budget = dict(COMPACT_EXECUTION_BUDGETS[normalized])
    budget["category"] = normalized
    return budget


def compact_exec_budget() -> dict[str, Any]:
    return {
        "ok": True,
        "compact_execution_harness_version": COMPACT_EXECUTION_HARNESS_VERSION,
        "quiet_runner_version": QUIET_RUNNER_VERSION,
        "categories": {
            category: {
                **budget,
                "category": category,
            }
            for category, budget in COMPACT_EXECUTION_BUDGETS.items()
        },
    }


def _recommendations(
    *,
    category: str,
    status: str,
    output_budget_check: dict[str, Any],
    diff_like_lines: int,
    mode: str,
) -> list[str]:
    recommendations: list[str] = []
    if status == "blocked":
        recommendations.append("Use codex-quiet-run e mantenha stdout/stderr em arquivo.")
    if output_budget_check.get("status") == "warn":
        recommendations.append("Reduza a saída terminal antes de repetir o comando.")
    if diff_like_lines > 0 and mode == "terminal":
        recommendations.append("Não imprimir diff/patch no terminal; grave em arquivo e resuma só métricas.")
    if diff_like_lines > 0 and mode == "captured" and status != "blocked":
        recommendations.append("Diff-like lines capturadas devem virar warning, não bloqueio.")
    if category in {"live_canary", "factory_start"}:
        recommendations.append("Preferir quiet runner e canários curtos.")
    return recommendations or ["Manter saída compacta e revisar budgets antes de executar."]


def analyze_compact_exec_log(log_path: str | Path, *, category: str, mode: str = "terminal") -> dict[str, Any]:
    path = Path(log_path)
    if not path.exists():
        raise TaskRunnerError(f"log inexistente: {path}")
    if not path.is_file():
        raise TaskRunnerError(f"log não aponta para arquivo: {path}")
    if path.is_symlink():
        raise TaskRunnerError("symlink não permitido no log.")

    normalized_category = _normalize_category(category)
    normalized_mode = str(mode).strip() or "terminal"
    if normalized_mode not in COMPACT_EXECUTION_MODES:
        raise TaskRunnerError(f"modo compacto inválido: {normalized_mode}")

    budget = compact_exec_budget_for_category(normalized_category)
    text = path.read_text(encoding="utf-8", errors="replace")
    output_budget_check = check_output_budget(
        path,
        max_lines=int(budget["max_terminal_lines"]),
        max_bytes=int(budget["max_output_bytes"]),
    )
    token_usage = parse_token_usage_log(path)
    diff_like_lines = count_diff_like_lines(text)

    status = "ok"
    if not bool(output_budget_check.get("ok", False)):
        status = "blocked"
    elif output_budget_check.get("status") == "warn":
        status = "warn"
    elif normalized_mode == "terminal" and diff_like_lines > int(budget["max_diff_like_lines_terminal"]):
        status = "blocked"
    elif normalized_mode == "captured" and diff_like_lines > 0:
        status = "warn"

    return {
        "ok": status != "blocked",
        "category": normalized_category,
        "mode": normalized_mode,
        "status": status,
        "output_lines": int(output_budget_check["output_lines"]),
        "output_bytes": int(output_budget_check["output_bytes"]),
        "diff_like_lines": diff_like_lines,
        "token_usage": token_usage,
        "budget": budget,
        "recommendations": _recommendations(
            category=normalized_category,
            status=status,
            output_budget_check=output_budget_check,
            diff_like_lines=diff_like_lines,
            mode=normalized_mode,
        ),
    }


def compact_exec_report(
    log_path: str | Path,
    *,
    category: str,
    mode: str = "terminal",
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    generated_at = _now_iso()
    analysis = analyze_compact_exec_log(log_path, category=category, mode=mode)
    report_path = repo / "reports" / COMPACT_EXECUTION_REPORTS_DIR / f"{_timestamp()}.json"
    payload = {
        "ok": analysis["ok"],
        "compact_execution_harness_version": COMPACT_EXECUTION_HARNESS_VERSION,
        "quiet_runner_version": QUIET_RUNNER_VERSION,
        "generated_at": generated_at,
        "category": analysis["category"],
        "mode": analysis["mode"],
        "budget": analysis["budget"],
        "check": analysis,
        "log_path": str(Path(log_path)),
        "report_path": report_path.relative_to(repo).as_posix(),
    }
    _write_json_atomic(report_path, payload)
    return payload


def infer_compact_exec_category(
    *,
    context_category: str | None = None,
    codex_profile: str | None = None,
    live: bool = False,
    factory_start: bool = False,
) -> str:
    if factory_start:
        return "live_canary" if live else "factory_start"
    normalized = _normalize_category(context_category)
    if normalized in COMPACT_EXECUTION_BUDGETS:
        return normalized
    if codex_profile == "codex_heavy_review_only":
        return "security_review"
    if live:
        return "live_canary"
    return "code_medium"


def compact_exec_handoff_metadata(
    *,
    context_category: str | None,
    model: str | None,
    reasoning: str | None,
    sandbox: str | None,
    approval: str | None,
    live: bool = False,
    final_summary_max_lines: int = 20,
    no_diff_required: bool = True,
    patch_narration_allowed: bool = False,
) -> dict[str, Any]:
    category = infer_compact_exec_category(context_category=context_category, live=live)
    budget = compact_exec_budget_for_category(category)
    model_hint = model or budget["model_hint"]
    reasoning_hint = reasoning or budget["reasoning_hint"]
    sandbox_hint = sandbox or "workspace-write"
    approval_hint = approval or ("never" if live else "on-request")
    command_example = (
        "codex-quiet-run --prompt-file <PATH> --cwd <PATH> "
        f"--model {model_hint} --reasoning {reasoning_hint} "
        f"--sandbox {sandbox_hint} --approval {approval_hint} --label <LABEL> --dry-run"
    )
    return {
        "compact_execution_harness_version": COMPACT_EXECUTION_HARNESS_VERSION,
        "compact_exec_category": category,
        "max_terminal_lines": int(budget["max_terminal_lines"]),
        "max_output_bytes": int(budget["max_output_bytes"]),
        "max_diff_like_lines_terminal": int(budget["max_diff_like_lines_terminal"]),
        "preferred_runner": budget["preferred_runner"],
        "quiet_runner_recommended": True,
        "diff_suppression_required": True,
        "raw_codex_exec_allowed": False,
        "raw_codex_exec_allowed_reason": "Somente debug/review manual explícito.",
        "final_summary_max_lines": final_summary_max_lines,
        "no_diff_required": no_diff_required,
        "patch_narration_allowed": patch_narration_allowed,
        "command_example": command_example,
        "model_hint": model_hint,
        "reasoning_hint": reasoning_hint,
        "sandbox_hint": sandbox_hint,
        "approval_hint": approval_hint,
    }
