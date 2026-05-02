# Reuse First - Capsule Execution Policy V0

## Objetivo

Encontrar o menor caminho seguro para executar tarefas simples e médias sem abrir o repo completo.

## Reuso desejado

- `codex_context_capsule`
- `codex_capsule_execution`
- `codex_context_router`
- `codex_profile`
- `factory_start`

## Hipótese

`codex-capsule-run` deve virar o caminho econômico padrão para `docs_only` e `code_small`.

## Critério de decisão

- usar cápsula quando a tarefa couber em contexto mínimo;
- usar `repo_quiet` quando o contexto precisar do repo mas ainda não exigir review pesado;
- usar `full_repo_review` para segurança ou revisão pesada;
- nunca liberar live diretamente.

## Saída esperada

- policy v0 com decisão explícita;
- baselines de tokens conhecidos;
- motivo claro para cada decisão;
- timeout classificado como recoverable_with_report.
