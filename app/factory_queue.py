from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.capsule_execution_policy import FACTORYOS_BASELINE_TOKENS, CAPSULE_MINIMAL_TOKENS, policy_for_category
from app.project_intake import load_latest_project_intake_report
from app.report_index import latest_report
from app.task_runner import TaskRunnerError, list_tasks

FACTORY_QUEUE_VERSION = "v0"
FACTORY_QUEUE_REPORTS_DIR = "factory-queue-starts"
DEFAULT_MAX_TASKS = 3
MAX_TASKS_CAP = 5
DEFAULT_MAX_STEPS_PER_TASK = 1


@dataclass(frozen=True, slots=True)
class QueueCandidate:
    candidate_id: str
    title: str
    category: str
    source: str
    task_status: str
    decision: str
    execution_mode_recommendation: str
    reason: str
    capsule_recommended: bool
    full_repo_required: bool
    blocked: bool
    selected: bool
    estimated_tokens_saved: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink nao permitido: {path}")

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


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "candidate"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_max_tasks(value: int) -> int:
    if value < 1:
        raise TaskRunnerError("max_tasks precisa ser pelo menos 1.")
    if value > MAX_TASKS_CAP:
        raise TaskRunnerError(f"max_tasks precisa ser no maximo {MAX_TASKS_CAP}.")
    return value


def _normalize_max_steps_per_task(value: int) -> int:
    if value < 1:
        raise TaskRunnerError("max_steps_per_task precisa ser pelo menos 1.")
    return value


def _task_text(task: dict[str, Any]) -> str:
    return " ".join(
        str(task.get(field, "")).strip()
        for field in ("title", "description", "factory_category", "executor", "risk")
    ).lower()


def _infer_category_from_task(task: dict[str, Any]) -> str:
    explicit_category = str(task.get("factory_category", "")).strip()
    if explicit_category:
        return explicit_category

    text = _task_text(task)
    if any(keyword in text for keyword in ("security", "auth", "token", "secret", "payment", "deploy")):
        return "security_review"
    if any(keyword in text for keyword in ("live canary", "canary", "gated")):
        return "live_canary"
    if any(keyword in text for keyword in ("review", "heavy")):
        return "heavy_review_only"
    if any(keyword in text for keyword in ("docs", "document", "prd", "spec", "sprint", "report")):
        return "docs_only"
    return "code_small"


def _route_for_category(category: str) -> dict[str, Any]:
    normalized = category.strip()
    if normalized == "live_canary":
        return {
            "ok": True,
            "category": normalized,
            "decision": "gated_only",
            "execution_mode_recommendation": "gated_only",
            "capsule_recommended": False,
            "full_repo_required_reason": "",
            "reason": "Live canary fica apenas em gate nesta sprint.",
            "allowed_to_execute_live": False,
            "expected_token_baseline": FACTORYOS_BASELINE_TOKENS,
            "expected_token_capsule": CAPSULE_MINIMAL_TOKENS,
            "expected_savings_percent": round(((FACTORYOS_BASELINE_TOKENS - CAPSULE_MINIMAL_TOKENS) / FACTORYOS_BASELINE_TOKENS) * 100, 2),
        }

    if normalized in {"docs_only", "code_small", "code_medium", "factory_start"}:
        policy = policy_for_category(normalized if normalized in {"docs_only", "code_small"} else "code_small")
        return {
            "ok": True,
            "category": normalized,
            "decision": str(policy.get("decision", "")).strip() or "capsule",
            "execution_mode_recommendation": str(policy.get("execution_mode_recommendation", "")).strip() or "capsule",
            "capsule_recommended": bool(policy.get("capsule_recommended", False)),
            "full_repo_required_reason": str(policy.get("full_repo_required_reason", "")).strip(),
            "reason": str(policy.get("reason", "")).strip(),
            "allowed_to_execute_live": False,
            "expected_token_baseline": int(policy.get("expected_token_baseline", FACTORYOS_BASELINE_TOKENS)),
            "expected_token_capsule": int(policy.get("expected_token_capsule", CAPSULE_MINIMAL_TOKENS)),
            "expected_savings_percent": float(policy.get("expected_savings_percent", 0.0)),
        }

    if normalized in {"security_review", "heavy_review_only"}:
        policy = policy_for_category("security_review")
        return {
            "ok": True,
            "category": normalized,
            "decision": str(policy.get("decision", "")).strip() or "full_repo_review",
            "execution_mode_recommendation": str(policy.get("execution_mode_recommendation", "")).strip() or "full_repo_review",
            "capsule_recommended": False,
            "full_repo_required_reason": str(policy.get("full_repo_required_reason", "")).strip(),
            "reason": str(policy.get("reason", "")).strip(),
            "allowed_to_execute_live": False,
            "expected_token_baseline": int(policy.get("expected_token_baseline", FACTORYOS_BASELINE_TOKENS)),
            "expected_token_capsule": int(policy.get("expected_token_capsule", CAPSULE_MINIMAL_TOKENS)),
            "expected_savings_percent": float(policy.get("expected_savings_percent", 0.0)),
        }

    return {
        "ok": True,
        "category": normalized or "code_small",
        "decision": "blocked",
        "execution_mode_recommendation": "blocked",
        "capsule_recommended": False,
        "full_repo_required_reason": "categoria nao suportada na queue v0.",
        "reason": "Categoria nao suportada na queue v0.",
        "allowed_to_execute_live": False,
        "expected_token_baseline": FACTORYOS_BASELINE_TOKENS,
        "expected_token_capsule": CAPSULE_MINIMAL_TOKENS,
        "expected_savings_percent": 0.0,
    }


