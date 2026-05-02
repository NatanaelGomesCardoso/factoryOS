from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.panel_data import (
    VIEWABLE_AREAS,
    _format_mtime,
    _human_size,
    build_panel_snapshot,
    repo_root,
)
from app.help_center import HELP_DOCS_BY_SLUG, list_help_docs, load_help_doc

HOST = "127.0.0.1"
PORT = 8787

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
MAX_VIEW_BYTES = 256 * 1024
SENSITIVE_EXACT_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "auth.json",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".token"}
AREA_LABELS = {
    "reports": "Reports",
    "docs": "Docs",
    "discovery": "Discovery",
    "prd": "PRD",
    "technical-spec": "Technical Spec",
    "sprints": "Sprints",
    "tasks": "Tasks",
}


@dataclass(frozen=True, slots=True)
class FileViewSnapshot:
    area: str
    area_label: str
    requested_path: str
    repo_relative_path: str
    resolved_path: str
    modified_at: str
    size_label: str
    content_kind: str
    content: str
    notice: str | None = None


def _is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered in SENSITIVE_EXACT_NAMES:
        return True
    return any(lowered.endswith(suffix) for suffix in SENSITIVE_SUFFIXES)


def _view_area_root(repo: Path, area: str) -> Path:
    try:
        relative_root = VIEWABLE_AREAS[area]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Área desconhecida.") from exc

    try:
        root = (repo / relative_root).resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Área indisponível.") from exc

    if not root.is_dir():
        raise HTTPException(status_code=404, detail="Área indisponível.")

    return root


def _resolve_view_path(repo: Path, area: str, file_path: str) -> tuple[Path, Path, Path]:
    root = _view_area_root(repo, area)

    if not file_path or not file_path.strip():
        raise HTTPException(status_code=400, detail="Caminho vazio.")

    raw_path = Path(file_path)
    if raw_path.is_absolute():
        raise HTTPException(status_code=400, detail="Caminho absoluto não permitido.")

    if any(part in {"..", "."} for part in raw_path.parts):
        raise HTTPException(status_code=400, detail="Path traversal não permitido.")

    if any(part.startswith(".") for part in raw_path.parts):
        raise HTTPException(status_code=404, detail="Arquivo oculto não permitido.")

    if _is_sensitive_name(raw_path.name):
        raise HTTPException(status_code=404, detail="Arquivo sensível não permitido.")

    candidate = root.joinpath(*raw_path.parts)

    current = root
    for part in raw_path.parts:
        current = current / part
        if current.is_symlink():
            raise HTTPException(status_code=404, detail="Symlink não permitido.")

    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Arquivo inexistente.")

    resolved = candidate.resolve(strict=True)
    if root not in resolved.parents:
        raise HTTPException(status_code=404, detail="Caminho fora da área permitida.")

    if resolved.is_dir():
        raise HTTPException(status_code=404, detail="Diretório não permitido.")

    if resolved.stat().st_size > MAX_VIEW_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite seguro de leitura.")

    return root, candidate, resolved


def _load_file_view(repo: Path, area: str, file_path: str) -> FileViewSnapshot:
    root, requested, resolved = _resolve_view_path(repo, area, file_path)
    raw_bytes = resolved.read_bytes()

    notice: str | None = None
    content_kind = "text"
    content = ""

    if b"\x00" in raw_bytes:
        notice = "Arquivo binário ou não textual; conteúdo não exibido."
        content_kind = "binary"
    else:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            notice = "Arquivo não textual ou com codificação incompatível."
            content_kind = "binary"
        else:
            if resolved.suffix.lower() == ".json":
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    content = text
                    content_kind = "text"
                else:
                    content = json.dumps(parsed, ensure_ascii=False, indent=2)
                    content_kind = "json"
                    notice = "JSON formatado para leitura."
            else:
                content = text

    if not content and raw_bytes == b"":
        notice = "Arquivo vazio."

    return FileViewSnapshot(
        area=area,
        area_label=AREA_LABELS.get(area, area),
        requested_path=requested.relative_to(root).as_posix(),
        repo_relative_path=resolved.relative_to(repo).as_posix(),
        resolved_path=str(resolved),
        modified_at=_format_mtime(resolved),
        size_label=_human_size(resolved.stat().st_size),
        content_kind=content_kind,
        content=content,
        notice=notice,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="FactoryOS Panel",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse({"ok": True, "service": "factoryos-panel"})

    @app.get("/")
    def index(request: Request):
        snapshot = build_panel_snapshot(repo_root())
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "snapshot": snapshot,
            },
        )

    @app.get("/help", name="help_index")
    def help_index(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="help.html",
            context={
                "docs": list_help_docs()["docs"],
            },
        )

    @app.get("/help/{doc_slug}", name="help_doc")
    def help_doc(request: Request, doc_slug: str):
        if doc_slug not in HELP_DOCS_BY_SLUG:
            raise HTTPException(status_code=404, detail="Documento de ajuda indisponivel.")
        doc, markdown, html_content = load_help_doc(doc_slug)
        return templates.TemplateResponse(
            request=request,
            name="help_doc.html",
            context={
                "doc": doc,
                "markdown": markdown,
                "html_content": html_content,
            },
        )

    @app.get("/view/{area}/{file_path:path}", name="view_file")
    def view_file(request: Request, area: str, file_path: str):
        view = _load_file_view(repo_root(), area, file_path)
        return templates.TemplateResponse(
            request=request,
            name="file_view.html",
            context={
                "view": view,
            },
        )

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
