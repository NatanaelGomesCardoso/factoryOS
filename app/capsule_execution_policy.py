from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.codex_context_router import context_pack_for_run, context_pack_for_task
from app.codex_profile import codex_plan_for_run, codex_plan_for_task
from app.run_workspace import show_run
from app.task_runner import TaskRunnerError, show_task

CAPSULE_EXECUTION_POLICY_VERSION = "v0"
FACTORYOS_BASELINE_TOKENS = 23302
CAPSULE_MINIMAL_TOKENS = 1198
CAPSULE_EXPECTED_SAVINGS_PERCENT = round(
    ((FACTORYOS_BASELINE_TOKENS - CAPSULE_MINIMAL_TOKENS) / FACTORYOS_BASELINE_TOKENS) * 100,
    2,
)

CAPSULE_EXECUTION_CATEGORIES = {
    "docs_only",
    "code_small",
    "code_medium",
    "factory_start",
    "live_canary",
    "security_review",
    "heavy_review_only",
}

CAPSULE_EXECUTION_DECISIONS = {
    "capsule",
    "repo_quiet",
    "repo_guarded",
    "full_repo_review",
    "blocked",
}


@dataclass(frozen=True, slots=True)
class CapsuleExecutionPolicyResult:
    ok: bool
    policy_version: str
    category: str
    decision: str
    execution_mode_recommendation: str
    capsule_policy_decision: str
    capsule_recommended: bool
    reason: str
    full_repo_required_reason: str
    expected_token_baseline: int
    expected_token_capsule: int
    expected_savings_percent: float
    requires_export_gate: bool
    allowed_to_execute_live: bool
    timeout_recovery_policy: str
    recommended_command_kind: str
    task_id: str | None
    run_id: str | None
    live_policy: str | None
    included_files_count: int
    included_files: list[str]
    routing_contract_source: str | None
    routing_contract_valid: bool | None
    context_status: str | None
    task_type: str | None
    model: str | None
    reasoning_effort: str | None
    sandbox_mode: str | None
    estimated_context_chars: int | None
    estimated_changed_files: int | None
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "policy_version": self.policy_version,
            "category": self.category,
            "decision": self.decision,
            "execution_mode_recommendation": self.execution_mode_recommendation,
            "capsule_policy_decision": self.capsule_policy_decision,
            "capsule_recommended": self.capsule_recommended,
            "reason": self.reason,
            "full_repo_required_reason": self.full_repo_required_reason,
            "expected_token_baseline": self.expected_token_baseline,
            "expected_token_capsule": self.expected_token_capsule,
            "expected_savings_percent": self.expected_savings_percent,
            "requires_export_gate": self.requires_export_gate,
            "allowed_to_execute_live": self.allowed_to_execute_live,
            "timeout_recovery_policy": self.timeout_recovery_policy,
            "recommended_command_kind": self.recommended_command_kind,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "live_policy": self.live_policy,
            "included_files_count": self.included_files_count,
            "included_files": self.included_files,
            "routing_contract_source": self.routing_contract_source,
            "routing_contract_valid": self.routing_contract_valid,
            "context_status": self.context_status,
            "task_type": self.task_type,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "sandbox_mode": self.sandbox_mode,
            "estimated_context_chars": self.estimated_context_chars,
            "estimated_changed_files": self.estimated_changed_files,
            "notes": self.notes,
        }


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _validate_category(category: str) -> str:
    normalized = str(category).strip()
    if normalized not in CAPSULE_EXECUTION_CATEGORIES:
        allowed = ", ".join(sorted(CAPSULE_EXECUTION_CATEGORIES))
        raise TaskRunnerError(f"categoria inválida para capsule execution policy: {normalized or '<vazia>'}. Permitidas: {allowed}.")
    return normalized


def _infer_category_from_plan(plan: dict[str, Any], context_pack: dict[str, Any] | None = None) -> str:
    if context_pack is not None:
        candidate = str(context_pack.get("category", "")).strip()
        if candidate:
            return candidate
    candidate = str(plan.get("task_type", "")).strip()
    if candidate == "security":
        return "security_review"
    if candidate == "docs":
        return "docs_only"
    if candidate == "code":
        if int(plan.get("estimated_changed_files", 0)) <= 5:
            return "code_small"
        return "code_medium"
    if candidate == "loop":
        return "factory_start"
    return "code_medium" if int(plan.get("estimated_changed_files", 0)) > 5 else "code_small"


