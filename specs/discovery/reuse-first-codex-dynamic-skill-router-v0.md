# Reuse First — Codex Dynamic Skill Router V0

## Objetivo

Reduzir prompt gigante e escolher contexto mínimo para Codex por tipo de task/run.

## Reaproveitar

- `app/codex_profile.py` para perfil recomendado.
- `app/codex_handoff.py` para report/prompt local.
- `app/report_index.py` para selecionar reports recentes.
- Specs por sprint em `specs/`.

## Decisão V0

Criar roteador local de contexto/skills como nomes e documentos recomendados. Não alterar skills globais, plugins, `~/.codex` ou harness global.

## Fora de Escopo

- Alterar `~/.codex`.
- Remover plugins ou skills reais.
- Mexer no harness global.
- Executar Codex live.
- Implementar daemon, scheduler, MCP novo ou execução paralela.
