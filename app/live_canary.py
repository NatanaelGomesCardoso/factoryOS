from __future__ import annotations

import json
import secrets
import subprocess
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_handoff import (
    LIVE_CODEX_ENV,
    LIVE_CODEX_TIMEOUT_SECONDS,
    build_factoryos_codex_exec_command,
    execute_live_codex,
    run_execute,
    run_handoff,
)
from app.run_workspace import (
    prepare_run_workspace,
    repo_root,
    run_workspace_readiness,
    run_workspace_sync_plan,
    show_run,
    workspace_status,
)
from app.task_runner import TaskRunnerError

LIVE_CANARY_REPORTS_DIR = "live-canary"
LIVE_CANARY_ALLOWED_FILE = "reports/live-canary/codex-canary.txt"
LIVE_CANARY_MODEL = "gpt-5.4-mini"
LIVE_CANARY_REASONING = "medium"


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


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports" / LIVE_CANARY_REPORTS_DIR


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


def _git(repo: Path, *args: str) -> str:
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
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"git {' '.join(args)} falhou."
        raise TaskRunnerError(detail)

    return completed.stdout.strip()


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


def _parse_changed_files_from_status(output: str) -> list[str]:
    changed: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip()
        if "->" in candidate:
            candidate = candidate.split("->", 1)[1].strip()
        if candidate:
            changed.append(candidate)
    return changed


def _collect_changed_files(
    repo: Path,
    *,
    workspace_head_before: str,
    workspace_head_after: str,
) -> list[str]:
    status_output = _git_optional(repo, "status", "--short", "--untracked-files=all") or ""
    if status_output.strip():
        return _parse_changed_files_from_status(status_output)

    if workspace_head_before and workspace_head_after and workspace_head_before != workspace_head_after:
        diff_output = _git(repo, "diff", "--name-only", workspace_head_before, workspace_head_after)
        return [line.strip() for line in diff_output.splitlines() if line.strip()]

    return []


def _build_live_prompt(*, run: dict[str, Any], workspace_branch: str | None) -> str:
    lines = [
        "Você está rodando dentro de um worktree isolado do FactoryOS.",
        "Faça apenas isto:",
        "- criar reports/live-canary/codex-canary.txt",
        "- escrever run_id, timestamp e a frase FactoryOS live canary completed",
        "- não editar nenhum outro arquivo",
        "- não instalar dependências",
        "- não usar rede",
        "- não usar API paga",
        "- não ler ou escrever secrets",
        "- não fazer deploy",
        "- não alterar config global",
        "- não fazer push",
        "- se fizer commit, commit local apenas no branch atual com mensagem chore: prove live codex canary",
        "- ao final, mostrar git status --short e git log --oneline -3",
        "",
        f"run_id: {run['id']}",
        f"workspace_path: {run['workspace_path']}",
        f"workspace_branch: {workspace_branch or 'n/d'}",
        f"canary_file: {LIVE_CANARY_ALLOWED_FILE}",
    ]
    return "\n".join(lines) + "\n"


def _build_codex_command(workspace_path: str) -> list[str]:
    codex_plan = {
        "budget_status": "ok",
        "model": LIVE_CANARY_MODEL,
        "reasoning_effort": LIVE_CANARY_REASONING,
        "sandbox_mode": "workspace-write",
        "approval_policy": "never",
        "live": True,
    }
    return build_factoryos_codex_exec_command(
        codex_plan=codex_plan,
        context_pack={"context_status": "ok", "category": "live_canary"},
        workspace_path=workspace_path,
        live=True,
        automated=True,
    )


def _validate_live_canary_inputs(run_id: str, *, repo: Path) -> dict[str, Any]:
    run_result = show_run(run_id, repo=repo)
    run = run_result["run"]
    if run.get("status") != "running":
        raise TaskRunnerError("run precisa estar em running para o canário live.")

    workspace_snapshot = workspace_status(run_id, repo=repo)["workspace"]
    readiness = run_workspace_readiness(run_id, repo=repo)["workspace"]
    sync_plan = run_workspace_sync_plan(run_id, repo=repo)["plan"]

    if readiness.get("status") != "ready":
        reasons = readiness.get("reasons", [])
        reason_text = "; ".join(str(item) for item in reasons) if isinstance(reasons, list) else "workspace não está ready."
        raise TaskRunnerError(f"canário bloqueado: {reason_text}")

    if sync_plan.get("status") != "already_current":
        reasons = sync_plan.get("reasons", [])
        reason_text = "; ".join(str(item) for item in reasons) if isinstance(reasons, list) else "sync plan não está already_current."
        raise TaskRunnerError(f"canário bloqueado: {reason_text}")

    return {
        "run": run,
        "workspace": workspace_snapshot,
        "readiness": readiness,
        "sync_plan": sync_plan,
    }


def _build_report_path(repo: Path, run_id: str, *, created_at: str) -> Path:
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d-%H%M%S")
    return _reports_root(repo) / f"{timestamp}-{run_id}.json"


def _validate_report_path(repo: Path, report_path: Path) -> None:
    if report_path.exists() and report_path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {report_path.name}")
    if report_path.parent != _reports_root(repo):
        raise TaskRunnerError("report_path fora do diretório permitido.")


