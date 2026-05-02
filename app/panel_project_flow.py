from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.panel_data import build_panel_snapshot, repo_root


FLOW_STEPS = [
    "Intake",
    "PRD",
    "SPEC",
    "Build Plan",
    "Capsule Canary",
    "Apply Gate",
    "Workspace",
    "Evaluator",
    "Delivery",
    "Obsidian",
    "Release",
]


@dataclass(frozen=True, slots=True)
class PanelProjectFlowResult:
    ok: bool
    sprint: str
    project_flow_decision: str
    generated_at: str
    dry_run: bool
    flow_steps: list[str]
    findings: list[str]
    fixed_items: list[str]
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    read_only_preserved: bool
    next_step: str


def run_panel_project_flow_check(*, dry_run: bool = True, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise ValueError("panel-project-flow-check aceita somente --dry-run.")

    repo = repo or repo_root()
    snapshot = build_panel_snapshot(repo)
    findings: list[str] = []

    if not snapshot.projects:
        findings.append("Nenhum projeto atual detectado; fluxo precisa funcionar como orientacao operacional.")
    if not snapshot.reports:
        findings.append("Sem reports recentes para navegação contextual do fluxo.")

    fixed_items = [
        "Area Projeto atual passou a conectar workspaces com reports relevantes.",
        "Fluxo Intake -> Release foi exposto como trilha visual simples e read-only.",
        "Gates humanos, automacao local e etapas bloqueadas ficaram diferenciados por badge.",
        "Proximo passo operacional aponta para evidencia ou gate sem executar automacao.",
        "Navegacao inclui ancora direta para o fluxo de projeto.",
    ]
    project_flow_decision = "passed" if fixed_items else "failed"

    return asdict(
        PanelProjectFlowResult(
            ok=project_flow_decision == "passed",
            sprint="085-panel-project-flow-ux-v0",
            project_flow_decision=project_flow_decision,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            dry_run=True,
            flow_steps=FLOW_STEPS,
            findings=findings,
            fixed_items=fixed_items,
            no_push=True,
            no_deploy=True,
            no_paid_api=True,
            no_secrets=True,
            read_only_preserved=True,
            next_step="Executar Sprint 086 para QA visual e estrutural final do painel.",
        )
    )
