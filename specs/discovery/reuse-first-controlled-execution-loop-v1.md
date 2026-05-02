# Reuse First Discovery

## Ideia

Evoluir o `factory-loop` para V1 usando o estado higienizado e uma seleção automática segura quando existir exatamente uma run elegível.

## Reaproveitamento obrigatório

- `factory-loop` V0;
- `factory-state-audit` e `factory-state-plan`;
- `run-workspace-readiness`;
- `run-workspace-sync-plan`;
- `factory-tick`;
- `execution-evaluate`.

## Decisão V1

Continuar explícito, local e síncrono, sem daemon, sem scheduler e sem live, mas com:

- seleção automática por elegibilidade real;
- summary de hygiene embutido no report;
- decisão final menos ambígua em dry-run.

## Restrições

Sem criar run automaticamente, sem `factory-start` ainda, sem execução paralela e sem live Codex.
