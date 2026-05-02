from __future__ import annotations

import json
import re
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.mvp_templates import MVPTemplate, get_template
from app.report_index import latest_report_for_project
from app.task_runner import TaskRunnerError

PROJECT_WORKSPACE_VERSION = "v0"
PROJECT_WORKSPACE_REPORTS_DIR = "project-workspaces"
PROJECT_WORKSPACE_BASE_DIR = Path("workspaces/projects")

PROJECT_REPORT_KINDS = {
    "intake": "project-intakes",
    "build_plan": "mvp-build-plans",
    "capsule_canary": "mvp-capsule-build-canaries",
    "apply_plan": "mvp-apply-plans",
    "evaluator": "mvp-evaluations",
}


@dataclass(frozen=True, slots=True)
class ProjectWorkspaceSummary:
    project_name: str
    kind: str
    template_id: str | None
    workspace_relative_path: str
    workspace_path: str
    workspace_exists: bool
    readme_exists: bool
    state_exists: bool
    backend_required: bool
    frontend_required: bool
    backend_exists: bool
    frontend_exists: bool
    docs_exists: bool
    reports_exists: bool
    status: str
    notes: list[str]
    latest_reports: dict[str, dict[str, Any] | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "kind": self.kind,
            "template_id": self.template_id,
            "workspace_relative_path": self.workspace_relative_path,
            "workspace_path": self.workspace_path,
            "workspace_exists": self.workspace_exists,
            "readme_exists": self.readme_exists,
            "state_exists": self.state_exists,
            "backend_required": self.backend_required,
            "frontend_required": self.frontend_required,
            "backend_exists": self.backend_exists,
            "frontend_exists": self.frontend_exists,
            "docs_exists": self.docs_exists,
            "reports_exists": self.reports_exists,
            "status": self.status,
            "notes": list(self.notes),
            "latest_reports": self.latest_reports,
        }


def _repo_root(repo: Path | None = None) -> Path:
    return repo or Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _slugify(value: str, max_length: int = 64) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    ascii_text = re.sub(r"-+", "-", ascii_text).strip("-")
    ascii_text = ascii_text[:max_length].strip("-")
    return ascii_text or "project"


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


def _workspace_relative(project_name: str) -> Path:
    return PROJECT_WORKSPACE_BASE_DIR / _slugify(project_name)


def _report_path(repo: Path, project_name: str) -> Path:
    return _unique_path(repo / "reports" / PROJECT_WORKSPACE_REPORTS_DIR / f"{_timestamp()}-{_slugify(project_name)}.json")


def _template_from_name(template_name: str) -> MVPTemplate:
    return get_template(template_name)


def _workspace_paths(workspace_path: Path) -> dict[str, Path]:
    return {
        "root": workspace_path,
        "backend": workspace_path / "backend",
        "frontend": workspace_path / "frontend",
        "docs": workspace_path / "docs",
        "reports": workspace_path / "reports",
        "readme": workspace_path / "README.md",
        "project_state": workspace_path / "PROJECT_STATE.md",
        "backend_readme": workspace_path / "backend" / "README.md",
        "frontend_readme": workspace_path / "frontend" / "README.md",
        "docs_readme": workspace_path / "docs" / "README.md",
        "reports_readme": workspace_path / "reports" / "README.md",
    }


