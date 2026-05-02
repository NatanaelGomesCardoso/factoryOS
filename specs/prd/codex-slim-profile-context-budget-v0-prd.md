# PRD — Codex Slim Profile Context Budget V0

## Problema

O FactoryOS já validou dry-run, evaluated run e canário live bounded, mas o uso de Codex ainda pode carregar contexto e perfil maiores que o necessário.

## Objetivo

Criar uma política local de perfis Codex e orçamento de contexto que gere plano antes da execução, bloqueie budgets excedidos e preserve a configuração global.

## Requisitos

- Listar perfis locais: `local_no_codex`, `codex_mini_low`, `codex_mini_medium`, `codex_standard_medium`, `codex_heavy_review_only`.
- Classificar task/run por risco, executor, dry-run/live, steps, arquivos estimados e tipo.
- Estimar contexto antes de execução.
- Expor `codex-plan --task-id` e `codex-plan --run-id`.
- Enriquecer `run-handoff` com perfil, modelo, reasoning, context budget e budget status.
- Bloquear plano quando contexto ou arquivos excederem o budget.

## Não Objetivos

- Não alterar `~/.codex/config.toml`.
- Não executar Codex live.
- Não remover skills.
- Não mexer no harness global.
