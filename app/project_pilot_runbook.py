from __future__ import annotations

import json
import re
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from app.task_runner import TaskRunnerError

PROJECT_PILOT_RUNBOOK_VERSION = "v0"
PROJECT_PILOT_RUNBOOK_REPORT_DIR = "project-pilot-runbooks"

PROJECT_PILOT_RUNBOOK_DOC_PATH = Path("docs/first-project-pilot-runbook.md")
PROJECT_PILOT_RUNBOOK_DISCOVERY_PATH = Path(
    "specs/discovery/reuse-first-first-project-pilot-runbook-v0.md"
)
PROJECT_PILOT_RUNBOOK_PRD_PATH = Path("specs/prd/first-project-pilot-runbook-v0-prd.md")
PROJECT_PILOT_RUNBOOK_SPEC_PATH = Path("specs/technical-spec/first-project-pilot-runbook-v0.md")
PROJECT_PILOT_RUNBOOK_SPRINT_PATH = Path("specs/sprints/073-first-project-pilot-runbook-v0.json")
PROJECT_PILOT_RUNBOOK_PROOF_PATH = Path("reports/first-project-pilot-runbook-v0-proof.txt")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "project"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    return path.with_name(f"{path.name}-{secrets.token_hex(3)}")


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
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _report_path(repo: Path, project_name: str) -> Path:
    filename = f"{_timestamp()}.json"
    return _unique_path(repo / "reports" / PROJECT_PILOT_RUNBOOK_REPORT_DIR / filename)


def _runbook_steps(project_name: str) -> list[dict[str, Any]]:
    approval_points = {
        "project_intake": True,
        "prd": True,
        "spec": True,
        "sprint_plan": True,
        "build_plan": True,
        "capsule_canary": True,
        "apply_gate": True,
        "workspace_scaffold": True,
        "evaluator": True,
        "delivery_package": True,
        "obsidian_sync": True,
        "retention_cleanup": True,
    }
    return [
        {
            "step": 1,
            "name": "project_intake",
            "title": "Entrada do projeto",
            "artifact": "project-intake",
            "approval_required": approval_points["project_intake"],
            "instruction": f"Registrar o projeto `{project_name}` e confirmar o escopo inicial antes de qualquer corte operacional.",
        },
        {
            "step": 2,
            "name": "prd",
            "title": "PRD",
            "artifact": "prd",
            "approval_required": approval_points["prd"],
            "instruction": "Fechar o PRD mínimo com objetivo, escopo, não objetivos e guardrails de segurança.",
        },
        {
            "step": 3,
            "name": "spec",
            "title": "SPEC",
            "artifact": "technical-spec",
            "approval_required": approval_points["spec"],
            "instruction": "Especificar a solução operacional, mantendo regra crítica no backend e sem segredos no frontend.",
        },
        {
            "step": 4,
            "name": "sprint_plan",
            "title": "Sprint plan",
            "artifact": "sprint-json",
            "approval_required": approval_points["sprint_plan"],
            "instruction": "Organizar a sequência de sprints em corte pequeno e auditável.",
        },
        {
            "step": 5,
            "name": "build_plan",
            "title": "Build plan",
            "artifact": "mvp-build-plan",
            "approval_required": approval_points["build_plan"],
            "instruction": "Gerar o build plan com dependências mínimas e sem execução live automática.",
        },
        {
            "step": 6,
            "name": "capsule_canary",
            "title": "Capsule canary",
            "artifact": "mvp-capsule-build-canary",
            "approval_required": approval_points["capsule_canary"],
            "instruction": "Rodar o canary de cápsula para validar o corte pequeno antes de avançar.",
        },
        {
            "step": 7,
            "name": "apply_gate",
            "title": "Apply gate humano",
            "artifact": "mvp-apply-plan",
            "approval_required": approval_points["apply_gate"],
            "instruction": "Submeter o apply gate humano para garantir que nenhuma mudança real avance sem revisão.",
        },
        {
            "step": 8,
            "name": "workspace_scaffold",
            "title": "Workspace scaffold",
            "artifact": "project-workspace",
            "approval_required": approval_points["workspace_scaffold"],
            "instruction": "Preparar o workspace com backend/frontend separados e guardrails explícitos.",
        },
        {
            "step": 9,
            "name": "evaluator",
            "title": "Evaluator",
            "artifact": "mvp-evaluator",
            "approval_required": approval_points["evaluator"],
            "instruction": "Conferir se o workspace satisfaz os checks mínimos do MVP antes da entrega.",
        },
        {
            "step": 10,
            "name": "delivery_package",
            "title": "Delivery package",
            "artifact": "mvp-delivery-package",
            "approval_required": approval_points["delivery_package"],
            "instruction": "Gerar o pacote de entrega em dry-run e marcar revisão humana obrigatória.",
        },
        {
            "step": 11,
            "name": "obsidian_sync",
            "title": "Obsidian sync",
            "artifact": "obsidian-project-sync",
            "approval_required": approval_points["obsidian_sync"],
            "instruction": "Sincronizar a memória curta do projeto sem expor segredos ou dados sensíveis.",
        },
        {
            "step": 12,
            "name": "retention_cleanup",
            "title": "Report retention",
            "artifact": "report-retention-cleanup-plan",
            "approval_required": approval_points["retention_cleanup"],
            "instruction": "Aplicar a política de retenção apenas como plano, sem apagar nada automaticamente.",
        },
    ]


def _runbook_sections(project_name: str) -> dict[str, Any]:
    return {
        "entry": {
            "project_name": project_name,
            "recommended_start_mode": "dry-run",
            "human_review_required": True,
        },
        "approval_points": [
            "project intake",
            "PRD",
            "SPEC",
            "sprint plan",
            "build plan",
            "capsule canary",
            "apply gate humano",
            "workspace scaffold",
            "evaluator",
            "delivery package",
            "Obsidian sync",
            "report retention",
        ],
        "never_automatic": [
            "push",
            "deploy",
            "paid API",
            "secrets",
        ],
        "deliverables": [
            str(PROJECT_PILOT_RUNBOOK_DOC_PATH),
            str(PROJECT_PILOT_RUNBOOK_DISCOVERY_PATH),
            str(PROJECT_PILOT_RUNBOOK_PRD_PATH),
            str(PROJECT_PILOT_RUNBOOK_SPEC_PATH),
            str(PROJECT_PILOT_RUNBOOK_SPRINT_PATH),
            str(PROJECT_PILOT_RUNBOOK_PROOF_PATH),
        ],
    }


def run_project_pilot_runbook_create(
    *,
    project_name: str,
    dry_run: bool,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_project = str(project_name).strip()
    if not normalized_project:
        raise TaskRunnerError("project_name não pode ficar vazio.")
    if not dry_run:
        raise TaskRunnerError("project-pilot-runbook-create aceita somente --dry-run nesta sprint.")

    report_path = _report_path(repo, normalized_project)
    report = {
        "ok": True,
        "project_pilot_runbook_version": PROJECT_PILOT_RUNBOOK_VERSION,
        "project_name": normalized_project,
        "project_slug": _slugify(normalized_project),
        "dry_run": True,
        "human_review_required": True,
        "runbook": _runbook_sections(normalized_project),
        "steps": _runbook_steps(normalized_project),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_path.relative_to(repo).as_posix(),
        "created_at": _now_iso(),
        "finished_at": _now_iso(),
    }
    _write_json_atomic(report_path, report)
    return report
