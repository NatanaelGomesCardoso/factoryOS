from __future__ import annotations

import json
import os
import secrets
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_context_router import context_pack_for_run
from app.capsule_execution_policy import policy_for_run
from app.compact_execution_harness import compact_exec_handoff_metadata
from app.codex_profile import codex_plan_for_run
from app.no_diff_prompt import NO_DIFF_PROMPT_CONTRACT_VERSION, no_diff_prompt_contract_text, prompt_has_no_diff_contract
from app.output_budget import output_budget_contract_summary, output_budget_contract_text
from app.run_workspace import repo_root, show_run, workspace_status
from app.task_runner import TaskRunnerError, show_task

LIVE_CODEX_ENV = "FACTORYOS_ENABLE_LIVE_CODEX"
HANDOFF_REPORTS_DIR = "run-handoffs"
LIVE_CODEX_TIMEOUT_SECONDS = 600
FACTORYOS_CODEX_SANDBOXES = {"read-only", "workspace-write"}
FACTORYOS_CODEX_APPROVALS = {"on-request", "never"}


@dataclass(frozen=True, slots=True)
class LatestHandoffResult:
    available: bool
    run_id: str
    task_id: str
    task_title: str
    task_description: str
    mode: str
    report_path: str
    prompt_path: str
    prompt_view_path: str | None
    view_path: str | None
    workspace_path: str
    workspace_kind: str | None
    workspace_branch: str | None
    workspace_state: str
    created_at: str
    executed: bool
    live_enabled: bool
    readiness_status: str | None
    readiness_reasons: list[str]
    budget: dict[str, Any]
    codex_command: list[str]
    technical_pending: str | None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / HANDOFF_REPORTS_DIR


def _prompt_path(repo: Path, run_id: str) -> Path:
    return _reports_root(repo) / f"{run_id}.prompt.md"


def _report_path(repo: Path, run_id: str) -> Path:
    return _reports_root(repo) / f"{run_id}.json"


def _safe_relative_path(value: str, *, prefix: str, suffix: str) -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {"..", "."} for part in candidate.parts):
        return False

    return candidate.as_posix().startswith(prefix) and candidate.suffix == suffix


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


def _validate_workspace_path(run_id: str, workspace_path: str) -> None:
    candidate = Path(workspace_path)
    if candidate.is_absolute():
        raise TaskRunnerError("workspace_path absoluto não permitido.")

    if any(part in {"..", "."} for part in candidate.parts):
        raise TaskRunnerError("path traversal não permitido em workspace_path.")

    expected = Path("workspaces") / "runs" / run_id
    if candidate.as_posix() != expected.as_posix():
        raise TaskRunnerError("workspace_path da run não corresponde ao id.")


