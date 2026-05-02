from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_handoff import load_latest_handoff_result
from app.execution_evaluator import (
    load_latest_execution_evaluation as load_latest_execution_evaluation_report,
)
from app.controlled_loop import load_latest_controlled_loop_result
from app.expanded_long_run_rehearsal import load_latest_expanded_long_run_rehearsal_result
from app.expanded_long_run_review_gate import load_latest_expanded_long_run_review_gate_result
from app.factory_start import (
    load_latest_factory_start_live_canary_result,
    load_latest_factory_start_result,
)
from app.factory_tick import load_latest_factory_tick_result
from app.live_canary_review_gate import load_latest_bounded_live_canary_review_gate_result
from app.live_canary import load_latest_live_canary_result
from app.long_run_expansion_policy import load_latest_long_run_expansion_policy_result
from app.project_workspace import discover_project_workspaces
from app.state_hygiene import load_latest_state_hygiene_result
from app.run_workspace import DEFAULT_BUDGET, run_workspace_readiness, run_workspace_sync_plan
from app.task_runner import TaskRunnerError

MAX_ITEMS = 5
SECRET_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
SECRET_SUFFIXES = {".key", ".pem", ".token"}
VIEWABLE_AREAS = {
    "reports": "reports",
    "docs": "docs",
    "discovery": "specs/discovery",
    "prd": "specs/prd",
    "technical-spec": "specs/technical-spec",
    "sprints": "specs/sprints",
    "tasks": "tasks",
}


@dataclass(frozen=True, slots=True)
class CommitEntry:
    short_hash: str
    subject: str


@dataclass(frozen=True, slots=True)
class FileEntry:
    name: str
    relative_path: str
    modified_at: str
    size_label: str
    view_area: str | None = None
    view_path: str | None = None


@dataclass(frozen=True, slots=True)
class TaskQueueFile:
    name: str
    relative_path: str
    modified_at: str
    size_label: str
    title: str | None = None
    risk: str | None = None
    executor: str | None = None
    updated_at: str | None = None
    view_area: str | None = None
    view_path: str | None = None


@dataclass(frozen=True, slots=True)
class TaskQueueGroup:
    key: str
    label: str
    description: str
    count: int
    files: list[TaskQueueFile]


@dataclass(frozen=True, slots=True)
class LatestEvaluatorResult:
    available: bool
    task_id: str
    report_path: str
    view_path: str | None
    decision: str
    risk: str
    reason: str
    next_action: str
    failed_checks: list[str]


@dataclass(frozen=True, slots=True)
class LatestRunResult:
    available: bool
    run_id: str
    task_id: str
    status: str
    updated_at: str
    workspace_path: str
    workspace_kind: str | None
    workspace_branch: str | None
    workspace_state: str | None
    readiness_status: str | None
    readiness_reasons: list[str]
    sync_plan_status: str | None
    budget: dict[str, Any]
    notes: list[str]


@dataclass(frozen=True, slots=True)
class LatestFactoryTickResult:
    available: bool
    tick_id: str
    run_id: str
    task_id: str
    mode: str
    status: str
    started_at: str
    finished_at: str
    readiness_status: str | None
    sync_plan_status: str | None
    handoff_report_path: str
    tick_report_path: str
    view_path: str | None
    executed_live: bool
    decision_can_continue_to_live_future: bool
    decision_next_recommended_action: str


@dataclass(frozen=True, slots=True)
class LatestControlledLoopResult:
    available: bool
    loop_version: str
    loop_id: str
    run_id: str
    task_id: str
    mode: str
    status: str
    decision: str
    auto_selected: bool
    eligible_runs_count: int
    hygiene: dict[str, int]
    max_steps: int
    steps_executed: int
    started_at: str
    finished_at: str
    readiness_status: str | None
    sync_plan_status: str | None
    factory_tick_report: str
    evaluation_report: str
    executed_live: bool
    closed: bool
    reasons: list[str]
    view_path: str | None


@dataclass(frozen=True, slots=True)
class LatestFactoryStartResult:
    available: bool
    factory_start_version: str
    mode: str
    start_id: str
    run_id: str
    status: str
    decision: str
    max_steps: int
    steps_completed: int
    executed_live: bool
    loop_report: str
    evaluation_report: str
    evaluation_decision: str
    final_decision: str
    final_status: str
    report_path: str
    view_path: str | None
    started_at: str
    finished_at: str
    reasons: list[str]


@dataclass(frozen=True, slots=True)
class LatestFactoryStartLiveCanaryResult:
    available: bool
    status: str
    mode: str
    max_steps: int
    steps_completed: int
    executed_live: bool
    canary_run_id: str
    canary_task_id: str
    report_path: str
    view_path: str | None
    workspace_path: str
    workspace_branch: str | None
    changed_files: list[str]
    canary_file: str
    codex_exit_code: int
    codex_exit_codes: list[int]
    stdout_path: str
    stderr_path: str
    master_head_before: str
    master_head_after: str
    workspace_head_before: str
    workspace_head_after: str
    allowed_files_changed: bool
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    created_at: str
    finished_at: str
    branch_commit: str | None
    decision: str
    evaluation_report: str
    evaluation_decision: str
    final_decision: str
    final_status: str


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


