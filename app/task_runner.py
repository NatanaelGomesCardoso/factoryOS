from __future__ import annotations

import json
import re
import secrets
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.evaluator import evaluate_signals
from app.routing_contracts import ROUTING_CONTRACT_FIELD_NAMES, normalize_routing_contract

TASK_STATUSES = ("pending", "running", "done", "failed")
TASK_RISKS = ("low", "medium", "high")
TASK_EXECUTORS = ("manual", "local", "codex")
TASK_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVALUATION_REPORTS_DIR = "task-evaluations"


class TaskRunnerError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TaskRecord:
    id: str
    title: str
    description: str
    status: str
    risk: str
    executor: str
    created_at: str
    updated_at: str
    notes: list[str]
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


def tasks_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "tasks"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _slugify(text: str, max_length: int = 48) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-+", "-", ascii_text).strip("-")
    ascii_text = ascii_text[:max_length].strip("-")
    return ascii_text or "task"


def _task_id_from(title: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    slug = _slugify(title, max_length=40)
    suffix = secrets.token_hex(3)
    task_id = f"{timestamp}-{slug}-{suffix}"
    return _validate_task_id(task_id)


def _ensure_task_root(repo: Path | None = None) -> Path:
    root = tasks_root(repo)
    root.mkdir(parents=True, exist_ok=True)
    for status in TASK_STATUSES:
        (root / status).mkdir(parents=True, exist_ok=True)
    return root


def _validate_task_id(task_id: str) -> str:
    if not isinstance(task_id, str):
        raise TaskRunnerError("id da task inválido.")

    normalized = task_id.strip()
    if not normalized:
        raise TaskRunnerError("id da task vazio.")

    if "/" in normalized or "\\" in normalized:
        raise TaskRunnerError("path traversal não permitido no id da task.")

    if not TASK_ID_PATTERN.fullmatch(normalized):
        raise TaskRunnerError("id da task contém caracteres inválidos.")

    return normalized


def _validate_status(status: str) -> str:
    if status not in TASK_STATUSES:
        raise TaskRunnerError(f"status inválido: {status}")
    return status


def _validate_risk(risk: str) -> str:
    if risk not in TASK_RISKS:
        raise TaskRunnerError(f"risk inválido: {risk}")
    return risk


def _validate_executor(executor: str) -> str:
    if executor not in TASK_EXECUTORS:
        raise TaskRunnerError(f"executor inválido: {executor}")
    return executor


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


def _task_filename(task_id: str) -> str:
    return f"{task_id}.json"


def _task_path(repo: Path, status: str, task_id: str) -> Path:
    return repo / status / _task_filename(task_id)


def _all_task_paths(repo: Path, task_id: str) -> list[Path]:
    filename = _task_filename(task_id)
    matches: list[Path] = []
    for status in TASK_STATUSES:
        candidate = repo / status / filename
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
        raise TaskRunnerError("task JSON precisa ser um objeto.")

    return payload


def _validate_payload(payload: dict[str, Any], *, source_path: Path | None = None) -> TaskRecord:
    required_fields = {
        "id",
        "title",
        "description",
        "status",
        "risk",
        "executor",
        "created_at",
        "updated_at",
        "notes",
    }
    missing = required_fields - payload.keys()
    if missing:
        raise TaskRunnerError(f"task JSON incompleto; faltam: {', '.join(sorted(missing))}")

    extra = set(payload.keys()) - required_fields - set(ROUTING_CONTRACT_FIELD_NAMES)
    if extra:
        raise TaskRunnerError(f"task JSON tem campos extras: {', '.join(sorted(extra))}")

    task_id = _validate_task_id(str(payload["id"]))
    title = str(payload["title"]).strip()
    description = str(payload["description"]).strip()
    status = _validate_status(str(payload["status"]))
    risk = _validate_risk(str(payload["risk"]))
    executor = _validate_executor(str(payload["executor"]))
    created_at = str(payload["created_at"]).strip()
    updated_at = str(payload["updated_at"]).strip()
    notes = _validate_notes(payload["notes"])
    try:
        routing_contract = normalize_routing_contract(payload)
    except ValueError as exc:
        raise TaskRunnerError(str(exc)) from exc

    if not title:
        raise TaskRunnerError("title da task não pode ficar vazio.")
    if not description:
        raise TaskRunnerError("description da task não pode ficar vazio.")
    if not created_at or not updated_at:
        raise TaskRunnerError("timestamps da task não podem ficar vazios.")

    if source_path is not None and source_path.stem != task_id:
        raise TaskRunnerError("arquivo e id da task não batem.")

    return TaskRecord(
        id=task_id,
        title=title,
        description=description,
        status=status,
        risk=risk,
        executor=executor,
        created_at=created_at,
        updated_at=updated_at,
        notes=notes,
        **routing_contract,
    )


def _record_to_payload(record: TaskRecord) -> dict[str, Any]:
    return asdict(record)


def _repo_relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root.parent).as_posix()


