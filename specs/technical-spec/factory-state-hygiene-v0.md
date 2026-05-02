# Factory State Hygiene V0

## Escopo

Implementar comandos locais para auditar e normalizar o estado de tasks e runs antigas:

- `factory-state-audit`
- `factory-state-plan`
- `factory-state-apply --dry-run`
- `factory-state-apply --execute`

O painel deve expor o último report de higiene sem mutação.

## Reuso primeiro

Usar os comandos e funções já existentes:

- `task-list`;
- `run-list`;
- `task-show`;
- `run-show`;
- `task-finish`;
- `run-finish`;
- reports e proofs antigos em `reports/`;
- leitura read-only do painel em `app/panel_data.py`.

## Comandos

### `factory-state-audit`

- listar contagem de tasks por estado;
- listar contagem de runs por estado;
- listar tasks running antigas;
- listar runs running antigas;
- cruzar `task_id` e `run_id` quando possível;
- verificar a existência de proofs/reports locais;
- gerar JSON em `reports/factory-state-hygiene/<timestamp>-audit.json`.

### `factory-state-plan`

- gerar um plano conservador;
- classificar cada item como:
  - `safe_to_close`;
  - `needs_review`;
  - `blocked`;
- não mutar nada;
- gerar JSON em `reports/factory-state-hygiene/<timestamp>-plan.json`.

### `factory-state-apply --dry-run`

- executar o plano sem mutar;
- mostrar o que seria fechado;
- gerar JSON de simulação;
- nunca mover arquivos.

### `factory-state-apply --execute`

- fechar apenas itens `safe_to_close`;
- nunca apagar nada;
- nunca remover worktrees;
- nunca tocar em branches;
- nunca executar Codex live;
- registrar tudo em report local.

## Modelo de hygiene report

Campos mínimos:

- `ok`;
- `kind`;
- `generated_at`;
- `report_path`;
- `view_path`;
- `counts.tasks`;
- `counts.runs`;
- `stats.running_tasks_count`;
- `stats.running_runs_count`;
- `stats.safe_to_close_count`;
- `stats.needs_review_count`;
- `stats.blocked_count`;
- `targets[]`.

Cada target deve registrar:

- `kind`;
- `id`;
- `status`;
- `decision`;
- `reason`;
- `age_days`;
- `linked_runs` ou `task_id`;
- `supporting_files`.

## Plano de fechamento

O plano deve ser conservador:

- `safe_to_close` quando houver prova/report local suficiente;
- `needs_review` quando faltar evidência ou houver ambiguidade;
- `blocked` quando o item for da sprint atual ou não puder ser validado.

## Fora de escopo

- deletar arquivos;
- remover worktrees;
- executar live;
- merge/rebase/fetch/pull;
- limpar branches;
- automatizar deploy;
- integrar GitHub/Linear;
- criar daemon ou scheduler.

## Validação

- `task-list`;
- `run-list`;
- `factory-state-audit`;
- `factory-state-plan`;
- `factory-state-apply --dry-run`;
- JSON válido dos reports;
- `TestClient` com `base_url=http://127.0.0.1` e `GET / = 200`;
- `git diff --check`.
