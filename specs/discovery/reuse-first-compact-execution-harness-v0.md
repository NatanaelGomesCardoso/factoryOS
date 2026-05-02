# Reuse First Discovery

## Ideia

Sprint 043 Compact Execution Harness V0

## Objetivo desta etapa

Padronizar budgets por categoria e consolidar a recomendação de execução compacta em FactoryOS.

## O que já existe no repo

- `app/output_budget.py`
- `app/token_usage.py`
- `app/codex_handoff.py`
- `app/factory_start.py`
- `app/codex_quiet_runner.py`

## Alternativas consideradas

| Opção | Tipo | Custo | Risco | Decisão |
|---|---|---|---|---|
| manter budget só em texto | manual | médio | médio | rejeitar |
| criar budget por categoria e check local | contrato explícito | baixo | baixo | adotar |
| expandir para live automático | acoplamento alto | alto | alto | rejeitar |

## Decisão final

- [x] criar budget por categoria;
- [x] criar check local de logs;
- [x] criar report consolidado;
- [x] recomendar quiet runner no handoff;
- [ ] liberar raw codex exec como padrão.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e integrar o budget compacto ao handoff e ao factory-start.
