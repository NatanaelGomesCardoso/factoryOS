# SPEC Técnica — Status da fila no painel

## Decisão técnica

Reaproveitar as pastas em `tasks/` como fonte de dados read-only.

## Arquivos prováveis

- `app/panel_data.py`
- `app/templates/index.html`
- `app/static/style.css`

## Mudança esperada

Adicionar função em `panel_data.py` para coletar:

- status da fila;
- contagem por pasta;
- lista curta de arquivos recentes.

## Estrutura esperada no template

Adicionar uma seção visual com quatro grupos:

- Pendentes;
- Rodando;
- Concluídas;
- Falhas.

## Regras

- read-only;
- não executar Codex;
- não criar, editar, mover ou apagar tasks;
- não ler segredos;
- não quebrar o painel atual.

## Validação

- `python -m compileall app`;
- `python -m py_compile app/*.py`;
- iniciar `python -m app.web`;
- abrir painel no navegador;
- confirmar seção de fila visível.
