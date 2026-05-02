# PRD — Factory Long Run Dry-Run Planner V0

## Problema

O FactoryOS já consegue preparar runs, avaliar contexto e controlar custo, mas ainda não existe um planner explícito para simular uma rodada longa de forma segura antes do live.

## Objetivo

Criar um comando `factory-long-run-plan` que consolide readiness, sync-plan, routing contract, perfil Codex, orçamento de contexto e higiene operacional em um único report dry-run.

## Requisitos

- `factory-long-run-plan --run-id <RUN_ID> --target-minutes 30 --max-steps 6`
- auto seleção apenas quando houver exatamente uma run elegível;
- `--live` deve bloquear com mensagem clara;
- `allowed_to_execute_live=false` sempre;
- `required_manual_review=true` sempre;
- gerar report em `reports/factory-long-run-plans/`.

## Não Objetivos

- executar `factory-loop` live;
- fechar tasks/runs automaticamente;
- limpar reports ou worktrees.
