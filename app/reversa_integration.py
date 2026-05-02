from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

CODE_ROOT = Path("<CODE_ROOT>")
PROTECTED_TARGETS = {
    CODE_ROOT / "harness": "protected_harness",
    CODE_ROOT / "factoryos": "protected_factoryos_default",
}

REVERSA_VERSION = "083.R-v0"
REPORT_FIELDS = (
    "ok",
    "dry_run",
    "target",
    "target_allowed",
    "blocked_reason",
    "git_detected",
    "git_clean",
    "dirty_reversa_artifacts_allowed",
    "allowed_dirty_paths",
    "reversa_detected",
    "reversa_installed_in_project",
    "would_create_paths",
    "would_read_paths",
    "would_write_paths",
    "human_review_required",
    "safe_to_execute",
    "no_push",
    "no_deploy",
    "no_paid_api",
    "no_secrets",
    "report_path",
)

SDD_CATEGORIES = {
    "inventory": ("inventory", "inventario", "files", "tree", "catalog"),
    "dependencies": ("dependency", "dependencies", "package", "requirements", "lock"),
    "domain": ("domain", "business", "entity", "use-case", "usecase"),
    "architecture": ("architecture", "arquitetura", "component", "module", "system"),
    "permissions": ("permission", "permissions", "auth", "authorization", "role", "acl"),
    "sdd": ("sdd", "specification", "design"),
    "openapi": ("openapi", "swagger", "api"),
    "ui": ("ui", "ux", "frontend", "screen", "page", "component"),
    "database": ("database", "db", "schema", "migration", "sql", "model"),
    "traceability": ("trace", "traceability", "matrix", "mapping"),
}

REVERSA_DIRTY_ALLOWLIST_PREFIXES = (
    "_reversa_sdd/",
    ".reversa/",
    ".agents/skills/",
)
REVERSA_DIRTY_ALLOWLIST_EXACT = {"AGENTS.md"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")


def _json_report_path(repo: Path, report_dir: str) -> Path:
    return repo / "reports" / report_dir / f"{_timestamp()}.json"


def _write_json_report(path: Path, payload: dict[str, Any], *, repo: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["report_path"] = path.relative_to(repo).as_posix()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _command_version(command: list[str], *, timeout: int = 8) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "path": None, "version": None, "returncode": None}
    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "path": executable,
            "version": None,
            "returncode": None,
            "error": str(exc),
        }

    output = (completed.stdout or completed.stderr).strip().splitlines()
    return {
        "available": completed.returncode == 0,
        "path": executable,
        "version": output[0] if output else None,
        "returncode": completed.returncode,
    }


def _node_major(version: str | None) -> int | None:
    if not version:
        return None
    raw = version.strip().lstrip("v")
    major = raw.split(".", 1)[0]
    return int(major) if major.isdigit() else None


def run_reversa_global_check() -> dict[str, Any]:
    node = _command_version(["node", "--version"])
    npm = _command_version(["npm", "--version"])
    reversa = _command_version(["reversa", "--version"])
    npx = _command_version(["npx", "--version"])
    npx_reversa = {"available": False, "checked": False, "mode": "npx --no-install"}

    if npx["path"]:
        npx_reversa = _command_version(["npx", "--no-install", "reversa", "--version"])
        npx_reversa["checked"] = True
        npx_reversa["mode"] = "npx --no-install"

    node_major = _node_major(node.get("version"))
    node_ok = bool(node["available"] and node_major is not None and node_major >= 18)
    reversa_detected = bool(reversa["available"] or npx_reversa["available"])

    return {
        "ok": bool(node_ok and npm["available"]),
        "check_version": REVERSA_VERSION,
        "node": node,
        "npm": npm,
        "node_major": node_major,
        "node_required": ">=18",
        "node_ok": node_ok,
        "reversa": reversa,
        "npx": npx,
        "npx_reversa": npx_reversa,
        "reversa_detected": reversa_detected,
        "installs_performed": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
    }


def _safe_resolve_target(target: str | Path) -> tuple[Path | None, str | None]:
    raw = Path(target).expanduser()
    try:
        resolved = raw.resolve(strict=True)
    except FileNotFoundError:
        return None, "target_not_found"
    except OSError:
        return None, "target_unresolvable"
    if not resolved.is_dir():
        return resolved, "target_not_directory"
    return resolved, None


