from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.codex_profile import codex_plan_for_run, codex_plan_for_task
from app.memory_digest import latest_memory_digest
from app.report_index import list_reports
from app.routing_contracts import resolve_routing_contract
from app.run_workspace import show_run
from app.task_runner import TaskRunnerError, show_task


@dataclass(frozen=True, slots=True)
class ContextCategory:
    name: str
    required_files: tuple[str, ...]
    candidate_files: tuple[str, ...]
    forbidden_prefixes: tuple[str, ...]
    context_limit_chars: int
    recommended_skills: tuple[str, ...]


DEFAULT_FORBIDDEN_PREFIXES = (
    ".git/",
    ".venv/",
    "workspaces/",
    "reports/bounded-long-run-live-canary/",
    "reports/live-canary/",
    "reports/factory-start-live-canary/",
    "reports/factory-ticks/",
    "reports/factory-loops/",
)

CONTEXT_CATEGORIES: dict[str, ContextCategory] = {
    "docs_only": ContextCategory(
        name="docs_only",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("docs/", "specs/discovery/", "specs/prd/", "specs/technical-spec/", "reports/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=20000,
        recommended_skills=("documentation-writer",),
    ),
    "code_small": ContextCategory(
        name="code_small",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=(
            "app/cli.py",
            "app/codex_profile.py",
            "app/codex_handoff.py",
            "app/factory_queue.py",
            "app/project_intake.py",
            "specs/sprints/",
        ),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=18000,
        recommended_skills=("verification-before-completion",),
    ),
    "code_medium": ContextCategory(
        name="code_medium",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/", "specs/prd/", "specs/technical-spec/", "specs/sprints/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=30000,
        recommended_skills=("verification-before-completion",),
    ),
    "safety_gate": ContextCategory(
        name="safety_gate",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/evaluator.py", "app/execution_evaluator.py", "app/state_hygiene.py", "reports/execution-evaluations/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=35000,
        recommended_skills=("continuous-security-loop", "verification-before-completion"),
    ),
    "live_canary": ContextCategory(
        name="live_canary",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=(
            "app/factory_start.py",
            "app/execution_evaluator.py",
            "specs/sprints/035-bounded-long-run-live-canary-v0.json",
        ),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=70000,
        recommended_skills=("continuous-security-loop", "verification-before-completion"),
    ),
    "evaluator": ContextCategory(
        name="evaluator",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/evaluator.py", "app/execution_evaluator.py", "reports/task-evaluations/", "reports/execution-evaluations/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=30000,
        recommended_skills=("verification-before-completion",),
    ),
    "factory_loop": ContextCategory(
        name="factory_loop",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/controlled_loop.py", "app/factory_tick.py", "app/run_workspace.py", "app/state_hygiene.py"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=42000,
        recommended_skills=("continuous-security-loop", "verification-before-completion"),
    ),
    "factory_start": ContextCategory(
        name="factory_start",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/factory_start.py", "specs/sprints/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=60000,
        recommended_skills=("continuous-security-loop", "verification-before-completion"),
    ),
    "security_review": ContextCategory(
        name="security_review",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/", "specs/technical-spec/", "reports/execution-evaluations/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=50000,
        recommended_skills=("security-best-practices", "verification-before-completion"),
    ),
    "heavy_review_only": ContextCategory(
        name="heavy_review_only",
        required_files=("AGENTS.md", "WORKFLOW.md"),
        candidate_files=("app/", "specs/technical-spec/", "reports/execution-evaluations/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=50000,
        recommended_skills=("security-best-practices", "verification-before-completion"),
    ),
    "retention": ContextCategory(
        name="retention",
        required_files=("AGENTS.md",),
        candidate_files=("app/report_index.py", "reports/", "specs/sprints/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=22000,
        recommended_skills=("verification-before-completion",),
    ),
    "worktree_lifecycle": ContextCategory(
        name="worktree_lifecycle",
        required_files=("AGENTS.md",),
        candidate_files=("app/run_workspace.py", "runs/", "specs/sprints/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=26000,
        recommended_skills=("verification-before-completion",),
    ),
    "cost_control": ContextCategory(
        name="cost_control",
        required_files=("AGENTS.md", "docs/codex-cost-normalization.md"),
        candidate_files=("app/codex_profile.py", "app/codex_handoff.py", "reports/codex-cost-audits/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=24000,
        recommended_skills=("verification-before-completion",),
    ),
    "long_run_planner": ContextCategory(
        name="long_run_planner",
        required_files=("AGENTS.md",),
        candidate_files=("app/factory_start.py", "app/codex_profile.py", "app/codex_context_router.py", "reports/"),
        forbidden_prefixes=DEFAULT_FORBIDDEN_PREFIXES,
        context_limit_chars=32000,
        recommended_skills=("verification-before-completion",),
    ),
}

SECRET_NAMES = {".env", ".env.local", ".env.production", "auth.json"}
SECRET_SUFFIXES = {".key", ".pem", ".token"}


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and not any(part in {"..", "."} for part in path.parts)


def _is_secret_path(relative_path: str) -> bool:
    path = Path(relative_path)
    name = path.name.lower()
    return name in SECRET_NAMES or any(name.endswith(suffix) for suffix in SECRET_SUFFIXES)


def _forbidden(relative_path: str, category: ContextCategory) -> bool:
    normalized = Path(relative_path).as_posix()
    return (
        not _safe_relative(normalized)
        or _is_secret_path(normalized)
        or any(normalized.startswith(prefix) for prefix in category.forbidden_prefixes)
        or ".stdout." in normalized
        or ".stderr." in normalized
    )


def _infer_category(task: dict[str, Any], run: dict[str, Any] | None = None) -> str:
    text = f"{task.get('title', '')} {task.get('description', '')}".lower()
    if any(word in text for word in ("security", "seguranca", "secret", "auth")):
        return "security_review"
    if "factory-start" in text or "factory start" in text:
        return "factory_start"
    if any(word in text for word in ("doc", "prd", "spec", "report", "relatorio", "json")):
        return "docs_only"
    if "canary" in text or "live" in text:
        return "live_canary"
    if "loop" in text:
        return "factory_loop"
    if "evaluator" in text or "avaliador" in text or "avalia" in text:
        return "evaluator"
    if "gate" in text or "readiness" in text or "safety" in text:
        return "safety_gate"
    if run is not None:
        return "code_medium"
    return "code_small"


def _category_from_routing_contract(contract: dict[str, Any]) -> str | None:
    category_name = contract.get("factory_category")
    if category_name is None:
        return None
    normalized = str(category_name)
    if normalized in CONTEXT_CATEGORIES:
        return normalized
    return None


def _policy_multiplier(policy_name: str | None) -> float:
    return {
        "minimal": 0.55,
        "compact": 0.75,
        "standard": 1.0,
        "expanded": 1.2,
    }.get(str(policy_name), 1.0)


def _file_size(repo: Path, relative_path: str) -> int:
    path = repo / relative_path
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _add_file(
    *,
    repo: Path,
    category: ContextCategory,
    relative_path: str,
    included: list[str],
    excluded: list[dict[str, str]],
    max_file_chars: int = 40000,
    directory_limit: int = 3,
) -> None:
    normalized = Path(relative_path).as_posix()
    if normalized in included:
        return
    if _forbidden(normalized, category):
        excluded.append({"path": normalized, "reason": "forbidden_or_unsafe"})
        return
    path = repo / normalized
    if not path.exists():
        excluded.append({"path": normalized, "reason": "missing"})
        return
    if path.is_dir():
        entries = [
            item for item in path.iterdir()
            if item.is_file() and not item.is_symlink()
        ]
        entries.sort(key=lambda entry: (entry.stat().st_mtime, entry.name.lower()), reverse=True)
        for item in entries[:directory_limit]:
            if item.is_file() and not item.is_symlink():
                _add_file(
                    repo=repo,
                    category=category,
                    relative_path=item.relative_to(repo).as_posix(),
                    included=included,
                    excluded=excluded,
                    max_file_chars=max_file_chars,
                    directory_limit=directory_limit,
                )
        return
    size = _file_size(repo, normalized)
    if size <= 0:
        excluded.append({"path": normalized, "reason": "not_readable"})
        return
    if size > max_file_chars:
        excluded.append({"path": normalized, "reason": "file_too_large"})
        return
    included.append(normalized)


def _add_latest_relevant_report(
    *,
    repo: Path,
    run_id: str | None,
    included: list[str],
    excluded: list[dict[str, str]],
    category: ContextCategory,
) -> None:
    if not run_id:
        return
    for kind in ("execution-evaluations", "factory-starts", "factory-loops", "factory-ticks"):
        try:
            reports = list_reports(kind, run_id=run_id, limit=1, repo=repo)
        except TaskRunnerError:
            continue
        for report in reports:
            _add_file(
                repo=repo,
                category=category,
                relative_path=report.relative_path,
                included=included,
                excluded=excluded,
                max_file_chars=12000,
            )


def _memory_digest_snapshot(repo: Path) -> dict[str, Any]:
    digest = latest_memory_digest(repo)
    if not digest.get("available"):
        return {
            "status": "missing",
            "path_json": "",
            "path_md": "",
            "summary": "",
            "chars": 0,
            "warnings": [str(item) for item in digest.get("warnings", []) if str(item).strip()],
        }

    path_json = str(digest.get("digest_path_json", "")).strip()
    path_md = str(digest.get("digest_path_md", "")).strip()
    summary = str(digest.get("summary", "")).strip()
    chars = 0
    for relative_path in (path_json, path_md):
        if relative_path:
            chars += _file_size(repo, relative_path)
    return {
        "status": "ok",
        "path_json": path_json,
        "path_md": path_md,
        "summary": summary,
        "chars": chars,
        "warnings": [str(item) for item in digest.get("warnings", []) if str(item).strip()],
    }


def build_context_pack(
    *,
    task: dict[str, Any],
    run: dict[str, Any] | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    routing_resolution = resolve_routing_contract(task=task, run=run)
    routing_contract = routing_resolution.routing_contract
    if not routing_resolution.valid:
        return {
            "ok": False,
            "task_id": task.get("id"),
            "run_id": None if run is None else str(run.get("id", "")),
            "category": None,
            "routing_status": "invalid",
            "routing_contract": routing_contract,
            "routing_contract_source": routing_resolution.source,
            "included_files": [],
            "excluded_files": [],
            "context_chars": 0,
            "context_limit_chars": 0,
            "context_status": "blocked",
            "reasons": list(routing_resolution.reasons),
            "warnings": list(routing_resolution.warnings),
            "recommended_skills": [],
        }

    category_name = _category_from_routing_contract(routing_contract) or _infer_category(task, run)
    category = CONTEXT_CATEGORIES[category_name]
    run_id = None if run is None else str(run.get("id", ""))
    plan = codex_plan_for_run(run_id, repo=repo) if run_id else codex_plan_for_task(str(task["id"]), repo=repo)
    context_policy = routing_contract.get("context_policy") or "standard"
    directory_limit = 1 if context_policy in {"minimal", "compact"} else 3
    memory_digest = _memory_digest_snapshot(repo)

    included: list[str] = []
    excluded: list[dict[str, str]] = []
    for required in category.required_files:
        _add_file(
            repo=repo,
            category=category,
            relative_path=required,
            included=included,
            excluded=excluded,
            directory_limit=directory_limit,
        )
    for candidate in category.candidate_files:
        if memory_digest["status"] == "ok" and candidate.startswith("reports/"):
            continue
        _add_file(
            repo=repo,
            category=category,
            relative_path=candidate,
            included=included,
            excluded=excluded,
            directory_limit=directory_limit,
        )
    if memory_digest["status"] == "ok":
        for relative_path in (memory_digest["path_json"], memory_digest["path_md"]):
            if relative_path:
                _add_file(
                    repo=repo,
                    category=category,
                    relative_path=relative_path,
                    included=included,
                    excluded=excluded,
                    max_file_chars=12000,
                )
    else:
        _add_latest_relevant_report(repo=repo, run_id=run_id, included=included, excluded=excluded, category=category)

    context_chars = sum(_file_size(repo, item) for item in included)
    reasons: list[str] = []
    warnings = list(routing_resolution.warnings)
    status = "ok"
    effective_limit = int(category.context_limit_chars * _policy_multiplier(str(context_policy)))
    override_limit = routing_contract.get("max_context_chars_override")
    if override_limit is not None:
        effective_limit = int(override_limit)
        reasons.append("max_context_chars_override explícito aplicado ao context pack.")
    if context_chars > effective_limit:
        status = "blocked"
        reasons.append(f"context_chars excede limite da categoria ({effective_limit}).")
    if not included:
        status = "blocked"
        reasons.append("Nenhum arquivo seguro incluído no context pack.")
    if plan.get("budget_status") == "blocked":
        status = "blocked"
        reasons.append("codex_plan já está bloqueado; context pack herdou bloqueio conservador.")

    return {
        "ok": True,
        "task_id": task.get("id"),
        "run_id": run_id,
        "category": category.name,
        "routing_status": "explicit" if routing_resolution.has_explicit_contract else "heuristic",
        "routing_contract": routing_contract,
        "routing_contract_source": routing_resolution.source,
        "recommended_profile": plan["recommended_profile"],
        "included_files": included,
        "excluded_files": excluded,
        "context_chars": context_chars,
        "context_limit_chars": effective_limit,
        "base_context_limit_chars": category.context_limit_chars,
        "context_policy": context_policy,
        "context_status": status,
        "reasons": reasons,
        "warnings": warnings,
        "recommended_skills": list(category.recommended_skills),
        "latest_memory_digest_path": memory_digest["path_json"],
        "memory_digest_status": memory_digest["status"],
        "memory_digest_chars": memory_digest["chars"],
        "memory_digest_summary": memory_digest["summary"],
        "memory_digest_md_path": memory_digest["path_md"],
    }


def context_pack_for_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    task = show_task(task_id, repo=repo)["task"]
    return build_context_pack(task=task, repo=repo)


def context_pack_for_run(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    repo = _repo_root(repo)
    run = show_run(run_id, repo=repo)["run"]
    task = show_task(str(run["task_id"]), repo=repo)["task"]
    return build_context_pack(task=task, run=run, repo=repo)


def list_context_categories() -> dict[str, Any]:
    return {
        "ok": True,
        "categories": [asdict(category) for category in CONTEXT_CATEGORIES.values()],
        "global_skills_changed": False,
        "policy_scope": "repo-local",
    }
