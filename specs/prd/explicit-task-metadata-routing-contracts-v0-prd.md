# PRD — Explicit Task Metadata & Routing Contracts V0

## Problema

O roteamento atual depende demais de heurísticas sobre título e descrição. Isso aumenta fragilidade, ambiguidade e risco de escolher perfil/contexto errados em rodadas futuras mais longas.

## Objetivo

Adicionar metadados explícitos opcionais em task/run, com contrato validável por CLI e uso preferencial por `codex-plan`, `codex-context` e `run-handoff`.

## Requisitos

- Criar schema `v0` com `factory_category`, `codex_profile_hint`, `context_policy`, `live_policy` e overrides opcionais.
- Permitir metadata opcional em task e run sem quebrar tasks/runs antigas.
- Comando `routing-contract-validate --task-id` e `--run-id`.
- `codex-plan` e `codex-context` devem preferir metadata explícita.
- Metadata inválida deve bloquear com motivo claro.
- `run-handoff` deve incluir `routing_contract`.

## Não Objetivos

- executar live;
- remover fallback heurístico;
- migrar automaticamente dados antigos.
