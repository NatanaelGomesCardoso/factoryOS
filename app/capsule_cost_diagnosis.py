from __future__ import annotations

import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.codex_quiet_runner import count_diff_like_lines
from app.task_runner import TaskRunnerError

CAPSULE_COST_DIAGNOSIS_REPORT_DIR = "capsule-cost-diagnosis"
CAPSULE_COST_DIAGNOSIS_VERSION = "v0"


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return path.with_name(f"{path.stem}-{secrets.token_hex(3)}{path.suffix}")


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


def _load_json(path: Path, *, kind: str) -> dict[str, Any]:
    if not path.exists() or not path.is_file() or path.is_symlink():
        raise TaskRunnerError(f"{kind} inválido: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskRunnerError(f"{kind} não é JSON válido: {path}") from exc
    if not isinstance(loaded, dict):
        raise TaskRunnerError(f"{kind} precisa ser objeto JSON: {path}")
    return loaded


def _resolve_report_path(value: str | Path, *, repo: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve(strict=False)


def _safe_file_bytes(path: Path) -> int:
    if not path.exists() or not path.is_file() or path.is_symlink():
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _tree_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return _safe_file_bytes(path)
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [item for item in dirs if not (Path(root) / item).is_symlink()]
        for filename in files:
            total += _safe_file_bytes(Path(root) / filename)
    return total


def _non_git_bytes(capsule_path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(capsule_path):
        dirs[:] = [item for item in dirs if item != ".git"]
        for filename in files:
            total += _safe_file_bytes(Path(root) / filename)
    return total


def _paths_from_e2e(e2e: dict[str, Any], *, repo: Path) -> dict[str, Path]:
    execution = str(e2e.get("execution_report_path", "")).strip()
    prompt = str(e2e.get("prompt_path", "")).strip()
    capsule_report = str(e2e.get("capsule", {}).get("report_path", "") if isinstance(e2e.get("capsule"), dict) else "").strip()
    capsule = str(e2e.get("capsule_path", "")).strip()
    if not capsule and isinstance(e2e.get("capsule"), dict):
        capsule = str(e2e["capsule"].get("capsule_path", "")).strip()
    return {
        "execution": _resolve_report_path(execution, repo=repo) if execution else Path(),
        "prompt": _resolve_report_path(prompt, repo=repo) if prompt else Path(),
        "capsule_report": _resolve_report_path(capsule_report, repo=repo) if capsule_report else Path(),
        "capsule": _resolve_report_path(capsule, repo=repo) if capsule else Path(),
    }


def _ranked_causes(*, git_hooks_bytes: int, docs_bytes: int, prompt_bytes: int, quiet_output_bytes: int, runner_context: bool, full_repo_leak: bool) -> list[dict[str, Any]]:
    causes: list[dict[str, Any]] = []
    if git_hooks_bytes > 8_000:
        causes.append(
            {
                "rank": 1,
                "cause": "git_template_hooks_in_capsule_cwd",
                "evidence": f".git/hooks bytes={git_hooks_bytes}",
                "confidence": "high",
            }
        )
    if docs_bytes > 0:
        causes.append(
            {
                "rank": len(causes) + 1,
                "cause": "docs_included_in_simple_canary",
                "evidence": f"docs bytes={docs_bytes}",
                "confidence": "medium",
            }
        )
    if runner_context:
        causes.append(
            {
                "rank": len(causes) + 1,
                "cause": "runner_context_injection",
                "evidence": "quiet runner command/context appears to add meaningful payload",
                "confidence": "medium",
            }
        )
    if full_repo_leak:
        causes.append(
            {
                "rank": len(causes) + 1,
                "cause": "full_repo_context_leak",
                "evidence": "cwd/source_root suggests full repo was used",
                "confidence": "high",
            }
        )
    if not causes:
        causes.append(
            {
                "rank": 1,
                "cause": "unproven_context_overhead",
                "evidence": f"prompt bytes={prompt_bytes}; output bytes={quiet_output_bytes}",
                "confidence": "low",
            }
        )
    return causes


def run_capsule_cost_diagnosis(
    *,
    e2e_report: str | Path,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    e2e_path = _resolve_report_path(e2e_report, repo=repo)
    e2e = _load_json(e2e_path, kind="e2e report")
    paths = _paths_from_e2e(e2e, repo=repo)

    execution = _load_json(paths["execution"], kind="capsule execution report") if paths["execution"] else {}
    quiet_path_value = str(execution.get("quiet_runner_report_path", "")).strip()
    quiet_path = _resolve_report_path(quiet_path_value, repo=repo) if quiet_path_value else Path()
    quiet = _load_json(quiet_path, kind="quiet run report") if quiet_path else {}
    capsule_report = _load_json(paths["capsule_report"], kind="capsule report") if paths["capsule_report"] else {}

    capsule_path = paths["capsule"]
    prompt_path = paths["prompt"]
    manifest_path = capsule_path / "CAPSULE_MANIFEST.json"
    agents_path = capsule_path / "AGENTS.md"
    manifest = _load_json(manifest_path, kind="capsule manifest") if manifest_path.exists() else {}

    prompt_bytes = _safe_file_bytes(prompt_path)
    capsule_total_bytes = _tree_bytes(capsule_path)
    capsule_git_bytes = _tree_bytes(capsule_path / ".git")
    capsule_git_hooks_bytes = _tree_bytes(capsule_path / ".git" / "hooks")
    capsule_non_git_bytes = _non_git_bytes(capsule_path)
    agents_bytes = _safe_file_bytes(agents_path)
    manifest_bytes = _safe_file_bytes(manifest_path)
    docs_bytes = _tree_bytes(capsule_path / "docs")
    memory_digest_bytes = _tree_bytes(capsule_path / "memory" / "digests")

    combined_log = str(quiet.get("combined_log_path", "")).strip()
    combined_path = _resolve_report_path(combined_log, repo=repo) if combined_log else Path()
    quiet_output_text = combined_path.read_text(encoding="utf-8", errors="replace") if combined_path.exists() else ""
    quiet_output_lines = int(quiet.get("output_lines") or len(quiet_output_text.splitlines()))
    quiet_output_bytes = int(quiet.get("output_bytes") or len(quiet_output_text.encode("utf-8")))
    diff_like_lines = int(quiet.get("diff_like_lines") or count_diff_like_lines(quiet_output_text))
    tokens_used = int(e2e.get("tokens_used") or execution.get("tokens_used") or 0)

    cwd_used = str(quiet.get("cwd") or "")
    full_repo_context_leak_detected = bool(cwd_used and Path(cwd_used).resolve() == repo.resolve())
    command_metadata = quiet.get("command_metadata", {})
    if not isinstance(command_metadata, dict):
        command_metadata = {}
    command_uses_expected_capsule_flags = bool(
        command_metadata.get("command_contains_ignore_user_config")
        and command_metadata.get("command_contains_ephemeral")
        and command_metadata.get("command_contains_cd")
    )
    runner_context_injection_detected = bool(
        not command_uses_expected_capsule_flags
        or prompt_bytes > 4_000
        or quiet_output_bytes > 12_000
    )

    suspected_causes = _ranked_causes(
        git_hooks_bytes=capsule_git_hooks_bytes,
        docs_bytes=docs_bytes,
        prompt_bytes=prompt_bytes,
        quiet_output_bytes=quiet_output_bytes,
        runner_context=runner_context_injection_detected,
        full_repo_leak=full_repo_context_leak_detected,
    )
    top_confidence = str(suspected_causes[0].get("confidence", "low"))
    root_cause_confidence = "high" if top_confidence == "high" and not full_repo_context_leak_detected else top_confidence
    safe_to_implement = root_cause_confidence in {"high", "medium"} and not full_repo_context_leak_detected

    report_path = _unique_path(repo / "reports" / CAPSULE_COST_DIAGNOSIS_REPORT_DIR / f"{_timestamp()}.json")
    recommended_fix = (
        "FactoryOS: criar capsule_mode=ultra_slim, inicializar git com template vazio para remover hooks sample, "
        "não incluir docs/digest por padrão no canário simples e registrar prompt_effective_bytes."
    )
    report = {
        "ok": True,
        "capsule_cost_diagnosis_version": CAPSULE_COST_DIAGNOSIS_VERSION,
        "root_cause_confidence": root_cause_confidence,
        "suspected_causes": suspected_causes,
        "prompt_bytes": prompt_bytes,
        "capsule_total_bytes": capsule_total_bytes,
        "capsule_non_git_bytes": capsule_non_git_bytes,
        "capsule_git_bytes": capsule_git_bytes,
        "capsule_git_hooks_bytes": capsule_git_hooks_bytes,
        "agents_bytes": agents_bytes,
        "manifest_bytes": manifest_bytes,
        "docs_bytes": docs_bytes,
        "memory_digest_bytes": memory_digest_bytes,
        "quiet_output_lines": quiet_output_lines,
        "quiet_output_bytes": quiet_output_bytes,
        "diff_like_lines": diff_like_lines,
        "tokens_used": tokens_used,
        "token_per_prompt_byte": round(tokens_used / prompt_bytes, 4) if prompt_bytes else None,
        "token_per_capsule_byte": round(tokens_used / capsule_total_bytes, 4) if capsule_total_bytes else None,
        "cwd_used": cwd_used,
        "full_repo_context_leak_detected": full_repo_context_leak_detected,
        "runner_context_injection_detected": runner_context_injection_detected,
        "codex_capsule_run_prompt_extra_detected": False,
        "codex_quiet_run_contract_extra_detected": False,
        "log_capture_as_token_source_detected": quiet_output_bytes > prompt_bytes * 10,
        "command_registered": bool(quiet.get("command")),
        "command_uses_expected_capsule_flags": command_uses_expected_capsule_flags,
        "capsule_path": str(capsule_path),
        "manifest_label": manifest.get("label", ""),
        "capsule_report_total_bytes": capsule_report.get("total_bytes"),
        "recommended_fix": recommended_fix,
        "safe_to_implement_054_055": safe_to_implement,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
