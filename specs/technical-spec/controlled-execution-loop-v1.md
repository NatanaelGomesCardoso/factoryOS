# SPEC Técnica - Controlled Execution Loop V1

## Seleção automática segura

Sem `--run-id`, o loop deve:

1. listar runs `running`;
2. calcular elegibilidade por run com `run-workspace-readiness` e `run-workspace-sync-plan`;
3. selecionar automaticamente apenas se existir exatamente uma run elegível;
4. retornar `blocked` se houver zero elegíveis;
5. retornar `needs_review` com lista curta se houver mais de uma elegível.

## Report V1

O report de `reports/factory-loops/` deve incluir:

- `loop_version = v1`
- `auto_selected`
- `eligible_runs_count`
- `hygiene.running_tasks_count`
- `hygiene.running_runs_count`
- `hygiene.safe_to_close_count`
- `hygiene.needs_review_count`
- `hygiene.blocked_count`

## Decisão final

- `dry_run_only` quando readiness, sync plan, tick seco e avaliação local passarem;
- `blocked` quando pré-condição falhar;
- `failed` quando a avaliação local falhar;
- `needs_review` quando a seleção automática for ambígua.

## Guardrails

- `--live` retorna erro claro;
- não cria run automaticamente;
- não executa Codex live;
- não implementa daemon, scheduler ou `factory-start`;
- mantém o painel read-only.
