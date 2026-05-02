# SPEC Técnica — Painel Web Local V1

## Decisão arquitetural

Usar FastAPI + Jinja2 + CSS simples.

## Estrutura proposta

Arquivos previstos:

- `app/web.py`
- `app/panel_data.py`
- `app/templates/base.html`
- `app/templates/index.html`
- `app/static/style.css`

## Endpoints

### GET `/health`

Retorna JSON:

{
  "ok": true,
  "service": "factoryos-panel"
}

### GET `/`

Renderiza página HTML com:

- título do FactoryOS;
- status básico;
- últimos commits;
- últimos reports;
- discoveries;
- docs úteis;
- aviso read-only.

## Regras

- O painel V1 é read-only.
- Não executa Codex.
- Não altera arquivos.
- Não lê segredos.
- Não expõe `.env`, `auth.json`, tokens ou chaves.
- Deve rodar apenas localmente em `127.0.0.1`.

## Coleta de dados

Usar Python para ler:

- `git log --oneline -5`;
- arquivos em `reports/`;
- arquivos em `specs/discovery/`;
- arquivos em `docs/`.

## Dependências permitidas

- FastAPI;
- Uvicorn;
- Jinja2.

## Evitar na V1

- React;
- Vite;
- Streamlit;
- NiceGUI;
- banco obrigatório;
- websocket obrigatório.

## Validação esperada

- `python3 -m py_compile app`
- `python3 -m app.web`
- `curl http://127.0.0.1:8787/health`
