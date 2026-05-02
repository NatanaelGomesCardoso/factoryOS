from __future__ import annotations

import json
import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from app.run_workspace import finish_run, list_runs, show_run
from app.task_runner import TaskRunnerError, finish_task, list_tasks, note_task, show_task

REPORTS_DIR = "factory-state-hygiene"
SAFE_REPORT_ROOTS = ("reports", "specs")
CURRENT_SPRINT_MARKERS = (
    "sprint 019",
    "sprint-019",
    "factory state hygiene",
    "factory-state-hygiene",
)
TASK_TITLE_RE = re.compile(r"^Sprint\s+(\d{3})\s+(.+)$", re.IGNORECASE)
SPRINT_013_TASK_ID = "20260430-134542-sprint-013-worktree-sync-readiness-gate-ae42c9"
SPRINT_013_COMMIT = "7c53cd5"
SPRINT_013_COMMIT_SUBJECT = "feat: add worktree readiness gate v0"
SPRINT_013_COMMAND = "run-workspace-readiness"
SPRINT_013_REPORT_KIND = "sprint-013-backfill"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(text: str, max_length: int = 64) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-+", "-", ascii_text).strip("-")
    return ascii_text[:max_length].strip("-") or "item"


def _safe_relative_out_path(value: str) -> bool:
    if not value:
        return False

    candidate = Path(value)
    if candidate.is_absolute():
        return False
    if any(part in {"..", "."} for part in candidate.parts):
        return False
    return True


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


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


def _repo_clean(repo: Path) -> bool:
    return not _run_git(repo, "status", "--porcelain", "--untracked-files=all").strip()


def _repo_dirty_paths(repo: Path) -> list[str]:
    output = _run_git(repo, "status", "--porcelain", "--untracked-files=all")
    paths: list[str] = []
    for line in output.splitlines():
        match = re.match(r"^[ MADRCU?!]{2} (.+)$", line)
        if match is None:
            continue
        path = match.group(1).strip()
        if path:
            paths.append(path)
    return paths


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _age_days(created_at: str) -> int | None:
    created = _parse_timestamp(created_at)
    if created is None:
        return None
    delta = datetime.now().astimezone() - created
    return max(delta.days, 0)


def _is_current_sprint_task(title: str, task_id: str, description: str) -> bool:
    haystack = " ".join([title, task_id, description]).lower()
    return any(marker in haystack for marker in CURRENT_SPRINT_MARKERS)


def _task_sprint_prefix(title: str) -> str:
    match = TASK_TITLE_RE.match(title.strip())
    if match is None:
        return _slugify(title)
    return f"{match.group(1)}-{_slugify(match.group(2))}"


def _supporting_files(repo: Path, needles: list[str]) -> list[str]:
    normalized_needles = [needle.lower() for needle in needles if needle]
    results: list[str] = []
    seen: set[str] = set()

    for root_name in SAFE_REPORT_ROOTS:
        root = repo / root_name
        if not root.exists():
            continue

        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue

            try:
                relative_path = path.relative_to(repo).as_posix()
            except ValueError:
                continue

            if relative_path.startswith(f"reports/{REPORTS_DIR}/"):
                continue

            relative_lower = relative_path.lower()
            if any(needle in relative_lower for needle in normalized_needles):
                if relative_path not in seen:
                    seen.add(relative_path)
                    results.append(relative_path)
                continue

            if path.stat().st_size > 512_000:
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue

            if any(needle in text for needle in normalized_needles):
                if relative_path not in seen:
                    seen.add(relative_path)
                    results.append(relative_path)

            if len(results) >= 20:
                return results

    return results


