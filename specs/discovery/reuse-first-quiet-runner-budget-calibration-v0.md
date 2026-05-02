# Reuse First Discovery

## Ideia

Sprint 044 Quiet Runner Budget Calibration V0

## Objetivo desta etapa

Separar budget de terminal visível e budget de log capturado para o quiet runner.

## O que já existe no repo

- `app/codex_quiet_runner.py`
- `app/compact_execution_harness.py`
- `app/output_budget.py`
- `app/cli.py`
- `reports/codex-quiet-runs/`

## Alternativas consideradas

| Opção | Tipo | Custo | Risco | Decisão |
|---|---|---|---|---|
| manter um único budget para tudo | regra antiga | alto | alto | rejeitar |
| separar terminal e captured com warning para diff-like capturado | fluxo calibrado | baixo | baixo | adotar |
| bloquear qualquer diff-like capturado automaticamente | conservador demais | médio | alto | rejeitar |

## Decisão final

- [x] separar `terminal_visible_budget` e `captured_log_budget`;
- [x] tratar diff-like lines capturadas como warning quando dentro do limite;
- [x] bloquear apenas por limite forte ou violação de segurança;
- [ ] voltar ao terminal bruto.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e validar o runner pequeno real.