def _repo_relative_path_from_repo(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def _ensure_no_symlink_ancestors(path: Path, *, stop_at: Path) -> None:
    current = path.parent
    while True:
        if current.is_symlink():
            raise TaskRunnerError(f"symlink não permitido: {current.name}")
        if current == stop_at:
            return
        if current.parent == current:
            return
        current = current.parent


def _report_root(repo: Path) -> Path:
    return repo / "reports"


def _task_evaluation_root(repo: Path) -> Path:
    return _report_root(repo) / EVALUATION_REPORTS_DIR


def _task_evaluation_report_path(repo: Path, task_id: str) -> Path:
    return _task_evaluation_root(repo) / _task_filename(task_id)


def _build_evaluation_inputs(record: TaskRecord) -> dict[str, Any]:
    source_status = record.status
    high_risk = record.risk == "high" or record.executor == "codex"
    task_notes = " | ".join(record.notes) if record.notes else ""

    return {
        "python_ok": source_status != "failed",
        "json_ok": True,
        "browser_ok": source_status != "failed",
        "security_ok": True,
        "high_risk": high_risk,
        "git_clean": source_status != "failed",
        "git_expected_dirty": source_status == "running",
        "notes": "; ".join(
            part
            for part in [
                f"source_status={source_status}",
                f"task_risk={record.risk}",
                f"task_executor={record.executor}",
                f"task_notes={task_notes}" if task_notes else "",
            ]
            if part
        ),
    }


def _write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")

    _ensure_no_symlink_ancestors(path, stop_at=path.parents[2])
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


def _safe_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise TaskRunnerError(f"task já existe em {path.as_posix()}.")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_json_with_validation(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        written_payload = _load_json_file(temp_path)
        _validate_payload(written_payload, source_path=path)
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _iter_tasks(repo: Path, status: str) -> list[tuple[Path, TaskRecord]]:
    directory = repo / status
    if not directory.exists():
        return []

    tasks: list[tuple[Path, TaskRecord]] = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name.lower()):
        if path.is_symlink():
            raise TaskRunnerError(f"symlink não permitido: {path.name}")
        payload = _load_json_file(path)
        record = _validate_payload(payload, source_path=path)
        tasks.append((path, record))

    return tasks


def _find_task(repo: Path, task_id: str) -> tuple[Path, TaskRecord]:
    normalized_id = _validate_task_id(task_id)
    matches = _all_task_paths(repo, normalized_id)

    if not matches:
        raise TaskRunnerError(f"task inexistente: {normalized_id}")

    if len(matches) > 1:
        raise TaskRunnerError(f"task duplicada encontrada para id {normalized_id}")

    source_path = matches[0]
    record = _load_task_from_source(source_path)

    return source_path, record


def _load_task_from_source(source_path: Path) -> TaskRecord:
    if source_path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {source_path.name}")

    payload = _load_json_file(source_path)
    record = _validate_payload(payload, source_path=source_path)

    if source_path.parent.name != record.status:
        raise TaskRunnerError(
            f"status no arquivo ({record.status}) não corresponde ao diretório ({source_path.parent.name})."
        )

    return record


def _ensure_unique_task_id(repo: Path, task_id: str) -> None:
    if _all_task_paths(repo, task_id):
        raise TaskRunnerError(f"task já existe: {task_id}")


def create_task(
    title: str,
    description: str,
    risk: str,
    executor: str,
    routing_contract: dict[str, Any] | None = None,
    *,
    repo: Path | None = None,
) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    normalized_title = title.strip()
    normalized_description = description.strip()
    normalized_risk = _validate_risk(risk)
    normalized_executor = _validate_executor(executor)

    if not normalized_title:
        raise TaskRunnerError("title da task não pode ficar vazio.")
    if not normalized_description:
        raise TaskRunnerError("description da task não pode ficar vazia.")

    routing_contract = dict(routing_contract or {})
    try:
        normalized_routing_contract = normalize_routing_contract(routing_contract)
    except ValueError as exc:
        raise TaskRunnerError(str(exc)) from exc

    task_id = _task_id_from(normalized_title)
    _ensure_unique_task_id(root, task_id)

    now = _now_iso()
    record = TaskRecord(
        id=task_id,
        title=normalized_title,
        description=normalized_description,
        status="pending",
        risk=normalized_risk,
        executor=normalized_executor,
        created_at=now,
        updated_at=now,
        notes=[],
        **normalized_routing_contract,
    )
    payload = _record_to_payload(record)

    destination = _task_path(root, "pending", task_id)
    _safe_write_json(destination, payload)

    return {
        "ok": True,
        "action": "created",
        "task": payload,
        "path": _repo_relative_path(root, destination),
    }


def _transition_task(
    task_id: str,
    *,
    from_statuses: Iterable[str],
    to_status: str,
    repo: Path | None = None,
) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    normalized_id = _validate_task_id(task_id)
    to_status = _validate_status(to_status)
    allowed_sources = tuple(from_statuses)
    if not allowed_sources:
        raise TaskRunnerError("nenhum status de origem informado.")

    matches: list[tuple[str, Path]] = []
    for status in allowed_sources:
        candidate = _task_path(root, status, normalized_id)
        if candidate.exists():
            matches.append((status, candidate))

    if not matches:
        raise TaskRunnerError(
            f"task {normalized_id} não encontrada nos status: {', '.join(allowed_sources)}"
        )

    if len(matches) > 1:
        raise TaskRunnerError(f"task duplicada encontrada para id {normalized_id}")

    from_status, source_path = matches[0]
    record = _load_task_from_source(source_path)

    if record.status != from_status:
        raise TaskRunnerError(
            f"status no arquivo ({record.status}) não corresponde ao diretório ({from_status})."
        )

    destination = _task_path(root, to_status, normalized_id)
    if destination.exists():
        raise TaskRunnerError(f"task já existe no destino {to_status}: {normalized_id}")

    updated = TaskRecord(
        id=record.id,
        title=record.title,
        description=record.description,
        status=to_status,
        risk=record.risk,
        executor=record.executor,
        created_at=record.created_at,
        updated_at=_now_iso(),
        notes=record.notes,
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
        "task": updated_payload,
        "source_path": _repo_relative_path(root, source_path),
        "path": _repo_relative_path(root, destination),
    }


def start_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    return _transition_task(task_id, from_statuses=("pending",), to_status="running", repo=repo)


def finish_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    return _transition_task(task_id, from_statuses=("running",), to_status="done", repo=repo)


def fail_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    return _transition_task(
        task_id,
        from_statuses=("pending", "running"),
        to_status="failed",
        repo=repo,
    )


def _task_public_view(record: TaskRecord, *, path: Path | None = None) -> dict[str, Any]:
    payload = _record_to_payload(record)
    if path is not None:
        payload["path"] = path.as_posix()
    return payload


def show_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    source_path, record = _find_task(root, task_id)
    return {
        "ok": True,
        "action": "show",
        "task": _task_public_view(record, path=source_path.relative_to(root.parent)),
        "path": _repo_relative_path(root, source_path),
    }


def evaluate_task(task_id: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    source_path, record = _find_task(root, task_id)
    repo_root_path = root.parent
    report_path = _task_evaluation_report_path(repo_root_path, record.id)

    signals = _build_evaluation_inputs(record)
    evaluation = evaluate_signals(signals)

    report = {
        "task_id": record.id,
        "task_title": record.title,
        "task_path": _repo_relative_path_from_repo(repo_root_path, source_path),
        "report_path": _repo_relative_path_from_repo(repo_root_path, report_path),
        "source_status": record.status,
        "evaluated_at": _now_iso(),
        "evaluator": "app.evaluator.evaluate_signals",
        "decision": evaluation["decision"],
        "risk": evaluation["risk"],
        "reason": evaluation["reason"],
        "next_action": evaluation["next_action"],
        "failed_checks": evaluation["failed_checks"],
        "inputs": evaluation["inputs"],
    }

    _write_json_atomically(report_path, report)

    return report


def note_task(task_id: str, note: str, *, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    normalized_note = note.strip()
    if not normalized_note:
        raise TaskRunnerError("nota da task não pode ficar vazia.")

    source_path, record = _find_task(root, task_id)
    current_status = source_path.parent.name
    if record.status != current_status:
        raise TaskRunnerError(
            f"status no arquivo ({record.status}) não corresponde ao diretório ({current_status})."
        )

    updated = TaskRecord(
        id=record.id,
        title=record.title,
        description=record.description,
        status=record.status,
        risk=record.risk,
        executor=record.executor,
        created_at=record.created_at,
        updated_at=_now_iso(),
        notes=[*record.notes, normalized_note],
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
    _write_json_with_validation(source_path, updated_payload)

    return {
        "ok": True,
        "action": "noted",
        "note": normalized_note,
        "task": updated_payload,
        "path": _repo_relative_path(root, source_path),
    }


def list_tasks(*, repo: Path | None = None) -> dict[str, Any]:
    root = _ensure_task_root(repo)
    groups: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for status in TASK_STATUSES:
        entries = _iter_tasks(root, status)
        counts[status] = len(entries)
        groups.append(
            {
                "status": status,
                "count": len(entries),
                "tasks": [
                    _task_public_view(record, path=path.relative_to(root.parent))
                    for path, record in entries
                ],
            }
        )

    return {
        "ok": True,
        "counts": counts,
        "groups": groups,
    }


def task_summary_counts(repo: Path | None = None) -> dict[str, int]:
    root = _ensure_task_root(repo)
    counts: dict[str, int] = {}
    for status in TASK_STATUSES:
        counts[status] = len(
            [
                path
                for path in (root / status).glob("*.json")
                if path.is_file() and not path.is_symlink()
            ]
        )
    return counts