def _workspace_text(
    *,
    project_name: str,
    kind: str,
    template: MVPTemplate,
    workspace_path: Path,
) -> dict[str, str]:
    backend_line = "regras críticas, secrets, auth, payment, rate limit, quota e transições de estado ficam no backend."
    frontend_line = "UI, experiência visual e chamadas ao backend ficam no frontend; nunca secrets."
    readme = "\n".join(
        [
            f"# {project_name}",
            "",
            "Workspace local controlado para o primeiro MVP.",
            "",
            f"- kind: `{kind}`",
            f"- template: `{template.template_id}`",
            f"- workspace: `{workspace_path.as_posix()}`",
            "- status: scaffold inicial",
            "- no_push: true",
            "- no_deploy: true",
            "- no_paid_api: true",
            "- no_secrets: true",
        ]
    ).strip() + "\n"
    project_state = "\n".join(
        [
            "# PROJECT_STATE",
            "",
            f"project_name={project_name}",
            f"kind={kind}",
            f"template_id={template.template_id}",
            f"workspace_path={workspace_path.as_posix()}",
            f"backend_required={'true' if template.backend_required else 'false'}",
            f"frontend_required={'true' if template.frontend_required else 'false'}",
            "status=scaffolded",
            "no_push=true",
            "no_deploy=true",
            "no_paid_api=true",
            "no_secrets=true",
            "git_init=false",
        ]
    ).strip() + "\n"
    backend_readme = "\n".join(
        [
            "# Backend",
            "",
            backend_line,
            "",
            "- auth, pagamento, rate limit, quota e transições de estado ficam aqui;",
            "- nenhuma chave, token ou regra crítica no frontend;",
            "- sem deploy automático e sem API paga por padrão.",
        ]
    ).strip() + "\n"
    frontend_readme = "\n".join(
        [
            "# Frontend",
            "",
            frontend_line,
            "",
            "- não armazenar secrets no bundle, HTML ou assets;",
            "- chamar o backend para qualquer operação crítica;",
            "- focar em UI, copy e experiência visual.",
        ]
    ).strip() + "\n"
    docs_readme = "\n".join(
        [
            "# Docs",
            "",
            "Documentação local do workspace. Os artefatos aqui devem permanecer curtos e auditáveis.",
        ]
    ).strip() + "\n"
    reports_readme = "\n".join(
        [
            "# Reports",
            "",
            "Reports locais do workspace. Nunca colocar secrets ou dados sensíveis aqui.",
        ]
    ).strip() + "\n"
    return {
        "README.md": readme,
        "PROJECT_STATE.md": project_state,
        "backend/README.md": backend_readme,
        "frontend/README.md": frontend_readme,
        "docs/README.md": docs_readme,
        "reports/README.md": reports_readme,
    }


def _parse_state_text(text: str) -> dict[str, str]:
    state: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            state[key] = value
    return state


