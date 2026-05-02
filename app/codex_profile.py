from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.routing_contracts import resolve_routing_contract
from app.run_workspace import show_run
from app.task_runner import TaskRunnerError, show_task


@dataclass(frozen=True, slots=True)
class CodexProfile:
    name: str
    use: str
    model: str | None
    reasoning_effort: str | None
    sandbox_mode: str | None
    max_context_chars: int
    max_changed_files: int
    must_use_codex: bool
    can_use_local: bool
    never_default: bool = False


CODEX_PROFILES: dict[str, CodexProfile] = {
    "local_no_codex": CodexProfile(
        name="local_no_codex",
        use="Tarefa trivial, relatório, JSON ou validação local.",
        model=None,
        reasoning_effort=None,
        sandbox_mode=None,
        max_context_chars=0,
        max_changed_files=0,
        must_use_codex=False,
        can_use_local=True,
    ),
    "codex_mini_low": CodexProfile(
        name="codex_mini_low",
        use="Texto simples, pequenos ajustes, reports e docs pequenas.",
        model="gpt-5.4-mini",
        reasoning_effort="low",
        sandbox_mode="workspace-write",
        max_context_chars=12000,
        max_changed_files=5,
        must_use_codex=True,
        can_use_local=False,
    ),
    "codex_mini_medium": CodexProfile(
        name="codex_mini_medium",
        use="Implementação pequena ou média em poucos arquivos.",
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        sandbox_mode="workspace-write",
        max_context_chars=25000,
        max_changed_files=15,
        must_use_codex=True,
        can_use_local=False,
    ),
    "codex_standard_medium": CodexProfile(
        name="codex_standard_medium",
        use="Arquitetura, loop, safety gate, execução live ou canary.",
        model="gpt-5.4",
        reasoning_effort="medium",
        sandbox_mode="workspace-write",
        max_context_chars=45000,
        max_changed_files=30,
        must_use_codex=True,
        can_use_local=False,
    ),
    "codex_heavy_review_only": CodexProfile(
        name="codex_heavy_review_only",
        use="Revisão crítica, segurança, falha repetida ou fechamento de marco.",
        model="gpt-5.4",
        reasoning_effort="high",
        sandbox_mode="workspace-write",
        max_context_chars=70000,
        max_changed_files=50,
        must_use_codex=True,
        can_use_local=False,
        never_default=True,
    ),
}

DOC_KEYWORDS = ("doc", "docs", "prd", "spec", "report", "relatorio", "json", "proof")
CODE_KEYWORDS = ("implementar", "app/", "cli", "painel", "template", "backend")
LOOP_KEYWORDS = ("loop", "factory-start", "factory start", "handoff", "run-execute", "canary")
SECURITY_KEYWORDS = ("security", "seguranca", "auth", "secret", "secrets", "deploy")
FACTORY_CATEGORY_TO_TASK_TYPE = {
    "docs_only": "docs",
    "code_small": "code",
    "code_medium": "code",
    "safety_gate": "security",
    "live_canary": "loop",
    "evaluator": "code",
    "factory_loop": "loop",
    "factory_start": "loop",
    "security_review": "security",
    "heavy_review_only": "security",
    "retention": "code",
    "worktree_lifecycle": "code",
    "cost_control": "code",
    "long_run_planner": "loop",
}


def list_codex_profiles() -> dict[str, Any]:
    return {
        "ok": True,
        "profiles": [asdict(profile) for profile in CODEX_PROFILES.values()],
        "global_config_changed": False,
        "policy_scope": "repo-local",
    }


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _safe_file_chars(repo: Path, relative_path: str, *, limit: int = 20000) -> int:
    candidate = Path(relative_path)
    if candidate.is_absolute() or any(part in {"..", "."} for part in candidate.parts):
        return 0
    path = repo / candidate
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    return min(size, limit)


def _infer_task_type(text: str) -> str:
    normalized = text.lower()
    if any(keyword in normalized for keyword in SECURITY_KEYWORDS):
        return "security"
    if any(keyword in normalized for keyword in LOOP_KEYWORDS):
        return "loop"
    if any(keyword in normalized for keyword in CODE_KEYWORDS):
        return "code"
    if any(keyword in normalized for keyword in DOC_KEYWORDS):
        return "docs"
    return "trivial"


