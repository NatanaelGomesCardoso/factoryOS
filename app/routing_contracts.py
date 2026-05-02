from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ROUTING_CONTRACT_VERSION_VALUES = {"v0"}
FACTORY_CATEGORY_VALUES = {
    "docs_only",
    "code_small",
    "code_medium",
    "safety_gate",
    "live_canary",
    "evaluator",
    "factory_loop",
    "factory_start",
    "security_review",
    "heavy_review_only",
    "retention",
    "worktree_lifecycle",
    "cost_control",
    "long_run_planner",
}
CODEX_PROFILE_HINT_VALUES = {
    "local_no_codex",
    "codex_mini_low",
    "codex_mini_medium",
    "codex_standard_medium",
    "codex_heavy_review_only",
}
CONTEXT_POLICY_VALUES = {"minimal", "compact", "standard", "expanded"}
LIVE_POLICY_VALUES = {"blocked", "canary_only", "gated", "review_required"}
ROUTING_CONTRACT_FIELD_NAMES = (
    "routing_contract_version",
    "factory_category",
    "codex_profile_hint",
    "context_policy",
    "live_policy",
    "max_context_chars_override",
    "max_changed_files_override",
    "max_steps_override",
    "target_minutes_override",
    "retention_policy",
    "worktree_policy",
)


@dataclass(frozen=True, slots=True)
class RoutingContractResolution:
    ok: bool
    valid: bool
    source: str
    has_explicit_contract: bool
    routing_contract: dict[str, Any]
    reasons: list[str]
    warnings: list[str]


def _normalize_optional_choice(
    value: Any,
    *,
    field_name: str,
    allowed: set[str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} precisa ser texto.")
    normalized = value.strip()
    if not normalized:
        return None
    if normalized not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} inválido: {normalized}. Permitidos: {allowed_values}.")
    return normalized


def _normalize_optional_positive_int(value: Any, *, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} precisa ser inteiro positivo.") from exc
    if normalized <= 0:
        raise ValueError(f"{field_name} precisa ser inteiro positivo.")
    return normalized


def _normalize_optional_text(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} precisa ser texto.")
    normalized = value.strip()
    if not normalized:
        return None
    if any(char in normalized for char in ("\n", "\r", "\t")):
        raise ValueError(f"{field_name} não pode conter quebras de linha.")
    return normalized


def extract_routing_contract(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: payload.get(field) for field in ROUTING_CONTRACT_FIELD_NAMES}


def normalize_routing_contract(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "routing_contract_version": _normalize_optional_choice(
            payload.get("routing_contract_version"),
            field_name="routing_contract_version",
            allowed=ROUTING_CONTRACT_VERSION_VALUES,
        ),
        "factory_category": _normalize_optional_choice(
            payload.get("factory_category"),
            field_name="factory_category",
            allowed=FACTORY_CATEGORY_VALUES,
        ),
        "codex_profile_hint": _normalize_optional_choice(
            payload.get("codex_profile_hint"),
            field_name="codex_profile_hint",
            allowed=CODEX_PROFILE_HINT_VALUES,
        ),
        "context_policy": _normalize_optional_choice(
            payload.get("context_policy"),
            field_name="context_policy",
            allowed=CONTEXT_POLICY_VALUES,
        ),
        "live_policy": _normalize_optional_choice(
            payload.get("live_policy"),
            field_name="live_policy",
            allowed=LIVE_POLICY_VALUES,
        ),
        "max_context_chars_override": _normalize_optional_positive_int(
            payload.get("max_context_chars_override"),
            field_name="max_context_chars_override",
        ),
        "max_changed_files_override": _normalize_optional_positive_int(
            payload.get("max_changed_files_override"),
            field_name="max_changed_files_override",
        ),
        "max_steps_override": _normalize_optional_positive_int(
            payload.get("max_steps_override"),
            field_name="max_steps_override",
        ),
        "target_minutes_override": _normalize_optional_positive_int(
            payload.get("target_minutes_override"),
            field_name="target_minutes_override",
        ),
        "retention_policy": _normalize_optional_text(
            payload.get("retention_policy"),
            field_name="retention_policy",
        ),
        "worktree_policy": _normalize_optional_text(
            payload.get("worktree_policy"),
            field_name="worktree_policy",
        ),
    }

    explicit_fields = {
        key: value for key, value in normalized.items()
        if key != "routing_contract_version" and value is not None
    }
    if explicit_fields and normalized["routing_contract_version"] is None:
        raise ValueError("routing_contract_version=v0 é obrigatório quando houver metadata explícita.")

    return normalized


def has_explicit_routing_contract(payload: dict[str, Any]) -> bool:
    contract = extract_routing_contract(payload)
    return any(value not in (None, "") for value in contract.values())


def _empty_contract() -> dict[str, Any]:
    return {field: None for field in ROUTING_CONTRACT_FIELD_NAMES}


def _resolve_single_contract(payload: dict[str, Any]) -> tuple[dict[str, Any], bool, list[str]]:
    empty = _empty_contract()
    if not has_explicit_routing_contract(payload):
        return empty, True, []
    try:
        normalized = normalize_routing_contract(payload)
    except ValueError as exc:
        return empty, False, [str(exc)]
    return normalized, True, []


def merge_routing_contracts(
    task_contract: dict[str, Any],
    run_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(task_contract)
    for key, value in (run_contract or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def resolve_routing_contract(
    *,
    task: dict[str, Any],
    run: dict[str, Any] | None = None,
) -> RoutingContractResolution:
    task_contract, task_valid, task_reasons = _resolve_single_contract(task)
    if not task_valid:
        return RoutingContractResolution(
            ok=True,
            valid=False,
            source="task",
            has_explicit_contract=True,
            routing_contract=task_contract,
            reasons=task_reasons,
            warnings=[],
        )

    run_contract = _empty_contract()
    if run is not None:
        run_contract, run_valid, run_reasons = _resolve_single_contract(run)
        if not run_valid:
            return RoutingContractResolution(
                ok=True,
                valid=False,
                source="run",
                has_explicit_contract=True,
                routing_contract=run_contract,
                reasons=run_reasons,
                warnings=[],
            )

    task_has_explicit = has_explicit_routing_contract(task)
    run_has_explicit = run is not None and has_explicit_routing_contract(run)
    if run_has_explicit:
        source = "run"
    elif task_has_explicit:
        source = "task"
    else:
        source = "heuristic"

    merged = merge_routing_contracts(task_contract, run_contract)
    warnings: list[str] = []
    if source == "heuristic":
        warnings.append("Nenhum routing contract explícito encontrado; usando fallback heurístico.")
    elif merged["routing_contract_version"] is None:
        warnings.append("Routing contract explícito parcial sem versão normalizada.")

    return RoutingContractResolution(
        ok=True,
        valid=True,
        source=source,
        has_explicit_contract=bool(task_has_explicit or run_has_explicit),
        routing_contract=merged,
        reasons=[],
        warnings=warnings,
    )


def routing_contract_validation_payload(
    *,
    task: dict[str, Any],
    run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = resolve_routing_contract(task=task, run=run)
    contract = resolved.routing_contract
    return {
        "ok": resolved.ok,
        "valid": resolved.valid,
        "source": resolved.source,
        "factory_category": contract.get("factory_category"),
        "codex_profile_hint": contract.get("codex_profile_hint"),
        "context_policy": contract.get("context_policy"),
        "live_policy": contract.get("live_policy"),
        "routing_contract_version": contract.get("routing_contract_version"),
        "routing_contract": contract,
        "reasons": resolved.reasons,
        "warnings": resolved.warnings,
    }