def _glob_evidence_files(repo: Path, patterns: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(repo.glob(pattern)):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(repo).as_posix()
            if relative in seen:
                continue
            seen.add(relative)
            results.append(relative)
    return results


def _factory_state_plan_decision(repo: Path, item_id: str) -> str | None:
    for target in _plan_payload(repo)["targets"]:
        if str(target.get("id", "")).strip() == item_id:
            return str(target.get("decision", "")).strip() or None
    return None


def factory_state_snapshot(*, repo: Path | None = None) -> dict[str, int]:
    repo = repo or repo_root()
    stats = _audit_payload(repo)["stats"]
    return {
        "running_tasks_count": int(stats["running_tasks_count"]),
        "running_runs_count": int(stats["running_runs_count"]),
        "safe_to_close_count": int(stats["safe_to_close_count"]),
        "needs_review_count": int(stats["needs_review_count"]),
        "blocked_count": int(stats["blocked_count"]),
    }


def _sprint_013_backfill_payload(repo: Path) -> dict[str, Any]:
    before_stats = factory_state_snapshot(repo=repo)
    repo_clean_before = _repo_clean(repo)
    dirty_paths = _repo_dirty_paths(repo)
    operational_dirty_paths = [
        path
        for path in dirty_paths
        if path.startswith("tasks/") or path.startswith("runs/") or path.startswith("workspaces/")
    ]
    operational_dirty_paths = [
        path for path in operational_dirty_paths if "sprint-020" not in path
    ]
    mutation_state_clean = not operational_dirty_paths
    task_exists = False
    task_status = ""
    task_title = ""
    task_path = ""
    task_notes_before: list[str] = []

    try:
        task_result = show_task(SPRINT_013_TASK_ID, repo=repo)
    except TaskRunnerError as exc:
        task_lookup_error = str(exc)
    else:
        task_lookup_error = ""
        task_exists = True
        task = task_result["task"]
        task_status = str(task.get("status", "")).strip()
        task_title = str(task.get("title", "")).strip()
        task_path = str(task.get("path", "")).strip()
        task_notes_before = [str(item) for item in task.get("notes", []) if str(item).strip()]

    run_listing = list_runs(repo=repo)
    linked_running_runs = [
        str(run.get("id", "")).strip()
        for group in run_listing["groups"]
        if group["status"] == "running"
        for run in group["runs"]
        if str(run.get("task_id", "")).strip() == SPRINT_013_TASK_ID
    ]

    log_output = _run_git(repo, "log", "--oneline", "--all", "--decorate=short", "-200")
    commit_found = any(
        line.startswith(SPRINT_013_COMMIT) and SPRINT_013_COMMIT_SUBJECT in line
        for line in log_output.splitlines()
    )

    cli_source = (repo / "app" / "cli.py").read_text(encoding="utf-8")
    run_workspace_source = (repo / "app" / "run_workspace.py").read_text(encoding="utf-8")
    readiness_command_present = (
        SPRINT_013_COMMAND in cli_source
        and "def run_workspace_readiness" in run_workspace_source
    )

    evidence_patterns = [
        "specs/sprints/013*",
        "specs/technical-spec/*readiness*",
        "specs/prd/*readiness*",
        "specs/discovery/*readiness*",
        "reports/*readiness*",
        "reports/*worktree*",
    ]
    glob_evidence = _glob_evidence_files(repo, evidence_patterns)
    supporting_evidence = _supporting_files(
        repo,
        [
            SPRINT_013_TASK_ID,
            task_title or "Sprint 013 Worktree Sync Readiness Gate V0",
            "worktree readiness gate",
            "run-workspace-readiness",
        ],
    )
    evidence_files = sorted(dict.fromkeys([*glob_evidence, *supporting_evidence]))

    plan_decision = _factory_state_plan_decision(repo, SPRINT_013_TASK_ID)
    plan_allows_review = plan_decision in {"safe_to_close", "needs_review"}
    sufficient_evidence = all(
        [
            mutation_state_clean,
            task_exists,
            task_status == "running",
            commit_found,
            readiness_command_present,
            bool(evidence_files),
            not linked_running_runs,
            plan_allows_review,
        ]
    )

    closed = False
    executed_mutations: list[dict[str, Any]] = []
    decision = "needs_review"
    decision_reason = "Evidência local insuficiente para fechar a Sprint 013 com segurança."

    if sufficient_evidence:
        note_result = note_task(
            SPRINT_013_TASK_ID,
            "Backfill Sprint 020: evidência local suficiente confirmada; commit 7c53cd5, comando run-workspace-readiness e specs/proofs locais encontrados.",
            repo=repo,
        )
        finish_result = finish_task(SPRINT_013_TASK_ID, repo=repo)
        closed = True
        decision = "closed"
        decision_reason = "Backfill conservador fechou a Sprint 013 com prova local suficiente."
        executed_mutations.extend(
            [
                {
                    "kind": "task-note",
                    "id": SPRINT_013_TASK_ID,
                    "path": note_result.get("path"),
                },
                {
                    "kind": "task-finish",
                    "id": SPRINT_013_TASK_ID,
                    "from_status": finish_result.get("from_status"),
                    "to_status": finish_result.get("to_status"),
                    "path": finish_result.get("path"),
                },
            ]
        )
    elif not repo_clean_before:
        decision = "needs_review"
        decision_reason = "Repo geral está sujo por artefatos da sprint atual; fila operacional continuou limpa."
    elif not mutation_state_clean:
        decision = "blocked"
        decision_reason = "Fila operacional precisa estar limpa antes da mutação de backfill."
    elif plan_decision == "blocked":
        decision = "blocked"
        decision_reason = "Factory state plan ainda bloqueia a Sprint 013."

    after_stats = factory_state_snapshot(repo=repo)
    task_status_after = task_status
    task_path_after = task_path
    task_notes_after = task_notes_before
    if task_exists:
        try:
            refreshed = show_task(SPRINT_013_TASK_ID, repo=repo)
        except TaskRunnerError:
            refreshed = None
        if refreshed is None:
            task_status_after = "done" if closed else task_status
            task_path_after = f"tasks/done/{SPRINT_013_TASK_ID}.json" if closed else task_path
        else:
            refreshed_task = refreshed["task"]
            task_status_after = str(refreshed_task.get("status", "")).strip()
            task_path_after = str(refreshed_task.get("path", "")).strip()
            task_notes_after = [str(item) for item in refreshed_task.get("notes", []) if str(item).strip()]

    return {
        "ok": True,
        "kind": SPRINT_013_REPORT_KIND,
        "generated_at": _now_iso(),
        "task_id": SPRINT_013_TASK_ID,
        "task_title": task_title,
        "task_path_before": task_path,
        "task_path_after": task_path_after,
        "task_status_before": task_status,
        "task_status_after": task_status_after,
        "repo_clean_before": repo_clean_before,
        "dirty_paths_before": dirty_paths,
        "operational_dirty_paths_before": operational_dirty_paths,
        "mutation_state_clean_before": mutation_state_clean,
        "linked_running_runs": linked_running_runs,
        "git_commit": {
            "short_hash": SPRINT_013_COMMIT,
            "subject": SPRINT_013_COMMIT_SUBJECT,
            "found": commit_found,
        },
        "command_checks": {
            "run_workspace_readiness_present": readiness_command_present,
        },
        "factory_state_plan_decision": plan_decision,
        "criteria": {
            "task_exists": task_exists,
            "task_running": task_status == "running",
            "commit_found": commit_found,
            "command_present": readiness_command_present,
            "has_evidence_files": bool(evidence_files),
            "running_runs_linked_zero": not linked_running_runs,
            "plan_not_blocked": plan_allows_review,
            "repo_clean_before_mutation": repo_clean_before,
            "queue_state_clean_before_mutation": mutation_state_clean,
            "sufficient_evidence": sufficient_evidence,
        },
        "evidence_files": evidence_files,
        "task_lookup_error": task_lookup_error,
        "decision": decision,
        "decision_reason": decision_reason,
        "closed": closed,
        "notes_before": task_notes_before,
        "notes_after": task_notes_after,
        "before_stats": before_stats,
        "after_stats": after_stats,
        "executed_mutations": executed_mutations,
        "deleted_files": [],
        "removed_worktrees": [],
        "executed_live": False,
    }


def _task_public_record(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    task_id = str(payload.get("id", "")).strip()
    status = str(payload.get("status", "")).strip()
    created_at = str(payload.get("created_at", "")).strip()
    updated_at = str(payload.get("updated_at", "")).strip()
    linked_runs = list(payload.get("linked_runs", []))
    age_days = _age_days(created_at)
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "age_days": age_days,
        "linked_runs": linked_runs,
    }


def _run_public_record(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = str(payload.get("id", "")).strip()
    task_id = str(payload.get("task_id", "")).strip()
    status = str(payload.get("status", "")).strip()
    created_at = str(payload.get("created_at", "")).strip()
    updated_at = str(payload.get("updated_at", "")).strip()
    linked_task = payload.get("linked_task")
    age_days = _age_days(created_at)
    return {
        "id": run_id,
        "task_id": task_id,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "age_days": age_days,
        "linked_task": linked_task,
    }


def _current_task_and_run_snapshot(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    tasks = list_tasks(repo=repo)
    runs = list_runs(repo=repo)
    task_map: dict[str, dict[str, Any]] = {}
    run_map: dict[str, dict[str, Any]] = {}

    for group in tasks["groups"]:
        for task in group["tasks"]:
            task_map[str(task["id"])] = task

    for group in runs["groups"]:
        for run in group["runs"]:
            run_map[str(run["id"])] = run

    return task_map, run_map


def _build_targets(repo: Path) -> list[dict[str, Any]]:
    task_map, run_map = _current_task_and_run_snapshot(repo)

    targets: list[dict[str, Any]] = []

    for task_id, task in sorted(task_map.items(), key=lambda item: item[0]):
        if task.get("status") != "running":
            continue

        try:
            detailed = show_task(task_id, repo=repo)
        except TaskRunnerError:
            continue

        record = detailed["task"]
        title = str(record.get("title", "")).strip()
        description = str(record.get("description", "")).strip()
        task_sprint_prefix = _task_sprint_prefix(title)
        linked_runs = [
            run["id"]
            for run in run_map.values()
            if str(run.get("task_id", "")).strip() == task_id
        ]
        needles = [
            task_id,
            title,
            description,
            task_sprint_prefix,
        ]
        if linked_runs:
            needles.extend(linked_runs)
        supporting_files = _supporting_files(repo, needles)
        current_sprint = _is_current_sprint_task(title, task_id, description)

        targets.append(
            {
                "kind": "task",
                "id": task_id,
                "title": title,
                "status": str(record.get("status", "")).strip(),
                "created_at": str(record.get("created_at", "")).strip(),
                "updated_at": str(record.get("updated_at", "")).strip(),
                "age_days": _age_days(str(record.get("created_at", "")).strip()),
                "linked_runs": linked_runs,
                "supporting_files": supporting_files,
                "current_sprint": current_sprint,
            }
        )

    for run_id, run in sorted(run_map.items(), key=lambda item: item[0]):
        if run.get("status") != "running":
            continue

        try:
            detailed = show_run(run_id, repo=repo)
        except TaskRunnerError:
            continue

        record = detailed["run"]
        task_id = str(record.get("task_id", "")).strip()
        task = task_map.get(task_id)
        task_title = str(task.get("title", "")).strip() if task else ""
        task_description = str(task.get("description", "")).strip() if task else ""
        sprint_prefix = _task_sprint_prefix(task_title) if task_title else _slugify(task_id)
        supporting_files = _supporting_files(
            repo,
            [
                run_id,
                task_id,
                task_title,
                task_description,
                sprint_prefix,
            ],
        )

        targets.append(
            {
                "kind": "run",
                "id": run_id,
                "task_id": task_id,
                "task_title": task_title,
                "status": str(record.get("status", "")).strip(),
                "created_at": str(record.get("created_at", "")).strip(),
                "updated_at": str(record.get("updated_at", "")).strip(),
                "age_days": _age_days(str(record.get("created_at", "")).strip()),
                "supporting_files": supporting_files,
                "current_sprint": bool(task and _is_current_sprint_task(task_title, task_id, task_description)),
            }
        )

    return targets


def _classify_target(target: dict[str, Any]) -> dict[str, Any]:
    supporting_files = list(target.get("supporting_files", []))
    current_sprint = bool(target.get("current_sprint"))
    status = str(target.get("status", "")).strip()
    kind = str(target.get("kind", "")).strip()

    if current_sprint:
        decision = "blocked"
        reason = "Item da sprint atual; não deve ser fechado pela higiene."
    elif status != "running":
        decision = "blocked"
        reason = f"Status inesperado para higiene: {status or 'indefinido'}."
    elif supporting_files:
        decision = "safe_to_close"
        reason = "Evidência local suficiente encontrada em reports e specs."
    else:
        decision = "needs_review"
        reason = "Não foi possível encontrar prova/report local suficiente."

    return {
        **target,
        "decision": decision,
        "reason": reason,
        "evidence": {
            "supporting_files": supporting_files,
            "has_proof_or_report": any("proof" in path.lower() or "report" in path.lower() for path in supporting_files),
        },
    }


def _audit_payload(repo: Path) -> dict[str, Any]:
    task_listing = list_tasks(repo=repo)
    run_listing = list_runs(repo=repo)
    targets = [_classify_target(target) for target in _build_targets(repo)]

    counts = {
        "tasks": task_listing["counts"],
        "runs": run_listing["counts"],
    }
    stats = {
        "running_tasks_count": int(task_listing["counts"].get("running", 0)),
        "running_runs_count": int(run_listing["counts"].get("running", 0)),
        "safe_to_close_count": sum(1 for item in targets if item["decision"] == "safe_to_close"),
        "needs_review_count": sum(1 for item in targets if item["decision"] == "needs_review"),
        "blocked_count": sum(1 for item in targets if item["decision"] == "blocked"),
    }

    return {
        "ok": True,
        "kind": "audit",
        "generated_at": _now_iso(),
        "counts": counts,
        "stats": stats,
        "targets": targets,
        "executed_mutations": [],
        "deleted_files": [],
        "removed_worktrees": [],
        "executed_live": False,
    }


def _plan_payload(repo: Path) -> dict[str, Any]:
    audit = _audit_payload(repo)
    planned_targets = []
    for target in audit["targets"]:
        planned_targets.append(
            {
                **target,
                "planned_action": target["decision"],
            }
        )

    report = {
        "ok": True,
        "kind": "plan",
        "generated_at": _now_iso(),
        "counts": audit["counts"],
        "stats": audit["stats"],
        "targets": planned_targets,
        "plan_summary": {
            "safe_to_close": audit["stats"]["safe_to_close_count"],
            "needs_review": audit["stats"]["needs_review_count"],
            "blocked": audit["stats"]["blocked_count"],
        },
        "executed_mutations": [],
        "deleted_files": [],
        "removed_worktrees": [],
        "executed_live": False,
    }

    return report


def _apply_payload(repo: Path, *, execute: bool) -> dict[str, Any]:
    plan = _plan_payload(repo)
    planned_targets = list(plan["targets"])
    mutations: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    deleted_files: list[str] = []
    removed_worktrees: list[str] = []

    if execute:
        for target in planned_targets:
            if target["decision"] != "safe_to_close":
                skipped.append(
                    {
                        "kind": target["kind"],
                        "id": target["id"],
                        "decision": target["decision"],
                        "reason": target["reason"],
                    }
                )
                continue

            if target["kind"] == "task":
                result = finish_task(str(target["id"]), repo=repo)
            else:
                result = finish_run(str(target["id"]), repo=repo)

            mutations.append(
                {
                    "kind": target["kind"],
                    "id": target["id"],
                    "from_status": result.get("from_status"),
                    "to_status": result.get("to_status"),
                    "path": result.get("path"),
                }
            )

    report = {
        "ok": True,
        "kind": "apply",
        "mode": "execute" if execute else "dry-run",
        "generated_at": _now_iso(),
        "counts": plan["counts"],
        "stats": plan["stats"],
        "targets": planned_targets,
        "applied_mutations": mutations,
        "skipped_targets": skipped,
        "deleted_files": deleted_files,
        "removed_worktrees": removed_worktrees,
        "executed_live": False,
    }

    return report


def _write_report(repo: Path, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    report_dir = repo / "reports" / REPORTS_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{_timestamp()}-{kind}.json"
    payload = {**payload, "report_path": report_path.relative_to(repo).as_posix()}
    payload["view_path"] = report_path.relative_to(repo / "reports").as_posix()
    _write_json(report_path, payload)
    return payload


def factory_state_audit(*, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    payload = _write_report(repo, "audit", _audit_payload(repo))
    return payload


def factory_state_plan(*, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    payload = _write_report(repo, "plan", _plan_payload(repo))
    return payload


def factory_state_apply(*, dry_run: bool = True, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    payload = _write_report(repo, "apply", _apply_payload(repo, execute=not dry_run))
    return payload


def factory_state_backfill_sprint_013(*, repo: Path | None = None) -> dict[str, Any]:
    repo = repo or repo_root()
    payload = _write_report(repo, SPRINT_013_REPORT_KIND, _sprint_013_backfill_payload(repo))
    return payload


def load_latest_state_hygiene_result(repo: Path) -> dict[str, Any] | None:
    reports_dir = repo / "reports" / REPORTS_DIR
    if not reports_dir.exists():
        return None

    candidates = sorted(
        reports_dir.glob("*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for path in candidates:
        payload = _load_json(path)
        if payload is None:
            continue
        report_path = str(payload.get("report_path", "")).strip()
        if report_path != path.relative_to(repo).as_posix():
            continue
        view_path = str(payload.get("view_path", "")).strip()
        if not view_path.startswith("factory-state-hygiene/"):
            continue
        kind = str(payload.get("kind", "")).strip()
        if kind not in {"audit", "plan", "apply", SPRINT_013_REPORT_KIND}:
            continue
        stats = payload.get("stats", {})
        if not isinstance(stats, dict):
            continue

        return {
            "available": True,
            "kind": kind,
            "generated_at": str(payload.get("generated_at", "")).strip(),
            "report_path": report_path,
            "view_path": view_path,
            "running_tasks_count": int(stats.get("running_tasks_count", 0)),
            "running_runs_count": int(stats.get("running_runs_count", 0)),
            "safe_to_close_count": int(stats.get("safe_to_close_count", 0)),
            "needs_review_count": int(stats.get("needs_review_count", 0)),
            "blocked_count": int(stats.get("blocked_count", 0)),
        }

    return {
        "available": False,
        "kind": "unknown",
        "generated_at": "",
        "report_path": "",
        "view_path": None,
        "running_tasks_count": 0,
        "running_runs_count": 0,
        "safe_to_close_count": 0,
        "needs_review_count": 0,
        "blocked_count": 0,
    }
