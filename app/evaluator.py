"""Simple local evaluator for FactoryOS validation results.

This module is intentionally small and dependency-free.

It does not execute Codex.
It does not mutate project files.
It only classifies validation signals into a standard decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


COMMON_CHECKS = (
    "python_ok",
    "json_ok",
    "browser_ok",
)


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result returned by the evaluator."""

    decision: str
    risk: str
    reason: str
    next_action: str
    failed_checks: list[str]
    inputs: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return {
            "decision": self.decision,
            "risk": self.risk,
            "reason": self.reason,
            "next_action": self.next_action,
            "failed_checks": self.failed_checks,
            "inputs": self.inputs,
        }


def _as_bool(value: Any, *, default: bool) -> bool:
    """Convert common CLI/string values to bool.

    Unknown values fall back to the provided default.
    """
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "sim", "s", "ok", "pass", "passed"}:
            return True
        if normalized in {"0", "false", "no", "n", "nao", "não", "fail", "failed"}:
            return False

    return default


def evaluate_signals(signals: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate simple FactoryOS validation signals.

    Decision order:
    1. Stop if security failed.
    2. Ask ChatGPT review if high risk.
    3. Retry if common validations failed.
    4. Retry if Git is dirty unexpectedly.
    5. Pass if everything is acceptable.
    """
    raw = dict(signals or {})

    normalized = {
        "python_ok": _as_bool(raw.get("python_ok"), default=True),
        "json_ok": _as_bool(raw.get("json_ok"), default=True),
        "browser_ok": _as_bool(raw.get("browser_ok"), default=True),
        "security_ok": _as_bool(raw.get("security_ok"), default=True),
        "high_risk": _as_bool(raw.get("high_risk"), default=False),
        "git_clean": _as_bool(raw.get("git_clean"), default=True),
        "git_expected_dirty": _as_bool(raw.get("git_expected_dirty"), default=False),
        "notes": raw.get("notes", ""),
    }

    if not normalized["security_ok"]:
        return EvaluationResult(
            decision="stopped_security",
            risk="high",
            reason="Security validation failed.",
            next_action="Stop implementation and review the security issue before continuing.",
            failed_checks=["security_ok"],
            inputs=normalized,
        ).to_dict()

    if normalized["high_risk"]:
        return EvaluationResult(
            decision="needs_chatgpt_review",
            risk="high",
            reason="The task or result was marked as high risk.",
            next_action="Ask ChatGPT to review architecture, security, and next steps before execution.",
            failed_checks=["high_risk"],
            inputs=normalized,
        ).to_dict()

    failed_checks = [check for check in COMMON_CHECKS if not normalized[check]]

    if not normalized["git_clean"] and not normalized["git_expected_dirty"]:
        failed_checks.append("git_clean")

    if failed_checks:
        return EvaluationResult(
            decision="failed_retryable",
            risk="medium",
            reason="One or more retryable validations failed.",
            next_action="Fix the failed checks locally, rerun validations, then evaluate again.",
            failed_checks=failed_checks,
            inputs=normalized,
        ).to_dict()

    return EvaluationResult(
        decision="passed",
        risk="low",
        reason="All required validations passed.",
        next_action="Proceed to commit, document, or move to the next planned step.",
        failed_checks=[],
        inputs=normalized,
    ).to_dict()