@dataclass(frozen=True, slots=True)
class LatestLiveCanaryResult:
    available: bool
    status: str
    mode: str
    executed_live: bool
    canary_run_id: str
    canary_task_id: str
    report_path: str
    view_path: str | None
    workspace_path: str
    workspace_branch: str | None
    changed_files: list[str]
    canary_file: str
    codex_exit_code: int
    stdout_path: str
    stderr_path: str
    master_head_before: str
    master_head_after: str
    workspace_head_before: str
    workspace_head_after: str
    allowed_files_changed: bool
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    created_at: str
    finished_at: str
    branch_commit: str | None


@dataclass(frozen=True, slots=True)
class LatestExecutionEvaluationPanelResult:
    available: bool
    run_id: str
    source_report: str
    report_path: str
    view_path: str | None
    decision: str
    checks: dict[str, bool]
    reasons: list[str]
    created_at: str


@dataclass(frozen=True, slots=True)
class LatestBoundedLiveCanaryReviewGateResult:
    available: bool
    review_gate_version: str
    run_id: str
    source_canary_report: str
    source_evaluation_report: str
    source_cost_audit_report: str
    source_maintenance_report: str
    report_path: str
    view_path: str | None
    approved_for_expansion_policy: bool
    allowed_to_execute_live: bool
    next_gate_requires_new_sprint: bool
    decision: str
    blockers: list[str]
    warnings: list[str]
    checks: dict[str, bool]
    recommended_next_gate: dict[str, Any]
    canary_decision: str
    evaluation_decision: str
    cost_audit_status: str
    target_minutes: int
    max_steps: int
    bwrap_path: str
    bwrap_version: str
    harness_global_doctor_status: str
    harness_doctor_status: str
    created_at: str
    finished_at: str


@dataclass(frozen=True, slots=True)
class LatestLongRunExpansionPolicyResult:
    available: bool
    policy_version: str
    run_id: str
    source_review_report: str
    source_canary_report: str
    source_evaluation_report: str
    source_cost_audit_report: str
    source_maintenance_report: str
    source_state_audit_report: str
    source_state_plan_report: str
    report_path: str
    view_path: str | None
    current_level: str
    proposed_next_level: str
    target_minutes: int
    max_steps: int
    allowed_to_execute_live: bool
    requires_new_sprint: bool
    requires_manual_review: bool
    required_gates: list[str]
    acceptance_criteria: list[str]
    levels: list[dict[str, Any]]
    decision: str
    blockers: list[str]
    warnings: list[str]
    checks: dict[str, bool]
    created_at: str
    finished_at: str


@dataclass(frozen=True, slots=True)
class LatestExpandedLongRunRehearsalResult:
    available: bool
    expanded_rehearsal_version: str
    run_id: str
    target_minutes: int
    max_steps: int
    mode: str
    source_expansion_policy_report: str
    long_run_rehearsal_report: str
    maintenance_plan_report: str
    factory_state_audit_report: str
    factory_state_plan_report: str
    allowed_to_execute_live: bool
    executed_live: bool
    requires_review_gate: bool
    requires_new_sprint_for_live: bool
    global_config_dependency: bool
    token_target_status: str
    budget_status: str
    context_status: str
    final_decision: str
    blockers: list[str]
    warnings: list[str]
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    report_path: str
    view_path: str | None
    generated_at: str


@dataclass(frozen=True, slots=True)
class LatestExpandedLongRunReviewGateResult:
    available: bool
    expanded_review_gate_version: str
    run_id: str
    source_expanded_rehearsal_report: str
    approved_for_expanded_live_sprint: bool
    allowed_to_execute_live: bool
    next_gate_requires_new_sprint: bool
    recommended_next_sprint: dict[str, Any]
    decision: str
    blockers: list[str]
    warnings: list[str]
    target_minutes: int
    max_steps: int
    allowed_no_push: bool
    allowed_no_deploy: bool
    allowed_no_paid_api: bool
    allowed_no_secrets: bool
    report_path: str
    view_path: str | None
    generated_at: str


@dataclass(frozen=True, slots=True)
class LatestStateHygieneResult:
    available: bool
    kind: str
    generated_at: str
    report_path: str
    view_path: str | None
    running_tasks_count: int
    running_runs_count: int
    safe_to_close_count: int
    needs_review_count: int
    blocked_count: int


@dataclass(frozen=True, slots=True)
class PanelSnapshot:
    repo_name: str
    branch: str
    generated_at: str
    read_only_notice: str
    commits: list[CommitEntry]
    reports: list[FileEntry]
    discoveries: list[FileEntry]
    docs: list[FileEntry]
    projects: list[dict[str, Any]]
    task_queue: list[TaskQueueGroup]
    latest_evaluator: LatestEvaluatorResult
    latest_run: LatestRunResult
    latest_factory_tick: LatestFactoryTickResult
    latest_controlled_loop: LatestControlledLoopResult
    latest_factory_start: LatestFactoryStartResult
    latest_factory_start_live_canary: LatestFactoryStartLiveCanaryResult
    latest_bounded_live_canary_review_gate: LatestBoundedLiveCanaryReviewGateResult
    latest_long_run_expansion_policy: LatestLongRunExpansionPolicyResult
    latest_expanded_long_run_rehearsal: LatestExpandedLongRunRehearsalResult
    latest_expanded_long_run_review_gate: LatestExpandedLongRunReviewGateResult
    latest_handoff: LatestHandoffResult
    latest_live_canary: LatestLiveCanaryResult
    latest_execution_evaluation: LatestExecutionEvaluationPanelResult
    latest_state_hygiene: LatestStateHygieneResult
    next_step: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(repo: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout.strip()


def _human_size(size_bytes: int) -> str:
    size = float(size_bytes)
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(size_bytes)} B"


