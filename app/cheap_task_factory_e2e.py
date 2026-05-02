from __future__ import annotations

import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.capsule_execution_policy import policy_for_category
from app.codex_capsule_execution import (
    run_codex_capsule_diff,
    run_codex_capsule_export_plan,
    run_codex_capsule_run,
    run_codex_capsule_status,
)
from app.codex_context_capsule import create_capsule
from app.task_runner import TaskRunnerError

CHEAP_TASK_FACTORY_E2E_VERSION = "v0"
CHEAP_TASK_FACTORY_E2E_REPORT_DIR = "cheap-task-factory-e2e"
CHEAP_TASK_FACTORY_E2E_PROMPT_DIR = "cheap-task-factory-e2e-prompts"
CHEAP_TASK_FACTORY_E2E_CANARY_FILE = "cheap-task-e2e-canary.txt"
CHEAP_TASK_FACTORY_E2E_ALLOWED_CATEGORIES = {"docs_only", "code_small"}
CHEAP_TASK_FACTORY_E2E_CAPSULE_MODES = {"standard", "ultra_slim", "ultra_slim_min"}
CHEAP_TASK_FACTORY_E2E_INCLUDE_MAP: dict[str, list[str]] = {
    "docs_only": [
        "docs/capsule-execution-policy.md",
        "docs/capsule-execution-patch-gate.md",
        "docs/codex-quiet-runner.md",
        "docs/compact-execution-harness.md",
        "docs/no-diff-prompt-discipline.md",
    ],
    "code_small": [
        "docs/capsule-execution-policy.md",
        "docs/capsule-execution-patch-gate.md",
        "docs/codex-quiet-runner.md",
        "app/capsule_execution_policy.py",
        "app/codex_capsule_execution.py",
        "app/codex_quiet_runner.py",
        "app/compact_execution_harness.py",
    ],
}


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
    return normalized[:max_length] or "cheap-task"


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


def _report_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CHEAP_TASK_FACTORY_E2E_REPORT_DIR / f"{_timestamp()}-{_slugify(label)}.json")


def _prompt_path(repo: Path, label: str) -> Path:
    return _unique_path(repo / "reports" / CHEAP_TASK_FACTORY_E2E_PROMPT_DIR / f"{_timestamp()}-{_slugify(label)}.md")


def _validate_category(category: str) -> str:
    normalized = str(category).strip()
    if normalized not in CHEAP_TASK_FACTORY_E2E_ALLOWED_CATEGORIES:
        allowed = ", ".join(sorted(CHEAP_TASK_FACTORY_E2E_ALLOWED_CATEGORIES))
        raise TaskRunnerError(f"categoria inválida para cheap-task-factory-e2e: {normalized or '<vazia>'}. Permitidas: {allowed}.")
    return normalized


def _canary_prompt_text(*, category: str, label: str, capsule_path: str, include_count: int, capsule_mode: str) -> str:
    if capsule_mode == "ultra_slim_min":
        return "\n".join(
            [
                "no-diff-prompt-contract",
                f"Create only {CHEAP_TASK_FACTORY_E2E_CANARY_FILE}.",
                f"Write: OK {category} {label}",
                "Final reply exactly: OK",
            ]
        ).strip() + "\n"

    if capsule_mode == "ultra_slim":
        return "\n".join(
            [
                "no-diff-prompt-contract",
                f"category={category}",
                f"label={label}",
                f"included_files={include_count}",
                f"Create only {CHEAP_TASK_FACTORY_E2E_CANARY_FILE}.",
                "File text: OK category and label.",
                "Do not edit anything else. Do not show diff, patch, file content, or lists.",
                "Final reply exactly: OK",
            ]
        ).strip() + "\n"

    return "\n".join(
        [
            "Você está dentro de uma cápsula FactoryOS isolada.",
            "Execute apenas o canário barato e não faça nenhuma outra alteração.",
            f"category={category}",
            f"label={label}",
            f"capsule_path={capsule_path}",
            f"included_files={include_count}",
            "",
            "Faça somente isto:",
            f"- criar apenas `{CHEAP_TASK_FACTORY_E2E_CANARY_FILE}`",
            f"- escrever um texto curto confirmando `category={category}` e `label={label}`",
            "- não editar nenhum outro arquivo",
            "- não fazer push, pull, fetch, rebase ou deploy",
            "- não usar API paga",
            "- não tocar em secrets",
            "- não imprimir diff bruto",
            "- manter a saída compacta",
        ]
    ).strip() + "\n"