def _queue_report_path(repo: Path) -> Path:
    return repo / "reports" / FACTORY_QUEUE_REPORTS_DIR / f"{_timestamp()}.json"


def _collect_pending_tasks(repo: Path) -> list[dict[str, Any]]:
    task_groups = list_tasks(repo=repo)["groups"]
    pending_group = next((group for group in task_groups if group["status"] == "pending"), None)
    if not pending_group:
        return []
    return [task for task in pending_group["tasks"] if isinstance(task, dict)]


def _intake_candidates(repo: Path) -> list[dict[str, Any]]:
    intake = load_latest_project_intake_report(repo=repo)
    if not intake:
        return []
    candidates: list[dict[str, Any]] = []
    for candidate in intake.get("task_candidates", []):
        if not isinstance(candidate, dict):
            continue
        normalized = dict(candidate)
        normalized["source"] = "project_intake"
        candidates.append(normalized)
    return candidates


def _task_candidate(task: dict[str, Any]) -> dict[str, Any]:
    category = _infer_category_from_task(task)
    route = _route_for_category(category)
    return {
        "candidate_id": str(task.get("id", "")).strip() or _slugify(str(task.get("title", "task"))),
        "title": str(task.get("title", "")).strip(),
        "category": category,
        "source": "task_queue",
        "task_status": str(task.get("status", "")).strip() or "pending",
        "decision": route["decision"],
        "execution_mode_recommendation": route["execution_mode_recommendation"],
        "reason": route["reason"],
        "capsule_recommended": bool(route["capsule_recommended"]),
        "full_repo_required": route["execution_mode_recommendation"] == "full_repo_review",
        "blocked": route["execution_mode_recommendation"] in {"blocked", "gated_only"},
        "selected": False,
        "estimated_tokens_saved": route["expected_token_baseline"] - route["expected_token_capsule"] if route["capsule_recommended"] else 0,
    }


def _intake_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    category = str(candidate.get("category", "")).strip() or "code_small"
    route = _route_for_category(category)
    candidate_id = str(candidate.get("candidate_id", "")).strip() or _slugify(str(candidate.get("title", "candidate")))
    return {
        "candidate_id": candidate_id,
        "title": str(candidate.get("title", "")).strip(),
        "category": category,
        "source": str(candidate.get("source", "")).strip() or "project_intake",
        "task_status": str(candidate.get("task_status", "")).strip() or "planned",
        "decision": route["decision"],
        "execution_mode_recommendation": route["execution_mode_recommendation"],
        "reason": str(candidate.get("reason", "")).strip() or route["reason"],
        "capsule_recommended": bool(candidate.get("capsule_recommended", route["capsule_recommended"])),
        "full_repo_required": bool(candidate.get("full_repo_required", route["execution_mode_recommendation"] == "full_repo_review")),
        "blocked": bool(candidate.get("blocked", route["execution_mode_recommendation"] in {"blocked", "gated_only"})),
        "selected": False,
        "estimated_tokens_saved": _safe_int(candidate.get("estimated_tokens_saved"), 0),
    }


