# Painel local

O painel local é uma interface read-only para acompanhar FactoryOS no navegador.

## Como abrir

```bash
.venv/bin/python -m app.web
```

Abra `http://127.0.0.1:8787`.

## Rotas principais

- `GET /`: dashboard local.
- `GET /health`: healthcheck JSON.
- `GET /view/{area}/{file_path}`: viewer read-only de áreas permitidas.
- `GET /help`: índice da Ajuda.
- `GET /help/{doc_slug}`: documento da Ajuda por slug allowlist.

## Aba Ajuda

A Ajuda lista docs principais e renderiza Markdown local. HTML bruto é escapado. Mermaid aparece como bloco de código legível, sem execução de JS externo.

## Viewer read-only

O viewer bloqueia:

- path traversal;
- caminho absoluto;
- arquivo oculto;
- symlink;
- nomes sensíveis;
- arquivo grande demais;
- diretório.

## Como interpretar cards/status

Cards resumem estado operacional: reports recentes, readiness, hygiene, runs, filas e ações sugeridas. Eles ajudam a decidir o próximo comando, mas não substituem validação de terminal.