def load_project_state(workspace_path: Path) -> dict[str, str]:
    state_path = workspace_path / "PROJECT_STATE.md"
    if not state_path.exists() or not state_path.is_file() or state_path.is_symlink():
        return {}
    try:
        return _parse_state_text(state_path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def _project_status(
    *,
    state: dict[str, str],
    backend_exists: bool,
    frontend_exists: bool,
    docs_exists: bool,
    reports_exists: bool,
    readme_exists: bool,
    required_backend: bool,
    required_frontend: bool,
) -> tuple[str, list[str]]:
    notes: list[str] = []
    if not readme_exists:
        notes.append("README ausente.")
    if not docs_exists:
        notes.append("docs ausente.")
    if not reports_exists:
        notes.append("reports ausente.")
    if required_backend and not backend_exists:
        notes.append("backend requerido ausente.")
    if required_frontend and not frontend_exists:
        notes.append("frontend requerido ausente.")
    if state.get("no_push") != "true":
        notes.append("no_push=false.")
    if state.get("no_deploy") != "true":
        notes.append("no_deploy=false.")
    if state.get("no_paid_api") != "true":
        notes.append("no_paid_api=false.")
    if state.get("no_secrets") != "true":
        notes.append("no_secrets=false.")

    if any(note.endswith("ausente.") for note in notes):
        return "needs_review", notes
    if any(note.endswith("false.") for note in notes):
        return "failed", notes
    return "ready", notes


def _latest_workspace_reports(repo: Path, project_name: str) -> dict[str, dict[str, Any] | None]:
    reports: dict[str, dict[str, Any] | None] = {}
    for key, kind in PROJECT_REPORT_KINDS.items():
        entry = latest_report_for_project(kind, project_name=project_name, repo=repo)
        if entry is None:
            reports[key] = None
            continue
        reports[key] = {
            "kind": kind,
            "report_path": entry.relative_path,
            "view_path": entry.view_path,
            "timestamp": entry.timestamp,
        }
    return reports


def discover_project_workspaces(repo: Path | None = None) -> list[dict[str, Any]]:
    repo = _repo_root(repo)
    root = repo / PROJECT_WORKSPACE_BASE_DIR
    if not root.exists():
        return []

    projects: list[dict[str, Any]] = []
    for workspace_path in sorted(path for path in root.iterdir() if path.is_dir() and not path.is_symlink()):
        state = load_project_state(workspace_path)
        project_name = state.get("project_name") or workspace_path.name
        kind = state.get("kind") or "unknown"
        template_id = state.get("template_id") or None
        template = None
        if template_id:
            try:
                template = _template_from_name(template_id)
            except TaskRunnerError:
                template = None

        backend_required = (template.backend_required if template else state.get("backend_required") == "true")
        frontend_required = (template.frontend_required if template else state.get("frontend_required") == "true")
        paths = _workspace_paths(workspace_path)
        backend_exists = paths["backend"].exists() and paths["backend"].is_dir()
        frontend_exists = paths["frontend"].exists() and paths["frontend"].is_dir()
        docs_exists = paths["docs"].exists() and paths["docs"].is_dir()
        reports_exists = paths["reports"].exists() and paths["reports"].is_dir()
        readme_exists = paths["readme"].exists() and paths["readme"].is_file()
        state_exists = paths["project_state"].exists() and paths["project_state"].is_file()
        status, notes = _project_status(
            state=state,
            backend_exists=backend_exists,
            frontend_exists=frontend_exists,
            docs_exists=docs_exists,
            reports_exists=reports_exists,
            readme_exists=readme_exists,
            required_backend=bool(backend_required),
            required_frontend=bool(frontend_required),
        )
        if status == "ready" and state.get("status") == "scaffolded":
            status = "scaffolded"
        projects.append(
            ProjectWorkspaceSummary(
                project_name=project_name,
                kind=kind,
                template_id=template_id,
                workspace_relative_path=workspace_path.relative_to(repo).as_posix(),
                workspace_path=str(workspace_path),
                workspace_exists=True,
                readme_exists=readme_exists,
                state_exists=state_exists,
                backend_required=bool(backend_required),
                frontend_required=bool(frontend_required),
                backend_exists=backend_exists,
                frontend_exists=frontend_exists,
                docs_exists=docs_exists,
                reports_exists=reports_exists,
                status=status,
                notes=notes,
                latest_reports=_latest_workspace_reports(repo, project_name),
            ).to_dict()
        )
    return projects


def run_project_workspace_scaffold(
    *,
    project_name: str,
    kind: str,
    from_template: str = "simple-web-mvp",
    dry_run: bool,
    create_workspace: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = _repo_root(repo)
    if dry_run == create_workspace:
        raise TaskRunnerError("informe exatamente um de --dry-run ou --create-workspace.")

    normalized_project = str(project_name).strip()
    normalized_kind = str(kind).strip()
    normalized_template = str(from_template).strip() or "simple-web-mvp"
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")
    if not normalized_kind:
        raise TaskRunnerError("kind não pode ficar vazio.")

    template = _template_from_name(normalized_template)
    workspace_relative = _workspace_relative(normalized_project)
    workspace_path = repo / workspace_relative
    report_path = _report_path(repo, normalized_project)
    created_at = _now_iso()
    workspace_preexisting = workspace_path.exists()
    created_directories: list[str] = []
    created_files: list[str] = []
    existing_files: list[str] = []

    directory_paths = _workspace_paths(workspace_path)
    if create_workspace:
        for key in ("root", "backend", "frontend", "docs", "reports"):
            target = directory_paths[key]
            target.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.is_dir() and target != workspace_path:
                created_directories.append(target.relative_to(repo).as_posix())
        for relative_name, content in _workspace_text(
            project_name=normalized_project,
            kind=normalized_kind,
            template=template,
            workspace_path=workspace_path,
        ).items():
            target_path = workspace_path / relative_name
            if target_path.exists():
                if target_path.is_symlink():
                    raise TaskRunnerError(f"symlink não permitido: {target_path}")
                existing_files.append(target_path.relative_to(repo).as_posix())
                continue
            _write_text_atomic(target_path, content)
            created_files.append(target_path.relative_to(repo).as_posix())
        for path in (
            directory_paths["backend"],
            directory_paths["frontend"],
            directory_paths["docs"],
            directory_paths["reports"],
        ):
            if path.exists() and path.is_dir():
                created_directories.append(path.relative_to(repo).as_posix())

    report = {
        "ok": True,
        "project_workspace_version": PROJECT_WORKSPACE_VERSION,
        "project_name": normalized_project,
        "kind": normalized_kind,
        "template_id": template.template_id,
        "template_name": template.name,
        "workspace_relative_path": workspace_relative.as_posix(),
        "workspace_path": str(workspace_path),
        "workspace_preexisting": workspace_preexisting,
        "dry_run": bool(dry_run),
        "create_workspace": bool(create_workspace),
        "workspace_created": bool(create_workspace and workspace_path.exists()),
        "created_directories": sorted(dict.fromkeys(created_directories)),
        "created_files": sorted(dict.fromkeys(created_files)),
        "existing_files": sorted(dict.fromkeys(existing_files)),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "git_init": False,
        "template_required_backend": template.backend_required,
        "template_required_frontend": template.frontend_required,
        "report_path": str(report_path.relative_to(repo).as_posix()),
        "created_at": created_at,
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
