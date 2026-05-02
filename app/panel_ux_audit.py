from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.panel_data import PanelSnapshot, build_panel_snapshot, repo_root


@dataclass(frozen=True, slots=True)
class PanelUxAuditResult:
    ok: bool
    sprint: str
    ux_decision: str
    generated_at: str
    dry_run: bool
    audited_sections: list[str]
    findings: list[str]
    proposed_visual_direction: str
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    read_only_preserved: bool
    next_step: str


def _available(value: Any) -> bool:
    return bool(getattr(value, "available", False))


def _count_available_operational_cards(snapshot: PanelSnapshot) -> int:
    cards = [
        snapshot.latest_evaluator,
        snapshot.latest_run,
        snapshot.latest_factory_tick,
        snapshot.latest_controlled_loop,
        snapshot.latest_state_hygiene,
        snapshot.latest_factory_start,
        snapshot.latest_factory_start_live_canary,
        snapshot.latest_handoff,
        snapshot.latest_live_canary,
        snapshot.latest_bounded_live_canary_review_gate,
        snapshot.latest_long_run_expansion_policy,
        snapshot.latest_expanded_long_run_rehearsal,
        snapshot.latest_expanded_long_run_review_gate,
        snapshot.latest_execution_evaluation,
    ]
    return sum(1 for card in cards if _available(card))


def _build_findings(snapshot: PanelSnapshot) -> list[str]:
    findings = [
        "O painel ja preserva o contrato read-only e centraliza links seguros para reports/docs.",
        "A hierarquia inicial ainda parece genérica: o topo explica o painel, mas nao prioriza decisao operacional.",
        "As secoes operacionais aparecem como muitos cards equivalentes, sem agrupamento claro por finalidade.",
        "Status existem, mas precisam de maior contraste visual e linguagem consistente para leitura rapida.",
        "Reports, docs, discoveries e proximos passos ficam no fim, reduzindo a utilidade para fechamento de sprint.",
        "O mobile funciona em grade simples, mas cards longos e caminhos tecnicos precisam de quebra e densidade melhor.",
        "A area central precisa parecer uma ferramenta de fabrica de software, nao uma lista acumulada de widgets.",
    ]

    if snapshot.projects:
        findings.append("Projetos detectados ja oferecem contexto real; devem subir para o bloco de Projeto atual.")
    else:
        findings.append("Projetos sem dados precisam de empty state operacional, evitando centro vazio.")

    if _count_available_operational_cards(snapshot) >= 6:
        findings.append("Ha informacao operacional suficiente para agrupar em fabrica, runs/capsulas e gates.")

    return findings


def run_panel_ux_audit(*, dry_run: bool = True, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise ValueError("panel-ux-audit aceita somente --dry-run nesta rodada.")

    repo = repo or repo_root()
    snapshot = build_panel_snapshot(repo)
    findings = _build_findings(snapshot)
    ux_decision = "needs_polish" if findings else "failed"

    result = PanelUxAuditResult(
        ok=ux_decision in {"passed", "needs_polish"},
        sprint="081-panel-ux-audit-visual-direction-v0",
        ux_decision=ux_decision,
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        dry_run=True,
        audited_sections=[
            "Estado da fabrica",
            "Projeto atual",
            "Tasks/fila",
            "Runs/capsulas",
            "Reports/evidencias",
            "Seguranca/gates",
            "Proximos passos",
        ],
        findings=findings,
        proposed_visual_direction=(
            "Command center local, dev/hacker sobrio, dark utilitario, cards densos, "
            "status legiveis e navegacao por blocos operacionais."
        ),
        no_push=True,
        no_deploy=True,
        no_paid_api=True,
        no_secrets=True,
        read_only_preserved=True,
        next_step="Executar Sprint 082 para reorganizar a arquitetura da informacao do painel.",
    )
    return asdict(result)
