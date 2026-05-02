# Reuse First — Explicit Task Metadata & Routing Contracts V0

## Objetivo

Reduzir heurística frágil por título/descrição, permitindo metadados explícitos de roteamento em task e run.

## Reaproveitar

- `app/task_runner.py` e `app/run_workspace.py` para persistir metadados opcionais sem quebrar JSON legado;
- `app/codex_profile.py` para preferência por hint explícito de perfil;
- `app/codex_context_router.py` para contexto por categoria com fallback heurístico;
- `app/codex_handoff.py` para carregar o contrato no report de handoff.

## Decisão V0

Criar um schema leve e local em `app/routing_contracts.py`, com validação centralizada, merge `run > task`, fallback heurístico e bloqueio conservador quando o metadata explícito for inválido.

## Fora de Escopo

- executar Codex live;
- alterar formatos antigos de task/run de forma incompatível;
- mudar harness, config global ou scheduler/daemon.