def _format_mtime(path: Path) -> str:
    timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp.strftime("%Y-%m-%d %H:%M")


def _safe_visible_file(path: Path) -> bool:
    name = path.name.lower()
    if name.startswith("."):
        return False
    if name in SECRET_EXACT_NAMES:
        return False
    if path.suffix.lower() in SECRET_SUFFIXES:
        return False
    return True


def _task_preview_fields(path: Path) -> tuple[str | None, str | None, str | None, str | None]:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None, None, None

    if not isinstance(payload, dict):
        return None, None, None, None

    def _extract_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        text = value.strip()
        return text or None

    return (
        _extract_text(payload.get("title")),
        _extract_text(payload.get("risk")),
        _extract_text(payload.get("executor")),
        _extract_text(payload.get("updated_at")),
    )


def _is_safe_relative_report_path(value: str, *, prefix: str = "reports/task-evaluations/") -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {"..", "."} for part in candidate.parts):
        return False

    normalized = candidate.as_posix()
    return normalized.startswith(prefix) and candidate.suffix == ".json"


def _is_safe_relative_run_path(value: str, *, prefix: str = "runs/") -> bool:
    if not value or Path(value).is_absolute():
        return False

    candidate = Path(value)
    if any(part in {"..", "."} for part in candidate.parts):
        return False

    normalized = candidate.as_posix()
    return normalized.startswith(prefix) and candidate.suffix == ".json"


def _collect_files(
    directory: Path,
    repo: Path,
    limit: int = MAX_ITEMS,
    *,
    view_area: str | None = None,
    view_root: Path | None = None,
) -> list[TaskQueueFile]:
    if not directory.exists():
        return []

    entries: list[tuple[float, Path]] = []
    for item in directory.iterdir():
        if not item.is_file():
            continue
        if item.is_symlink():
            continue
        if not _safe_visible_file(item):
            continue
        try:
            entries.append((item.stat().st_mtime, item))
        except OSError:
            continue

    entries.sort(key=lambda pair: (pair[0], pair[1].name.lower()), reverse=True)

    results: list[TaskQueueFile] = []
    for _, item in entries[:limit]:
        try:
            relative_path = item.relative_to(repo).as_posix()
        except ValueError:
            continue

        if view_area:
            base = view_root or directory
            try:
                view_path = item.relative_to(base).as_posix()
            except ValueError:
                view_path = None
        else:
            view_path = None

        task_title = task_risk = task_executor = task_updated_at = None
        if view_area == "tasks":
            task_title, task_risk, task_executor, task_updated_at = _task_preview_fields(item)

        results.append(
            TaskQueueFile(
                name=item.name,
                relative_path=relative_path,
                modified_at=_format_mtime(item),
                size_label=_human_size(item.stat().st_size),
                title=task_title,
                risk=task_risk,
                executor=task_executor,
                updated_at=task_updated_at,
                view_area=view_area,
                view_path=view_path,
            )
        )

    return results


def _count_files(directory: Path) -> int:
    if not directory.exists():
        return 0

    count = 0
    for item in directory.iterdir():
        if not item.is_file():
            continue
        if item.is_symlink():
            continue
        if not _safe_visible_file(item):
            continue
        count += 1

    return count


def task_queue_groups(repo: Path) -> list[TaskQueueGroup]:
    specs = [
        ("pending", "Pendentes", "Aguardando decisão ou execução."),
        ("running", "Rodando", "Em execução ou reservadas para trabalho."),
        ("done", "Concluídas", "Finalizadas ou validadas."),
        ("failed", "Falhas", "Precisam de revisão antes de continuar."),
    ]

    groups: list[TaskQueueGroup] = []
    for key, label, description in specs:
        directory = repo / "tasks" / key
        files = _collect_files(
            directory,
            repo,
            limit=MAX_ITEMS,
            view_area="tasks",
            view_root=repo / "tasks",
        )
        groups.append(
            TaskQueueGroup(
                key=key,
                label=label,
                description=description,
                count=_count_files(directory),
                files=files,
            )
        )

    return groups


def load_latest_evaluator_result(repo: Path) -> LatestEvaluatorResult:
    reports_dir = repo / "reports" / "task-evaluations"

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

        task_id = str(payload.get("task_id", "")).strip()
        report_path = str(payload.get("report_path", "")).strip()
        decision = str(payload.get("decision", "")).strip()
        risk = str(payload.get("risk", "")).strip()
        reason = str(payload.get("reason", "")).strip()
        next_action = str(payload.get("next_action", "")).strip()
        failed_checks = payload.get("failed_checks", [])
        if not isinstance(failed_checks, list):
            continue

        actual_report_path = latest.relative_to(repo).as_posix()
        if not task_id or not report_path or not decision or not risk:
            continue

        if report_path != actual_report_path:
            continue

        if not _is_safe_relative_report_path(report_path):
            continue

        return LatestEvaluatorResult(
            available=True,
            task_id=task_id,
            report_path=report_path,
            view_path=latest.relative_to(repo / "reports").as_posix(),
            decision=decision,
            risk=risk,
            reason=reason,
            next_action=next_action,
            failed_checks=[str(item) for item in failed_checks],
        )

    return LatestEvaluatorResult(
        available=False,
        task_id="",
        report_path="",
        view_path=None,
        decision="not_available",
        risk="unknown",
        reason="Nenhum report válido encontrado em reports/task-evaluations/.",
        next_action="Execute python -m app.cli task-evaluate <id> para gerar um report local.",
        failed_checks=[],
    )


