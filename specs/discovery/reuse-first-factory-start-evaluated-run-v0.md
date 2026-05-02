# Reuse First — Factory Start Evaluated Run V0

## Objetivo

Fazer o `factory-start` produzir uma execução avaliada automaticamente, em dry-run e no live canary bounded, sem loop longo.

## Reuso obrigatório

- reaproveitar `factory-start` V0;
- reaproveitar `execution-evaluate`;
- reaproveitar `report_index`;
- reaproveitar `factory-loop` V1;
- reaproveitar o live canary bounded já entregue.

## Decisão V0

- `factory-start --evaluate` roda a execução bounded;
- depois localiza o source report correto;
- gera `execution-evaluation`;
- grava `evaluation_report`, `evaluation_decision`, `final_decision` e `final_status` no report do `factory-start`;
- não cria retry loop;
- não cria loop longo.

## Fora de escopo

- retry automático;
- loop longo;
- merge;
- push;
- deploy;
- API paga;
- secrets.
