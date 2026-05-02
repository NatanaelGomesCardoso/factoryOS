# Reuse First Discovery - FactoryOS V1 Readiness Gate V0

## Ideia

Criar um gate local de prontidão para a etapa V1 do FactoryOS antes das auditorias e correções futuras.

## Objetivo

Decidir se o FactoryOS já está pronto para avançar para auditoria, correção e lapidação sem depender de execução live ou de ações destrutivas.

## O que reutilizar

- CLI existente;
- reports já produzidos;
- painel local;
- evaluator MVP;
- delivery package dry-run;
- report retention cleanup plan;
- Obsidian sync dry-run;
- quiet runner status contract.

## Decisão esperada

- `ready_for_audit` quando tudo bater;
- `needs_review` quando houver lacuna observável;
- `failed` apenas quando um requisito crítico quebrar.
