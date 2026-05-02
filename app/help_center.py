from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"
README_PATH = REPO_ROOT / "README.md"


@dataclass(frozen=True, slots=True)
class HelpDoc:
    slug: str
    title: str
    path: Path
    description: str


HELP_DOCS: tuple[HelpDoc, ...] = (
    HelpDoc("getting-started", "Primeiros passos", DOCS_ROOT / "GETTING_STARTED.md", "Instalar, abrir e validar o FactoryOS."),
    HelpDoc("user-guide", "Guia de uso", DOCS_ROOT / "USER_GUIDE.md", "Usar projetos novos, antigos, reports e revisoes."),
    HelpDoc("architecture", "Arquitetura", DOCS_ROOT / "ARCHITECTURE.md", "Como backend, painel, memoria, runner e reports se conectam."),
    HelpDoc("commands", "Comandos", DOCS_ROOT / "COMMANDS.md", "Comandos reais da CLI agrupados por categoria."),
    HelpDoc("workflows", "Fluxos", DOCS_ROOT / "WORKFLOWS.md", "Receitas operacionais para MVP, Reversa, tarefas e release."),
    HelpDoc("security", "Seguranca", DOCS_ROOT / "SECURITY.md", "Bloqueios, ameacas, segredos e revisao humana."),
    HelpDoc("reversa", "Reversa", DOCS_ROOT / "REVERSA.md", "Retomar projetos antigos com guards locais."),
    HelpDoc("local-panel", "Painel local", DOCS_ROOT / "LOCAL_PANEL.md", "Rotas, cards, Ajuda e viewer read-only."),
    HelpDoc("extended-runs", "Runs estendidas", DOCS_ROOT / "EXTENDED_RUNS.md", "Politica de 2h, budgets, gates e stop conditions."),
    HelpDoc("cleanup-release", "Limpeza e release", DOCS_ROOT / "CLEANUP_AND_RELEASE.md", "Preparar GitHub publico sem apagar historico util."),
    HelpDoc("release-packaging", "Estrategia de release", DOCS_ROOT / "release-packaging-strategy.md", "Backup local, export limpo e plano GitHub sem push automatico."),
    HelpDoc("clean-public-export", "Export publico limpo", DOCS_ROOT / "clean-public-v1-export.md", "Planejar, criar e validar export limpo sem reports ou secrets."),
    HelpDoc("public-readiness", "Gate publico final", DOCS_ROOT / "final-public-repo-readiness-gate.md", "Gate final antes de revisao humana para GitHub."),
    HelpDoc("contributing", "Contribuir", DOCS_ROOT / "CONTRIBUTING.md", "Padroes para contribuidor, testes e comandos novos."),
    HelpDoc("faq", "FAQ", DOCS_ROOT / "FAQ.md", "Perguntas simples para leigos."),
    HelpDoc("diagrams", "Diagramas", DOCS_ROOT / "diagrams" / "README.md", "Indice dos diagramas Mermaid."),
)

HELP_DOCS_BY_SLUG = {doc.slug: doc for doc in HELP_DOCS}
REQUIRED_DOC_PATHS = (
    README_PATH,
    DOCS_ROOT / "README.md",
    *(doc.path for doc in HELP_DOCS),
)


def list_help_docs() -> dict[str, Any]:
    docs = [
        {
            "slug": doc.slug,
            "title": doc.title,
            "description": doc.description,
            "path": doc.path.relative_to(REPO_ROOT).as_posix(),
            "exists": doc.path.is_file(),
        }
        for doc in HELP_DOCS
    ]
    return {"ok": all(item["exists"] for item in docs), "docs": docs, "count": len(docs)}


