# Reuse First Discovery

## Ideia

Sprint 042 Codex CLI Output Suppression & Quiet Runner V0

## Objetivo desta etapa

Reduzir custo de terminal e de logs ao executar Codex localmente.

## O que já existe no repo

- `app/output_budget.py`
- `app/token_usage.py`
- `app/codex_handoff.py`
- `app/factory_start.py`
- `reports/token-economy/`

## Alternativas consideradas

| Opção | Tipo | Custo | Risco | Decisão |
|---|---|---|---|---|
| imprimir diff e summary no terminal | padrão antigo | alto | alto | rejeitar |
| guardar logs em arquivo e resumir no terminal | fluxo silencioso | baixo | baixo | adotar |
| depender de ferramenta externa paga | dependência externa | alto | alto | rejeitar |

## Decisão final

- [x] criar quiet runner local;
- [x] salvar stdout/stderr/combined em arquivo;
- [x] extrair tokens e métricas compactas;
- [x] impedir patch bruto no terminal;
- [ ] depender de API paga.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e implementar o runner e o comando de comparação.