def _default_live_policy_for_category(category: str) -> str:
    return {
        "docs_only": "blocked",
        "code_small": "blocked",
        "code_medium": "blocked",
        "factory_start": "review_required",
        "live_canary": "canary_only",
        "security_review": "review_required",
        "heavy_review_only": "review_required",
    }.get(category, "blocked")


def _decision_for_category(
    *,
    category: str,
    included_files: list[str],
    live_policy: str | None,
) -> tuple[str, str, str, bool, bool, str]:
    included_count = len(included_files)
    policy = (live_policy or _default_live_policy_for_category(category)).strip() or "blocked"

    if category in {"security_review", "heavy_review_only"}:
        reason = "Segurança e revisão pesada exigem revisão completa do repositório."
        return "full_repo_review", "full_repo_review", reason, False, False, "full_repo_review"

    if category == "live_canary":
        reason = "Canário live precisa de execução guardada no repositório e não deve cair em cápsula."
        return "repo_quiet", "repo_guarded", reason, False, False, "factory-start --plan-only --cost-aware"

    if category == "docs_only":
        reason = "Tarefa só de docs é o caso padrão para cápsula econômica."
        return "capsule", "capsule", reason, True, False, "codex-capsule-run"

    if category == "code_small":
        reason = "Mudança pequena de código continua sendo caso padrão para cápsula econômica."
        return "capsule", "capsule", reason, True, False, "codex-capsule-run"

    if category == "code_medium":
        if included_count <= 6:
            reason = "Mudança média com poucos arquivos incluídos ainda cabe na cápsula."
            return "capsule", "capsule", reason, True, False, "codex-capsule-run"
        reason = "Mudança média com conjunto maior de arquivos pede repo_quiet para manter contexto previsível."
        return "repo_quiet", "repo_quiet", reason, False, False, "factory-start --plan-only --cost-aware"

    if category == "factory_start":
        if policy in {"review_required", "gated"}:
            reason = f"live_policy={policy} pede execução guardada no repositório."
            return "repo_quiet", "repo_guarded", reason, False, False, "factory-start --plan-only --cost-aware"
        if included_count <= 6:
            reason = "Factory Start barato e com pouco contexto pode usar cápsula."
            return "capsule", "capsule", reason, True, False, "codex-capsule-run"
        reason = "Factory Start com mais contexto fica mais estável em repo_quiet."
        return "repo_quiet", "repo_quiet", reason, False, False, "factory-start --plan-only --cost-aware"

    reason = "Categoria não reconhecida caiu no fallback conservador de repo_quiet."
    return "repo_quiet", "repo_quiet", reason, False, False, "factory-start --plan-only --cost-aware"


