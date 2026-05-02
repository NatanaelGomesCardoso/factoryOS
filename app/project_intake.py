from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.mvp_templates import get_template
from app.report_index import latest_report
from app.task_runner import TaskRunnerError

PROJECT_INTAKE_VERSION = "v0"
PROJECT_INTAKE_REPORTS_DIR = "project-intakes"
PROJECT_INTAKE_TEMPLATE = "simple-web-mvp"
PROJECT_INTAKE_SPRINT_ID = "060"

PROJECT_INTAKE_DOC_PATH = Path("docs/first-mvp-project-intake.md")
PROJECT_INTAKE_DISCOVERY_PATH = Path("specs/discovery/reuse-first-first-mvp-project-intake-v0.md")
PROJECT_INTAKE_PRD_PATH = Path("specs/prd/first-mvp-project-intake-v0-prd.md")
PROJECT_INTAKE_SPEC_PATH = Path("specs/technical-spec/first-mvp-project-intake-v0.md")
PROJECT_INTAKE_SPRINT_PATH = Path("specs/sprints/060-first-mvp-project-intake-v0.json")


@dataclass(frozen=True, slots=True)
class IntakeCandidate:
    candidate_id: str
    title: str
    category: str
    source: str
    decision: str
    execution_mode_recommendation: str
    reason: str
    capsule_recommended: bool
    full_repo_required: bool
    blocked: bool
    estimated_tokens_saved: int
    priority: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def _write_text_atomic(path: Path, content: str) -> None:
    if path.exists() and path.is_symlink():
        raise TaskRunnerError(f"symlink nao permitido: {path}")

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


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "project"


def _candidate_id(project_name: str, suffix: str) -> str:
    return f"{_slugify(project_name)}-{suffix}"


def _template_candidates(project_name: str, template_name: str) -> list[IntakeCandidate]:
    template = get_template(template_name)
    candidates: list[IntakeCandidate] = []
    for index, candidate in enumerate(template.default_task_candidates, start=1):
        candidate_id = str(candidate.get("candidate_id", "")).strip()
        if not candidate_id:
            candidate_id = _candidate_id(project_name, f"candidate-{index}")
        title = str(candidate.get("title", "")).strip() or candidate_id
        category = str(candidate.get("category", "")).strip() or "code_small"
        source = str(candidate.get("source", "")).strip() or f"template:{template.template_id}"
        reason = str(candidate.get("reason", "")).strip() or "Plano derivado do template."
        execution_mode_recommendation = str(candidate.get("execution_mode_recommendation", "")).strip() or "capsule"
        capsule_recommended = bool(candidate.get("capsule_recommended", execution_mode_recommendation == "capsule"))
        full_repo_required = bool(candidate.get("full_repo_required", False))
        blocked = bool(candidate.get("blocked", False))
        priority = int(candidate.get("priority", index))
        candidates.append(
            IntakeCandidate(
                candidate_id=_candidate_id(project_name, candidate_id.removeprefix("project-")),
                title=title if "{project_name}" not in title else title.format(project_name=project_name),
                category=category,
                source=source,
                decision="capsule" if execution_mode_recommendation == "capsule" else execution_mode_recommendation,
                execution_mode_recommendation=execution_mode_recommendation,
                reason=reason if "{project_name}" not in reason else reason.format(project_name=project_name),
                capsule_recommended=capsule_recommended,
                full_repo_required=full_repo_required,
                blocked=blocked,
                estimated_tokens_saved=22104 if capsule_recommended else 0,
                priority=priority,
            )
        )
    return candidates