def _target_guard(target: str | Path) -> dict[str, Any]:
    resolved, blocked_reason = _safe_resolve_target(target)
    allowed = False
    if resolved is not None and blocked_reason is None:
        allowed = resolved == CODE_ROOT or CODE_ROOT in resolved.parents
        if not allowed:
            blocked_reason = "outside_code_root"
        else:
            for protected, reason in PROTECTED_TARGETS.items():
                if resolved == protected:
                    allowed = False
                    blocked_reason = reason
                    break

    return {
        "target": str(resolved or Path(target).expanduser()),
        "target_path": resolved,
        "target_allowed": allowed,
        "blocked_reason": blocked_reason,
    }


def _git_status(target: Path | None) -> dict[str, Any]:
    if target is None:
        return {"git_detected": False, "git_clean": False, "dirty_paths": []}
    git_dir = target / ".git"
    detected = git_dir.exists()
    if not detected:
        return {"git_detected": False, "git_clean": False, "dirty_paths": []}
    completed = subprocess.run(
        ["git", "-C", str(target), "status", "--porcelain", "--untracked-files=all"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return {"git_detected": True, "git_clean": False, "dirty_paths": []}

    dirty_paths: list[str] = []
    for raw_line in completed.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        path_spec = raw_line[3:]
        if " -> " in path_spec:
            dirty_paths.extend(part.strip() for part in path_spec.split(" -> ") if part.strip())
        else:
            dirty_paths.append(path_spec.strip())

    return {
        "git_detected": True,
        "git_clean": not dirty_paths,
        "dirty_paths": dirty_paths,
    }


def _is_reversa_dirty_path(path: str) -> bool:
    return path in REVERSA_DIRTY_ALLOWLIST_EXACT or any(
        path.startswith(prefix) for prefix in REVERSA_DIRTY_ALLOWLIST_PREFIXES
    )


def _project_reversa_state(target: Path | None) -> dict[str, Any]:
    if target is None:
        return {
            "reversa_installed_in_project": False,
            "reversa_state": None,
            "sdd_detected": False,
        }
    state_path = target / ".reversa" / "state.json"
    state_payload: dict[str, Any] | None = None
    if state_path.exists() and not state_path.is_symlink() and state_path.is_file():
        try:
            state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state_payload = {"read_error": True}
    return {
        "reversa_installed_in_project": (target / ".reversa").is_dir(),
        "reversa_state": state_payload,
        "sdd_detected": (target / "_reversa_sdd").is_dir(),
    }


def _base_report(
    *,
    target: str | Path,
    dry_run: bool,
    report_dir: str,
    repo: Path,
    allow_reversa_dirty_artifacts: bool = False,
) -> tuple[dict[str, Any], Path | None]:
    guard = _target_guard(target)
    target_path = guard["target_path"]
    git = _git_status(target_path)
    project_state = _project_reversa_state(target_path)
    global_check = run_reversa_global_check()
    blocked_reason = guard["blocked_reason"]
    dirty_reversa_artifacts_allowed = False
    allowed_dirty_paths: list[str] = []
    if guard["target_allowed"] and git["git_detected"] and not git["git_clean"]:
        if allow_reversa_dirty_artifacts:
            allowed_dirty_paths = [path for path in git["dirty_paths"] if _is_reversa_dirty_path(path)]
            if len(allowed_dirty_paths) == len(git["dirty_paths"]):
                dirty_reversa_artifacts_allowed = True
            else:
                blocked_reason = "git_not_clean_non_reversa_changes"
        else:
            blocked_reason = "git_not_clean"
    elif guard["target_allowed"] and not git["git_detected"]:
        blocked_reason = "git_not_detected"

    target_allowed = bool(guard["target_allowed"] and blocked_reason is None)
    report_path = _json_report_path(repo, report_dir)
    payload = {
        "ok": target_allowed,
        "created_at": _now_iso(),
        "check_version": REVERSA_VERSION,
        "dry_run": dry_run,
        "target": guard["target"],
        "target_allowed": target_allowed,
        "blocked_reason": blocked_reason,
        "git_detected": git["git_detected"],
        "git_clean": git["git_clean"],
        "dirty_reversa_artifacts_allowed": dirty_reversa_artifacts_allowed,
        "allowed_dirty_paths": allowed_dirty_paths,
        "reversa_detected": global_check["reversa_detected"],
        "reversa_installed_in_project": project_state["reversa_installed_in_project"],
        "would_create_paths": [],
        "would_read_paths": [],
        "would_write_paths": [],
        "human_review_required": True,
        "safe_to_execute": False,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": None,
    }
    return payload, target_path


def _assert_report_shape(payload: dict[str, Any]) -> None:
    missing = [field for field in REPORT_FIELDS if field not in payload]
    if missing:
        raise TaskRunnerError(f"report reversa incompleto: {', '.join(missing)}")


def run_reversa_project_plan(
    *,
    target: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("reversa-project-plan exige --dry-run nesta sprint.")
    repo = repo or repo_root()
    payload, target_path = _base_report(target=target, dry_run=True, report_dir="reversa-project-plans", repo=repo)
    if target_path is not None:
        payload["would_create_paths"] = [
            str(target_path / ".reversa"),
            str(target_path / "_reversa_sdd"),
            str(target_path / ".agents" / "skills"),
        ]
        payload["would_read_paths"] = [
            str(target_path / "AGENTS.md"),
            str(target_path / ".reversa" / "state.json"),
            str(target_path / "_reversa_sdd"),
        ]
        payload["would_write_paths"] = [
            str(target_path / ".reversa"),
            str(target_path / "_reversa_sdd"),
            str(target_path / ".agents" / "skills"),
            str(target_path / "AGENTS.md"),
        ]
    payload["plan_command"] = "npx reversa install"
    payload["safe_to_execute"] = bool(payload["ok"] and payload["dry_run"])
    payload["human_review_required"] = True
    _assert_report_shape(payload)
    return _write_json_report(_json_report_path(repo, "reversa-project-plans"), payload, repo=repo)


def run_reversa_project_install(
    *,
    target: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("live install not enabled in V0")
    repo = repo or repo_root()
    payload, target_path = _base_report(target=target, dry_run=True, report_dir="reversa-installs", repo=repo)
    if target_path is not None:
        payload["would_create_paths"] = [
            str(target_path / ".reversa"),
            str(target_path / "_reversa_sdd"),
            str(target_path / ".agents" / "skills"),
        ]
        payload["would_write_paths"] = [
            str(target_path / ".reversa"),
            str(target_path / "_reversa_sdd"),
            str(target_path / ".agents" / "skills"),
            str(target_path / "AGENTS.md"),
        ]
    payload["install_command"] = "npx reversa install"
    payload["install_executed"] = False
    payload["safe_to_execute"] = bool(payload["ok"] and payload["dry_run"])
    _assert_report_shape(payload)
    return _write_json_report(_json_report_path(repo, "reversa-installs"), payload, repo=repo)


def run_reversa_project_status(
    *,
    target: str | Path,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    payload, target_path = _base_report(target=target, dry_run=True, report_dir="reversa-project-status", repo=repo)
    project_state = _project_reversa_state(target_path)
    payload.update(
        {
            "ok": bool(target_path is not None and payload["target_allowed"]),
            "reversa_state": project_state["reversa_state"],
            "sdd_detected": project_state["sdd_detected"],
            "would_read_paths": [str(target_path / ".reversa" / "state.json")] if target_path else [],
            "safe_to_execute": bool(target_path is not None and payload["target_allowed"]),
        }
    )
    _assert_report_shape(payload)
    return _write_json_report(_json_report_path(repo, "reversa-project-status"), payload, repo=repo)


def _classify_sdd_artifact(path: Path) -> str:
    haystack = path.name.lower()
    for category, needles in SDD_CATEGORIES.items():
        if any(needle in haystack for needle in needles):
            return category
    return "sdd"


def _list_sdd_artifacts(sdd_root: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    if not sdd_root.is_dir():
        return artifacts
    for path in sorted(sdd_root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            artifacts.append(
                {
                    "path": path.as_posix(),
                    "category": _classify_sdd_artifact(path),
                    "suffix": path.suffix.lower(),
                }
            )
    return artifacts


def run_reversa_project_sdd_intake(
    *,
    target: str | Path,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("reversa-project-sdd-intake aceita somente --dry-run nesta sprint.")
    repo = repo or repo_root()
    payload, target_path = _base_report(
        target=target,
        dry_run=True,
        report_dir="reversa-sdd-intakes",
        repo=repo,
        allow_reversa_dirty_artifacts=True,
    )
    sdd_root = target_path / "_reversa_sdd" if target_path else None
    artifacts = _list_sdd_artifacts(sdd_root) if sdd_root else []
    categories = sorted({artifact["category"] for artifact in artifacts})
    payload.update(
        {
            "ok": bool(payload["target_allowed"]),
            "sdd_detected": bool(sdd_root and sdd_root.is_dir()),
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "categories": categories,
            "would_read_paths": [str(sdd_root)] if sdd_root else [],
            "would_write_paths": [],
            "safe_to_execute": bool(payload["target_allowed"] and dry_run),
            "human_review_required": True,
        }
    )
    if payload["dirty_reversa_artifacts_allowed"]:
        payload["safe_to_execute"] = True
    _assert_report_shape(payload)
    return _write_json_report(_json_report_path(repo, "reversa-sdd-intakes"), payload, repo=repo)
