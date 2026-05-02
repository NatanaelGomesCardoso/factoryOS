from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_context_capsule import create_capsule
from app.codex_capsule_execution import (
    run_codex_capsule_diff,
    run_codex_capsule_export_plan,
    run_codex_capsule_run,
    run_codex_capsule_status,
)
from app.task_runner import TaskRunnerError

MVP_CAPSULE_BUILD_CANARY_VERSION = "v0"
MVP_CAPSULE_BUILD_CANARY_REPORTS_DIR = "mvp-capsule-build-canaries"
MVP_CAPSULE_BUILD_CANARY_PROMPT_DIR = "mvp-capsule-build-canary-prompts"
MVP_CAPSULE_CANARY_FILE = "mvp-build-canary.txt"
MVP_CAPSULE_MODE = "ultra_slim_min"


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, *, max_length: int = 64) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:max_length] or "mvp-capsule-build-canary"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return path.with_name(f"{path.name}-{secrets.token_hex(3)}")


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
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


def _resolve_report_path(repo: Path, report_path: str | Path) -> Path:
    candidate = Path(report_path)
    if not candidate.is_absolute():
        candidate = (repo / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise TaskRunnerError(f"report inexistente: {candidate}")
    if not candidate.is_file() or candidate.is_symlink():
        raise TaskRunnerError(f"report inválido: {candidate}")
    try:
        candidate.relative_to(repo.resolve())
    except ValueError as exc:
        raise TaskRunnerError("report precisa ficar dentro do repo.") from exc
    return candidate


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.name}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")
    return payload


def _report_path(repo: Path, project_name: str) -> Path:
    return _unique_path(repo / "reports" / MVP_CAPSULE_BUILD_CANARY_REPORTS_DIR / f"{_timestamp()}-{_slugify(project_name)}.json")


def _prompt_path(repo: Path, project_name: str) -> Path:
    return _unique_path(repo / "reports" / MVP_CAPSULE_BUILD_CANARY_PROMPT_DIR / f"{_timestamp()}-{_slugify(project_name)}.md")


def _build_prompt_text(*, project_name: str, build_plan_report: str, capsule_path: str) -> str:
    return "\n".join(
        [
            "Você está dentro de uma cápsula FactoryOS isolada.",
            "Execute apenas um canary mínimo de build e não altere o repo real.",
            f"project={project_name}",
            f"build_plan_report={build_plan_report}",
            f"capsule_path={capsule_path}",
            "",
            "Faça somente isto:",
            f"- manter apenas `{MVP_CAPSULE_CANARY_FILE}` como marcador seguro já criado",
            "- não editar nenhum outro arquivo",
            "- não fazer push, pull, fetch, rebase ou deploy",
            "- não usar API paga",
            "- não tocar em secrets",
            "- manter a saída compacta",
            "Final reply exactly: OK",
        ]
    ).strip() + "\n"


