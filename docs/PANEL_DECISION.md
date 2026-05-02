# Decisão Arquitetural — Painel Web Local

## Contexto

O FactoryOS precisa de um painel leve para acompanhar progresso, decisões de rota, reports e estado futuro da fila.

## Decisão

A V1 do painel usará:

- FastAPI;
- Jinja2;
- CSS simples;
- leitura de arquivos locais;
- sem frontend build.

## Evolução futura

- HTMX para interações parciais;
- SSE para atualização em tempo real;
- SQLite quando a fila de tarefas estiver pronta;
- Playwright para validar tela.

## Não usar na V1

- React/Vite;
- Streamlit;
- NiceGUI;
- dashboard pesado;
- login/autenticação;
- deploy externo.

## Critério de pronto

O painel V1 estará pronto quando abrir localmente em `127.0.0.1`, mostrar status básico, ler reports locais e não exigir build frontend.
