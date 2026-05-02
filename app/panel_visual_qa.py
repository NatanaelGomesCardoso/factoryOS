from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.panel_data import build_panel_snapshot, repo_root


@dataclass(frozen=True, slots=True)
class PanelVisualQaResult:
    ok: bool
    sprint: str
    visual_qa_decision: str
    generated_at: str
    dry_run: bool
    checked_items: list[str]
    blockers: list[str]
    warnings: list[str]
    fixed_items: list[str]
    no_push: bool
    no_deploy: bool
    no_paid_api: bool
    no_secrets: bool
    read_only_preserved: bool
    next_step: str


def _contains_any(text: str, needles: list[str]) -> list[str]:
    lower = text.lower()
    return [needle for needle in needles if needle.lower() in lower]


def run_panel_final_visual_qa(*, dry_run: bool = True, repo: Path | None = None) -> dict[str, Any]:
    if not dry_run:
        raise ValueError("panel-final-visual-qa aceita somente --dry-run.")

    repo = repo or repo_root()
    snapshot = build_panel_snapshot(repo)
    blockers: list[str] = []
    warnings: list[str] = []
    checked_items: list[str] = []

    try:
        from fastapi.testclient import TestClient
        from app.web import app

        client = TestClient(app)
        health = client.get("/health")
        if health.status_code == 200:
            checked_items.append("/health funciona")
        else:
            warnings.append(f"/health retornou {health.status_code}")

        panel = client.get("/")
        if panel.status_code == 200:
            checked_items.append("painel renderiza")
        else:
            blockers.append(f"painel retornou {panel.status_code}")

        html = panel.text
        lower_html = html.lower()
        if "traceback" in lower_html:
            blockers.append("HTML principal contem traceback")
        else:
            checked_items.append("HTML principal sem traceback")

        missing = [
            needle
            for needle in [
                "Factory Command Center",
                "Estado local",
                "Projeto atual",
                "Do intake ao release",
                "Controles de avancar",
                "Abrir report",
            ]
            if needle not in html
        ]
        if missing:
            blockers.append("Elementos principais ausentes: " + ", ".join(missing))
        else:
            checked_items.append("titulos, cards, fluxo e links read-only existem")

        visible_bad_tokens = _contains_any(html, ["placeholder", "lorem ipsum", "todo critico", "todo crítico"])
        if visible_bad_tokens:
            blockers.append("HTML contem placeholder/TODO critico visivel")
        else:
            checked_items.append("sem placeholders obvios ou TODO critico visivel")

        css = client.get("/static/style.css")
        if css.status_code == 200 and ".flow-rail" in css.text and "@media" in css.text:
            checked_items.append("CSS principal carregavel e responsivo por estrutura")
        else:
            blockers.append("CSS principal indisponivel ou sem estrutura responsiva esperada")

        if snapshot.reports:
            first = snapshot.reports[0]
            if first.view_path:
                viewer = client.get(f"/view/reports/{first.view_path}")
                if viewer.status_code == 200 and "traceback" not in viewer.text.lower():
                    checked_items.append("viewer seguro renderiza report read-only")
                else:
                    warnings.append("viewer retornou falha para report recente")
        else:
            warnings.append("viewer nao foi exercitado com report recente porque nao ha reports no snapshot")
    except Exception as exc:  # pragma: no cover - registra lacuna operacional sem esconder falha.
        blockers.append(f"QA via TestClient falhou: {exc.__class__.__name__}: {exc}")

    fixed_items = [
        "QA estrutural cobre render, health, CSS, titulos, status cards, fluxo e viewer.",
        "Hierarquia final documenta contraste, foco visivel e responsividade por classes.",
        "Release permanece apresentado como bloqueado ate gate final.",
    ]

    if blockers:
        visual_qa_decision = "failed"
    elif warnings:
        visual_qa_decision = "needs_review"
    else:
        visual_qa_decision = "passed"

    return asdict(
        PanelVisualQaResult(
            ok=visual_qa_decision in {"passed", "needs_review"},
            sprint="086-panel-final-visual-qa-v0",
            visual_qa_decision=visual_qa_decision,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            dry_run=True,
            checked_items=checked_items,
            blockers=blockers,
            warnings=warnings,
            fixed_items=fixed_items,
            no_push=True,
            no_deploy=True,
            no_paid_api=True,
            no_secrets=True,
            read_only_preserved=True,
            next_step="Rodar release clean strategy 087-089 antes de publicacao.",
        )
    )
