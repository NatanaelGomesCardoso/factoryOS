from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

REPORT_TIMESTAMP_RE = re.compile(r"^(?P<ts>\d{8}-\d{6})(?:-.+)?$")
RUN_ID_KEYS = ("run_id", "canary_run_id")

REPORT_KINDS: dict[str, str] = {
    "artifact-intake-plans": "artifact-intakes",
    "artifact-intake-registers": "artifact-intakes",
    "artifact-intakes": "artifact-intakes",
    "bounded-live-canary-review-gates": "bounded-live-canary-reviews",
    "bounded-live-canary-reviews": "bounded-live-canary-reviews",
    "bounded-long-run-live-canary": "bounded-long-run-live-canary",
    "expanded-bounded-live-canary": "expanded-bounded-live-canary",
    "codex-cost-audits": "codex-cost-audits",
    "cost-aware-factory-starts": "cost-aware-factory-starts",
    "execution-evaluations": "execution-evaluations",
    "expanded-long-run-rehearsals": "expanded-long-run-rehearsals",
    "expanded-long-run-reviews": "expanded-long-run-reviews",
    "factory-long-run-plans": "factory-long-run-plans",
    "factory-long-run-rehearsals": "factory-long-run-rehearsals",
    "factory-queue-starts": "factory-queue-starts",
    "factory-maintenance-plans": "factory-maintenance-plans",
    "factory-loops": "factory-loops",
    "factory-start-live-canary": "factory-start-live-canary",
    "factory-starts": "factory-starts",
    "factory-state-hygiene": "factory-state-hygiene",
    "factory-ticks": "factory-ticks",
    "mvp-apply-plan": "mvp-apply-plans",
    "mvp-apply-plans": "mvp-apply-plans",
    "mvp-build-plan": "mvp-build-plans",
    "mvp-build-plans": "mvp-build-plans",
    "mvp-capsule-build-canary": "mvp-capsule-build-canaries",
    "mvp-capsule-build-canaries": "mvp-capsule-build-canaries",
    "mvp-evaluations": "mvp-evaluations",
    "live-canary": "live-canary",
    "long-run-expansion-policies": "long-run-expansion-policies",
    "report-retention-plans": "report-retention-plans",
    "post-expansion-evaluations": "post-expansion-evaluations",
    "post-expansion-rollback-plans": "post-expansion-rollback-plans",
    "project-intakes": "project-intakes",
    "project-workspaces": "project-workspaces",
    "run-handoffs": "run-handoffs",
    "mvp-delivery-packages": "mvp-delivery-packages",
    "project-pilot-runbooks": "project-pilot-runbooks",
    "factoryos-v1-readiness-gates": "factoryos-v1-readiness-gates",
    "factoryos-v1-audits": "factoryos-v1-audits",
    "final-v1-polish-consistency-pass": "final-v1-polish-consistency-pass",
    "final-v1-readiness-closure": "final-v1-readiness-closure",
    "factoryos-v1-technical-freeze": "factoryos-v1-technical-freeze",
    "security-safety-reviews": "security-safety-reviews",
    "reliability-hardening": "reliability-hardening",
    "obsidian-project-syncs": "obsidian-project-syncs",
    "report-retention": "report-retention",
    "report-retention-audits": "report-retention",
    "report-retention-cleanup-plans": "report-retention",
    "report-retention-plans": "report-retention",
    "worktree-lifecycle-plans": "worktree-lifecycle-plans",
}


@dataclass(frozen=True, slots=True)
class ReportIndexEntry:
    kind: str
    relative_path: str
    view_path: str
    filename: str
    mtime: float
    timestamp: str | None
    run_id: str | None
    payload: dict[str, Any]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports"


def report_directory(kind: str, *, repo: Path | None = None) -> Path:
    try:
        directory = REPORT_KINDS[kind]
    except KeyError as exc:
        raise TaskRunnerError(f"kind de report inválido: {kind}") from exc
    return reports_root(repo) / directory


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _is_temporary_report(path: Path) -> bool:
    name = path.name
    if name.startswith("."):
        return True
    if path.suffix != ".json":
        return True
    if name.endswith(".stdout.json") or name.endswith(".stderr.json"):
        return True
    if ".tmp" in name:
        return True
    return False


def _parse_payload_timestamp(payload: dict[str, Any]) -> str | None:
    for key in ("finished_at", "created_at", "started_at", "generated_at", "evaluated_at"):
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized:
            continue
        try:
            return datetime.fromisoformat(normalized).isoformat()
        except ValueError:
            continue
    return None


def _parse_filename_timestamp(path: Path) -> str | None:
    match = REPORT_TIMESTAMP_RE.match(path.stem)
    if not match:
        return None
    raw = match.group("ts")
    try:
        return datetime.strptime(raw, "%Y%m%d-%H%M%S").isoformat()
    except ValueError:
        return None


def _sort_key(path: Path, payload: dict[str, Any]) -> tuple[str, float, str]:
    timestamp = _parse_payload_timestamp(payload) or _parse_filename_timestamp(path) or ""
    return (timestamp, path.stat().st_mtime, path.name)


def _payload_run_id(payload: dict[str, Any]) -> str | None:
    for key in RUN_ID_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def list_reports(
    kind: str,
    *,
    repo: Path | None = None,
    run_id: str | None = None,
    limit: int | None = None,
) -> list[ReportIndexEntry]:
    root = repo or repo_root()
    directory = report_directory(kind, repo=root)
    if not directory.exists():
        return []

    normalized_run_id = run_id.strip() if isinstance(run_id, str) and run_id.strip() else None
    entries: list[tuple[tuple[str, float, str], ReportIndexEntry]] = []

    for path in directory.iterdir():
        if not path.is_file() or path.is_symlink() or _is_temporary_report(path):
            continue

        payload = _load_json(path)
        if payload is None:
            continue

        payload_run_id = _payload_run_id(payload)
        if normalized_run_id is not None and payload_run_id != normalized_run_id:
            continue

        entries.append(
            (
                _sort_key(path, payload),
                ReportIndexEntry(
                    kind=kind,
                    relative_path=path.relative_to(root).as_posix(),
                    view_path=path.relative_to(root / "reports").as_posix(),
                    filename=path.name,
                    mtime=path.stat().st_mtime,
                    timestamp=_parse_payload_timestamp(payload) or _parse_filename_timestamp(path),
                    run_id=payload_run_id,
                    payload=payload,
                ),
            )
        )

    entries.sort(key=lambda item: item[0], reverse=True)
    result = [entry for _, entry in entries]
    if limit is not None:
        return result[: max(limit, 0)]
    return result


def latest_report(
    kind: str,
    *,
    repo: Path | None = None,
    run_id: str | None = None,
) -> ReportIndexEntry | None:
    reports = list_reports(kind, repo=repo, run_id=run_id, limit=1)
    return reports[0] if reports else None


def latest_report_for_project(
    kind: str,
    *,
    project_name: str,
    repo: Path | None = None,
) -> ReportIndexEntry | None:
    normalized_project = project_name.strip()
    if not normalized_project:
        return None

    for entry in list_reports(kind, repo=repo):
        payload_project_name = str(entry.payload.get("project_name", "")).strip()
        if payload_project_name == normalized_project:
            return entry
    return None


def latest_report_among(
    kinds: list[str],
    *,
    repo: Path | None = None,
    run_id: str | None = None,
) -> ReportIndexEntry | None:
    for kind in kinds:
        entry = latest_report(kind, repo=repo, run_id=run_id)
        if entry is not None:
            return entry
    return None
