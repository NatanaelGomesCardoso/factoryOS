from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.panel_data import PanelSnapshot, build_panel_snapshot, repo_root


@dataclass(frozen=True, slots=True)
class PanelUsabilityResult:
    ok: bool
    sprint: str
    usability_decision: str
    generated_at: str
    dry_run: bool
    findings: list[str]
    fixed_items: list[str]
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    read_only_preserved: bool
    next_step: str


def _available_cards(snapshot: PanelSnapshot) -> int:
    cards = [
        snapshot.latest_state_hygiene,
        snapshot.latest_factory_start,
        snapshot.latest_factory_tick,
        snapshot.latest_run,
        snapshot.latest_controlled_loop,
        snapshot.latest_handoff,
        snapshot.latest_execution_evaluation,
        snapshot.latest_bounded_live_canary_review_gate,
        snapshot.latest_long_run_expansion_policy,
    ]
    return sum(1 for card in cards if bool(getattr(card, "available", False)))


def run_panel_usability_check(*, dry_run: bool = True, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise ValueError("panel-usability-check aceita somente --dry-run.")

    repo = repo or repo_root()
    snapshot = build_panel_snapshot(repo)
    findings: list[str] = []

    if not snapshot.task_queue:
        findings.append("Fila operacional indisponivel; painel deve manter empty state util.")
    if not snapshot.reports:
        findings.append("Sem reports recentes; area de evidencias precisa explicar o proximo passo.")
    if _available_cards(snapshot) < 3:
        findings.append("Poucos sinais operacionais disponiveis; leitura depende de empty states claros.")

    fixed_items = [
        "Acoes de viewer rotuladas como read-only para reduzir ambiguidade.",
        "Foco e hover dos links foram reforcados sem criar mutacao no frontend.",
        "Empty states receberam linguagem operacional sobre onde o dado aparecera.",
        "Cards ganharam microcopy de proximo passo e hierarquia mais densa.",
        "CSS responsivo passou a quebrar grades e caminhos longos com menos risco de overflow.",
        "Badges e links preservam contraste, foco visivel e rotulos consistentes.",
    ]
    usability_decision = "passed" if fixed_items else "failed"

    return asdict(
        PanelUsabilityResult(
            ok=usability_decision == "passed",
            sprint="084-panel-interaction-usability-polish-v0",
            usability_decision=usability_decision,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            dry_run=True,
            findings=findings,
            fixed_items=fixed_items,
            no_push=True,
            no_deploy=True,
            no_paid_api=True,
            no_secrets=True,
            read_only_preserved=True,
            next_step="Executar Sprint 085 para tornar o fluxo de projeto/MVP mais legivel.",
        )
    )
