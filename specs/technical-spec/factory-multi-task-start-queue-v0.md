# SPEC Tecnica - Factory Multi-Task Start Queue V0

## Decisao

Criar um planner local de fila curta que consome task candidates de intake e tasks pendentes sem alterar estado.

## Fluxo

1. validar flags e limites;
2. ler intake recente e tasks pendentes;
3. aplicar routing por categoria;
4. selecionar ate `max_tasks`;
5. gravar report em `reports/factory-queue-starts/<timestamp>.json`.

## Guardrails

- dry-run ou plan-only apenas;
- nao tocar em running/failed;
- `live_canary` permanece gated;
- `security_review` e `heavy_review_only` podem ficar em full_repo_review ou blocked;
- `executed_live=false` em todos os casos.