def _load_running_run(run_id: str, *, repo: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = repo or repo_root()

    run_result = show_run(run_id, repo=repo)
    run = run_result["run"]
    if run.get("status") != "running":
        raise TaskRunnerError("run precisa estar em running para gerar handoff.")

    task_result = show_task(str(run["task_id"]), repo=repo)
    task = task_result["task"]

    workspace_path = str(run.get("workspace_path", "")).strip()
    if not workspace_path:
        raise TaskRunnerError("workspace_path da run não pode ficar vazio.")

    _validate_workspace_path(str(run["id"]), workspace_path)

    return run, task


def _workspace_state(repo: Path, workspace_path: str) -> tuple[str, str | None]:
    workspace_dir = repo / workspace_path

    if not workspace_dir.exists():
        return "missing", "Workspace ainda não existe; pendência técnica para Sprint 012/013."

    if not workspace_dir.is_dir():
        raise TaskRunnerError("workspace_path não aponta para um diretório.")

    if any(workspace_dir.iterdir()):
        return "populated", None

    return "empty_directory", "Workspace vazio; decidir depois entre git worktree real ou execução no repo com branch isolada."


def _allowed_paths(run_id: str) -> list[str]:
    return [
        "app/",
        "specs/",
        "tasks/",
        "reports/run-handoffs/",
        f"workspaces/runs/{run_id}/",
    ]


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _resolved_workspace_path(workspace_path: str | Path, *, repo: Path | None = None) -> Path:
    repo = repo or repo_root()
    candidate = Path(workspace_path)
    if not candidate.is_absolute():
        candidate = repo / candidate
    return candidate.resolve()


def build_factoryos_codex_exec_command(
    *,
    codex_plan: dict[str, Any],
    context_pack: dict[str, Any] | None,
    workspace_path: str | Path,
    live: bool = False,
    automated: bool = False,
    repo: Path | None = None,
) -> list[str]:
    budget_status = str(codex_plan.get("budget_status", "")).strip()
    if budget_status != "ok":
        raise TaskRunnerError(f"Codex bloqueado por budget_status={budget_status or 'missing'}.")

    context = context_pack or {}
    context_status = str(context.get("context_status", "ok")).strip() or "ok"
    if live and context_status != "ok":
        raise TaskRunnerError(f"Codex live bloqueado por context_status={context_status}.")

    if live and not bool(codex_plan.get("live")):
        raise TaskRunnerError("Codex live bloqueado: codex_plan não permite execução live.")

    model = str(codex_plan.get("model", "")).strip()
    reasoning_effort = str(codex_plan.get("reasoning_effort", "")).strip()
    if not model or not reasoning_effort:
        raise TaskRunnerError("Codex bloqueado: codex_plan sem model/reasoning_effort explícitos.")

    sandbox_mode = str(codex_plan.get("sandbox_mode", "workspace-write")).strip() or "workspace-write"
    if sandbox_mode not in FACTORYOS_CODEX_SANDBOXES:
        raise TaskRunnerError(f"Codex bloqueado: sandbox_mode inseguro para FactoryOS ({sandbox_mode}).")

    plan_approval = str(codex_plan.get("approval_policy", "")).strip()
    approval_policy = "never" if (live or automated) else (plan_approval or "on-request")
    if approval_policy not in FACTORYOS_CODEX_APPROVALS:
        raise TaskRunnerError(f"Codex bloqueado: approval_policy inválido ({approval_policy}).")

    return [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--cd",
        str(_resolved_workspace_path(workspace_path, repo=repo)),
        "--model",
        model,
        "-c",
        f"model_reasoning_effort={_toml_string(reasoning_effort)}",
        "-c",
        f"approval_policy={_toml_string(approval_policy)}",
        "-c",
        f"sandbox_mode={_toml_string(sandbox_mode)}",
        "-",
    ]


def _codex_command_metadata(command: list[str], codex_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "uses_ignore_user_config": "--ignore-user-config" in command,
        "uses_ephemeral": "--ephemeral" in command,
        "uses_cd": "--cd" in command,
        "model": codex_plan.get("model"),
        "reasoning_effort": codex_plan.get("reasoning_effort"),
        "sandbox_mode": codex_plan.get("sandbox_mode"),
        "approval_policy": "never" if 'approval_policy="never"' in command else codex_plan.get("approval_policy"),
        "source_of_truth": "codex_plan",
        "global_config_dependency": False,
        "reasons": [
            "FactoryOS sempre usa --ignore-user-config para não depender do global.",
            "FactoryOS sempre usa --ephemeral para evitar persistência de sessão.",
            "Modelo, reasoning, sandbox e approval vêm do codex_plan/política local.",
        ],
    }


def _local_no_codex_metadata(codex_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "uses_ignore_user_config": False,
        "uses_ephemeral": False,
        "uses_cd": False,
        "model": codex_plan.get("model"),
        "reasoning_effort": codex_plan.get("reasoning_effort"),
        "sandbox_mode": codex_plan.get("sandbox_mode"),
        "approval_policy": codex_plan.get("approval_policy"),
        "source_of_truth": "codex_plan",
        "global_config_dependency": False,
        "reasons": [
            "Tarefa barata pode ser resolvida localmente sem invocar Codex.",
            "FactoryOS preserva o caminho econômico quando recommended_profile=local_no_codex.",
        ],
    }


def _validate_factoryos_codex_command(command: list[str]) -> None:
    required = {"codex", "exec", "--ignore-user-config", "--ephemeral", "--cd", "--model", "-c"}
    missing = [item for item in required if item not in command]
    if missing:
        raise TaskRunnerError(f"comando Codex inseguro; flags ausentes: {', '.join(sorted(missing))}.")
    joined = " ".join(command)
    for key in ("model_reasoning_effort=", "approval_policy=", "sandbox_mode="):
        if key not in joined:
            raise TaskRunnerError(f"comando Codex inseguro; config ausente: {key}")


def _build_prompt(
    *,
    run: dict[str, Any],
    task: dict[str, Any],
    mode: str,
    workspace_kind: str | None,
    workspace_branch: str | None,
    workspace_state: str,
    readiness_status: str | None,
    readiness_reasons: list[str],
    technical_pending: str | None,
    codex_plan: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
) -> str:
    budget_block = json.dumps(run["budget"], ensure_ascii=False, indent=2)
    codex_plan_block = json.dumps(codex_plan or {}, ensure_ascii=False, indent=2)
    context_pack_block = json.dumps(context_pack or {}, ensure_ascii=False, indent=2)
    budget_contract = output_budget_contract_summary()
    output_budget_block = output_budget_contract_text().strip()
    compact_metadata = compact_exec_handoff_metadata(
        context_category=str((context_pack or {}).get("category", "")).strip() or None,
        model=str((codex_plan or {}).get("model", "")).strip() or None,
        reasoning=str((codex_plan or {}).get("reasoning_effort", "")).strip() or None,
        sandbox=str((codex_plan or {}).get("sandbox_mode", "")).strip() or None,
        approval=str((codex_plan or {}).get("approval_policy", "")).strip() or None,
    )
    no_diff_contract = no_diff_prompt_contract_text(final_summary_max_lines=20)
    allowed_block = "\n".join(f"- `{path}`" for path in _allowed_paths(str(run["id"])))
    validation_block = "\n".join(
        [
            "- Validar `run_id` e `task_id` antes de qualquer escrita.",
            "- Bloquear path traversal e symlinks.",
            "- Não usar `shell=True` em nenhuma chamada.",
            "- Não executar live sem `FACTORYOS_ENABLE_LIVE_CODEX=1`.",
            "- Não registrar segredo, token, cookie ou credencial.",
            "- Não fazer deploy.",
            "- Não usar API paga.",
            "- Não alterar arquivos fora do escopo permitido.",
        ]
    )
    technical_block = technical_pending or "Nenhuma pendência técnica adicional registrada."

    return "\n".join(
        [
            "# FactoryOS Codex Handoff",
            "",
            "## Contexto",
            f"- Run ID: `{run['id']}`",
            f"- Task ID: `{task['id']}`",
            f"- Task title: `{task['title']}`",
            f"- Run status: `{run['status']}`",
            f"- Mode: `{mode}`",
            f"- Workspace path: `{run['workspace_path']}`",
            f"- Workspace kind: `{workspace_kind or 'n/d'}`",
            f"- Workspace branch: `{workspace_branch or 'n/d'}`",
            f"- Workspace state: `{workspace_state}`",
            f"- Workspace readiness: `{readiness_status or 'n/d'}`",
            "",
            "## Task context",
            task["description"],
            "",
            "## Budget",
            "```json",
            budget_block,
            "```",
            "",
            "## Codex profile plan",
            "```json",
            codex_plan_block,
            "```",
            "",
            "## Codex context pack",
            "```json",
            context_pack_block,
            "```",
            "",
            "## Output budget contract",
            output_budget_block,
            "",
            "## Output budget metadata",
            f"- output_budget_contract_version: `{budget_contract['output_budget_contract_version']}`",
            f"- tool_stdout_budget_contract_version: `{budget_contract['tool_stdout_budget_contract_version']}`",
            f"- compact_summary_required: `{str(budget_contract['compact_summary_required']).lower()}`",
            f"- token_usage_parser_available: `{str(budget_contract['token_usage_parser_available']).lower()}`",
            "",
            "## Compact execution harness",
            f"- compact_execution_harness_version: `{compact_metadata['compact_execution_harness_version']}`",
            f"- compact_exec_category: `{compact_metadata['compact_exec_category']}`",
            f"- max_terminal_lines: `{compact_metadata['max_terminal_lines']}`",
            f"- max_output_bytes: `{compact_metadata['max_output_bytes']}`",
            f"- diff_suppression_required: `{str(compact_metadata['diff_suppression_required']).lower()}`",
            f"- no_diff_required: `{str(compact_metadata['no_diff_required']).lower()}`",
            f"- patch_narration_allowed: `{str(compact_metadata['patch_narration_allowed']).lower()}`",
            f"- final_summary_max_lines: `{compact_metadata['final_summary_max_lines']}`",
            f"- quiet_runner_recommended: `{str(compact_metadata['quiet_runner_recommended']).lower()}`",
            f"- raw_codex_exec_allowed: `{str(compact_metadata['raw_codex_exec_allowed']).lower()}`",
            f"- preferred_runner: `{compact_metadata['preferred_runner']}`",
            "",
            "## No-diff prompt contract",
            no_diff_contract.strip(),
            "",
            "## Regras de segurança",
            "- Backend continua sendo a fonte de verdade.",
            "- O painel e o frontend continuam apenas leitura.",
            "- Proibido registrar segredos, tokens, cookies ou credenciais.",
            "- Proibido fazer deploy ou chamar API paga.",
            "- Proibido executar live sem `FACTORYOS_ENABLE_LIVE_CODEX=1`.",
            "- Proibido usar `shell=True`.",
            "- Proibido despejar patch bruto no terminal.",
            "",
            "## Arquivos permitidos",
            allowed_block,
            "",
            "## Validações obrigatórias",
            validation_block,
            "",
            "## Pendência técnica",
            technical_block,
            "",
            "## Readiness",
            f"- status: `{readiness_status or 'n/d'}`",
            *([f"- {reason}" for reason in readiness_reasons] if readiness_reasons else []),
            "",
            "## Pedido final",
            "Retorne um relatório final em JSON com resumo, arquivos alterados, validações executadas, riscos, bloqueios e confirmação explícita de execução ou não execução live.",
        ]
    )


def _prompt_and_report_paths(repo: Path, run_id: str) -> tuple[Path, Path]:
    return _prompt_path(repo, run_id), _report_path(repo, run_id)


def _build_report(
    *,
    repo: Path,
    run: dict[str, Any],
    task: dict[str, Any],
    mode: str,
    prompt_path: Path,
    report_path: Path,
    workspace_kind: str | None,
    workspace_branch: str | None,
    workspace_state: str,
    readiness_status: str | None,
    readiness_reasons: list[str],
    technical_pending: str | None,
    executed: bool,
    live_enabled: bool,
    prompt_has_no_diff_contract_value: bool,
    codex_plan: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile_plan = codex_plan or {}
    context = context_pack or {}
    capsule_policy = policy_for_run(str(run["id"]), repo=repo)
    budget_contract = output_budget_contract_summary()
    compact_metadata = compact_exec_handoff_metadata(
        context_category=str(context.get("category", "")).strip() or None,
        model=str(profile_plan.get("model", "")).strip() or None,
        reasoning=str(profile_plan.get("reasoning_effort", "")).strip() or None,
        sandbox=str(profile_plan.get("sandbox_mode", "")).strip() or None,
        approval=str(profile_plan.get("approval_policy", "")).strip() or None,
        live=live_enabled,
    )
    if str(profile_plan.get("recommended_profile", "")).strip() == "local_no_codex" or not bool(profile_plan.get("must_use_codex", False)):
        codex_command = []
        command_metadata = _local_no_codex_metadata(profile_plan)
    else:
        codex_command = build_factoryos_codex_exec_command(
            codex_plan=profile_plan,
            context_pack=context,
            workspace_path=str(run["workspace_path"]),
            live=live_enabled,
            automated=live_enabled,
            repo=repo,
        )
        _validate_factoryos_codex_command(codex_command)
        command_metadata = _codex_command_metadata(codex_command, profile_plan)
    return {
        "ok": True,
        "mode": mode,
        "run_id": run["id"],
        "task_id": task["id"],
        "task_title": task["title"],
        "task_description": task["description"],
        "task_status": task["status"],
        "workspace_path": run["workspace_path"],
        "workspace_kind": workspace_kind,
        "workspace_branch": workspace_branch,
        "workspace_state": workspace_state,
        "readiness_status": readiness_status,
        "readiness_reasons": readiness_reasons,
        "technical_pending": technical_pending,
        "budget": run["budget"],
        "routing_contract": profile_plan.get("routing_contract") or context.get("routing_contract") or {},
        "routing_contract_source": profile_plan.get("routing_contract_source") or context.get("routing_contract_source"),
        "routing_contract_valid": profile_plan.get("routing_contract_valid", context.get("routing_contract_valid")),
        "codex_plan": profile_plan,
        "codex_profile": profile_plan.get("recommended_profile"),
        "model": profile_plan.get("model"),
        "reasoning_effort": profile_plan.get("reasoning_effort"),
        "context_budget": {
            "estimated_context_chars": profile_plan.get("estimated_context_chars"),
            "max_context_chars": profile_plan.get("max_context_chars"),
            "estimated_changed_files": profile_plan.get("estimated_changed_files"),
            "max_changed_files": profile_plan.get("max_changed_files"),
        },
        "budget_status": profile_plan.get("budget_status"),
        "context_pack": context,
        "context_category": context.get("category"),
        "included_files": context.get("included_files", []),
        "excluded_files": context.get("excluded_files", []),
        "context_chars": context.get("context_chars"),
        "context_status": context.get("context_status"),
        "execution_mode_recommendation": capsule_policy["execution_mode_recommendation"],
        "capsule_recommended": capsule_policy["capsule_recommended"],
        "capsule_policy_decision": capsule_policy["capsule_policy_decision"],
        "expected_savings_percent": capsule_policy["expected_savings_percent"],
        "full_repo_required_reason": capsule_policy["full_repo_required_reason"],
        "timeout_recovery_policy": capsule_policy["timeout_recovery_policy"],
        "allowed_to_execute_live": capsule_policy["allowed_to_execute_live"],
        "recommended_command_kind": capsule_policy["recommended_command_kind"],
        "policy_version": capsule_policy["policy_version"],
        "policy_decision": capsule_policy["decision"],
        "policy_reason": capsule_policy["reason"],
        "policy_notes": capsule_policy["notes"],
        "codex_command": codex_command,
        "codex_command_policy": command_metadata,
        "uses_ignore_user_config": command_metadata["uses_ignore_user_config"],
        "uses_ephemeral": command_metadata["uses_ephemeral"],
        "approval_policy": command_metadata["approval_policy"],
        "sandbox_mode": command_metadata["sandbox_mode"],
        "source_of_truth": command_metadata["source_of_truth"],
        "global_config_dependency": command_metadata["global_config_dependency"],
        "output_budget_contract_version": budget_contract["output_budget_contract_version"],
        "tool_stdout_budget_contract_version": budget_contract["tool_stdout_budget_contract_version"],
        "max_terminal_lines": budget_contract["max_terminal_lines"],
        "large_stdout_policy": budget_contract["large_stdout_policy"],
        "token_usage_parser_available": budget_contract["token_usage_parser_available"],
        "compact_summary_required": budget_contract["compact_summary_required"],
        "no_diff_prompt_contract_version": NO_DIFF_PROMPT_CONTRACT_VERSION,
        "no_diff_required": compact_metadata["no_diff_required"],
        "patch_narration_allowed": compact_metadata["patch_narration_allowed"],
        "final_summary_max_lines": compact_metadata["final_summary_max_lines"],
        "prompt_has_no_diff_contract": prompt_has_no_diff_contract_value,
        **compact_metadata,
        "prompt_path": prompt_path.relative_to(repo).as_posix(),
        "report_path": report_path.relative_to(repo).as_posix(),
        "executed": executed,
        "live_enabled": live_enabled,
        "created_at": _now_iso(),
        "allowed_paths": _allowed_paths(str(run["id"])),
    }


def _require_live_enabled() -> None:
    if os.environ.get(LIVE_CODEX_ENV) != "1":
        raise TaskRunnerError(
            f"live Codex bloqueado; defina {LIVE_CODEX_ENV}=1 para permitir execução."
        )


def _write_prompt(
    *,
    run: dict[str, Any],
    task: dict[str, Any],
    prompt_path: Path,
    mode: str,
    workspace_kind: str | None,
    workspace_branch: str | None,
    workspace_state: str,
    readiness_status: str | None,
    readiness_reasons: list[str],
    technical_pending: str | None,
    codex_plan: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
) -> None:
    prompt_text = _build_prompt(
        run=run,
        task=task,
        mode=mode,
        workspace_kind=workspace_kind,
        workspace_branch=workspace_branch,
        workspace_state=workspace_state,
        readiness_status=readiness_status,
        readiness_reasons=readiness_reasons,
        technical_pending=technical_pending,
        codex_plan=codex_plan,
        context_pack=context_pack,
    )
    _write_text_atomic(prompt_path, prompt_text + "\n")


def execute_live_codex(
    command: list[str],
    *,
    cwd: Path | None = None,
    input_text: str | None = None,
    timeout_seconds: int = LIVE_CODEX_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    _validate_factoryos_codex_command(command)
    try:
        return subprocess.run(
            command,
            cwd=cwd or repo_root(),
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise TaskRunnerError("comando codex não encontrado no PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise TaskRunnerError(
            f"execução live do Codex excedeu {timeout_seconds} segundos."
        ) from exc


def run_handoff(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    run, task = _load_running_run(run_id, repo=repo)
    workspace_snapshot = workspace_status(run_id, repo=repo)["workspace"]
    readiness_status = workspace_snapshot.get("readiness_status")
    readiness_reasons = workspace_snapshot.get("readiness_reasons", [])
    prompt_path, report_path = _prompt_and_report_paths(repo, str(run["id"]))
    codex_plan = codex_plan_for_run(str(run["id"]), repo=repo)
    context_pack = context_pack_for_run(str(run["id"]), repo=repo)

    _write_prompt(
        run=run,
        task=task,
        prompt_path=prompt_path,
        mode="handoff",
        workspace_kind=workspace_snapshot.get("kind"),
        workspace_branch=workspace_snapshot.get("branch"),
        workspace_state=str(workspace_snapshot.get("state", "")) or "unknown",
        readiness_status=readiness_status if isinstance(readiness_status, str) else None,
        readiness_reasons=[str(item) for item in readiness_reasons] if isinstance(readiness_reasons, list) else [],
        technical_pending=workspace_snapshot.get("technical_pending"),
        codex_plan=codex_plan,
        context_pack=context_pack,
    )
    prompt_contract_ok = prompt_has_no_diff_contract(prompt_path.read_text(encoding="utf-8"))
    if not prompt_contract_ok:
        raise TaskRunnerError("prompt de handoff não contém no-diff-prompt-contract.")

    report = _build_report(
        repo=repo,
        run=run,
        task=task,
        mode="handoff",
        prompt_path=prompt_path,
        report_path=report_path,
        workspace_kind=workspace_snapshot.get("kind"),
        workspace_branch=workspace_snapshot.get("branch"),
        workspace_state=str(workspace_snapshot.get("state", "")) or "unknown",
        readiness_status=readiness_status if isinstance(readiness_status, str) else None,
        readiness_reasons=[str(item) for item in readiness_reasons] if isinstance(readiness_reasons, list) else [],
        technical_pending=workspace_snapshot.get("technical_pending"),
        executed=False,
        live_enabled=False,
        prompt_has_no_diff_contract_value=prompt_contract_ok,
        codex_plan=codex_plan,
        context_pack=context_pack,
    )
    _write_json_atomic(report_path, report)
    return report


def run_execute(
    run_id: str,
    *,
    live: bool = False,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    run, task = _load_running_run(run_id, repo=repo)
    workspace_snapshot = workspace_status(run_id, repo=repo)["workspace"]
    readiness_status = workspace_snapshot.get("readiness_status")
    readiness_reasons = workspace_snapshot.get("readiness_reasons", [])
    prompt_path, report_path = _prompt_and_report_paths(repo, str(run["id"]))

    mode = "live" if live else "dry-run"
    codex_plan = codex_plan_for_run(str(run["id"]), live=live, repo=repo)
    context_pack = context_pack_for_run(str(run["id"]), repo=repo)
    if live:
        _require_live_enabled()
        if readiness_status != "ready":
            reasons = [str(item) for item in readiness_reasons] if isinstance(readiness_reasons, list) else []
            reason_text = "; ".join(reasons) if reasons else "workspace não está ready."
            raise TaskRunnerError(f"live Codex bloqueado: {reason_text}")

    _write_prompt(
        run=run,
        task=task,
        prompt_path=prompt_path,
        mode=mode,
        workspace_kind=workspace_snapshot.get("kind"),
        workspace_branch=workspace_snapshot.get("branch"),
        workspace_state=str(workspace_snapshot.get("state", "")) or "unknown",
        readiness_status=readiness_status if isinstance(readiness_status, str) else None,
        readiness_reasons=[str(item) for item in readiness_reasons] if isinstance(readiness_reasons, list) else [],
        technical_pending=workspace_snapshot.get("technical_pending"),
        codex_plan=codex_plan,
        context_pack=context_pack,
    )
    prompt_contract_ok = prompt_has_no_diff_contract(prompt_path.read_text(encoding="utf-8"))
    if not prompt_contract_ok:
        raise TaskRunnerError("prompt de execução não contém no-diff-prompt-contract.")

    report = _build_report(
        repo=repo,
        run=run,
        task=task,
        mode=mode,
        prompt_path=prompt_path,
        report_path=report_path,
        workspace_kind=workspace_snapshot.get("kind"),
        workspace_branch=workspace_snapshot.get("branch"),
        workspace_state=str(workspace_snapshot.get("state", "")) or "unknown",
        readiness_status=readiness_status if isinstance(readiness_status, str) else None,
        readiness_reasons=[str(item) for item in readiness_reasons] if isinstance(readiness_reasons, list) else [],
        technical_pending=workspace_snapshot.get("technical_pending"),
        executed=False,
        live_enabled=live,
        prompt_has_no_diff_contract_value=prompt_contract_ok,
        codex_plan=codex_plan,
        context_pack=context_pack,
    )
    _write_json_atomic(report_path, report)

    if live:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        execution = execute_live_codex(report["codex_command"], input_text=prompt_text)
        if execution.returncode != 0:
            stderr = execution.stderr.strip() if execution.stderr else ""
            stdout = execution.stdout.strip() if execution.stdout else ""
            detail = stderr or stdout or "saída vazia"
            raise TaskRunnerError(
                f"execução live do Codex falhou com código {execution.returncode}: {detail}"
            )
        report["executed"] = True
        report["created_at"] = _now_iso()
        _write_json_atomic(report_path, report)

    return report


def load_latest_handoff_result(repo: Path) -> LatestHandoffResult:
    reports_dir = _reports_root(repo)
    candidates = sorted(
        reports_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for latest in candidates:
        try:
            payload: dict[str, Any] = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(payload, dict):
            continue

        run_id = str(payload.get("run_id", "")).strip()
        task_id = str(payload.get("task_id", "")).strip()
        task_title = str(payload.get("task_title", "")).strip()
        task_description = str(payload.get("task_description", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        report_path = str(payload.get("report_path", "")).strip()
        prompt_path = str(payload.get("prompt_path", "")).strip()
        workspace_path = str(payload.get("workspace_path", "")).strip()
        workspace_kind = payload.get("workspace_kind")
        workspace_branch = payload.get("workspace_branch")
        workspace_state = str(payload.get("workspace_state", "")).strip()
        readiness_status = payload.get("readiness_status")
        readiness_reasons = payload.get("readiness_reasons", [])
        created_at = str(payload.get("created_at", "")).strip()
        executed = bool(payload.get("executed", False))
        live_enabled = bool(payload.get("live_enabled", False))
        budget = payload.get("budget", {})
        codex_command = payload.get("codex_command", [])
        technical_pending = payload.get("technical_pending")

        if not all([run_id, task_id, task_title, task_description, mode, report_path, prompt_path, workspace_path, workspace_state, created_at]):
            continue

        actual_report_path = latest.relative_to(repo).as_posix()
        if report_path != actual_report_path:
            continue

        if not _safe_relative_path(report_path, prefix=f"reports/{HANDOFF_REPORTS_DIR}/", suffix=".json"):
            continue

        if not _safe_relative_path(prompt_path, prefix=f"reports/{HANDOFF_REPORTS_DIR}/", suffix=".md"):
            continue

        if not isinstance(budget, dict):
            continue

        if not isinstance(codex_command, list) or not all(isinstance(item, str) for item in codex_command):
            continue

        if readiness_status is not None and not isinstance(readiness_status, str):
            continue

        if not isinstance(readiness_reasons, list):
            continue

        if mode not in {"handoff", "dry-run", "live"}:
            continue

        return LatestHandoffResult(
            available=True,
            run_id=run_id,
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            mode=mode,
            report_path=report_path,
            prompt_path=prompt_path,
            prompt_view_path=Path(prompt_path).relative_to("reports").as_posix(),
            view_path=latest.relative_to(repo / "reports").as_posix(),
            workspace_path=workspace_path,
            workspace_kind=str(workspace_kind).strip() if isinstance(workspace_kind, str) and workspace_kind.strip() else None,
            workspace_branch=str(workspace_branch).strip() if isinstance(workspace_branch, str) and workspace_branch.strip() else None,
            workspace_state=workspace_state,
            created_at=created_at,
            executed=executed,
            live_enabled=live_enabled,
            readiness_status=str(readiness_status).strip() if isinstance(readiness_status, str) and readiness_status.strip() else None,
            readiness_reasons=[str(item) for item in readiness_reasons],
            budget={str(key): value for key, value in budget.items()},
            codex_command=[str(item) for item in codex_command],
            technical_pending=str(technical_pending).strip() if isinstance(technical_pending, str) and technical_pending.strip() else None,
        )

    return LatestHandoffResult(
        available=False,
        run_id="",
        task_id="",
        task_title="",
        task_description="",
        mode="unknown",
        report_path="",
        prompt_path="",
        prompt_view_path=None,
        view_path=None,
        workspace_path="",
        workspace_kind=None,
        workspace_branch=None,
        workspace_state="unknown",
        created_at="",
        executed=False,
        live_enabled=False,
        readiness_status=None,
        readiness_reasons=[],
        budget={},
        codex_command=[],
        technical_pending=None,
    )