def _choose_profile(
    *,
    risk: str,
    executor: str,
    live: bool,
    max_steps: int,
    estimated_changed_files: int,
    task_type: str,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if executor == "local" or (task_type in {"trivial", "docs"} and risk == "low" and estimated_changed_files <= 2):
        reasons.append("Tarefa simples pode ser resolvida por ferramentas locais sem Codex.")
        return "local_no_codex", reasons

    if live:
        reasons.append("Execução live/canary exige perfil standard ou revisão pesada.")
        if risk == "high" and task_type == "security":
            return "codex_heavy_review_only", reasons
        return "codex_standard_medium", reasons

    if risk == "high" and task_type == "security":
        reasons.append("Risco alto com segurança recomenda perfil de revisão, nunca como padrão automático.")
        return "codex_heavy_review_only", reasons

    if risk == "high" or task_type == "loop" or max_steps > 1:
        reasons.append("Risco alto, loop ou múltiplos steps exigem perfil standard.")
        return "codex_standard_medium", reasons

    if estimated_changed_files > 5 or task_type == "code":
        reasons.append("Mudança de código pequena/média usa mini medium.")
        return "codex_mini_medium", reasons

    reasons.append("Docs ou ajuste pequeno usam mini low.")
    return "codex_mini_low", reasons


def validate_codex_budget(plan: dict[str, Any]) -> dict[str, Any]:
    profile_name = str(plan["recommended_profile"])
    profile = CODEX_PROFILES[profile_name]
    reasons = [str(item) for item in plan.get("reasons", [])]
    status = "ok"

    if profile.name != "local_no_codex" and int(plan["estimated_context_chars"]) > profile.max_context_chars:
        status = "blocked"
        reasons.append(
            f"estimated_context_chars excede max_context_chars do perfil ({profile.max_context_chars})."
        )

    estimated_changed_files = int(plan.get("estimated_changed_files", 0))
    if profile.max_changed_files and estimated_changed_files > profile.max_changed_files:
        status = "blocked"
        reasons.append(
            f"estimated_changed_files excede max_changed_files do perfil ({profile.max_changed_files})."
        )

    if bool(plan.get("live")) and profile.name not in {"codex_standard_medium", "codex_heavy_review_only"}:
        status = "blocked"
        reasons.append("live só pode usar codex_standard_medium ou codex_heavy_review_only.")

    updated = dict(plan)
    updated["budget_status"] = status
    updated["reasons"] = reasons
    return updated


def build_codex_plan(
    *,
    task: dict[str, Any],
    run: dict[str, Any] | None = None,
    live: bool = False,
    max_steps: int = 1,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    routing_resolution = resolve_routing_contract(task=task, run=run)
    routing_contract = routing_resolution.routing_contract
    if not routing_resolution.valid:
        return {
            "ok": False,
            "task_id": task.get("id"),
            "run_id": None if run is None else run.get("id"),
            "routing_status": "invalid",
            "routing_contract": routing_contract,
            "routing_contract_source": routing_resolution.source,
            "routing_contract_valid": False,
            "recommended_profile": None,
            "codex_profile": None,
            "model": None,
            "reasoning_effort": None,
            "sandbox_mode": None,
            "approval_policy": "never" if live else "on-request",
            "estimated_context_chars": 0,
            "max_context_chars": 0,
            "estimated_changed_files": 0,
            "max_changed_files": 0,
            "budget_status": "blocked",
            "reasons": list(routing_resolution.reasons),
            "warnings": list(routing_resolution.warnings),
            "must_use_codex": False,
            "can_use_local": False,
            "live": live,
            "max_steps": max_steps,
            "global_config_changed": False,
        }

    text = " ".join(
        [
            str(task.get("title", "")),
            str(task.get("description", "")),
        ]
    )
    explicit_factory_category = routing_contract.get("factory_category")
    task_type = FACTORY_CATEGORY_TO_TASK_TYPE.get(
        str(explicit_factory_category),
        _infer_task_type(text),
    )
    risk = str(task.get("risk", "medium"))
    executor = str(task.get("executor", "manual"))
    default_changed_files = {
        "trivial": 1,
        "docs": 2,
        "code": 8,
        "loop": 18,
        "security": 25,
    }.get(task_type, 8)
    budget = run.get("budget", {}) if isinstance(run, dict) else {}
    budget_changed_files = int(budget.get("max_changed_files", default_changed_files))
    estimated_changed_files = min(default_changed_files, budget_changed_files)

    reasons: list[str] = []
    warnings = list(routing_resolution.warnings)
    explicit_profile_hint = routing_contract.get("codex_profile_hint")
    if explicit_profile_hint is not None:
        profile_name = str(explicit_profile_hint)
        reasons.append("codex_profile_hint explícito prevaleceu sobre a heurística.")
    else:
        profile_name, heuristic_reasons = _choose_profile(
            risk=risk,
            executor=executor,
            live=live,
            max_steps=max_steps,
            estimated_changed_files=estimated_changed_files,
            task_type=task_type,
        )
        reasons.extend(heuristic_reasons)

    if explicit_factory_category is not None:
        reasons.append(f"factory_category explícito aplicado: {explicit_factory_category}.")

    profile = CODEX_PROFILES[profile_name]

    context_chars = len(text)
    for relative_path in ("AGENTS.md", "WORKFLOW.md"):
        context_chars += _safe_file_chars(repo, relative_path, limit=12000)
    if run is not None:
        context_chars += len(json.dumps(run, ensure_ascii=False, indent=2))
    if routing_resolution.has_explicit_contract:
        context_chars += len(json.dumps(routing_contract, ensure_ascii=False, indent=2))

    max_context_chars = profile.max_context_chars
    max_context_override = routing_contract.get("max_context_chars_override")
    if max_context_override is not None:
        max_context_chars = int(max_context_override)
        reasons.append("max_context_chars_override explícito aplicado ao budget.")

    max_changed_files = profile.max_changed_files
    changed_files_override = routing_contract.get("max_changed_files_override")
    if changed_files_override is not None:
        max_changed_files = int(changed_files_override)
        reasons.append("max_changed_files_override explícito aplicado ao budget.")

    effective_max_steps = max_steps
    steps_override = routing_contract.get("max_steps_override")
    if steps_override is not None:
        effective_max_steps = min(int(steps_override), max_steps)
        reasons.append("max_steps_override explícito considerado no plano.")

    plan = {
        "ok": True,
        "task_id": task.get("id"),
        "run_id": None if run is None else run.get("id"),
        "task_type": task_type,
        "routing_status": "explicit" if routing_resolution.has_explicit_contract else "heuristic",
        "routing_contract": routing_contract,
        "routing_contract_source": routing_resolution.source,
        "routing_contract_valid": True,
        "recommended_profile": profile.name,
        "codex_profile": profile.name,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "sandbox_mode": profile.sandbox_mode,
        "approval_policy": "never" if live else "on-request",
        "estimated_context_chars": context_chars,
        "max_context_chars": max_context_chars,
        "estimated_changed_files": estimated_changed_files,
        "max_changed_files": max_changed_files,
        "budget_status": "ok",
        "reasons": reasons,
        "warnings": warnings,
        "must_use_codex": profile.must_use_codex,
        "can_use_local": profile.can_use_local,
        "live": live,
        "max_steps": effective_max_steps,
        "global_config_changed": False,
    }
    live_policy = routing_contract.get("live_policy")
    if live and live_policy == "blocked":
        plan["budget_status"] = "blocked"
        plan["reasons"] = [*reasons, "live_policy=blocked impede execução live."]
    return validate_codex_budget(plan)


def codex_plan_for_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = show_task(task_id, repo=repo)["task"]
    return build_codex_plan(task=task, repo=repo)


def codex_plan_for_run(
    run_id: str,
    *,
    live: bool = False,
    max_steps: int = 1,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    run = show_run(run_id, repo=repo)["run"]
    task = show_task(str(run["task_id"]), repo=repo)["task"]
    return build_codex_plan(task=task, run=run, live=live, max_steps=max_steps, repo=repo)
