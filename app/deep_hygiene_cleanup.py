from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.deep_hygiene_audit import run_deep_hygiene_audit
from app.task_runner import TaskRunnerError

CLEANUP_VERSION = "v0"
FACTORYOS_ROOT = Path("<FACTORYOS_ROOT>")
FIXTURE_ROOT = Path("<TMP_DIR>/factoryos-cleanup-fixture")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _write_text_atomic(path: Path, text: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            handle.write(text)
            if not text.endswith("\n"):
                handle.write("\n")
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists() or source.is_symlink():
        raise TaskRunnerError("audit/cleanup report inexistente ou symlink não permitido.")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser objeto JSON.")
    return payload


def _is_under(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
    except FileNotFoundError:
        resolved = path.absolute()
        root_resolved = root.absolute()
    return resolved == root_resolved or root_resolved in resolved.parents


def _safe_plan_item(candidate: dict[str, Any], repo: Path) -> tuple[bool, str]:
    path = Path(str(candidate.get("path", "")))
    if candidate.get("classification") != "safe_delete_candidate":
        return False, "classificação não segura"
    if candidate.get("contains_git") or candidate.get("sensitive_name"):
        return False, "git/segredo detectado"
    if _is_under(path, repo):
        return True, "cache/runtime interno do FactoryOS"
    if _is_under(path, FIXTURE_ROOT):
        return True, "fixture sintética controlada"
    return False, "fora da allowlist de aplicação"


def _cleanup_report_path(repo: Path, kind: str) -> Path:
    return repo / "reports" / "deep-hygiene-cleanup-plans" / f"{_timestamp()}-{kind}-{secrets.token_hex(3)}.json"


def _validation_path(repo: Path) -> Path:
    return repo / "reports" / "deep-hygiene-cleanup-validations" / f"{_timestamp()}.json"


def _write_proof(repo: Path, report: dict[str, Any]) -> None:
    lines = [
        "Sprint 080.M.1 safe cleanup apply and final hygiene validation V0 proof",
        f"report_path={report['report_path']}",
        f"dry_run={str(report['dry_run']).lower()}",
        f"applied={str(report['applied']).lower()}",
        f"deleted_count={report['deleted_count']}",
        f"human_review_required={str(report['human_review_required']).lower()}",
        f"safe_to_apply={str(report['safe_to_apply']).lower()}",
        "applied_real=false",
        "no_push=true no_deploy=true no_paid_api=true no_secrets=true",
    ]
    _write_text_atomic(repo / "reports" / "safe-cleanup-apply-final-hygiene-validation-v0-proof.txt", "\n".join(lines) + "\n")


def run_cleanup_plan(*, audit_report: str, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-cleanup-plan V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    audit = _load_json(audit_report)
    planned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for candidate in audit.get("safe_delete_candidates", []):
        ok, reason = _safe_plan_item(dict(candidate), repo)
        item = {
            "path": str(candidate.get("path", "")),
            "reason": reason,
            "size_bytes": int(candidate.get("size_bytes", 0) or 0),
        }
        if ok:
            planned.append(item)
        else:
            skipped.append(item)
    report_path = _cleanup_report_path(repo, "plan")
    safe_to_apply = bool(planned) and not bool(audit.get("include_external"))
    payload = {
        "ok": True,
        "deep_hygiene_cleanup_version": CLEANUP_VERSION,
        "kind": "cleanup_plan",
        "dry_run": True,
        "applied": False,
        "audit_report": str(audit_report),
        "planned_paths": planned,
        "deleted_count": 0,
        "deleted_paths": [],
        "skipped_count": len(skipped) + len(audit.get("needs_review_candidates", [])) + len(audit.get("unsafe_candidates", [])),
        "skipped_paths": skipped,
        "human_review_required": bool(audit.get("human_review_required")) or bool(audit.get("include_external")),
        "safe_to_apply": safe_to_apply,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload


def run_cleanup_apply(*, cleanup_plan: str, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    repo = (repo or repo_root()).resolve()
    plan = _load_json(cleanup_plan)
    if not dry_run and not plan.get("safe_to_apply"):
        raise TaskRunnerError("plano não está seguro para aplicação real.")
    deleted_paths: list[str] = []
    skipped_paths: list[dict[str, Any]] = []
    for item in plan.get("planned_paths", []):
        path = Path(str(item.get("path", "")))
        if not (_is_under(path, repo) or _is_under(path, FIXTURE_ROOT)):
            skipped_paths.append({"path": path.as_posix(), "reason": "fora da allowlist de aplicação"})
            continue
        if dry_run:
            skipped_paths.append({"path": path.as_posix(), "reason": "dry-run não apaga"})
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        deleted_paths.append(path.as_posix())
    report_path = _cleanup_report_path(repo, "apply")
    payload = {
        "ok": True,
        "deep_hygiene_cleanup_version": CLEANUP_VERSION,
        "kind": "cleanup_apply",
        "dry_run": dry_run,
        "applied": not dry_run,
        "cleanup_plan": str(cleanup_plan),
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "skipped_count": len(skipped_paths),
        "skipped_paths": skipped_paths,
        "human_review_required": bool(plan.get("human_review_required")),
        "safe_to_apply": bool(plan.get("safe_to_apply")),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload


def _create_fixture() -> None:
    (FIXTURE_ROOT / "__pycache__").mkdir(parents=True, exist_ok=True)
    (FIXTURE_ROOT / "__pycache__" / "sample.cpython-312.pyc").write_bytes(b"factoryos cleanup fixture\n")
    (FIXTURE_ROOT / "factoryos-temp.log").write_text("fixture\n", encoding="utf-8")


def run_cleanup_validate(*, dry_run: bool, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("factoryos-cleanup-validate V0 exige --dry-run.")
    repo = (repo or repo_root()).resolve()
    _create_fixture()
    audit = run_deep_hygiene_audit(dry_run=True, include_external=True, repo=repo)
    fixture_detected = any(str(item.get("path", "")).startswith(FIXTURE_ROOT.as_posix()) for item in audit.get("candidates", []))
    plan = run_cleanup_plan(audit_report=str(repo / audit["report_path"]), dry_run=True, repo=repo)
    apply_report = run_cleanup_apply(cleanup_plan=str(repo / plan["report_path"]), dry_run=True, repo=repo)
    fixture_still_exists = FIXTURE_ROOT.exists()
    report_path = _validation_path(repo)
    payload = {
        "ok": bool(fixture_detected and fixture_still_exists and apply_report.get("deleted_count") == 0),
        "deep_hygiene_cleanup_version": CLEANUP_VERSION,
        "kind": "cleanup_validation",
        "dry_run": True,
        "applied": False,
        "fixture_root": FIXTURE_ROOT.as_posix(),
        "fixture_detected": fixture_detected,
        "fixture_still_exists": fixture_still_exists,
        "audit_report": audit["report_path"],
        "cleanup_plan_report": plan["report_path"],
        "cleanup_apply_report": apply_report["report_path"],
        "deleted_count": 0,
        "deleted_paths": [],
        "skipped_count": int(apply_report.get("skipped_count", 0)),
        "skipped_paths": apply_report.get("skipped_paths", []),
        "human_review_required": bool(audit.get("human_review_required")),
        "safe_to_apply": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, payload)
    _write_proof(repo, payload)
    return payload