def _template_docs(project_name: str, project_kind: str, template_name: str) -> dict[str, str]:
    template = get_template(template_name)
    return {
        str(PROJECT_INTAKE_DOC_PATH): (
            "# First MVP Project Intake\n\n"
            "Comando local para criar um intake minimo de MVP a partir de PRD, SPEC e sprints.\n\n"
            "## Fluxo\n\n"
            f"- projeto: `{project_name}`\n"
            f"- kind: `{project_kind}`\n"
            f"- template: `{template.template_id}`\n"
            "- gera discovery, PRD, SPEC e sprint plan rascunho;\n"
            "- nao instala dependencias;\n"
            "- nao faz deploy;\n"
            "- nao faz push;\n"
            "- mantem live bloqueado.\n\n"
            "## Separação\n\n"
            "- regras criticas ficam no backend;\n"
            "- frontend não recebe secrets;\n"
            "- integração externa só com justificativa explícita.\n"
        ),
        str(PROJECT_INTAKE_DISCOVERY_PATH): (
            "# Reuse First Discovery - First MVP Project Intake V0\n\n"
            "## Ideia\n\n"
            f"Intake inicial para o projeto `{project_name}` do tipo `{project_kind}`.\n\n"
            "## Objetivo\n\n"
            "Pesquisar apenas o suficiente para estruturar PRD, SPEC e sprints sem iniciar produto real.\n\n"
            "## O que comparar\n\n"
            "- templates simples de MVP web;\n"
            "- estruturas de scaffold minimo;\n"
            "- padroes de inicio rapido sem dependencia pesada;\n"
            "- fluxos locais sem API paga.\n\n"
            "## Decisao esperada\n\n"
            "- usar pequeno customizado;\n"
            "- manter o primeiro corte documental e tecnico leve.\n"
        ),
        str(PROJECT_INTAKE_PRD_PATH): (
            f"# PRD - First MVP Project Intake V0\n\n"
            "## Problema\n\n"
            "Ainda falta um fluxo padronizado para transformar uma ideia de MVP em PRD, SPEC e sprint plan sem construir produto completo.\n\n"
            "## Objetivo\n\n"
            f"Preparar a entrada do projeto `{project_name}` com escopo minimo, foco em docs e zero execucao live.\n\n"
            "## Escopo V0\n\n"
            "- rascunho de PRD;\n"
            "- rascunho de SPEC tecnica;\n"
            "- rascunho de sprint plan;\n"
            "- nenhuma instalacao de dependencia;\n"
            "- nenhum deploy;\n"
            "- nenhum push.\n\n"
            "## Fora de escopo\n\n"
            "- produto real em producao;\n"
            "- autenticacao, pagamento ou integracao externa;\n"
            "- qualquer execucao live de Codex.\n\n"
            "## Guardrails\n\n"
            "- segredo nunca vai para frontend;\n"
            "- regra critica nunca depende do bundle;\n"
            "- o backend continua sendo a borda de decisao.\n"
        ),
        str(PROJECT_INTAKE_SPEC_PATH): (
            f"# SPEC Tecnica - First MVP Project Intake V0\n\n"
            "## Decisao\n\n"
            "Criar uma camada de intake para MVP que gera artefatos documentais minimos e candidatos de tarefa, mas nao executa live.\n\n"
            "## Fluxo\n\n"
            "1. validar nome, kind e template;\n"
            "2. gerar discovery, PRD, SPEC e sprint plan;\n"
            "3. produzir candidatos de tarefa;\n"
            "4. gravar report local em reports/project-intakes/.\n\n"
            "## Guardrails\n\n"
            "- dry-run apenas;\n"
            "- sem push, deploy, API paga ou secrets;\n"
            "- artifacts locais pequenos e auditaveis.\n"
        ),
        str(PROJECT_INTAKE_SPRINT_PATH): json.dumps(
            {
                "id": "060",
                "name": "First MVP Project Intake From PRD SPEC Sprints V0",
                "status": "planned",
                "objective": "Criar um intake minimo de MVP a partir de PRD, SPEC e sprints sem construir produto real completo.",
                "command": "project-intake-create",
                "template": template.template_id,
                "safety": {
                    "dry_run": True,
                    "executed_live": False,
                    "no_push": True,
                    "no_deploy": True,
                    "no_paid_api": True,
                    "no_secrets": True,
                },
                "reports": {
                    "proof": "reports/first-mvp-project-intake-v0-proof.txt",
                    "generated": "reports/project-intakes/",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    }


def _write_template_artifacts(project_name: str, project_kind: str, template_name: str, *, repo: Path) -> dict[str, str]:
    docs = _template_docs(project_name, project_kind, template_name)
    for relative_path, content in docs.items():
        _write_text_atomic(repo / relative_path, content)
    return {
        "generated_discovery_path": str(PROJECT_INTAKE_DISCOVERY_PATH),
        "generated_prd_path": str(PROJECT_INTAKE_PRD_PATH),
        "generated_spec_path": str(PROJECT_INTAKE_SPEC_PATH),
        "generated_sprint_path": str(PROJECT_INTAKE_SPRINT_PATH),
        "generated_doc_path": str(PROJECT_INTAKE_DOC_PATH),
    }


def _report_path(repo: Path) -> Path:
    return repo / "reports" / PROJECT_INTAKE_REPORTS_DIR / f"{_timestamp()}.json"


def _prioritize_candidates(candidates: list[IntakeCandidate]) -> list[IntakeCandidate]:
    return sorted(candidates, key=lambda item: (item.priority, item.candidate_id))


def build_project_intake_plan(
    *,
    project_name: str,
    project_kind: str,
    from_template: str | None = None,
    repo: Path | None = None,
) -> dict[str, Any]:
    repo = repo or repo_root()
    normalized_name = project_name.strip()
    normalized_kind = project_kind.strip()
    normalized_template = (from_template or PROJECT_INTAKE_TEMPLATE).strip()

    if not normalized_name:
        raise TaskRunnerError("project_name nao pode ficar vazio.")
    if not normalized_kind:
        raise TaskRunnerError("project_kind nao pode ficar vazio.")
    template = get_template(normalized_template)
    template_paths = _write_template_artifacts(normalized_name, normalized_kind, template.template_id, repo=repo)
    candidates = _prioritize_candidates(_template_candidates(normalized_name, template.template_id))
    created_at = _now_iso()
    report_path = _report_path(repo)
    report_relative = report_path.relative_to(repo).as_posix()

    task_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "title": candidate.title,
            "category": candidate.category,
            "source": candidate.source,
            "decision": candidate.decision,
            "execution_mode_recommendation": candidate.execution_mode_recommendation,
            "reason": candidate.reason,
            "capsule_recommended": candidate.capsule_recommended,
            "full_repo_required": candidate.full_repo_required,
            "blocked": candidate.blocked,
            "estimated_tokens_saved": candidate.estimated_tokens_saved,
        }
        for candidate in candidates
    ]

    routing_recommendations = [
        {
            "candidate_id": candidate.candidate_id,
            "category": candidate.category,
            "routing": candidate.execution_mode_recommendation,
            "reason": candidate.reason,
        }
        for candidate in candidates
    ]

    capsule_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "title": candidate.title,
            "category": candidate.category,
        }
        for candidate in candidates
        if candidate.capsule_recommended
    ]

    blocked_or_review_required = [
        {
            "candidate_id": candidate.candidate_id,
            "title": candidate.title,
            "category": candidate.category,
            "reason": candidate.reason,
        }
        for candidate in candidates
        if candidate.blocked or candidate.full_repo_required
    ]

    report = {
        "ok": True,
        "project_intake_version": PROJECT_INTAKE_VERSION,
        "project_name": normalized_name,
        "project_kind": normalized_kind,
        "from_template": normalized_template,
        "template_registry_version": template.to_dict()["template_version"],
        "template_metadata": template.to_dict(),
        "dry_run": True,
        "executed_live": False,
        "created_at": created_at,
        "finished_at": _now_iso(),
        "generated_discovery_path": template_paths["generated_discovery_path"],
        "generated_prd_path": template_paths["generated_prd_path"],
        "generated_spec_path": template_paths["generated_spec_path"],
        "generated_sprint_path": template_paths["generated_sprint_path"],
        "generated_doc_path": template_paths["generated_doc_path"],
        "task_candidates": task_candidates,
        "routing_recommendations": routing_recommendations,
        "capsule_candidates": capsule_candidates,
        "blocked_or_review_required": blocked_or_review_required,
        "candidate_count": len(task_candidates),
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
        "report_path": report_relative,
    }

    _write_json_atomic(report_path, report)
    return report


def run_project_intake_create(
    *,
    project_name: str,
    project_kind: str,
    from_template: str | None = None,
    dry_run: bool = True,
    repo: Path | None = None,
) -> dict[str, Any]:
    if not dry_run:
        raise TaskRunnerError("project-intake-create aceita somente --dry-run nesta sprint.")
    return build_project_intake_plan(
        project_name=project_name,
        project_kind=project_kind,
        from_template=from_template,
        repo=repo,
    )


def load_latest_project_intake_report(repo: Path | None = None) -> dict[str, Any] | None:
    repo = repo or repo_root()
    latest = latest_report("project-intakes", repo=repo)
    if latest is None:
        return None
    return latest.payload