def run_cheap_task_factory_e2e(
    *,
    category: str,
    label: str,
    dry_run: bool,
    execute_canary: bool,
    capsule_mode: str = "standard",
    max_prompt_bytes: int | None = None,
    max_capsule_bytes: int | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    normalized_category = _validate_category(category)
    normalized_label = str(label).strip() or "cheap-task"
    normalized_capsule_mode = str(capsule_mode).strip() or "standard"
    if normalized_capsule_mode not in CHEAP_TASK_FACTORY_E2E_CAPSULE_MODES:
        allowed_modes = ", ".join(sorted(CHEAP_TASK_FACTORY_E2E_CAPSULE_MODES))
        raise TaskRunnerError(f"capsule_mode inválido: {normalized_capsule_mode}. Permitidos: {allowed_modes}.")
    policy = policy_for_category(normalized_category, live_policy="blocked")

    if policy.get("capsule_policy_decision") != "capsule":
        raise TaskRunnerError(f"policy não recomenda capsule para {normalized_category}: {policy.get('capsule_policy_decision')}.")

    slim_modes = {"ultra_slim", "ultra_slim_min"}
    include_paths = [] if normalized_capsule_mode in slim_modes else CHEAP_TASK_FACTORY_E2E_INCLUDE_MAP[normalized_category]
    report_path = _report_path(repo, normalized_label)

    if dry_run and not execute_canary:
        payload = {
            "ok": True,
            "cheap_task_factory_e2e_version": CHEAP_TASK_FACTORY_E2E_VERSION,
            "category": normalized_category,
            "label": normalized_label,
            "policy_decision": policy.get("capsule_policy_decision"),
            "expected_savings_percent": policy.get("expected_savings_percent"),
            "baseline_factoryos_tokens": policy.get("expected_token_baseline", 23302),
            "capsule_tokens": policy.get("expected_token_capsule"),
            "tokens_used": 0,
            "changed_files_count": 0,
            "disallowed_files": [],
            "executed_live": False,
            "no_push": True,
            "no_deploy": True,
            "no_paid_api": True,
            "no_secrets": True,
            "capsule_path": "",
            "capsule_mode": normalized_capsule_mode,
            "prompt_path": "",
            "prompt_effective_bytes": 0,
            "agents_bytes": 0,
            "manifest_bytes": 0,
            "capsule_total_bytes": 0,
            "capsule_non_git_bytes": 0,
            "capsule_git_hooks_bytes": 0,
            "max_prompt_bytes": max_prompt_bytes,
            "max_capsule_bytes": max_capsule_bytes,
            "execution_report_path": "",
            "diff_report_path": "",
            "export_plan_report_path": "",
            "status_report_path": "",
            "capsule_run_decision": "dry_run_only",
            "capsule_run_ok": True,
            "target_le_7000": False,
            "floor_estimate_tokens": None,
            "accepted_floor_recommendation": False,
            "report_path": str(report_path.relative_to(repo).as_posix()),
            "created_at": _now_iso(),
            "warnings": [],
            "blockers": [],
            "policy": policy,
        }
        _write_json_atomic(report_path, payload)
        return payload

    capsule_result = create_capsule(
        label=normalized_label,
        source_root=repo,
        include_paths=include_paths,
        use_latest_digest=False,
        max_context_bytes=max_capsule_bytes or (5 * 1024 if normalized_capsule_mode == "ultra_slim_min" else 12 * 1024 if normalized_capsule_mode == "ultra_slim" else 64 * 1024),
        capsule_mode=normalized_capsule_mode,
        allowed_write_paths=[CHEAP_TASK_FACTORY_E2E_CANARY_FILE],
        allow_empty_context=normalized_capsule_mode in slim_modes,
        repo=repo,
    )
    capsule_path = str(capsule_result["capsule_path"])

    prompt_path = _prompt_path(repo, normalized_label)
    prompt_text = _canary_prompt_text(
        category=normalized_category,
        label=normalized_label,
        capsule_path=capsule_path,
        include_count=len(include_paths),
        capsule_mode=normalized_capsule_mode,
    )
    prompt_effective_bytes = len(prompt_text.encode("utf-8"))
    if max_prompt_bytes is not None and prompt_effective_bytes > max_prompt_bytes:
        raise TaskRunnerError(
            f"prompt excede max_prompt_bytes: prompt_effective_bytes={prompt_effective_bytes} max_prompt_bytes={max_prompt_bytes}."
        )
    _write_text_atomic(prompt_path, prompt_text)

    capsule_run_label = f"{normalized_label}-capsule"
    capsule_run = run_codex_capsule_run(
        capsule=capsule_path,
        prompt_file=prompt_path,
        label=capsule_run_label,
        model="gpt-5.4-mini",
        reasoning="low",
        sandbox="workspace-write",
        execute=True,
        repo=repo,
    )
    diff_report = run_codex_capsule_diff(capsule=capsule_path, repo=repo)
    export_plan = run_codex_capsule_export_plan(capsule=capsule_path, source_root=repo, repo=repo)
    status_report = run_codex_capsule_status(
        execution_report=capsule_run["report_path"],
        export_plan=export_plan["report_path"],
        diff_report=diff_report["report_path"],
        repo=repo,
    )

    tokens_used = int(status_report.get("tokens_used") or capsule_run.get("tokens_used") or 0)
    capsule_tokens = int(capsule_run.get("tokens_used") or tokens_used or 0)
    warnings = [str(item) for item in status_report.get("warnings", []) if str(item).strip()]
    target_tokens = 7000 if normalized_capsule_mode in slim_modes else 5000
    target_le_7000 = bool(tokens_used <= 7000)
    floor_estimate_tokens = tokens_used if normalized_capsule_mode == "ultra_slim_min" and tokens_used > 7000 else None
    accepted_floor_recommendation = bool(floor_estimate_tokens)
    if tokens_used > target_tokens:
        warnings.append(f"tokens_used={tokens_used} acima do alvo de {target_tokens}.")
    if accepted_floor_recommendation:
        warnings.append("ultra_slim_min ficou acima de 7000 tokens; menor modo seguro recomenda aceitar piso real medido.")

    payload = {
        "ok": bool(status_report.get("capsule_run_ok", False)),
        "cheap_task_factory_e2e_version": CHEAP_TASK_FACTORY_E2E_VERSION,
        "category": normalized_category,
        "label": normalized_label,
        "policy_decision": policy.get("capsule_policy_decision"),
        "expected_savings_percent": policy.get("expected_savings_percent"),
        "baseline_factoryos_tokens": policy.get("expected_token_baseline", 23302),
        "capsule_tokens": capsule_tokens,
        "tokens_used": tokens_used,
        "changed_files_count": int(status_report.get("changed_files_count") or 0),
        "disallowed_files": status_report.get("disallowed_files", []),
        "executed_live": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "capsule_path": capsule_path,
        "capsule_mode": normalized_capsule_mode,
        "prompt_path": str(prompt_path.relative_to(repo).as_posix()),
        "prompt_effective_bytes": prompt_effective_bytes,
        "agents_bytes": int(capsule_result.get("agents_bytes") or 0),
        "manifest_bytes": int(capsule_result.get("manifest_bytes") or 0),
        "capsule_total_bytes": int(capsule_result.get("capsule_total_bytes") or 0),
        "capsule_non_git_bytes": int(capsule_result.get("capsule_non_git_bytes") or 0),
        "capsule_git_hooks_bytes": int(capsule_result.get("capsule_git_hooks_bytes") or 0),
        "max_prompt_bytes": max_prompt_bytes,
        "max_capsule_bytes": max_capsule_bytes,
        "execution_report_path": str(capsule_run.get("report_path", "")),
        "diff_report_path": str(diff_report.get("report_path", "")),
        "export_plan_report_path": str(export_plan.get("report_path", "")),
        "status_report_path": str(status_report.get("report_path", "")),
        "capsule_run_ok": bool(status_report.get("capsule_run_ok", False)),
        "capsule_run_decision": str(status_report.get("capsule_run_decision", "")),
        "target_le_7000": target_le_7000,
        "floor_estimate_tokens": floor_estimate_tokens,
        "accepted_floor_recommendation": accepted_floor_recommendation,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
        "warnings": warnings,
        "blockers": [str(item) for item in status_report.get("blockers", []) if str(item).strip()],
        "policy": policy,
        "capsule": capsule_result,
        "capsule_run": capsule_run,
        "diff_report": diff_report,
        "export_plan": export_plan,
        "status_report": status_report,
        "canary_file": CHEAP_TASK_FACTORY_E2E_CANARY_FILE,
    }
    _write_json_atomic(report_path, payload)
    return payload
