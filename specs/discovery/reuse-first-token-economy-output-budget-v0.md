# Reuse First Discovery

## Ideia

Sprint 040 Token Economy & Output Budget Enforcement V0

## Criado em

2026-05-01T00:00:00-03:00

## Objetivo desta etapa

Reduzir custo operacional no FactoryOS/Codex limitando stdout grande, saída final gigante e handoffs verbosos.

## O que já existe no repo

- `app/codex_handoff.py` para gerar prompt e report de handoff;
- `app/factory_start.py` para prompts de canary e expedição;
- `app/codex_context_router.py` para montar contexto;
- `app/codex_cost_audit.py` com parsing parcial de tokens;
- `reports/` como fonte de prova local.

## Alternativas consideradas

| Opção | Tipo | Custo | Risco | Decisão |
|---|---|---|---|---|
| continuar sem contrato explícito | improviso | alto | alto | rejeitar |
| regex pontual em cada comando | remendo | médio | médio | rejeitar |
| módulo reutilizável de output budget + parser local | contrato explícito | baixo | baixo | adotar |

## Decisão final

- [x] criar contrato compacto reutilizável;
- [x] criar parser local de token usage;
- [x] produzir reports compactos e evidência detalhada em arquivos;
- [ ] despejar JSON grande em terminal;
- [ ] depender de API paga.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e implementar os comandos e o contrato de handoff.
