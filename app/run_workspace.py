from __future__ import annotations

import json
import re
import secrets
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.routing_contracts import ROUTING_CONTRACT_FIELD_NAMES, normalize_routing_contract
from app.task_runner import TaskRunnerError, show_task

RUN_STATUSES = ("pending", "running", "done", "failed")
RUN_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WORKSPACE_KIND_DIRECTORY = "directory"
WORKSPACE_KIND_GIT_WORKTREE = "git_worktree"
WORKSPACE_STATE_PREPARED = "prepared"
WORKSPACE_BRANCH_PREFIX = "factoryos/run/"
SYNC_PLAN_STATUS_FAST_FORWARD_AVAILABLE = "fast_forward_available"
SYNC_PLAN_STATUS_ALREADY_CURRENT = "already_current"
SYNC_PLAN_STATUS_BLOCKED_DIRTY = "blocked_dirty"
SYNC_PLAN_STATUS_BLOCKED_WRONG_BRANCH = "blocked_wrong_branch"
SYNC_PLAN_STATUS_BLOCKED_NOT_WORKTREE = "blocked_not_worktree"
SYNC_PLAN_STATUS_BLOCKED_DIVERGED = "blocked_diverged"
SYNC_PLAN_STATUS_BLOCKED_MISSING = "blocked_missing"
DEFAULT_BUDGET = {
    "max_codex_runs": 1,
    "max_retry_attempts": 0,
    "max_changed_files": 20,
    "max_minutes": 60,
    "model": "gpt-5.4-mini",
    "reasoning_effort": "medium",
    "stop_on_security_risk": True,
}


@dataclass(frozen=True, slots=True)
class RunRecord:
    id: str
    task_id: str
    status: str
    created_at: str
    updated_at: str
    workspace_path: str
    budget: dict[str, Any]
    notes: list[str]
    workspace_kind: str | None = None
    workspace_branch: str | None = None
    workspace_state: str | None = None
    workspace_head: str | None = None
    main_head: str | None = None
    snapshot_at: str | None = None
    routing_contract_version: str | None = None
    factory_category: str | None = None
    codex_profile_hint: str | None = None
    context_policy: str | None = None
    live_policy: str | None = None
    max_context_chars_override: int | None = None
    max_changed_files_override: int | None = None
    max_steps_override: int | None = None
    target_minutes_override: int | None = None
    retention_policy: str | None = None
    worktree_policy: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runs_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "runs"


def workspaces_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "workspaces" / "runs"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _slugify(text: str, max_length: int = 48) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-+", "-", ascii_text).strip("-")
    ascii_text = ascii_text[:max_length].strip("-")
    return ascii_text or "run"


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str):
        raise TaskRunnerError("id da run inválido.")

    normalized = run_id.strip()
    if not normalized:
        raise TaskRunnerError("id da run vazio.")

    if "/" in normalized or "\\" in normalized:
        raise TaskRunnerError("path traversal não permitido no id da run.")

    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise TaskRunnerError("id da run contém caracteres inválidos.")

    return normalized


def _validate_task_id(task_id: str) -> str:
    if not isinstance(task_id, str):
        raise TaskRunnerError("id da task inválido.")

    normalized = task_id.strip()
    if not normalized:
        raise TaskRunnerError("id da task vazio.")

    if "/" in normalized or "\\" in normalized:
        raise TaskRunnerError("path traversal não permitido no id da task.")

    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise TaskRunnerError("id da task contém caracteres inválidos.")

    return normalized


def _validate_status(status: str) -> str:
    if status not in RUN_STATUSES:
        raise TaskRunnerError(f"status inválido: {status}")
    return status


def _validate_notes(notes: Any) -> list[str]:
    if notes is None:
        return []

    if not isinstance(notes, list):
        raise TaskRunnerError("notes deve ser uma lista.")

    normalized: list[str] = []
    for note in notes:
        if not isinstance(note, str):
            raise TaskRunnerError("cada note precisa ser texto.")
        normalized.append(note)

    return normalized


