# Technical Spec — Explicit Task Metadata & Routing Contracts V0

## Módulo

`app/routing_contracts.py` centraliza:

- enums válidos do contrato;
- normalização/validação;
- detecção de contrato explícito;
- merge de task/run;
- resolução `run > task > heuristic`.

## Persistência

Tasks e runs aceitam campos opcionais de roteamento como chaves de topo no JSON. Arquivos legados continuam válidos porque todos os campos são opcionais.

## Regras

- Se houver metadata explícito, `routing_contract_version=v0` é obrigatório.
- Contrato inválido bloqueia `codex-plan` e `codex-context`.
- Sem metadata explícito: `valid=true`, `source=heuristic` e warning de fallback.
- `run-handoff` replica `routing_contract` no report final.

## CLI

- `routing-contract-validate --task-id <TASK_ID>`
- `routing-contract-validate --run-id <RUN_ID>`
- `task-create` e `run-create` aceitam flags de contrato explícito.

## Segurança

Somente valores enumerados ou textos curtos controlados. Nenhum path externo, nenhum live e nenhuma dependência de config global.