def load_help_doc(slug: str) -> tuple[HelpDoc, str, str]:
    if slug not in HELP_DOCS_BY_SLUG:
        raise HTTPException(status_code=404, detail="Documento de ajuda indisponivel.")
    doc = HELP_DOCS_BY_SLUG[slug]
    try:
        resolved = doc.path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Documento de ajuda indisponivel.") from exc
    docs_root = DOCS_ROOT.resolve(strict=True)
    if docs_root != resolved.parent and docs_root not in resolved.parents:
        raise HTTPException(status_code=404, detail="Documento fora da allowlist.")
    markdown = resolved.read_text(encoding="utf-8")
    return doc, markdown, render_markdown(markdown)


def render_markdown(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph)
            blocks.append(f"<p>{_inline_markdown(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("```"):
            if in_code:
                classes = f' class="language-{html.escape(code_lang)}"' if code_lang else ""
                code = html.escape("\n".join(code_lines))
                blocks.append(f"<pre><code{classes}>{code}</code></pre>")
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                flush_paragraph()
                flush_list()
                in_code = True
                code_lang = line[3:].strip()
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            text = _inline_markdown(heading.group(2).strip())
            blocks.append(f"<h{level}>{text}</h{level}>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            list_items.append(_inline_markdown(line[2:].strip()))
            continue
        if line.startswith("|"):
            flush_paragraph()
            flush_list()
            blocks.append(f'<pre class="markdown-table"><code>{html.escape(line)}</code></pre>')
            continue
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    if in_code:
        code = html.escape("\n".join(code_lines))
        blocks.append(f"<pre><code>{code}</code></pre>")
    return "\n".join(blocks)


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: _safe_link(match.group(1), match.group(2)),
        escaped,
    )
    return escaped


def _safe_link(label: str, target: str) -> str:
    if target.startswith(("http://", "https://", "javascript:", "data:")):
        return label
    if target.endswith(".md"):
        slug = _slug_for_doc_target(target)
        if slug:
            return f'<a href="/help/{slug}">{label}</a>'
    return f'<a href="{html.escape(target, quote=True)}">{label}</a>'


def _slug_for_doc_target(target: str) -> str | None:
    name = Path(target).name
    for doc in HELP_DOCS:
        if doc.path.name == name:
            return doc.slug
    return None


def check_help_docs(*, dry_run: bool = True) -> dict[str, Any]:
    missing = [path.relative_to(REPO_ROOT).as_posix() for path in REQUIRED_DOC_PATHS if not path.is_file()]
    slug_errors = [doc.slug for doc in HELP_DOCS if not re.fullmatch(r"[a-z0-9-]+", doc.slug)]
    mermaid_count = 0
    commands_documented = 0
    for path in REQUIRED_DOC_PATHS:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            mermaid_count += text.count("```mermaid")
            commands_documented += len(re.findall(r"`([a-z0-9][a-z0-9-]+)`", text))

    panel_status = None
    help_status = None
    doc_status = None
    traversal_status = None
    try:
        from app.web import create_app

        client = TestClient(create_app())
        panel_status = client.get("/").status_code
        help_status = client.get("/help").status_code
        doc_status = client.get("/help/getting-started").status_code
        traversal_status = client.get("/help/..%2FREADME.md").status_code
    except Exception as exc:  # pragma: no cover
        panel_status = f"error:{type(exc).__name__}"

    ok = (
        not missing
        and not slug_errors
        and mermaid_count >= 5
        and commands_documented >= 20
        and panel_status == 200
        and help_status == 200
        and doc_status == 200
        and traversal_status == 404
    )
    return {
        "ok": ok,
        "dry_run": dry_run,
        "missing": missing,
        "slug_errors": slug_errors,
        "docs_count": len(HELP_DOCS),
        "help_docs_list_ok": list_help_docs()["ok"],
        "mermaid_diagrams_count": mermaid_count,
        "commands_documented": commands_documented,
        "panel_status": panel_status,
        "help_status": help_status,
        "principal_doc_status": doc_status,
        "traversal_status": traversal_status,
        "traversal_blocked": traversal_status == 404,
        "no_push": True,
        "no_deploy": True,
        "no_paid_api": True,
        "no_secrets": True,
    }


def print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0
