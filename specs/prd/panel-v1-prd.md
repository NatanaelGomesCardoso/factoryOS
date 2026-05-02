# PRD — Painel Web Local do FactoryOS V1

## Objetivo

Criar um painel web local, leve e simples para acompanhar o estado do FactoryOS sem precisar abrir VS Code o tempo todo.

## Usuário

Natan, operador leigo em programação, usando WSL/local para conduzir criação de MVPs com ChatGPT, Codex, Ollama, Git e harness.

## Problema

Hoje o estado do FactoryOS aparece apenas no terminal e em arquivos. Para rodadas longas, isso dificulta acompanhar:

- último status;
- últimas decisões;
- arquivos gerados;
- reports;
- docs/specs;
- próximos passos.

## Solução

Criar uma primeira versão de painel web local com:

- FastAPI;
- Jinja2;
- CSS simples;
- leitura de arquivos locais;
- sem login;
- sem banco obrigatório;
- sem execução automática de Codex.

## Funcionalidades V1

1. Página inicial `/`.
2. Healthcheck `/health`.
3. Mostrar últimos commits do repo.
4. Mostrar arquivos recentes em `reports/`.
5. Mostrar arquivos em `specs/discovery/`.
6. Mostrar links para docs principais.
7. Mostrar aviso de segurança: painel local e read-only na V1.
8. Não executar Codex.
9. Não alterar arquivos pelo painel.

## Fora do escopo

- login;
- multiusuário;
- deploy;
- execução de Codex;
- edição de arquivos;
- fila real em SQLite;
- WebSocket/SSE;
- UI complexa;
- React/Vite.

## Critérios de pronto

- `python3 -m py_compile app` passa.
- Servidor local sobe em `127.0.0.1`.
- `/health` retorna JSON simples.
- `/` renderiza HTML.
- Página mostra commits, reports, discoveries e docs.
- Sem segredos expostos.
- Sem escrita em arquivos via painel.