def run_live_canary(run_id: str, *, repo: Path | None = None, live: bool = False) -> dict[str, Any]:
    repo = repo or repo_root()
    run_preview = show_run(run_id, repo=repo)["run"]
    if not (
        run_preview.get("workspace_kind") == "git_worktree"
        and run_preview.get("workspace_state") == "prepared"
    ):
        prepare_run_workspace(run_id, repo=repo)

    validation = _validate_live_canary_inputs(run_id, repo=repo)
    run = validation["run"]
    workspace_snapshot = validation["workspace"]
    readiness = validation["readiness"]
    sync_plan = validation["sync_plan"]
    run_handoff(run_id, repo=repo)
    dry_run_report = run_execute(run_id, live=False, repo=repo)

    master_head_before = _git(repo, "rev-parse", "HEAD")
    workspace_path = repo / str(run["workspace_path"])
    workspace_head_before = workspace_snapshot.get("workspace_head") or _git_optional(workspace_path, "rev-parse", "HEAD") or ""
    workspace_branch = workspace_snapshot.get("branch")
    created_at = _now_iso()

    if not live:
        return {
            "ok": True,
            "mode": "dry-run",
            "status": "dry_run_only",
            "executed_live": False,
            "canary_run_id": run["id"],
            "canary_task_id": run["task_id"],
            "workspace_path": run["workspace_path"],
            "workspace_branch": workspace_branch,
            "readiness_status": readiness.get("status"),
            "sync_plan_status": sync_plan.get("status"),
            "dry_run_report_path": dry_run_report.get("report_path"),
            "master_head_before": master_head_before,
            "workspace_head_before": workspace_head_before,
            "canary_file": LIVE_CANARY_ALLOWED_FILE,
            "allowed_files_changed": False,
            "changed_files": [],
        }

    if os.environ.get(LIVE_CODEX_ENV) != "1":
        raise TaskRunnerError(f"live canary bloqueado; defina {LIVE_CODEX_ENV}=1 para permitir execução.")

    prompt = _build_live_prompt(run=run, workspace_branch=workspace_branch)
    command = _build_codex_command(str(workspace_path))
    execution_error: str | None = None
    try:
        execution = execute_live_codex(
            command,
            cwd=repo,
            input_text=prompt,
            timeout_seconds=LIVE_CODEX_TIMEOUT_SECONDS,
        )
    except TaskRunnerError as exc:
        execution = None
        execution_error = str(exc)

    finished_at = _now_iso()
    report_path = _build_report_path(repo, run["id"], created_at=finished_at)
    _validate_report_path(repo, report_path)

    stdout_path = report_path.with_suffix(".stdout.txt")
    stderr_path = report_path.with_suffix(".stderr.txt")
    stdout_text = execution.stdout if execution is not None else ""
    stderr_text = execution.stderr if execution is not None else (execution_error or "")
    _write_text_atomic(stdout_path, stdout_text or "")
    _write_text_atomic(stderr_path, stderr_text or "")

    master_head_after = _git(repo, "rev-parse", "HEAD")
    workspace_status_after = workspace_status(run_id, repo=repo)["workspace"]
    workspace_head_after = workspace_status_after.get("workspace_head") or ""
    changed_files = _collect_changed_files(
        workspace_path,
        workspace_head_before=str(workspace_head_before),
        workspace_head_after=str(workspace_head_after),
    )

    allowed_files_changed = bool(changed_files) and len(changed_files) <= 2 and all(
        path == LIVE_CANARY_ALLOWED_FILE for path in changed_files
    )
    branch_commit = workspace_head_after if workspace_head_after and workspace_head_after != workspace_head_before else None
    no_push = True
    no_deploy = True
    no_paid_api = True
    no_secrets = True
    status = "passed"
    reason: str | None = None

    codex_exit_code = execution.returncode if execution is not None else 1

    if codex_exit_code != 0:
        status = "failed"
        reason = f"codex exitou com código {codex_exit_code}."
    elif master_head_after != master_head_before:
        status = "failed"
        reason = "master foi alterado durante o canário."
    elif not allowed_files_changed:
        status = "failed"
        reason = "alteração fora do arquivo permitido ou sem alteração registrada."

    report = {
        "ok": True,
        "mode": "live-canary",
        "status": status,
        "reason": reason,
        "executed_live": True,
        "canary_run_id": run["id"],
        "canary_task_id": run["task_id"],
        "workspace_path": run["workspace_path"],
        "workspace_branch": workspace_branch,
        "master_head_before": master_head_before,
        "master_head_after": master_head_after,
        "workspace_head_before": str(workspace_head_before),
        "workspace_head_after": str(workspace_head_after),
        "allowed_files_changed": allowed_files_changed,
        "changed_files": changed_files,
        "canary_file": LIVE_CANARY_ALLOWED_FILE,
        "codex_exit_code": codex_exit_code,
        "stdout_path": stdout_path.relative_to(repo).as_posix(),
        "stderr_path": stderr_path.relative_to(repo).as_posix(),
        "no_push": no_push,
        "no_deploy": no_deploy,
        "no_paid_api": no_paid_api,
        "no_secrets": no_secrets,
        "created_at": created_at,
        "finished_at": finished_at,
        "branch_commit": branch_commit,
        "readiness_status": readiness.get("status"),
        "sync_plan_status": sync_plan.get("status"),
        "codex_command": command,
        "uses_ignore_user_config": "--ignore-user-config" in command,
        "uses_ephemeral": "--ephemeral" in command,
        "approval_policy": "never",
        "sandbox_mode": "workspace-write",
        "source_of_truth": "codex_plan",
        "global_config_dependency": False,
        "dry_run_report_path": dry_run_report.get("report_path"),
    }

    report["report_path"] = report_path.relative_to(repo).as_posix()
    _write_json_atomic(report_path, report)
    return report


