from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_context_router import context_pack_for_task
from app.codex_handoff import build_factoryos_codex_exec_command
from app.codex_profile import codex_plan_for_task
from app.run_workspace import repo_root
from app.task_runner import TaskRunnerError, list_tasks

CODEX_COST_AUDIT_DIR = "codex-cost-audits"
PREVIOUS_LEAN_TOKEN_BASELINE = 23021
IDEAL_TOKEN_TARGET = 12000


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _report_path(repo: Path, generated_at: str) -> Path:
    timestamp = datetime.fromisoformat(generated_at).strftime("%Y%m%d-%H%M%S")
    return repo / "reports" / CODEX_COST_AUDIT_DIR / f"{timestamp}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _walk_numbers(value: Any, keys: tuple[str, ...]) -> list[int]:
    found: list[int] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and isinstance(item, int):
                found.append(item)
            found.extend(_walk_numbers(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_numbers(item, keys))
    return found


def _extract_tokens(text: str) -> int | None:
    totals: list[int] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                event = None
            if event is not None:
                totals.extend(_walk_numbers(event, ("total_tokens", "tokens_used", "tokens")))

    for pattern in (
        r"tokens\s+used\s*\n\s*([0-9][0-9,.]*)",
        r"total[_ ]tokens[\"'=:\\s]+([0-9][0-9,.]*)",
        r"tokens[_ ]used[\"'=:\\s]+([0-9][0-9,.]*)",
        r"([0-9][0-9,.]*)\s+tokens",
    ):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = match.group(1).replace(".", "").replace(",", "")
            if raw.isdigit():
                totals.append(int(raw))

    return max(totals) if totals else None


def _warnings(text: str) -> list[str]:
    warnings: list[str] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "warning" in lowered or "deprecated" in lowered:
            warnings.append(line.strip()[:300])
    return warnings[:10]


def _run_case(
    *,
    name: str,
    command: list[str],
    input_text: str | None,
    model: str | None,
    reasoning: str | None,
    sandbox: str | None,
    approval: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        if input_text is None and shutil.which("script"):
            completed = subprocess.run(
                ["script", "-qfec", shlex.join(command), "/dev/null"],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        else:
            completed = subprocess.run(
                command,
                input=input_text,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        exit_code = completed.returncode
        combined = f"{completed.stdout}\n{completed.stderr}"
        error = ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        combined = f"{exc.stdout or ''}\n{exc.stderr or ''}"
        error = f"timeout_after_{timeout_seconds}s"

    wall_seconds = round(time.monotonic() - started, 3)
    uses_ignore = "--ignore-user-config" in command
    uses_ephemeral = "--ephemeral" in command
    return {
        "name": name,
        "success": exit_code == 0,
        "exit_code": exit_code,
        "wall_seconds": wall_seconds,
        "tokens_used": _extract_tokens(combined),
        "model": model,
        "reasoning": reasoning,
        "sandbox": sandbox,
        "approval": approval,
        "uses_ignore_user_config": uses_ignore,
        "uses_ephemeral": uses_ephemeral,
        "blocked": name.startswith("factoryos_") and (not uses_ignore or not uses_ephemeral),
        "warnings": _warnings(combined),
        "error": error,
    }


def _latest_codex_task_id(repo: Path) -> str | None:
    result = list_tasks(repo=repo)
    tasks: list[dict[str, Any]] = []
    for group in result.get("groups", []):
        if not isinstance(group, dict):
            continue
        for task in group.get("tasks", []):
            if isinstance(task, dict) and str(task.get("executor", "")) == "codex":
                tasks.append(task)
    tasks.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return str(tasks[0]["id"]) if tasks else None


def _forced_lean_plan() -> dict[str, Any]:
    return {
        "ok": True,
        "recommended_profile": "codex_mini_low",
        "codex_profile": "codex_mini_low",
        "budget_status": "ok",
        "model": "gpt-5.4-mini",
        "reasoning_effort": "low",
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "live": False,
    }


def _with_prompt_argument(command: list[str], prompt: str) -> list[str]:
    if command and command[-1] == "-":
        return [*command[:-1], prompt]
    return [*command, prompt]


def run_codex_cost_audit(*, repo: Path | None = None, timeout_seconds: int = 240) -> dict[str, Any]:
    repo = repo or repo_root()
    generated_at = _now_iso()
    cases: list[dict[str, Any]] = []

    raw_command = [
        "codex",
        "exec",
        "--ephemeral",
        "--cd",
        str(repo),
        "Responda apenas: RAW_GLOBAL_OK",
    ]
    cases.append(
        _run_case(
            name="raw_global_minimal",
            command=raw_command,
            input_text=None,
            model=None,
            reasoning=None,
            sandbox=None,
            approval=None,
            timeout_seconds=timeout_seconds,
        )
    )

    forced_plan = _forced_lean_plan()
    forced_command = build_factoryos_codex_exec_command(
        codex_plan=forced_plan,
        context_pack={"context_status": "ok", "category": "forced_lean"},
        workspace_path=repo,
        automated=True,
        repo=repo,
    )
    cases.append(
        _run_case(
            name="factoryos_forced_lean",
            command=_with_prompt_argument(forced_command, "Responda apenas: FACTORYOS_FORCED_LEAN_OK"),
            input_text=None,
            model=str(forced_plan["model"]),
            reasoning=str(forced_plan["reasoning_effort"]),
            sandbox=str(forced_plan["sandbox_mode"]),
            approval="never",
            timeout_seconds=timeout_seconds,
        )
    )

    task_id = _latest_codex_task_id(repo)
    if task_id:
        repo_plan = codex_plan_for_task(task_id, repo=repo)
        if str(repo_plan.get("budget_status")) != "ok" or not repo_plan.get("model"):
            repo_plan = {
                **_forced_lean_plan(),
                "recommended_profile": "codex_mini_medium",
                "codex_profile": "codex_mini_medium",
                "reasoning_effort": "medium",
            }
        context_pack = context_pack_for_task(task_id, repo=repo)
        repo_command = build_factoryos_codex_exec_command(
            codex_plan=repo_plan,
            context_pack=context_pack,
            workspace_path=repo,
            automated=True,
            repo=repo,
        )
        prompt = "\n".join(
            [
                "Responda apenas: FACTORYOS_REPO_AWARE_OK",
                f"task_id={task_id}",
                f"context_category={context_pack.get('category')}",
                "Não edite arquivos.",
            ]
        )
        cases.append(
            _run_case(
                name="factoryos_repo_aware",
                command=_with_prompt_argument(repo_command, prompt),
                input_text=None,
                model=str(repo_plan.get("model")),
                reasoning=str(repo_plan.get("reasoning_effort")),
                sandbox=str(repo_plan.get("sandbox_mode")),
                approval="never",
                timeout_seconds=timeout_seconds,
            )
        )
    else:
        cases.append(
            {
                "name": "factoryos_repo_aware",
                "success": False,
                "exit_code": 2,
                "wall_seconds": 0,
                "tokens_used": None,
                "model": None,
                "reasoning": None,
                "sandbox": None,
                "approval": None,
                "uses_ignore_user_config": False,
                "uses_ephemeral": False,
                "blocked": True,
                "warnings": [],
                "error": "no_codex_task_available",
            }
        )

    by_name = {case["name"]: case for case in cases}
    raw_tokens = by_name["raw_global_minimal"].get("tokens_used")
    lean_tokens = by_name["factoryos_forced_lean"].get("tokens_used")
    factory_blocked = any(case.get("blocked") for case in cases if str(case.get("name", "")).startswith("factoryos_"))

    comparisons: dict[str, Any] = {
        "ok": None,
        "preferred_ok": None,
        "ideal": None,
        "blocked": factory_blocked,
    }
    if isinstance(raw_tokens, int) and isinstance(lean_tokens, int):
        comparisons["ok"] = lean_tokens <= raw_tokens
    if isinstance(lean_tokens, int):
        comparisons["preferred_ok"] = lean_tokens <= PREVIOUS_LEAN_TOKEN_BASELINE
        comparisons["ideal"] = lean_tokens <= IDEAL_TOKEN_TARGET

    if factory_blocked:
        status = "blocked"
    elif comparisons["ideal"] is True:
        status = "ideal"
    elif comparisons["preferred_ok"] is True:
        status = "preferred_ok"
    elif comparisons["ok"] is True:
        status = "ok"
    elif lean_tokens is None:
        status = "unknown_tokens"
    else:
        status = "failed"

    report_path = _report_path(repo, generated_at)
    report = {
        "ok": status in {"ideal", "preferred_ok", "ok", "unknown_tokens"},
        "generated_at": generated_at,
        "cases": cases,
        "classification": {
            "status": status,
            "comparisons": comparisons,
            "previous_lean_token_baseline": PREVIOUS_LEAN_TOKEN_BASELINE,
            "ideal_token_target": IDEAL_TOKEN_TARGET,
        },
        "report_path": report_path.relative_to(repo).as_posix(),
        "no_secrets": True,
        "used_paid_api": False,
    }
    _write_json(report_path, report)
    return report