def _unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ordered: list[dict[str, Any]] = []
    for candidate in candidates:
        key = str(candidate.get("candidate_id", "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(candidate)
    return ordered


def _select_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_tasks: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def sort_key(candidate: dict[str, Any]) -> tuple[int, str]:
        category = str(candidate.get("category", "")).strip()
        priority = {
            "docs_only": 0,
            "code_small": 1,
            "code_medium": 2,
            "factory_start": 3,
            "security_review": 4,
            "heavy_review_only": 5,
            "live_canary": 6,
        }.get(category, 9)
        return priority, str(candidate.get("candidate_id", "")).strip()

    for candidate in sorted(candidates, key=sort_key):
        decision = str(candidate.get("decision", "")).strip()
        task_status = str(candidate.get("task_status", "")).strip()
        is_live_or_gated = decision == "gated_only"
        is_blocked = decision == "blocked"
        is_terminal_task = task_status in {"running", "failed", "done"}

        if is_terminal_task:
            candidate["skip_reason"] = f"task_status={task_status}"
            skipped.append(candidate)
            continue

        if is_blocked:
            candidate["skip_reason"] = "blocked_by_routing"
            skipped.append(candidate)
            continue

        if is_live_or_gated:
            candidate["skip_reason"] = "gated_only"
            skipped.append(candidate)
            continue

        if len(selected) >= max_tasks:
            candidate["skip_reason"] = "max_tasks_reached"
            skipped.append(candidate)
            continue

        candidate["selected"] = True
        selected.append(candidate)

    return selected, skipped


def run_factory_queue_start(
    *,
    dry_run: bool,
    plan_only: bool,
    max_tasks: int = DEFAULT_MAX_TASKS,
    max_steps_per_task: int = DEFAULT_MAX_STEPS_PER_TASK,
    cost_aware: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    if dry_run == plan_only:
        raise TaskRunnerError("factory-queue-start exige exatamente um de --dry-run ou --plan-only.")
    if not cost_aware:
        raise TaskRunnerError("factory-queue-start exige --cost-aware nesta sprint.")

    validated_max_tasks = _normalize_max_tasks(max_tasks)
    validated_max_steps_per_task = _normalize_max_steps_per_task(max_steps_per_task)

    latest_intake = latest_report("project-intakes", repo=repo)
    pending_tasks = _collect_pending_tasks(repo)
    intake_candidates = _intake_candidates(repo)
    candidates = [_task_candidate(task) for task in pending_tasks]
    candidates.extend(_intake_candidate(candidate) for candidate in intake_candidates)
    candidates = _unique_candidates(candidates)

    selected_tasks, skipped_tasks = _select_candidates(candidates, max_tasks=validated_max_tasks)
    selected_count = len(selected_tasks)
    capsule_recommended_count = sum(1 for item in selected_tasks if bool(item.get("capsule_recommended")))
    full_repo_required_count = sum(1 for item in selected_tasks if bool(item.get("full_repo_required")))
    blocked_count = sum(1 for item in candidates if str(item.get("decision", "")).strip() == "blocked")
    gated_count = sum(1 for item in candidates if str(item.get("decision", "")).strip() == "gated_only")

    execution_mode_recommendations = [
        {
            "candidate_id": item["candidate_id"],
            "title": item["title"],
            "category": item["category"],
            "decision": item["decision"],
            "execution_mode_recommendation": item["execution_mode_recommendation"],
            "reason": item["reason"],
        }
        for item in candidates
    ]

    all_saved = sum(max(int(item.get("estimated_tokens_saved", 0)), 0) for item in selected_tasks)
    all_possible_saved = sum(max(int(item.get("estimated_tokens_saved", 0)), 0) for item in candidates if item.get("selected") or item.get("execution_mode_recommendation") == "capsule")

    created_at = _now_iso()
    report_path = _queue_report_path(repo)
    report_relative = report_path.relative_to(repo).as_posix()

    report = {
        "ok": True,
        "queue_version": FACTORY_QUEUE_VERSION,
        "dry_run": dry_run,
        "plan_only": plan_only,
        "mode": "dry-run" if dry_run else "plan-only",
        "selected_tasks": selected_tasks,
        "skipped_tasks": skipped_tasks,
        "max_tasks": validated_max_tasks,
        "max_steps_per_task": validated_max_steps_per_task,
        "execution_mode_recommendations": execution_mode_recommendations,
        "capsule_recommended_count": capsule_recommended_count,
        "full_repo_required_count": full_repo_required_count,
        "blocked_count": blocked_count + gated_count,
        "gated_count": gated_count,
        "selected_count": selected_count,
        "estimated_savings": {
            "estimated_tokens_saved": all_saved,
            "estimated_possible_tokens_saved": all_possible_saved,
            "estimated_token_baseline": FACTORYOS_BASELINE_TOKENS,
            "estimated_token_capsule": CAPSULE_MINIMAL_TOKENS,
            "estimated_savings_percent": round((all_saved / FACTORYOS_BASELINE_TOKENS) * 100, 2) if all_saved else 0.0,
        },
        "source_intake_report": str(latest_intake.relative_path) if latest_intake else "",
        "executed_live": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "created_at": created_at,
        "finished_at": _now_iso(),
        "report_path": report_relative,
    }

    _write_json_atomic(report_path, report)
    return report