def load_latest_live_canary_result(repo: Path) -> LatestLiveCanaryResult:
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

        report_path = str(payload.get("report_path", "")).strip() or latest.relative_to(repo).as_posix()
        canary_run_id = str(payload.get("canary_run_id", "")).strip()
        canary_task_id = str(payload.get("canary_task_id", "")).strip()
        status = str(payload.get("status", "")).strip()
        mode = str(payload.get("mode", "")).strip()
        executed_live = bool(payload.get("executed_live", False))
        workspace_path = str(payload.get("workspace_path", "")).strip()
        workspace_branch = payload.get("workspace_branch")
        changed_files = payload.get("changed_files", [])
        canary_file = str(payload.get("canary_file", "")).strip()
        codex_exit_code = int(payload.get("codex_exit_code", -1))
        stdout_path = str(payload.get("stdout_path", "")).strip()
        stderr_path = str(payload.get("stderr_path", "")).strip()
        master_head_before = str(payload.get("master_head_before", "")).strip()
        master_head_after = str(payload.get("master_head_after", "")).strip()
        workspace_head_before = str(payload.get("workspace_head_before", "")).strip()
        workspace_head_after = str(payload.get("workspace_head_after", "")).strip()
        allowed_files_changed = bool(payload.get("allowed_files_changed", False))
        no_push = bool(payload.get("no_push", False))
        no_deploy = bool(payload.get("no_deploy", False))
        no_paid_api = bool(payload.get("no_paid_api", False))
        no_secrets = bool(payload.get("no_secrets", False))
        created_at = str(payload.get("created_at", "")).strip()
        finished_at = str(payload.get("finished_at", "")).strip()
        branch_commit = payload.get("branch_commit")

        if not all([report_path, canary_run_id, canary_task_id, status, mode, workspace_path, canary_file, stdout_path, stderr_path, master_head_before, master_head_after, workspace_head_before, workspace_head_after, created_at, finished_at]):
            continue

        if not _safe_relative_path(report_path, prefix=f"reports/{LIVE_CANARY_REPORTS_DIR}/", suffix=".json"):
            continue
        if not _safe_relative_path(stdout_path, prefix=f"reports/{LIVE_CANARY_REPORTS_DIR}/", suffix=".txt"):
            continue
        if not _safe_relative_path(stderr_path, prefix=f"reports/{LIVE_CANARY_REPORTS_DIR}/", suffix=".txt"):
            continue
        if changed_files is not None and not isinstance(changed_files, list):
            continue

        return LatestLiveCanaryResult(
            available=True,
            status=status,
            mode=mode,
            executed_live=executed_live,
            canary_run_id=canary_run_id,
            canary_task_id=canary_task_id,
            report_path=report_path,
            view_path=latest.relative_to(repo / "reports").as_posix(),
            workspace_path=workspace_path,
            workspace_branch=str(workspace_branch).strip() if isinstance(workspace_branch, str) and workspace_branch.strip() else None,
            changed_files=[str(item) for item in changed_files],
            canary_file=canary_file,
            codex_exit_code=codex_exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            master_head_before=master_head_before,
            master_head_after=master_head_after,
            workspace_head_before=workspace_head_before,
            workspace_head_after=workspace_head_after,
            allowed_files_changed=allowed_files_changed,
            no_push=no_push,
            no_deploy=no_deploy,
            no_paid_api=no_paid_api,
            no_secrets=no_secrets,
            created_at=created_at,
            finished_at=finished_at,
            branch_commit=str(branch_commit).strip() if isinstance(branch_commit, str) and branch_commit.strip() else None,
        )

    return LatestLiveCanaryResult(
        available=False,
        status="unknown",
        mode="unknown",
        executed_live=False,
        canary_run_id="",
        canary_task_id="",
        report_path="",
        view_path=None,
        workspace_path="",
        workspace_branch=None,
        changed_files=[],
        canary_file=LIVE_CANARY_ALLOWED_FILE,
        codex_exit_code=-1,
        stdout_path="",
        stderr_path="",
        master_head_before="",
        master_head_after="",
        workspace_head_before="",
        workspace_head_after="",
        allowed_files_changed=False,
        no_push=False,
        no_deploy=False,
        no_paid_api=False,
        no_secrets=False,
        created_at="",
        finished_at="",
        branch_commit=None,
    )
