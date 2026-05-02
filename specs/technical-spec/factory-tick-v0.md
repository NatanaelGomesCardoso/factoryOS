# SPEC Tecnica - Factory Tick V0

## Decisao

Implementar um tick síncrono, local e explícito que compõe readiness, sync plan, handoff e dry-run em um único comando auditável. O tick V0 não executa live real de Codex.

## Estados do tick

- `passed`
- `blocked`
- `failed`
- `dry_run_only`

## Arquivos alvo

- `app/factory_tick.py`
- `app/cli.py`
- `app/panel_data.py`
- `app/templates/index.html`
- `app/static/style.css`
- `reports/factory-tick-v0-proof.txt`
- `specs/discovery/reuse-first-factory-tick-v0.md`
- `specs/prd/factory-tick-v0-prd.md`
- `specs/sprints/015-factory-tick-v0.json`

## Entrada

- `run_id`

## Saida

- report JSON do tick em `reports/factory-ticks/<tick-id>.json`
- JSON no stdout com:
  - `ok`
  - `mode`
  - `tick_id`
  - `run_id`
  - `task_id`
  - `started_at`
  - `finished_at`
  - `status`
  - `readiness_status`
  - `sync_plan_status`
  - `handoff_report_path`
  - `tick_report_path`
  - `executed_live`
  - `decision`

## Pre-checagens

1. run existe;
2. run está `running`;
3. workspace readiness é `ready`;
4. sync plan é `already_current`.

## Acoes

1. chamar `run-handoff`;
2. chamar `run-execute --dry-run`;
3. validar o report JSON produzido;
4. registrar report do tick;
5. retornar o report no stdout.

## Regras de decisao

- `dry_run_only`:
  - pre-checagens aprovadas;
  - handoff concluído;
  - dry-run concluído;
  - `executed_live=false`.
- `blocked`:
  - run inexistente;
  - run não está `running`;
  - readiness diferente de `ready`;
  - sync plan diferente de `already_current`.
- `failed`:
  - handoff falhou;
  - dry-run falhou;
  - report JSON inválido;
  - qualquer erro inesperado da orquestração.

## Validacoes de seguranca

- validar `run_id` com bloqueio de path traversal;
- bloquear `--live` com erro explícito nesta sprint;
- não usar `shell=True`;
- não permitir execução live real;
- não alterar worktree;
- não alterar segredos;
- não fazer deploy.

## Integracao com painel

- o painel continua read-only;
- o último Factory Tick pode aparecer com status, run, mode, readiness, sync plan, `executed_live` e link para o report;
- não há botão nem formulário.

## Fora de escopo

- execução live real de Codex;
- daemon;
- scheduler;
- factory-start;
- retry loop;
- PR automático;
- deploy;
- GitHub/Linear;
- execução paralela;
- MCP.
