from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

SOURCE_REPORT_DIR = "expanded-bounded-live-canary"
EVALUATION_REPORTS_DIR = "post-expansion-evaluations"
ROLLBACK_REPORTS_DIR = "post-expansion-rollback-plans"
TOKEN_SUMMARY_REASONABLE_LIMIT = 50000
MAX_ALLOWED_STEPS = 6
MAX_ALLOWED_MINUTES = 30


@dataclass(frozen=True, slots=True)
class LatestPostExpansionEvaluationResult:
    available: bool
    decision: str
    final_decision: str
    run_id: str
    source_report: str
    report_path: str
    view_path: str | None
    checks: dict[str, bool]
    reasons: list[str]
    token_summary: dict[str, Any]
    created_at: str


@dataclass(frozen=True, slots=True)
class LatestPostExpansionRollbackPlanResult:
    available: bool
    decision: str
    final_decision: str
    run_id: str
    source_report: str
    report_path: str
    view_path: str | None
    rollback_files: list[str]
    safe_to_apply: bool
    human_review_required: bool
    reasons: list[str]
    created_at: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _reports_root(repo: Path | None = None) -> Path:
    return (repo or repo_root()) / "reports"


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink não permitido: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{datetime.now().timestamp():.0f}.tmp")
    try:
        with temp_path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskRunnerError(f"JSON inválido em {path.as_posix()}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise TaskRunnerError("report precisa ser um objeto JSON.")
    return payload


def _safe_relative_path(value: str, *, prefix: str, suffix: str) -> bool:
    if not value or Path(value).is_absolute():
        return False
    candidate = Path(value)
    if any(part in {".", ".."} for part in candidate.parts):
        return False
    return candidate.as_posix().startswith(prefix) and candidate.suffix == suffix


def _load_source_report(repo: Path, report_path: str) -> tuple[Path, dict[str, Any]]:
    normalized = report_path.strip()
    if not normalized:
        raise TaskRunnerError("report path vazio.")
    if Path(normalized).is_absolute():
        raise TaskRunnerError("path absoluto não permitido no report.")
    candidate = Path(normalized)
    if any(part in {".", ".."} for part in candidate.parts):
        raise TaskRunnerError("path traversal não permitido no report.")
    if not candidate.as_posix().startswith(f"reports/{SOURCE_REPORT_DIR}/"):
        raise TaskRunnerError("report precisa apontar para reports/expanded-bounded-live-canary/.")
    if candidate.suffix != ".json":
        raise TaskRunnerError("report precisa terminar em .json.")

    source_path = repo / candidate
    if not source_path.exists():
        raise TaskRunnerError("report informado não existe.")
    if not source_path.is_file() or source_path.is_symlink():
        raise TaskRunnerError("report inválido.")

    return source_path, _load_json_file(source_path)


def _infer_run_id(payload: dict[str, Any], source_report: Path) -> str:
    for key in ("canary_run_id", "run_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    stem = source_report.stem
    if "-" in stem:
        return stem.split("-", 1)[1]
    return stem


def _duration_seconds(payload: dict[str, Any]) -> float | None:
    explicit = payload.get("duration_seconds")
    if isinstance(explicit, (int, float)):
        return float(explicit)

    created_at = payload.get("created_at")
    finished_at = payload.get("finished_at")
    if isinstance(created_at, str) and isinstance(finished_at, str) and created_at.strip() and finished_at.strip():
        try:
            created = datetime.fromisoformat(created_at)
            finished = datetime.fromisoformat(finished_at)
        except ValueError:
            return None
        return max(0.0, (finished - created).total_seconds())
    return None


def _token_summary_ok(token_summary: dict[str, Any]) -> bool:
    tokens_used = token_summary.get("tokens_used")
    if not isinstance(tokens_used, int):
        return False
    if tokens_used > TOKEN_SUMMARY_REASONABLE_LIMIT:
        return False
    warnings = token_summary.get("warnings", [])
    return isinstance(warnings, list)


def _attempt_paths_ok(payload: dict[str, Any]) -> bool:
    attempt_id = str(payload.get("attempt_id", "")).strip()
    if not attempt_id:
        return True
    prefix = f"reports/{SOURCE_REPORT_DIR}/attempts/{attempt_id}/"
    paths: list[str] = []
    for key in ("allowed_files", "changed_files"):
        value = payload.get(key, [])
        if not isinstance(value, list):
            return False
        paths.extend(str(item) for item in value if isinstance(item, str) and item.strip())
    return all(_safe_relative_path(path, prefix=prefix, suffix=".txt") for path in paths)


def _local_checks(payload: dict[str, Any]) -> tuple[dict[str, bool], list[str], str]:
    checks = {
        "json_valid": True,
        "executed_live_true": bool(payload.get("executed_live", False)),
        "steps_completed_le_6": int(payload.get("steps_completed", 0) or 0) <= MAX_ALLOWED_STEPS,
        "max_steps_le_6": int(payload.get("max_steps", 0) or 0) <= MAX_ALLOWED_STEPS,
        "max_minutes_le_30": int(payload.get("max_minutes", 0) or 0) <= MAX_ALLOWED_MINUTES,
        "disallowed_files_empty": not bool(payload.get("disallowed_files", [])),
        "master_unchanged": str(payload.get("master_head_before", "")).strip() == str(payload.get("master_head_after", "")).strip(),
        "workspace_unchanged": str(payload.get("workspace_head_before", "")).strip() == str(payload.get("workspace_head_after", "")).strip(),
        "no_push": bool(payload.get("no_push", False)),
        "no_deploy": bool(payload.get("no_deploy", False)),
        "no_paid_api": bool(payload.get("no_paid_api", False)),
        "no_secrets": bool(payload.get("no_secrets", False)),
        "token_summary_reasonable": _token_summary_ok(payload.get("token_summary", {})),
        "final_decision_accepts_review": str(payload.get("final_decision", "")).strip() in {"passed", "needs_review"},
        "attempt_paths_valid": _attempt_paths_ok(payload),
    }
    reasons: list[str] = []

    duration_seconds = _duration_seconds(payload)
    if duration_seconds is not None:
        checks["duration_le_30m"] = duration_seconds <= (MAX_ALLOWED_MINUTES * 60)
    else:
        checks["duration_le_30m"] = False
        reasons.append("duration_seconds ausente ou inválido.")

    if not checks["executed_live_true"]:
        reasons.append("executed_live precisa ser true.")
    if not checks["steps_completed_le_6"]:
        reasons.append("steps_completed precisa ser <= 6.")
    if not checks["max_steps_le_6"]:
        reasons.append("max_steps precisa ser <= 6.")
    if not checks["max_minutes_le_30"]:
        reasons.append("max_minutes precisa ser <= 30.")
    if not checks["disallowed_files_empty"]:
        reasons.append("disallowed_files precisa estar vazio.")
    if not checks["master_unchanged"]:
        reasons.append("master_head_before e master_head_after precisam ser iguais.")
    if not checks["workspace_unchanged"]:
        reasons.append("workspace_head_before e workspace_head_after precisam ser iguais.")
    if not checks["no_push"]:
        reasons.append("no_push precisa ser true.")
    if not checks["no_deploy"]:
        reasons.append("no_deploy precisa ser true.")
    if not checks["no_paid_api"]:
        reasons.append("no_paid_api precisa ser true.")
    if not checks["no_secrets"]:
        reasons.append("no_secrets precisa ser true.")
    if not checks["token_summary_reasonable"]:
        reasons.append("token_summary não está em um limite razoável.")
    if not checks["attempt_paths_valid"]:
        reasons.append("allowed_files/changed_files precisam apontar para attempts/<attempt_id>/step-N.txt.")
    final_decision_value = str(payload.get("final_decision", "")).strip()
    if final_decision_value not in {"passed", "needs_review"}:
        reasons.append("final_decision não é passed nem needs_review.")

    hard_fail_checks = {
        key: value
        for key, value in checks.items()
        if key not in {"token_summary_reasonable", "final_decision_accepts_review"}
    }
    if all(hard_fail_checks.values()) and checks["token_summary_reasonable"] and final_decision_value == "passed":
        decision = "passed"
    elif all(hard_fail_checks.values()) and final_decision_value in {"passed", "needs_review"}:
        decision = "needs_review"
    else:
        decision = "failed"
    return checks, reasons, decision


def evaluate_post_expansion_canary_report(
    *,
    report_path: str,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    source_path, payload = _load_source_report(repo, report_path)
    run_id = _infer_run_id(payload, source_path)
    created_at = _now_iso()
    checks, reasons, decision = _local_checks(payload)
    token_summary = payload.get("token_summary", {})
    report = {
        "ok": True,
        "run_id": run_id,
        "source_report": source_path.relative_to(repo).as_posix(),
        "decision": decision,
        "final_decision": decision,
        "checks": checks,
        "reasons": reasons,
        "token_summary": token_summary if isinstance(token_summary, dict) else {},
        "duration_seconds": _duration_seconds(payload),
        "created_at": created_at,
    }
    evaluation_path = _reports_root(repo) / EVALUATION_REPORTS_DIR / f"{_timestamp()}-{run_id}.json"
    report["report_path"] = evaluation_path.relative_to(repo).as_posix()
    _write_json_atomic(evaluation_path, report)
    return report


def run_post_expansion_rollback_plan(
    *,
    report: str,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    if not dry_run:
        raise TaskRunnerError("post-expansion rollback plan aceita somente --dry-run.")

    source_path, payload = _load_source_report(repo, report)
    run_id = _infer_run_id(payload, source_path)
    created_at = _now_iso()
    rollback_files = [str(item) for item in payload.get("changed_files", []) if isinstance(item, str) and item.strip()]
    if not rollback_files:
        rollback_files = [str(item) for item in payload.get("allowed_files", []) if isinstance(item, str) and item.strip()]

    report_payload = {
        "ok": True,
        "run_id": run_id,
        "source_report": source_path.relative_to(repo).as_posix(),
        "decision": "rollback_plan_ready",
        "final_decision": "rollback_plan_ready",
        "rollback_files": rollback_files,
        "safe_to_apply": False,
        "human_review_required": True,
        "reasons": [
            "rollback não é aplicado automaticamente.",
            "plano gerado apenas em dry-run.",
        ],
        "created_at": created_at,
    }
    rollback_path = _reports_root(repo) / ROLLBACK_REPORTS_DIR / f"{_timestamp()}-{run_id}.json"
    report_payload["report_path"] = rollback_path.relative_to(repo).as_posix()
    _write_json_atomic(rollback_path, report_payload)
    return report_payload


def load_latest_post_expansion_evaluation_result(repo: Path) -> LatestPostExpansionEvaluationResult:
    latest_dir = _reports_root(repo) / EVALUATION_REPORTS_DIR
    if not latest_dir.exists():
        return LatestPostExpansionEvaluationResult(
            available=False,
            decision="unknown",
            final_decision="unknown",
            run_id="",
            source_report="",
            report_path="",
            view_path=None,
            checks={},
            reasons=[],
            token_summary={},
            created_at="",
        )

    candidates = [path for path in latest_dir.glob("*.json") if path.is_file() and not path.is_symlink()]
    if not candidates:
        return LatestPostExpansionEvaluationResult(
            available=False,
            decision="unknown",
            final_decision="unknown",
            run_id="",
            source_report="",
            report_path="",
            view_path=None,
            checks={},
            reasons=[],
            token_summary={},
            created_at="",
        )

    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    payload = _load_json_file(latest)
    return LatestPostExpansionEvaluationResult(
        available=True,
        decision=str(payload.get("decision", "")).strip(),
        final_decision=str(payload.get("final_decision", "")).strip(),
        run_id=str(payload.get("run_id", "")).strip(),
        source_report=str(payload.get("source_report", "")).strip(),
        report_path=str(payload.get("report_path", "")).strip(),
        view_path=latest.relative_to(repo / "reports").as_posix() if latest.exists() else None,
        checks={str(key): bool(value) for key, value in payload.get("checks", {}).items()} if isinstance(payload.get("checks", {}), dict) else {},
        reasons=[str(item) for item in payload.get("reasons", []) if str(item).strip()],
        token_summary=dict(payload.get("token_summary", {})) if isinstance(payload.get("token_summary", {}), dict) else {},
        created_at=str(payload.get("created_at", "")).strip(),
    )


def load_latest_post_expansion_rollback_plan_result(repo: Path) -> LatestPostExpansionRollbackPlanResult:
    latest_dir = _reports_root(repo) / ROLLBACK_REPORTS_DIR
    if not latest_dir.exists():
        return LatestPostExpansionRollbackPlanResult(
            available=False,
            decision="unknown",
            final_decision="unknown",
            run_id="",
            source_report="",
            report_path="",
            view_path=None,
            rollback_files=[],
            safe_to_apply=False,
            human_review_required=True,
            reasons=[],
            created_at="",
        )

    candidates = [path for path in latest_dir.glob("*.json") if path.is_file() and not path.is_symlink()]
    if not candidates:
        return LatestPostExpansionRollbackPlanResult(
            available=False,
            decision="unknown",
            final_decision="unknown",
            run_id="",
            source_report="",
            report_path="",
            view_path=None,
            rollback_files=[],
            safe_to_apply=False,
            human_review_required=True,
            reasons=[],
            created_at="",
        )

    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    payload = _load_json_file(latest)
    return LatestPostExpansionRollbackPlanResult(
        available=True,
        decision=str(payload.get("decision", "")).strip(),
        final_decision=str(payload.get("final_decision", "")).strip(),
        run_id=str(payload.get("run_id", "")).strip(),
        source_report=str(payload.get("source_report", "")).strip(),
        report_path=str(payload.get("report_path", "")).strip(),
        view_path=latest.relative_to(repo / "reports").as_posix(),
        rollback_files=[str(item) for item in payload.get("rollback_files", []) if str(item).strip()],
        safe_to_apply=bool(payload.get("safe_to_apply", False)),
        human_review_required=bool(payload.get("human_review_required", True)),
        reasons=[str(item) for item in payload.get("reasons", []) if str(item).strip()],
        created_at=str(payload.get("created_at", "")).strip(),
    )
