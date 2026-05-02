# Reuse First — Minimal Codex Context Capsule V0

## Objetivo

Criar uma cápsula Git mínima para executar Codex com menos contexto automático do que o repo FactoryOS completo.

## Reaproveitar

- `app/codex_context_router.py`
- `app/memory_digest.py`
- `app/codex_quiet_runner.py`
- `app/report_index.py`
- `reports/` e `specs/` já existentes

## Decisão V0

A cápsula fica em `workspaces/codex-capsules/<timestamp>-<label>/`, recebe `AGENTS.md` mínimo, copia apenas os includes explícitos e pode incluir o digest mais recente quando disponível.

## Fora de escopo

- alterar `~/.codex/config.toml`
- mexer no harness global
- executar live automático
- copiar reports grandes ou segredos