def _summary_from_status(status_report: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    changed_files = [str(item) for item in status_report.get("changed_files", []) if str(item).strip()]
    disallowed_files = [str(item) for item in status_report.get("disallowed_files", []) if str(item).strip()]
    warnings = [str(item) for item in status_report.get("warnings", []) if str(item).strip()]
    return changed_files, disallowed_files, warnings


def run_mvp_capsule_build_canary(
    *,
    build_plan: str | Path,
    dry_run: bool,
    execute_canary: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    if dry_run == execute_canary:
        raise TaskRunnerError("informe exatamente um de --dry-run ou --execute-canary.")

    build_plan_path = _resolve_report_path(repo, build_plan)
    build_plan_payload = _load_json(build_plan_path)
    project_name = str(build_plan_payload.get("project_name", "")).strip()
    if not project_name:
        raise TaskRunnerError("build plan sem project_name.")

    report_path = _report_path(repo, project_name)
    created_at = _now_iso()

    if dry_run:
        report = {
            "ok": True,
            "mvp_capsule_build_canary_version": MVP_CAPSULE_BUILD_CANARY_VERSION,
            "project_name": project_name,
            "build_plan_report": build_plan_path.relative_to(repo).as_posix(),
            "build_plan_report_absolute": str(build_plan_path),
            "dry_run": True,
            "execute_canary": False,
            "executed_live": False,
            "capsule_path": "",
            "capsule_mode": MVP_CAPSULE_MODE,
            "prompt_path": "",
            "prompt_bytes": 0,
            "execution_report_path": "",
            "diff_report_path": "",
            "export_plan_report_path": "",
            "status_report_path": "",
            "changed_files": [],
            "disallowed_files": [],
            "no_push": True,
            "no_deploy": True,
            "no_paid_api": True,
            "no_secrets": True,
            "report_path": str(report_path.relative_to(repo).as_posix()),
            "created_at": created_at,
            "finished_at": _now_iso(),
            "warnings": [],
            "blockers": [],
        }
        _write_json_atomic(report_path, report)
        return report

    capsule_result = create_capsule(
        label=f"{_slugify(project_name)}-build-canary",
        source_root=repo,
        include_paths=[],
        use_latest_digest=False,
        max_context_bytes=4 * 1024,
        capsule_mode=MVP_CAPSULE_MODE,
        allowed_write_paths=[MVP_CAPSULE_CANARY_FILE],
        allow_empty_context=True,
        repo=repo,
    )
    capsule_path = str(capsule_result["capsule_path"])

    prompt_path = _prompt_path(repo, project_name)
    prompt_text = _build_prompt_text(
        project_name=project_name,
        build_plan_report=build_plan_path.relative_to(repo).as_posix(),
        capsule_path=capsule_path,
    )
    _write_text_atomic(prompt_path, prompt_text)

    canary_path = Path(capsule_path) / MVP_CAPSULE_CANARY_FILE
    canary_text = "\n".join(
        [
            f"OK project={project_name}",
            f"build_plan={build_plan_path.relative_to(repo).as_posix()}",
            "scope=build-canary",
        ]
    ).strip() + "\n"
    _write_text_atomic(canary_path, canary_text)

    capsule_run = run_codex_capsule_run(
        capsule=capsule_path,
        prompt_file=prompt_path,
        label=f"{_slugify(project_name)}-build-canary",
        model="gpt-5.4-mini",
        reasoning="low",
        sandbox="workspace-write",
        execute=True,
        repo=repo,
        timeout_seconds=180,
    )
    _write_text_atomic(canary_path, canary_text)
    diff_report = run_codex_capsule_diff(capsule=capsule_path, repo=repo)
    export_plan = run_codex_capsule_export_plan(capsule=capsule_path, source_root=repo, repo=repo)
    status_report = run_codex_capsule_status(
        execution_report=capsule_run["report_path"],
        export_plan=export_plan["report_path"],
        diff_report=diff_report["report_path"],
        repo=repo,
    )

    changed_files, disallowed_files, warnings = _summary_from_status(status_report)
    export_changed_files = [str(item) for item in export_plan.get("changed_files", []) if str(item).strip()]
    export_changed_count = int(export_plan.get("changed_files_count") or len(export_changed_files))
    blockers = [str(item) for item in status_report.get("blockers", []) if str(item).strip()]
    report = {
        "ok": bool(status_report.get("capsule_run_ok", False)),
        "mvp_capsule_build_canary_version": MVP_CAPSULE_BUILD_CANARY_VERSION,
        "project_name": project_name,
        "build_plan_report": build_plan_path.relative_to(repo).as_posix(),
        "build_plan_report_absolute": str(build_plan_path),
        "dry_run": False,
        "execute_canary": True,
        "executed_live": False,
        "capsule_mode": MVP_CAPSULE_MODE,
        "capsule_path": capsule_path,
        "prompt_path": str(prompt_path.relative_to(repo).as_posix()),
        "prompt_bytes": len(prompt_text.encode("utf-8")),
        "capsule": capsule_result,
        "capsule_run": capsule_run,
        "diff_report": diff_report,
        "export_plan": export_plan,
        "status_report": status_report,
        "execution_report_path": str(capsule_run.get("report_path", "")),
        "diff_report_path": str(diff_report.get("report_path", "")),
        "export_plan_report_path": str(export_plan.get("report_path", "")),
        "status_report_path": str(status_report.get("report_path", "")),
        "changed_files": export_changed_files,
        "changed_files_count": export_changed_count,
        "disallowed_files": disallowed_files,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": created_at,
        "finished_at": _now_iso(),
        "warnings": warnings,
        "blockers": blockers,
    }
    _write_json_atomic(report_path, report)
    return report