def _policy_result(
    *,
    category: str,
    task: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
    included_files: list[str] | None = None,
    live_policy: str | None = None,
) -> CapsuleExecutionPolicyResult:
    normalized_category = _validate_category(category)
    normalized_plan = plan or {}
    normalized_context = context_pack or {}
    effective_included_files = [str(item) for item in (included_files if included_files is not None else normalized_context.get("included_files", [])) if str(item).strip()]
    effective_live_policy = live_policy or str(normalized_plan.get("routing_contract", {}).get("live_policy", "")).strip() or str(normalized_context.get("routing_contract", {}).get("live_policy", "")).strip() or None

    execution_mode_recommendation, capsule_policy_decision, reason, capsule_recommended, requires_export_gate, recommended_command_kind = _decision_for_category(
        category=normalized_category,
        included_files=effective_included_files,
        live_policy=effective_live_policy,
    )
    full_repo_required_reason = reason if capsule_policy_decision == "full_repo_review" else ""
    decision = capsule_policy_decision if capsule_policy_decision in {"capsule", "repo_quiet", "full_repo_review", "blocked"} else "repo_quiet"
    if capsule_policy_decision == "repo_guarded":
        decision = "repo_quiet"
    if capsule_policy_decision == "full_repo_review":
        requires_export_gate = False
    if capsule_policy_decision == "blocked":
        capsule_recommended = False
        requires_export_gate = False

    notes = [
        "Capsule é o caminho econômico padrão para docs_only e code_small.",
        "Execução live nunca é liberada diretamente por esta policy.",
        "Timeouts são tratados como recoverable_with_report quando houver artefatos válidos.",
    ]
    if normalized_category == "factory_start" and effective_live_policy:
        notes.append(f"live_policy efetiva: {effective_live_policy}.")
    if effective_included_files:
        notes.append(f"included_files={len(effective_included_files)}.")

    return CapsuleExecutionPolicyResult(
        ok=True,
        policy_version=CAPSULE_EXECUTION_POLICY_VERSION,
        category=normalized_category,
        decision=decision,
        execution_mode_recommendation=execution_mode_recommendation,
        capsule_policy_decision=capsule_policy_decision,
        capsule_recommended=capsule_recommended,
        reason=reason,
        full_repo_required_reason=full_repo_required_reason,
        expected_token_baseline=FACTORYOS_BASELINE_TOKENS,
        expected_token_capsule=CAPSULE_MINIMAL_TOKENS,
        expected_savings_percent=CAPSULE_EXPECTED_SAVINGS_PERCENT,
        requires_export_gate=requires_export_gate,
        allowed_to_execute_live=False,
        timeout_recovery_policy="recoverable_with_report",
        recommended_command_kind=recommended_command_kind,
        task_id=None if task is None else str(task.get("id", "")).strip() or None,
        run_id=None if run is None else str(run.get("id", "")).strip() or None,
        live_policy=effective_live_policy,
        included_files_count=len(effective_included_files),
        included_files=effective_included_files,
        routing_contract_source=str(normalized_plan.get("routing_contract_source", "")).strip() or None,
        routing_contract_valid=bool(normalized_plan.get("routing_contract_valid")) if normalized_plan else None,
        context_status=str(normalized_context.get("context_status", "")).strip() or None,
        task_type=str(normalized_plan.get("task_type", "")).strip() or None,
        model=str(normalized_plan.get("model", "")).strip() or None,
        reasoning_effort=str(normalized_plan.get("reasoning_effort", "")).strip() or None,
        sandbox_mode=str(normalized_plan.get("sandbox_mode", "")).strip() or None,
        estimated_context_chars=(
            int(normalized_plan.get("estimated_context_chars"))
            if normalized_plan.get("estimated_context_chars") is not None
            else None
        ),
        estimated_changed_files=(
            int(normalized_plan.get("estimated_changed_files"))
            if normalized_plan.get("estimated_changed_files") is not None
            else None
        ),
        notes=notes,
    )


def evaluate_capsule_execution_policy(
    *,
    category: str,
    task: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    context_pack: dict[str, Any] | None = None,
    included_files: list[str] | None = None,
    live_policy: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    normalized_category = _validate_category(category)
    normalized_task = task
    normalized_run = run
    normalized_plan = plan
    normalized_context = context_pack

    if normalized_task is not None and normalized_plan is None:
        normalized_plan = codex_plan_for_task(str(normalized_task.get("id", "")), repo=repo)
    if normalized_run is not None and normalized_plan is None:
        normalized_plan = codex_plan_for_run(str(normalized_run.get("id", "")), repo=repo)
    if normalized_run is not None and normalized_context is None:
        normalized_context = context_pack_for_run(str(normalized_run.get("id", "")), repo=repo)
    if normalized_task is not None and normalized_context is None and normalized_run is None:
        normalized_context = context_pack_for_task(str(normalized_task.get("id", "")), repo=repo)

    policy = _policy_result(
        category=normalized_category,
        task=normalized_task,
        run=normalized_run,
        plan=normalized_plan,
        context_pack=normalized_context,
        included_files=included_files,
        live_policy=live_policy,
    )
    return policy.as_dict()


def policy_for_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = show_task(task_id, repo=repo)["task"]
    plan = codex_plan_for_task(task_id, repo=repo)
    context_pack = context_pack_for_task(task_id, repo=repo)
    category = _infer_category_from_plan(plan, context_pack)
    return evaluate_capsule_execution_policy(
        category=category,
        task=task,
        plan=plan,
        context_pack=context_pack,
        repo=repo,
    )


def policy_for_run(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    run = show_run(run_id, repo=repo)["run"]
    task = show_task(str(run["task_id"]), repo=repo)["task"]
    plan = codex_plan_for_run(run_id, repo=repo)
    context_pack = context_pack_for_run(run_id, repo=repo)
    category = _infer_category_from_plan(plan, context_pack)
    return evaluate_capsule_execution_policy(
        category=category,
        task=task,
        run=run,
        plan=plan,
        context_pack=context_pack,
        repo=repo,
    )


def policy_for_category(
    category: str,
    *,
    included_files: list[str] | None = None,
    live_policy: str | None = None,
) -> dict[str, Any]:
    return evaluate_capsule_execution_policy(
        category=category,
        included_files=included_files,
        live_policy=live_policy,
    )
