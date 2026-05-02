# PRD - Controlled Execution Loop V1

## Problema

O loop V0 ainda exige inspeção demais quando a fila está limpa, porque decide apenas por runs `running` e não por elegibilidade real.

## Objetivo

Evoluir o `factory-loop` para V1, integrando o estado de hygiene e selecionando automaticamente uma única run elegível quando isso for seguro.

## Reuso primeiro

- `factory-loop` V0
- `factory-state-audit` e `factory-state-plan`
- `run-workspace-readiness`
- `run-workspace-sync-plan`
- `factory-tick`
- `execution-evaluate`

## Regras V1

- com `--run-id`, manter o fluxo explícito do V0 e marcar `auto_selected=false`;
- sem `--run-id`, selecionar automaticamente apenas quando houver exatamente uma run `running` elegível;
- elegível significa `readiness=ready` e `sync_plan=already_current`;
- zero elegíveis resulta em `blocked`;
- mais de uma elegível resulta em `needs_review`;
- `--live` continua bloqueado;
- o report precisa incluir `loop_version`, `auto_selected`, `eligible_runs_count` e summary de hygiene.

## Critérios de pronto

- `factory-loop --max-steps 1 --dry-run` funciona com e sem `--run-id`;
- a seleção automática segura funciona;
- o painel continua read-only e mostra os campos novos;
- nenhuma execução live nova acontece.
