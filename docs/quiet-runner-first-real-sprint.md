# Quiet Runner First Real Sprint

## O que é

Primeiro canário real do FactoryOS executado via quiet runner com mudança controlada em um único arquivo esperado.

## Objetivo

Provar que uma sprint pequena real pode ser executada com terminal compacto sem abrir mão da segurança local.

## Regras

- permitir apenas `reports/quiet-runner-first-real-sprint/canary.txt` como saída esperada;
- bloquear qualquer outro arquivo modificado;
- não usar push, deploy, API paga ou segredos;
- manter o terminal compacto.

## Evidências

- report em `reports/quiet-runner-first-real-sprint-execution-v0-proof.txt`;
- canary em `reports/quiet-runner-first-real-sprint/canary.txt`.

## Status esperado

- `changed_files_ok=true`
- `terminal_ok=true`
- `overall_status=ok` ou `ok_with_captured_warnings`