def load_latest_run(repo: Path) -> LatestRunResult:
    runs_dir = repo / "runs"

    candidates = sorted(
        [path for path in runs_dir.glob("*/*.json") if path.is_file() and not path.is_symlink()],
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

        run_id = str(payload.get("id", "")).strip()
        task_id = str(payload.get("task_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        updated_at = str(payload.get("updated_at", "")).strip()
        workspace_path = str(payload.get("workspace_path", "")).strip()
        workspace_kind = payload.get("workspace_kind")
        workspace_branch = payload.get("workspace_branch")
        workspace_state = payload.get("workspace_state")
        budget = payload.get("budget", {})
        notes = payload.get("notes", [])

        if not run_id or not task_id or not status or not updated_at or not workspace_path:
            continue

        actual_run_path = latest.relative_to(repo).as_posix()
        expected_run_path = f"runs/{status}/{run_id}.json"
        if actual_run_path != expected_run_path:
            continue

        if not _is_safe_relative_run_path(actual_run_path):
            continue

        if workspace_path != f"workspaces/runs/{run_id}":
            continue

        if not isinstance(budget, dict) or not isinstance(notes, list):
            continue

        if set(budget.keys()) != set(DEFAULT_BUDGET):
            continue

        readiness_status = None
        readiness_reasons: list[str] = []
        sync_plan_status = None
        try:
            readiness_result = run_workspace_readiness(run_id, repo=repo)
        except TaskRunnerError:
            pass
        else:
            workspace_readiness = readiness_result.get("workspace", {})
            if isinstance(workspace_readiness, dict):
                status_value = workspace_readiness.get("status")
                if isinstance(status_value, str) and status_value.strip():
                    readiness_status = status_value.strip()
                reasons_value = workspace_readiness.get("reasons", [])
                if isinstance(reasons_value, list):
                    readiness_reasons = [str(item) for item in reasons_value]
        try:
            sync_plan_result = run_workspace_sync_plan(run_id, repo=repo)
        except TaskRunnerError:
            pass
        else:
            plan_value = sync_plan_result.get("plan", {})
            if isinstance(plan_value, dict):
                status_value = plan_value.get("status")
                if isinstance(status_value, str) and status_value.strip():
                    sync_plan_status = status_value.strip()

        return LatestRunResult(
            available=True,
            run_id=run_id,
            task_id=task_id,
            status=status,
            updated_at=updated_at,
            workspace_path=workspace_path,
            workspace_kind=str(workspace_kind).strip() if isinstance(workspace_kind, str) and workspace_kind.strip() else None,
            workspace_branch=str(workspace_branch).strip() if isinstance(workspace_branch, str) and workspace_branch.strip() else None,
            workspace_state=str(workspace_state).strip() if isinstance(workspace_state, str) and workspace_state.strip() else None,
            readiness_status=readiness_status,
            readiness_reasons=readiness_reasons,
            sync_plan_status=sync_plan_status,
            budget={str(key): value for key, value in budget.items()},
            notes=[str(item) for item in notes],
        )

    return LatestRunResult(
        available=False,
        run_id="",
        task_id="",
        status="unknown",
        updated_at="",
        workspace_path="",
        workspace_kind=None,
        workspace_branch=None,
        workspace_state=None,
        readiness_status=None,
        readiness_reasons=[],
        sync_plan_status=None,
        budget={},
        notes=[],
    )


def load_latest_handoff(repo: Path) -> LatestHandoffResult:
    result = load_latest_handoff_result(repo)
    return LatestHandoffResult(
        available=result.available,
        run_id=result.run_id,
        task_id=result.task_id,
        task_title=result.task_title,
        task_description=result.task_description,
        mode=result.mode,
        report_path=result.report_path,
        prompt_path=result.prompt_path,
        prompt_view_path=result.prompt_view_path,
        view_path=result.view_path,
        workspace_path=result.workspace_path,
        workspace_kind=result.workspace_kind,
        workspace_branch=result.workspace_branch,
        workspace_state=result.workspace_state,
        created_at=result.created_at,
        executed=result.executed,
        live_enabled=result.live_enabled,
        readiness_status=result.readiness_status,
        readiness_reasons=list(result.readiness_reasons),
        budget={str(key): value for key, value in result.budget.items()},
        codex_command=list(result.codex_command),
        technical_pending=result.technical_pending,
    )


def load_latest_factory_tick(repo: Path) -> LatestFactoryTickResult:
    result = load_latest_factory_tick_result(repo)
    return LatestFactoryTickResult(
        available=result.available,
        tick_id=result.tick_id,
        run_id=result.run_id,
        task_id=result.task_id,
        mode=result.mode,
        status=result.status,
        started_at=result.started_at,
        finished_at=result.finished_at,
        readiness_status=result.readiness_status,
        sync_plan_status=result.sync_plan_status,
        handoff_report_path=result.handoff_report_path,
        tick_report_path=result.tick_report_path,
        view_path=result.view_path,
        executed_live=result.executed_live,
        decision_can_continue_to_live_future=result.decision_can_continue_to_live_future,
        decision_next_recommended_action=result.decision_next_recommended_action,
    )


def load_latest_controlled_loop(repo: Path) -> LatestControlledLoopResult:
    result = load_latest_controlled_loop_result(repo)
    return LatestControlledLoopResult(
        available=result.available,
        loop_version=result.loop_version,
        loop_id=result.loop_id,
        run_id=result.run_id,
        task_id=result.task_id,
        mode=result.mode,
        status=result.status,
        decision=result.decision,
        auto_selected=result.auto_selected,
        eligible_runs_count=result.eligible_runs_count,
        hygiene={str(key): int(value) for key, value in result.hygiene.items()},
        max_steps=result.max_steps,
        steps_executed=result.steps_executed,
        started_at=result.started_at,
        finished_at=result.finished_at,
        readiness_status=result.readiness_status,
        sync_plan_status=result.sync_plan_status,
        factory_tick_report=result.factory_tick_report,
        evaluation_report=result.evaluation_report,
        executed_live=result.executed_live,
        closed=result.closed,
        reasons=list(result.reasons),
        view_path=result.view_path,
    )


def load_latest_factory_start(repo: Path) -> LatestFactoryStartResult:
    result = load_latest_factory_start_result(repo)
    return LatestFactoryStartResult(
        available=result.available,
        factory_start_version=result.factory_start_version,
        mode=result.mode,
        start_id=result.start_id,
        run_id=result.run_id,
        status=result.status,
        decision=result.decision,
        max_steps=result.max_steps,
        steps_completed=result.steps_completed,
        executed_live=result.executed_live,
        loop_report=result.loop_report,
        evaluation_report=result.evaluation_report,
        evaluation_decision=result.evaluation_decision,
        final_decision=result.final_decision,
        final_status=result.final_status,
        report_path=result.report_path,
        view_path=result.view_path,
        started_at=result.started_at,
        finished_at=result.finished_at,
        reasons=list(result.reasons),
    )


def load_latest_factory_start_live_canary(repo: Path) -> LatestFactoryStartLiveCanaryResult:
    result = load_latest_factory_start_live_canary_result(repo)
    return LatestFactoryStartLiveCanaryResult(
        available=result.available,
        status=result.status,
        mode=result.mode,
        max_steps=result.max_steps,
        steps_completed=result.steps_completed,
        executed_live=result.executed_live,
        canary_run_id=result.canary_run_id,
        canary_task_id=result.canary_task_id,
        report_path=result.report_path,
        view_path=result.view_path,
        workspace_path=result.workspace_path,
        workspace_branch=result.workspace_branch,
        changed_files=list(result.changed_files),
        canary_file=result.canary_file,
        codex_exit_code=result.codex_exit_code,
        codex_exit_codes=list(result.codex_exit_codes),
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        master_head_before=result.master_head_before,
        master_head_after=result.master_head_after,
        workspace_head_before=result.workspace_head_before,
        workspace_head_after=result.workspace_head_after,
        allowed_files_changed=result.allowed_files_changed,
        no_push=result.no_push,
        no_deploy=result.no_deploy,
        no_paid_api=result.no_paid_api,
        no_secrets=result.no_secrets,
        created_at=result.created_at,
        finished_at=result.finished_at,
        branch_commit=result.branch_commit,
        decision=result.decision,
        evaluation_report=result.evaluation_report,
        evaluation_decision=result.evaluation_decision,
        final_decision=result.final_decision,
        final_status=result.final_status,
    )


def load_latest_live_canary(repo: Path) -> LatestLiveCanaryResult:
    result = load_latest_live_canary_result(repo)
    return LatestLiveCanaryResult(
        available=result.available,
        status=result.status,
        mode=result.mode,
        executed_live=result.executed_live,
        canary_run_id=result.canary_run_id,
        canary_task_id=result.canary_task_id,
        report_path=result.report_path,
        view_path=result.view_path,
        workspace_path=result.workspace_path,
        workspace_branch=result.workspace_branch,
        changed_files=list(result.changed_files),
        canary_file=result.canary_file,
        codex_exit_code=result.codex_exit_code,
        stdout_path=result.stdout_path,
        stderr_path=result.stderr_path,
        master_head_before=result.master_head_before,
        master_head_after=result.master_head_after,
        workspace_head_before=result.workspace_head_before,
        workspace_head_after=result.workspace_head_after,
        allowed_files_changed=result.allowed_files_changed,
        no_push=result.no_push,
        no_deploy=result.no_deploy,
        no_paid_api=result.no_paid_api,
        no_secrets=result.no_secrets,
        created_at=result.created_at,
        finished_at=result.finished_at,
        branch_commit=result.branch_commit,
    )


def load_latest_execution_evaluation(repo: Path) -> LatestExecutionEvaluationPanelResult:
    result = load_latest_execution_evaluation_report(repo)
    return LatestExecutionEvaluationPanelResult(
        available=result.available,
        run_id=result.run_id,
        source_report=result.source_report,
        report_path=result.report_path,
        view_path=result.view_path,
        decision=result.decision,
        checks={str(key): bool(value) for key, value in result.checks.items()},
        reasons=list(result.reasons),
        created_at=result.created_at,
    )


def load_latest_bounded_live_canary_review_gate(repo: Path) -> LatestBoundedLiveCanaryReviewGateResult:
    result = load_latest_bounded_live_canary_review_gate_result(repo)
    return LatestBoundedLiveCanaryReviewGateResult(
        available=result.available,
        review_gate_version=result.review_gate_version,
        run_id=result.run_id,
        source_canary_report=result.source_canary_report,
        source_evaluation_report=result.source_evaluation_report,
        source_cost_audit_report=result.source_cost_audit_report,
        source_maintenance_report=result.source_maintenance_report,
        report_path=result.report_path,
        view_path=result.view_path,
        approved_for_expansion_policy=result.approved_for_expansion_policy,
        allowed_to_execute_live=result.allowed_to_execute_live,
        next_gate_requires_new_sprint=result.next_gate_requires_new_sprint,
        decision=result.decision,
        blockers=list(result.blockers),
        warnings=list(result.warnings),
        checks={str(key): bool(value) for key, value in result.checks.items()},
        recommended_next_gate={str(key): value for key, value in result.recommended_next_gate.items()},
        canary_decision=result.canary_decision,
        evaluation_decision=result.evaluation_decision,
        cost_audit_status=result.cost_audit_status,
        target_minutes=result.target_minutes,
        max_steps=result.max_steps,
        bwrap_path=result.bwrap_path,
        bwrap_version=result.bwrap_version,
        harness_global_doctor_status=result.harness_global_doctor_status,
        harness_doctor_status=result.harness_doctor_status,
        created_at=result.created_at,
        finished_at=result.finished_at,
    )


def load_latest_long_run_expansion_policy(repo: Path) -> LatestLongRunExpansionPolicyResult:
    result = load_latest_long_run_expansion_policy_result(repo)
    return LatestLongRunExpansionPolicyResult(
        available=result.available,
        policy_version=result.policy_version,
        run_id=result.run_id,
        source_review_report=result.source_review_report,
        source_canary_report=result.source_canary_report,
        source_evaluation_report=result.source_evaluation_report,
        source_cost_audit_report=result.source_cost_audit_report,
        source_maintenance_report=result.source_maintenance_report,
        source_state_audit_report=result.source_state_audit_report,
        source_state_plan_report=result.source_state_plan_report,
        report_path=result.report_path,
        view_path=result.view_path,
        current_level=result.current_level,
        proposed_next_level=result.proposed_next_level,
        target_minutes=result.target_minutes,
        max_steps=result.max_steps,
        allowed_to_execute_live=result.allowed_to_execute_live,
        requires_new_sprint=result.requires_new_sprint,
        requires_manual_review=result.requires_manual_review,
        required_gates=list(result.required_gates),
        acceptance_criteria=list(result.acceptance_criteria),
        levels=[{str(key): value for key, value in level.items()} for level in result.levels],
        decision=result.decision,
        blockers=list(result.blockers),
        warnings=list(result.warnings),
        checks={str(key): bool(value) for key, value in result.checks.items()},
        created_at=result.created_at,
        finished_at=result.finished_at,
    )


def load_latest_expanded_long_run_rehearsal(repo: Path) -> LatestExpandedLongRunRehearsalResult:
    result = load_latest_expanded_long_run_rehearsal_result(repo)
    return LatestExpandedLongRunRehearsalResult(
        available=result.available,
        expanded_rehearsal_version=result.expanded_rehearsal_version,
        run_id=result.run_id,
        target_minutes=result.target_minutes,
        max_steps=result.max_steps,
        mode=result.mode,
        source_expansion_policy_report=result.source_expansion_policy_report,
        long_run_rehearsal_report=result.long_run_rehearsal_report,
        maintenance_plan_report=result.maintenance_plan_report,
        factory_state_audit_report=result.factory_state_audit_report,
        factory_state_plan_report=result.factory_state_plan_report,
        allowed_to_execute_live=result.allowed_to_execute_live,
        executed_live=result.executed_live,
        requires_review_gate=result.requires_review_gate,
        requires_new_sprint_for_live=result.requires_new_sprint_for_live,
        global_config_dependency=result.global_config_dependency,
        token_target_status=result.token_target_status,
        budget_status=result.budget_status,
        context_status=result.context_status,
        final_decision=result.final_decision,
        blockers=list(result.blockers),
        warnings=list(result.warnings),
        no_push=result.no_push,
        no_deploy=result.no_deploy,
        no_paid_api=result.no_paid_api,
        no_secrets=result.no_secrets,
        report_path=result.report_path,
        view_path=result.view_path,
        generated_at=result.generated_at,
    )


def load_latest_expanded_long_run_review_gate(repo: Path) -> LatestExpandedLongRunReviewGateResult:
    result = load_latest_expanded_long_run_review_gate_result(repo)
    return LatestExpandedLongRunReviewGateResult(
        available=result.available,
        expanded_review_gate_version=result.expanded_review_gate_version,
        run_id=result.run_id,
        source_expanded_rehearsal_report=result.source_expanded_rehearsal_report,
        approved_for_expanded_live_sprint=result.approved_for_expanded_live_sprint,
        allowed_to_execute_live=result.allowed_to_execute_live,
        next_gate_requires_new_sprint=result.next_gate_requires_new_sprint,
        recommended_next_sprint={str(key): value for key, value in result.recommended_next_sprint.items()},
        decision=result.decision,
        blockers=list(result.blockers),
        warnings=list(result.warnings),
        target_minutes=result.target_minutes,
        max_steps=result.max_steps,
        allowed_no_push=result.allowed_no_push,
        allowed_no_deploy=result.allowed_no_deploy,
        allowed_no_paid_api=result.allowed_no_paid_api,
        allowed_no_secrets=result.allowed_no_secrets,
        report_path=result.report_path,
        view_path=result.view_path,
        generated_at=result.generated_at,
    )


def load_latest_state_hygiene(repo: Path) -> LatestStateHygieneResult:
    result = load_latest_state_hygiene_result(repo)
    if result is None:
        return LatestStateHygieneResult(
            available=False,
            kind="unknown",
            generated_at="",
            report_path="",
            view_path=None,
            running_tasks_count=0,
            running_runs_count=0,
            safe_to_close_count=0,
            needs_review_count=0,
            blocked_count=0,
        )

    return LatestStateHygieneResult(
        available=bool(result["available"]),
        kind=str(result["kind"]),
        generated_at=str(result["generated_at"]),
        report_path=str(result["report_path"]),
        view_path=str(result["view_path"]) if result["view_path"] else None,
        running_tasks_count=int(result["running_tasks_count"]),
        running_runs_count=int(result["running_runs_count"]),
        safe_to_close_count=int(result["safe_to_close_count"]),
        needs_review_count=int(result["needs_review_count"]),
        blocked_count=int(result["blocked_count"]),
    )


def recent_commits(repo: Path, limit: int = MAX_ITEMS) -> list[CommitEntry]:
    output = _run_git(repo, "log", "--oneline", f"-{limit}")
    if not output:
        return []

    commits: list[CommitEntry] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        short_hash, _, subject = line.partition(" ")
        commits.append(
            CommitEntry(
                short_hash=short_hash,
                subject=subject or "(sem mensagem)",
            )
        )

    return commits


def current_branch(repo: Path) -> str:
    branch = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return branch or "indisponível"


def suggested_next_step(snapshot: PanelSnapshot) -> str:
    if snapshot.latest_state_hygiene.available:
        if snapshot.latest_state_hygiene.safe_to_close_count:
            return (
                f"Revisar o último Factory State Hygiene em {snapshot.latest_state_hygiene.view_path}; "
                "fechar apenas os itens safe_to_close."
            )
        return (
            f"Revisar o último Factory State Hygiene em {snapshot.latest_state_hygiene.view_path}; "
            "manter itens ambíguos em needs_review."
        )

    if snapshot.latest_controlled_loop.available:
        if snapshot.latest_controlled_loop.decision == "blocked":
            return (
                f"Controlled Loop bloqueado em {snapshot.latest_controlled_loop.view_path}; "
                "corrigir readiness ou sync plan antes do próximo passo."
            )
        if snapshot.latest_controlled_loop.decision == "needs_review":
            return (
                f"Controlled Loop em {snapshot.latest_controlled_loop.view_path}; "
                "revisar a decisão e fechar a sprint se estiver consistente."
            )
        return (
            f"Controlled Loop registrado em {snapshot.latest_controlled_loop.view_path}; "
            "revisar os reports associados antes de avançar."
        )

    if snapshot.latest_factory_start_live_canary.available:
        if snapshot.latest_factory_start_live_canary.final_decision == "passed":
            return (
                f"Factory Start Live Canary avaliado em {snapshot.latest_factory_start_live_canary.report_path}; "
                "decisão final passada, com master intacto e arquivo permitido validado."
            )
        return (
            f"Factory Start Live Canary registrado em {snapshot.latest_factory_start_live_canary.report_path}; "
            "confirmar master intacto antes de fechar a sprint."
        )

    if snapshot.latest_bounded_live_canary_review_gate.available:
        if snapshot.latest_bounded_live_canary_review_gate.approved_for_expansion_policy:
            return (
                f"Review gate do bounded live canary em {snapshot.latest_bounded_live_canary_review_gate.report_path}; "
                "pode preparar a policy de expansão sem liberar live maior."
            )
        return (
            f"Review gate do bounded live canary em {snapshot.latest_bounded_live_canary_review_gate.report_path}; "
            "revisar blockers antes de qualquer expansão."
        )

    if snapshot.latest_expanded_long_run_review_gate.available:
        if snapshot.latest_expanded_long_run_review_gate.approved_for_expanded_live_sprint:
            return (
                f"Expanded review gate em {snapshot.latest_expanded_long_run_review_gate.report_path}; "
                "a próxima sprint recomendada já pode ser planejada, mas o live continua bloqueado."
            )
        return (
            f"Expanded review gate em {snapshot.latest_expanded_long_run_review_gate.report_path}; "
            "revisar blockers antes de qualquer live 30m/6 steps."
        )

    if snapshot.latest_expanded_long_run_rehearsal.available:
        return (
            f"Expanded rehearsal em {snapshot.latest_expanded_long_run_rehearsal.report_path}; "
            "submeter ao review gate antes de pensar em live."
        )

    if snapshot.latest_long_run_expansion_policy.available:
        return (
            f"Policy de expansão em {snapshot.latest_long_run_expansion_policy.report_path}; "
            "manter 30m/6 steps bloqueado até a próxima sprint."
        )

    if snapshot.latest_factory_start.available:
        return (
            f"Factory Start registrado em {snapshot.latest_factory_start.report_path}; "
            "revisar decisão final e avaliação antes de liberar qualquer live futuro."
        )

    if snapshot.latest_execution_evaluation.available:
        if snapshot.latest_execution_evaluation.decision == "passed":
            return (
                f"Última execução avaliada em {snapshot.latest_execution_evaluation.report_path}; "
                "pode fechar a run/task se ainda estiver running."
            )
        return (
            f"Última execução avaliada em {snapshot.latest_execution_evaluation.report_path}; "
            "revisar a decisão antes de avançar."
        )

    if snapshot.latest_factory_tick.available:
        return (
            f"Revisar o ultimo Factory Tick em {snapshot.latest_factory_tick.tick_report_path} "
            "e manter o live bloqueado ate a proxima sprint."
        )

    if snapshot.latest_evaluator.decision == "stopped_security":
        return "Parar e revisar o problema de segurança apontado pelo evaluator."

    if snapshot.latest_evaluator.decision == "needs_chatgpt_review":
        return "Pedir revisão do ChatGPT antes de continuar a implementação."

    if snapshot.latest_evaluator.decision == "failed_retryable":
        return "Corrigir os checks com falha, rodar validações novamente e reavaliar."

    if snapshot.latest_handoff.available:
        return (
            f"Revisar o último handoff em {snapshot.latest_handoff.report_path} "
            "e manter o live bloqueado até a próxima revisão."
        )

    if snapshot.latest_evaluator.available:
        return (
            f"Avaliação mais recente em {snapshot.latest_evaluator.report_path}; "
            "confira o resultado e siga com o próximo corte pequeno."
        )

    if snapshot.discoveries:
        latest = snapshot.discoveries[0].name
        return (
            f"Revisar {latest} em `specs/discovery/` e atualizar a sprint JSON "
            "antes de abrir a próxima feature."
        )

    if snapshot.reports:
        latest = snapshot.reports[0].name
        return (
            f"Conferir {latest} em `reports/` e registrar o próximo corte pequeno "
            "do FactoryOS."
        )

    return "Criar um discovery Reuse First antes de iniciar uma nova feature."


def build_panel_snapshot(repo: Path | None = None) -> PanelSnapshot:
    repo = repo or repo_root()
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")

    snapshot = PanelSnapshot(
        repo_name="FactoryOS",
        branch=current_branch(repo),
        generated_at=now,
        read_only_notice="read-only V1",
        commits=recent_commits(repo),
        reports=_collect_files(repo / "reports", repo, view_area="reports"),
        discoveries=_collect_files(repo / "specs" / "discovery", repo, view_area="discovery"),
        docs=_collect_files(repo / "docs", repo, view_area="docs"),
        projects=discover_project_workspaces(repo),
        task_queue=task_queue_groups(repo),
        latest_evaluator=load_latest_evaluator_result(repo),
        latest_run=load_latest_run(repo),
        latest_factory_tick=load_latest_factory_tick(repo),
        latest_controlled_loop=load_latest_controlled_loop(repo),
        latest_factory_start=load_latest_factory_start(repo),
        latest_factory_start_live_canary=load_latest_factory_start_live_canary(repo),
        latest_bounded_live_canary_review_gate=load_latest_bounded_live_canary_review_gate(repo),
        latest_long_run_expansion_policy=load_latest_long_run_expansion_policy(repo),
        latest_expanded_long_run_rehearsal=load_latest_expanded_long_run_rehearsal(repo),
        latest_expanded_long_run_review_gate=load_latest_expanded_long_run_review_gate(repo),
        latest_handoff=load_latest_handoff(repo),
        latest_live_canary=load_latest_live_canary(repo),
        latest_execution_evaluation=load_latest_execution_evaluation(repo),
        latest_state_hygiene=load_latest_state_hygiene(repo),
        next_step="",
    )

    return PanelSnapshot(
        repo_name=snapshot.repo_name,
        branch=snapshot.branch,
        generated_at=snapshot.generated_at,
        read_only_notice=snapshot.read_only_notice,
        commits=snapshot.commits,
        reports=snapshot.reports,
        discoveries=snapshot.discoveries,
        docs=snapshot.docs,
        projects=snapshot.projects,
        task_queue=snapshot.task_queue,
        latest_evaluator=snapshot.latest_evaluator,
        latest_run=snapshot.latest_run,
        latest_factory_tick=snapshot.latest_factory_tick,
        latest_controlled_loop=snapshot.latest_controlled_loop,
        latest_factory_start=snapshot.latest_factory_start,
        latest_factory_start_live_canary=snapshot.latest_factory_start_live_canary,
        latest_bounded_live_canary_review_gate=snapshot.latest_bounded_live_canary_review_gate,
        latest_long_run_expansion_policy=snapshot.latest_long_run_expansion_policy,
        latest_expanded_long_run_rehearsal=snapshot.latest_expanded_long_run_rehearsal,
        latest_expanded_long_run_review_gate=snapshot.latest_expanded_long_run_review_gate,
        latest_handoff=snapshot.latest_handoff,
        latest_live_canary=snapshot.latest_live_canary,
        latest_execution_evaluation=snapshot.latest_execution_evaluation,
        latest_state_hygiene=snapshot.latest_state_hygiene,
        next_step=suggested_next_step(snapshot),
    )