def _validate_optional_text(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TaskRunnerError(f"{field_name} precisa ser texto.")
    normalized = value.strip()
    return normalized or None


def _validate_workspace_kind(value: Any) -> str | None:
    normalized = _validate_optional_text(value, field_name="workspace_kind")
    if normalized is None:
        return None
    if normalized not in {WORKSPACE_KIND_DIRECTORY, WORKSPACE_KIND_GIT_WORKTREE}:
        raise TaskRunnerError("workspace_kind inválido.")
    return normalized


def _validate_workspace_branch(value: Any) -> str | None:
    normalized = _validate_optional_text(value, field_name="workspace_branch")
    if normalized is None:
        return None
    if normalized.startswith("/") or normalized.startswith("\\"):
        raise TaskRunnerError("workspace_branch absoluto não permitido.")
    if "/" not in normalized or not normalized.startswith(WORKSPACE_BRANCH_PREFIX):
        raise TaskRunnerError("workspace_branch fora do prefixo permitido.")
    if any(part in {"..", "."} for part in Path(normalized).parts):
        raise TaskRunnerError("path traversal não permitido em workspace_branch.")
    return normalized


def _validate_workspace_state(value: Any) -> str | None:
    normalized = _validate_optional_text(value, field_name="workspace_state")
    if normalized is None:
        return None
    return normalized


def _validate_workspace_head(value: Any, *, field_name: str) -> str | None:
    normalized = _validate_optional_text(value, field_name=field_name)
    if normalized is None:
        return None
    if any(char.isspace() for char in normalized):
        raise TaskRunnerError(f"{field_name} inválido.")
    return normalized


def _validate_budget(budget: Any) -> dict[str, Any]:
    if not isinstance(budget, dict):
        raise TaskRunnerError("budget precisa ser um objeto.")

    expected_keys = set(DEFAULT_BUDGET)
    missing = expected_keys - budget.keys()
    if missing:
        raise TaskRunnerError(f"budget incompleto; faltam: {', '.join(sorted(missing))}")

    extra = set(budget.keys()) - expected_keys
    if extra:
        raise TaskRunnerError(f"budget tem campos extras: {', '.join(sorted(extra))}")

    normalized: dict[str, Any] = {
        "max_codex_runs": int(budget["max_codex_runs"]),
        "max_retry_attempts": int(budget["max_retry_attempts"]),
        "max_changed_files": int(budget["max_changed_files"]),
        "max_minutes": int(budget["max_minutes"]),
        "model": str(budget["model"]).strip(),
        "reasoning_effort": str(budget["reasoning_effort"]).strip(),
        "stop_on_security_risk": bool(budget["stop_on_security_risk"]),
    }

    if normalized["max_codex_runs"] < 0:
        raise TaskRunnerError("max_codex_runs inválido.")
    if normalized["max_retry_attempts"] < 0:
        raise TaskRunnerError("max_retry_attempts inválido.")
    if normalized["max_changed_files"] <= 0:
        raise TaskRunnerError("max_changed_files inválido.")
    if normalized["max_minutes"] <= 0:
        raise TaskRunnerError("max_minutes inválido.")
    if not normalized["model"]:
        raise TaskRunnerError("model não pode ficar vazio.")
    if not normalized["reasoning_effort"]:
        raise TaskRunnerError("reasoning_effort não pode ficar vazio.")

    return normalized


def _validate_payload(payload: dict[str, Any], *, source_path: Path | None = None) -> RunRecord:
    required_fields = {
        "id",
        "task_id",
        "status",
        "created_at",
        "updated_at",
        "workspace_path",
        "budget",
        "notes",
    }
    optional_fields = {
        "workspace_kind",
        "workspace_branch",
        "workspace_state",
        "workspace_head",
        "main_head",
        "snapshot_at",
    }
    missing = required_fields - payload.keys()
    if missing:
        raise TaskRunnerError(f"run JSON incompleto; faltam: {', '.join(sorted(missing))}")

    extra = set(payload.keys()) - required_fields - optional_fields - set(ROUTING_CONTRACT_FIELD_NAMES)
    if extra:
        raise TaskRunnerError(f"run JSON tem campos extras: {', '.join(sorted(extra))}")

    run_id = _validate_run_id(str(payload["id"]))
    task_id = _validate_task_id(str(payload["task_id"]))
    status = _validate_status(str(payload["status"]))
    created_at = str(payload["created_at"]).strip()
    updated_at = str(payload["updated_at"]).strip()
    workspace_path = str(payload["workspace_path"]).strip()
    budget = _validate_budget(payload["budget"])
    notes = _validate_notes(payload["notes"])
    workspace_kind = _validate_workspace_kind(payload.get("workspace_kind"))
    workspace_branch = _validate_workspace_branch(payload.get("workspace_branch"))
    workspace_state = _validate_workspace_state(payload.get("workspace_state"))
    workspace_head = _validate_workspace_head(payload.get("workspace_head"), field_name="workspace_head")
    main_head = _validate_workspace_head(payload.get("main_head"), field_name="main_head")
    snapshot_at = _validate_optional_text(payload.get("snapshot_at"), field_name="snapshot_at")
    try:
        routing_contract = normalize_routing_contract(payload)
    except ValueError as exc:
        raise TaskRunnerError(str(exc)) from exc

    if not created_at or not updated_at:
        raise TaskRunnerError("timestamps da run não podem ficar vazios.")
    if not workspace_path:
        raise TaskRunnerError("workspace_path da run não pode ficar vazio.")
    if source_path is not None and source_path.stem != run_id:
        raise TaskRunnerError("arquivo e id da run não batem.")

    expected_workspace = f"workspaces/runs/{run_id}"
    if workspace_path != expected_workspace:
        raise TaskRunnerError("workspace_path da run não corresponde ao id.")

    return RunRecord(
        id=run_id,
        task_id=task_id,
        status=status,
        created_at=created_at,
        updated_at=updated_at,
        workspace_path=workspace_path,
        budget=budget,
        notes=notes,
        workspace_kind=workspace_kind,
        workspace_branch=workspace_branch,
        workspace_state=workspace_state,
        workspace_head=workspace_head,
        main_head=main_head,
        snapshot_at=snapshot_at,
        **routing_contract,
    )


def _record_to_payload(record: RunRecord) -> dict[str, Any]:
    return asdict(record)


def _ensure_run_roots(repo: Path | None = None) -> Path:
    root = runs_root(repo)
    root.mkdir(parents=True, exist_ok=True)
    for status in RUN_STATUSES:
        (root / status).mkdir(parents=True, exist_ok=True)
    workspaces_root(repo).mkdir(parents=True, exist_ok=True)
    return root


def _run_filename(run_id: str) -> str:
    return f"{run_id}.json"


def _run_path(root: Path, status: str, run_id: str) -> Path:
    return root / status / _run_filename(run_id)


def _workspace_dir(repo: Path, run_id: str) -> Path:
    return workspaces_root(repo) / run_id


def _workspace_branch(run_id: str) -> str:
    return f"{WORKSPACE_BRANCH_PREFIX}{run_id}"


def _run_workspace_path(repo: Path, run: RunRecord | dict[str, Any]) -> Path:
    workspace_path = str(run["workspace_path"] if isinstance(run, dict) else run.workspace_path)
    candidate = Path(workspace_path)
    if candidate.is_absolute():
        raise TaskRunnerError("workspace_path absoluto não permitido.")
    if any(part in {"..", "."} for part in candidate.parts):
        raise TaskRunnerError("path traversal não permitido em workspace_path.")
    return repo / candidate


def _run_branch_name(run: RunRecord | dict[str, Any]) -> str:
    run_id = str(run["id"] if isinstance(run, dict) else run.id)
    return _workspace_branch(run_id)


def _run_workspace_relative(run: RunRecord | dict[str, Any]) -> str:
    workspace_path = str(run["workspace_path"] if isinstance(run, dict) else run.workspace_path)
    return Path(workspace_path).as_posix()


def _run_git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        raise TaskRunnerError("git não disponível no ambiente.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        message = stderr or f"git {' '.join(args)} falhou."
        raise TaskRunnerError(message)

    return completed.stdout.strip()


def _repo_status_clean(repo: Path) -> bool:
    output = _run_git(repo, "status", "--porcelain", "--untracked-files=all")
    return not output.strip()


def _repo_dirty_paths(repo: Path) -> list[str]:
    output = _run_git(repo, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        paths.append(line[3:].strip())
    return [path for path in paths if path]


def _repo_prepare_safe(repo: Path) -> bool:
    dirty_paths = _repo_dirty_paths(repo)
    return not any(path.startswith("workspaces/") for path in dirty_paths)


def _parse_worktree_list(output: str) -> dict[str, dict[str, str | None]]:
    entries: dict[str, dict[str, str | None]] = {}
    current_path: str | None = None
    current_branch: str | None = None

    def _commit_current() -> None:
        nonlocal current_path, current_branch
        if current_path is None:
            return
        entries[current_path] = {
            "branch": current_branch,
        }
        current_path = None
        current_branch = None

    for line in output.splitlines():
        if not line.strip():
            _commit_current()
            continue
        if line.startswith("worktree "):
            _commit_current()
            current_path = line.split(" ", 1)[1].strip()
            current_branch = None
            continue
        if line.startswith("branch "):
            branch_ref = line.split(" ", 1)[1].strip()
            if branch_ref.startswith("refs/heads/"):
                current_branch = branch_ref.removeprefix("refs/heads/")
            else:
                current_branch = branch_ref
            continue
        if line == "detached":
            current_branch = None

    _commit_current()
    return entries


def _worktree_map(repo: Path) -> dict[str, dict[str, str | None]]:
    output = _run_git(repo, "worktree", "list", "--porcelain")
    return _parse_worktree_list(output)


def _git_optional(repo: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout.strip()


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError:
        return None

    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    return None


def _workspace_file_state(workspace_dir: Path) -> str:
    if not workspace_dir.exists():
        return "missing"
    if not workspace_dir.is_dir():
        raise TaskRunnerError("workspace_path não aponta para um diretório.")
    if any(workspace_dir.iterdir()):
        return "populated"
    return "empty_directory"


def _workspace_runtime_snapshot(
    *,
    repo: Path,
    run: RunRecord,
) -> dict[str, Any]:
    workspace_dir = _run_workspace_path(repo, run)
    relative_path = Path(run.workspace_path).as_posix()
    expected_branch = _run_branch_name(run)
    file_state = _workspace_file_state(workspace_dir)
    worktrees = _worktree_map(repo)
    main_head = _git_optional(repo, "rev-parse", "HEAD")

    actual = worktrees.get(workspace_dir.resolve(strict=False).as_posix())
    branch = actual["branch"] if actual is not None else None
    is_worktree = actual is not None
    workspace_head = _git_optional(workspace_dir, "rev-parse", "HEAD") if is_worktree else None
    clean_output = _git_optional(workspace_dir, "status", "--porcelain", "--untracked-files=all") if is_worktree else None
    clean = None if clean_output is None or not is_worktree else not clean_output.strip()
    dirty = None if clean is None else not clean
    readiness = _workspace_readiness_snapshot(
        repo=repo,
        run=run,
        file_state=file_state,
        actual_worktree=actual,
        branch=branch,
        main_head=main_head,
        workspace_head=workspace_head,
        clean=clean,
    )

    if actual is not None:
        state = run.workspace_state or WORKSPACE_STATE_PREPARED
        kind = run.workspace_kind or WORKSPACE_KIND_GIT_WORKTREE
        return {
            "exists": True,
            "is_worktree": True,
            "kind": kind,
            "branch": branch,
            "expected_branch": expected_branch,
            "state": state,
            "file_state": file_state,
            "clean": clean,
            "dirty": dirty,
            "main_head": main_head,
            "workspace_head": workspace_head,
            "expected_main_head": run.main_head,
            "expected_workspace_head": run.workspace_head,
            "head_matches_main": readiness["head_matches_main"],
            "readiness_status": readiness["status"],
            "readiness_reasons": readiness["reasons"],
            "snapshot_at": run.snapshot_at,
            "relative_path": relative_path,
            "absolute_path": workspace_dir.as_posix(),
            "technical_pending": readiness["technical_pending"],
        }

    if file_state == "missing":
        return {
            "exists": False,
            "is_worktree": False,
            "kind": run.workspace_kind or None,
            "branch": branch,
            "expected_branch": expected_branch,
            "state": run.workspace_state or file_state,
            "file_state": file_state,
            "clean": None,
            "dirty": None,
            "main_head": main_head,
            "workspace_head": workspace_head,
            "expected_main_head": run.main_head,
            "expected_workspace_head": run.workspace_head,
            "head_matches_main": readiness["head_matches_main"],
            "readiness_status": readiness["status"],
            "readiness_reasons": readiness["reasons"],
            "snapshot_at": run.snapshot_at,
            "relative_path": relative_path,
            "absolute_path": workspace_dir.as_posix(),
            "technical_pending": readiness["technical_pending"],
        }

    if file_state == "empty_directory":
        return {
            "exists": True,
            "is_worktree": False,
            "kind": run.workspace_kind or WORKSPACE_KIND_DIRECTORY,
            "branch": branch,
            "expected_branch": expected_branch,
            "state": run.workspace_state or file_state,
            "file_state": file_state,
            "clean": None,
            "dirty": None,
            "main_head": main_head,
            "workspace_head": workspace_head,
            "expected_main_head": run.main_head,
            "expected_workspace_head": run.workspace_head,
            "head_matches_main": readiness["head_matches_main"],
            "readiness_status": readiness["status"],
            "readiness_reasons": readiness["reasons"],
            "snapshot_at": run.snapshot_at,
            "relative_path": relative_path,
            "absolute_path": workspace_dir.as_posix(),
            "technical_pending": readiness["technical_pending"],
        }

    return {
        "exists": True,
        "is_worktree": False,
        "kind": run.workspace_kind or WORKSPACE_KIND_DIRECTORY,
        "branch": branch,
        "expected_branch": expected_branch,
        "state": run.workspace_state or file_state,
        "file_state": file_state,
        "clean": None,
        "dirty": None,
        "main_head": main_head,
        "workspace_head": workspace_head,
        "expected_main_head": run.main_head,
        "expected_workspace_head": run.workspace_head,
        "head_matches_main": readiness["head_matches_main"],
        "readiness_status": readiness["status"],
        "readiness_reasons": readiness["reasons"],
        "snapshot_at": run.snapshot_at,
        "relative_path": relative_path,
        "absolute_path": workspace_dir.as_posix(),
        "technical_pending": readiness["technical_pending"],
    }


def _workspace_readiness_snapshot(
    *,
    repo: Path,
    run: RunRecord,
    file_state: str,
    actual_worktree: dict[str, str | None] | None,
    branch: str | None,
    main_head: str | None,
    workspace_head: str | None,
    clean: bool | None,
) -> dict[str, Any]:
    expected_branch = _run_branch_name(run)
    expected_main_head = run.main_head
    expected_workspace_head = run.workspace_head
    reasons: list[str] = []
    status = "blocked"
    head_matches_main = False

    if file_state == "missing":
        reasons.append("Workspace inexistente.")
    elif file_state == "empty_directory":
        reasons.append("Workspace vazio.")
    elif file_state == "populated" and actual_worktree is None:
        reasons.append("Workspace populado sem git worktree correspondente.")

    if actual_worktree is None:
        if file_state != "missing":
            reasons.append("Workspace não é um git worktree.")
    else:
        if branch != expected_branch:
            reasons.append(f"Branch esperada {expected_branch}, encontrada {branch or 'desanexada'}.")

        if clean is None:
            reasons.append("Não foi possível ler o git status do workspace.")
        elif not clean:
            reasons.append("Workspace sujo.")

        if main_head is None:
            reasons.append("HEAD principal indisponível.")

        if workspace_head is None:
            reasons.append("HEAD do workspace indisponível.")

        branch_ok = branch == expected_branch
        workspace_matches_snapshot = (
            expected_workspace_head is None or workspace_head == expected_workspace_head
        )
        main_matches_snapshot = expected_main_head is None or main_head == expected_main_head

        if expected_workspace_head and workspace_head and workspace_head != expected_workspace_head:
            reasons.append("HEAD do workspace divergiu do snapshot registrado no prepare.")

        if expected_main_head and main_head and main_head != expected_main_head:
            reasons.append(
                "HEAD principal mudou desde o prepare; revisar sincronização antes do próximo live."
            )

        if branch_ok and clean and main_head and workspace_head:
            head_matches_main = main_head == workspace_head
            if not workspace_matches_snapshot:
                status = "blocked"
            elif not main_matches_snapshot:
                status = "needs_sync_review"
            elif head_matches_main:
                status = "ready"
                reasons = []
            else:
                status = "needs_sync_review"
                reasons = [
                    "HEAD do workspace difere do HEAD principal; revisão de sincronização necessária."
                ]
        else:
            status = "blocked"

    if status == "blocked" and not reasons:
        reasons = ["Workspace não está pronto para execução."]

    technical_pending = reasons[0] if status != "ready" and reasons else None

    return {
        "status": status,
        "reasons": reasons,
        "head_matches_main": head_matches_main,
        "technical_pending": technical_pending,
        "main_head": main_head,
        "workspace_head": workspace_head,
        "branch": branch,
        "expected_branch": expected_branch,
        "clean": clean,
    }


def _workspace_sync_plan_snapshot(
    *,
    repo: Path,
    run: RunRecord,
) -> dict[str, Any]:
    workspace = _workspace_runtime_snapshot(repo=repo, run=run)
    reasons: list[str] = []
    status = SYNC_PLAN_STATUS_BLOCKED_MISSING
    safe_to_apply = False

    main_head = workspace.get("main_head")
    workspace_head = workspace.get("workspace_head")
    branch = workspace.get("branch")
    expected_branch = workspace.get("expected_branch")
    is_worktree = bool(workspace.get("is_worktree"))
    clean = workspace.get("clean")
    file_state = workspace.get("file_state")

    if file_state == "missing":
        reasons.append("Workspace inexistente.")
        status = SYNC_PLAN_STATUS_BLOCKED_MISSING
    elif not is_worktree:
        reasons.append("Workspace não é um git worktree real.")
        status = SYNC_PLAN_STATUS_BLOCKED_NOT_WORKTREE
    elif branch != expected_branch:
        reasons.append(f"Branch esperada {expected_branch}, encontrada {branch or 'desanexada'}.")
        status = SYNC_PLAN_STATUS_BLOCKED_WRONG_BRANCH
    elif clean is False:
        reasons.append("Workspace sujo.")
        status = SYNC_PLAN_STATUS_BLOCKED_DIRTY
    elif clean is None:
        reasons.append("Não foi possível ler o git status do workspace.")
        status = SYNC_PLAN_STATUS_BLOCKED_MISSING
    elif main_head is None or workspace_head is None:
        reasons.append("Não foi possível ler main_head ou workspace_head.")
        status = SYNC_PLAN_STATUS_BLOCKED_MISSING
    elif main_head == workspace_head:
        status = SYNC_PLAN_STATUS_ALREADY_CURRENT
    else:
        ancestor = _git_is_ancestor(repo, workspace_head, main_head)
        if ancestor is None:
            reasons.append("Falha ao verificar a ancestralidade entre workspace_head e main_head.")
            status = SYNC_PLAN_STATUS_BLOCKED_MISSING
        elif ancestor:
            status = SYNC_PLAN_STATUS_FAST_FORWARD_AVAILABLE
            safe_to_apply = True
        else:
            reasons.append(
                "workspace_head não é ancestral de main_head; sincronização segura não é possível."
            )
            status = SYNC_PLAN_STATUS_BLOCKED_DIVERGED

    return {
        "status": status,
        "safe_to_apply": safe_to_apply,
        "main_head": main_head,
        "workspace_head": workspace_head,
        "expected_branch": expected_branch,
        "branch": branch,
        "is_worktree": is_worktree,
        "clean": clean,
        "reasons": reasons,
        "workspace": workspace,
    }


def _write_run_payload(path: Path, payload: dict[str, Any]) -> None:
    _safe_write_json(path, payload)


def _all_run_paths(root: Path, run_id: str) -> list[Path]:
    filename = _run_filename(run_id)
    matches: list[Path] = []
    for status in RUN_STATUSES:
        candidate = root / status / filename
        if candidate.is_symlink():
            raise TaskRunnerError(f"symlink não permitido: {candidate.name}")
        if candidate.exists():
            matches.append(candidate)
    return matches


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.name}: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise TaskRunnerError("run JSON precisa ser um objeto.")

    return payload


def _load_run_from_source(source_path: Path) -> RunRecord:
    if source_path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {source_path.name}")

    payload = _load_json_file(source_path)
    record = _validate_payload(payload, source_path=source_path)

    if source_path.parent.name != record.status:
        raise TaskRunnerError(
            f"status no arquivo ({record.status}) não corresponde ao diretório ({source_path.parent.name})."
        )

    return record


def _find_run(root: Path, run_id: str) -> tuple[Path, RunRecord]:
    normalized_id = _validate_run_id(run_id)
    matches = _all_run_paths(root, normalized_id)

    if not matches:
        raise TaskRunnerError(f"run inexistente: {normalized_id}")

    if len(matches) > 1:
        raise TaskRunnerError(f"run duplicada encontrada para id {normalized_id}")

    source_path = matches[0]
    record = _load_run_from_source(source_path)
    return source_path, record


def _ensure_unique_run_id(root: Path, run_id: str) -> None:
    if _all_run_paths(root, run_id):
        raise TaskRunnerError(f"run já existe: {run_id}")


def _safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _workspace_payload_path(repo: Path, run_id: str) -> str:
    return _workspace_dir(repo, run_id).relative_to(repo).as_posix()


def _build_run_id(task_id: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    slug = _slugify(task_id, max_length=40)
    suffix = secrets.token_hex(3)
    return _validate_run_id(f"{timestamp}-{slug}-{suffix}")


def _task_exists(task_id: str, *, repo: Path) -> None:
    show_task(task_id, repo=repo)


def create_run(
    task_id: str,
    routing_contract: dict[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_task_id = _validate_task_id(task_id)
    _task_exists(normalized_task_id, repo=repo_root_path)

    routing_contract = dict(routing_contract or {})
    try:
        normalized_routing_contract = normalize_routing_contract(routing_contract)
    except ValueError as exc:
        raise TaskRunnerError(str(exc)) from exc

    run_id = _build_run_id(normalized_task_id)
    _ensure_unique_run_id(root, run_id)

    workspace_dir = _workspace_dir(repo_root_path, run_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    now = _now_iso()
    record = RunRecord(
        id=run_id,
        task_id=normalized_task_id,
        status="running",
        created_at=now,
        updated_at=now,
        workspace_path=_workspace_payload_path(repo_root_path, run_id),
        budget=dict(DEFAULT_BUDGET),
        notes=[],
        **normalized_routing_contract,
    )
    payload = _record_to_payload(record)

    destination = _run_path(root, "running", run_id)
    _safe_write_json(destination, payload)

    return {
        "ok": True,
        "action": "created",
        "run": payload,
        "path": destination.relative_to(repo_root_path).as_posix(),
        "workspace_path": record.workspace_path,
    }


def prepare_run_workspace(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    source_path, record = _find_run(root, normalized_id)

    if record.status != "running":
        raise TaskRunnerError("run precisa estar em running para preparar workspace.")

    # Bloqueamos apenas sujeira operacional no espaço de worktrees; mudanças da sprint atual
    # em código/spec/task não impedem criar um worktree isolado a partir do HEAD já commitado.
    if not _repo_prepare_safe(repo_root_path):
        raise TaskRunnerError("workspace/worktree pendente no repo principal bloqueia a preparação.")

    workspace_dir = _run_workspace_path(repo_root_path, record)
    workspace_relative = Path(record.workspace_path)
    expected_branch = _workspace_branch(normalized_id)
    worktrees = _worktree_map(repo_root_path)
    resolved_workspace = workspace_dir.resolve(strict=False).as_posix()
    existing_worktree = worktrees.get(resolved_workspace)

    if existing_worktree is not None:
        branch = existing_worktree["branch"]
        if branch != expected_branch:
            raise TaskRunnerError(
                f"workspace já é um git worktree de branch diferente: {branch or 'desanexada'}."
            )
    else:
        if workspace_dir.exists():
            if not workspace_dir.is_dir():
                raise TaskRunnerError("workspace_path não aponta para um diretório.")
            if any(workspace_dir.iterdir()):
                raise TaskRunnerError("workspace populado não é um git worktree da run.")
        else:
            workspace_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            _run_git(
                repo_root_path,
                "worktree",
                "add",
                "-b",
                expected_branch,
                workspace_relative.as_posix(),
                "HEAD",
            )
        except TaskRunnerError as exc:
            raise TaskRunnerError(f"falha ao criar git worktree: {exc}") from exc

    updated = RunRecord(
        id=record.id,
        task_id=record.task_id,
        status=record.status,
        created_at=record.created_at,
        updated_at=_now_iso(),
        workspace_path=record.workspace_path,
        budget=record.budget,
        notes=record.notes,
        workspace_kind=WORKSPACE_KIND_GIT_WORKTREE,
        workspace_branch=expected_branch,
        workspace_state=WORKSPACE_STATE_PREPARED,
        workspace_head=None,
        main_head=None,
        snapshot_at=None,
    )
    prepared_snapshot = _workspace_runtime_snapshot(repo=repo_root_path, run=updated)
    snapshot_now = _now_iso()
    updated = RunRecord(
        id=updated.id,
        task_id=updated.task_id,
        status=updated.status,
        created_at=updated.created_at,
        updated_at=snapshot_now,
        workspace_path=updated.workspace_path,
        budget=updated.budget,
        notes=updated.notes,
        workspace_kind=updated.workspace_kind,
        workspace_branch=updated.workspace_branch,
        workspace_state=updated.workspace_state,
        workspace_head=str(prepared_snapshot.get("workspace_head", "")).strip() or None,
        main_head=str(prepared_snapshot.get("main_head", "")).strip() or None,
        snapshot_at=snapshot_now,
        routing_contract_version=record.routing_contract_version,
        factory_category=record.factory_category,
        codex_profile_hint=record.codex_profile_hint,
        context_policy=record.context_policy,
        live_policy=record.live_policy,
        max_context_chars_override=record.max_context_chars_override,
        max_changed_files_override=record.max_changed_files_override,
        max_steps_override=record.max_steps_override,
        target_minutes_override=record.target_minutes_override,
        retention_policy=record.retention_policy,
        worktree_policy=record.worktree_policy,
    )
    updated_payload = _record_to_payload(updated)
    _validate_payload(updated_payload, source_path=source_path)
    _write_run_payload(source_path, updated_payload)

    snapshot = _workspace_runtime_snapshot(repo=repo_root_path, run=updated)
    return {
        "ok": True,
        "action": "prepared",
        "run": updated_payload,
        "workspace": snapshot,
        "path": source_path.relative_to(repo_root_path).as_posix(),
    }


def _transition_run(
    run_id: str,
    *,
    from_statuses: Iterable[str],
    to_status: str,
    repo: Path | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    allowed_sources = tuple(from_statuses)
    if not allowed_sources:
        raise TaskRunnerError("nenhum status de origem informado.")

    matches: list[tuple[str, Path]] = []
    for status in allowed_sources:
        candidate = _run_path(root, status, normalized_id)
        if candidate.exists():
            matches.append((status, candidate))

    if not matches:
        raise TaskRunnerError(
            f"run {normalized_id} não encontrada nos status: {', '.join(allowed_sources)}"
        )

    if len(matches) > 1:
        raise TaskRunnerError(f"run duplicada encontrada para id {normalized_id}")

    from_status, source_path = matches[0]
    record = _load_run_from_source(source_path)

    if record.status != from_status:
        raise TaskRunnerError(
            f"status no arquivo ({record.status}) não corresponde ao diretório ({from_status})."
        )

    destination = _run_path(root, to_status, normalized_id)
    if destination.exists():
        raise TaskRunnerError(f"run já existe no destino {to_status}: {normalized_id}")

    notes = record.notes
    if note is not None:
        notes = [*notes, note]

    updated = RunRecord(
        id=record.id,
        task_id=record.task_id,
        status=to_status,
        created_at=record.created_at,
        updated_at=_now_iso(),
        workspace_path=record.workspace_path,
        budget=record.budget,
        notes=notes,
        workspace_kind=record.workspace_kind,
        workspace_branch=record.workspace_branch,
        workspace_state=record.workspace_state,
        workspace_head=record.workspace_head,
        main_head=record.main_head,
        snapshot_at=record.snapshot_at,
        routing_contract_version=record.routing_contract_version,
        factory_category=record.factory_category,
        codex_profile_hint=record.codex_profile_hint,
        context_policy=record.context_policy,
        live_policy=record.live_policy,
        max_context_chars_override=record.max_context_chars_override,
        max_changed_files_override=record.max_changed_files_override,
        max_steps_override=record.max_steps_override,
        target_minutes_override=record.target_minutes_override,
        retention_policy=record.retention_policy,
        worktree_policy=record.worktree_policy,
    )
    updated_payload = _record_to_payload(updated)
    _validate_payload(updated_payload)

    source_path.replace(destination)
    destination.write_text(json.dumps(updated_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "action": f"moved_to_{to_status}",
        "from_status": from_status,
        "to_status": to_status,
        "run": updated_payload,
        "source_path": source_path.relative_to(repo_root_path).as_posix(),
        "path": destination.relative_to(repo_root_path).as_posix(),
    }


def finish_run(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    return _transition_run(run_id, from_statuses=("running",), to_status="done", repo=repo)


def fail_run(run_id: str, reason: str, *, repo: Path | None = None) -> dict[str, Any]:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise TaskRunnerError("reason da run não pode ficar vazio.")

    return _transition_run(
        run_id,
        from_statuses=("running",),
        to_status="failed",
        repo=repo,
        note=f"failure_reason: {normalized_reason}",
    )


def _run_public_view(record: RunRecord, *, path: Path | None = None) -> dict[str, Any]:
    payload = _record_to_payload(record)
    if path is not None:
        payload["path"] = path.as_posix()
    return payload


def show_run(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    source_path, record = _find_run(root, run_id)
    return {
        "ok": True,
        "action": "show",
        "run": _run_public_view(record, path=source_path.relative_to(repo_root_path)),
        "path": source_path.relative_to(repo_root_path).as_posix(),
    }


def list_runs(*, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    groups: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for status in RUN_STATUSES:
        directory = root / status
        entries: list[tuple[Path, RunRecord]] = []
        if directory.exists():
            for path in sorted(directory.glob("*.json"), key=lambda item: item.name.lower()):
                if path.is_symlink():
                    raise TaskRunnerError(f"symlink não permitido: {path.name}")
                record = _load_run_from_source(path)
                entries.append((path, record))

        counts[status] = len(entries)
        groups.append(
            {
                "status": status,
                "count": len(entries),
                "runs": [
                    _run_public_view(record, path=path.relative_to(repo_root_path))
                    for path, record in entries
                ],
            }
        )

    return {
        "ok": True,
        "counts": counts,
        "groups": groups,
    }


def workspace_status(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    source_path, record = _find_run(root, normalized_id)
    snapshot = _workspace_runtime_snapshot(repo=repo_root_path, run=record)

    return {
        "ok": True,
        "action": "workspace_status",
        "run": _run_public_view(record, path=source_path.relative_to(repo_root_path)),
        "workspace": snapshot,
        "path": source_path.relative_to(repo_root_path).as_posix(),
    }


def run_workspace_readiness(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    _, record = _find_run(root, normalized_id)
    snapshot = _workspace_runtime_snapshot(repo=repo_root_path, run=record)

    return {
        "ok": True,
        "run_id": normalized_id,
        "workspace": {
            "exists": bool(snapshot["exists"]),
            "is_worktree": bool(snapshot["is_worktree"]),
            "branch": snapshot["branch"],
            "expected_branch": snapshot["expected_branch"],
            "clean": snapshot["clean"],
            "main_head": snapshot["main_head"],
            "workspace_head": snapshot["workspace_head"],
            "expected_main_head": snapshot["expected_main_head"],
            "expected_workspace_head": snapshot["expected_workspace_head"],
            "snapshot_at": snapshot["snapshot_at"],
            "head_matches_main": snapshot["head_matches_main"],
            "status": snapshot["readiness_status"],
            "reasons": list(snapshot["readiness_reasons"]),
        },
    }


def run_workspace_sync_plan(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    _, record = _find_run(root, normalized_id)
    plan_snapshot = _workspace_sync_plan_snapshot(repo=repo_root_path, run=record)

    return {
        "ok": True,
        "run_id": normalized_id,
        "plan": {
            "status": plan_snapshot["status"],
            "safe_to_apply": bool(plan_snapshot["safe_to_apply"]),
            "main_head": plan_snapshot["main_head"],
            "workspace_head": plan_snapshot["workspace_head"],
            "expected_branch": plan_snapshot["expected_branch"],
            "branch": plan_snapshot["branch"],
            "reasons": list(plan_snapshot["reasons"]),
        },
    }


def _run_git_command(repo: Path, *args: str) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except OSError as exc:
        raise TaskRunnerError("git não disponível no ambiente.") from exc

    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def run_workspace_sync_apply(run_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_run_roots(repo)
    repo_root_path = root.parent
    normalized_id = _validate_run_id(run_id)
    _, record = _find_run(root, normalized_id)
    before = _workspace_sync_plan_snapshot(repo=repo_root_path, run=record)

    if before["status"] != SYNC_PLAN_STATUS_FAST_FORWARD_AVAILABLE or not before["safe_to_apply"]:
        reasons = list(before["reasons"])
        if before["status"] == SYNC_PLAN_STATUS_ALREADY_CURRENT:
            reasons = ["Workspace já está sincronizado com main_head."]
        raise TaskRunnerError(
            f"sync bloqueado: {before['status']}" + (f" | {'; '.join(reasons)}" if reasons else "")
        )

    workspace_dir = _run_workspace_path(repo_root_path, record)
    main_head = str(before["main_head"])

    code, stdout, stderr = _run_git_command(workspace_dir, "merge", "--ff-only", main_head)
    if code != 0:
        message = stderr or stdout or "falha ao aplicar fast-forward."
        raise TaskRunnerError(f"sync bloqueado: {message}")

    after = _workspace_sync_plan_snapshot(repo=repo_root_path, run=record)
    readiness_after = run_workspace_readiness(normalized_id, repo=repo_root_path)

    return {
        "ok": True,
        "run_id": normalized_id,
        "applied": True,
        "before": {
            "plan": {
                "status": before["status"],
                "safe_to_apply": bool(before["safe_to_apply"]),
                "main_head": before["main_head"],
                "workspace_head": before["workspace_head"],
                "expected_branch": before["expected_branch"],
                "branch": before["branch"],
                "reasons": list(before["reasons"]),
            },
            "readiness": workspace_status(normalized_id, repo=repo_root_path)["workspace"],
        },
        "after": {
            "plan": {
                "status": after["status"],
                "safe_to_apply": bool(after["safe_to_apply"]),
                "main_head": after["main_head"],
                "workspace_head": after["workspace_head"],
                "expected_branch": after["expected_branch"],
                "branch": after["branch"],
                "reasons": list(after["reasons"]),
            },
            "readiness": readiness_after["workspace"],
        },
        "git": {
            "returncode": code,
            "stdout": stdout,
            "stderr": stderr,
        },
    }
