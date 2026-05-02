# PRD - Long Run Expansion Policy V0

## Contexto

A Sprint 036 aprovou o review gate do bounded live canary, mas ainda não libera expansão live maior. A próxima etapa precisa ser apenas uma política explícita, conservadora e rastreável.

## Objetivo

Definir a política de expansão para o próximo gate de long run live, mantendo `allowed_to_execute_live=false` e exigindo nova sprint para qualquer execução futura.

## Requisitos

1. O comando aceita `--run-id`, `--target-minutes 30` e `--max-steps 6`.
2. O gate consome o review gate aprovado da Sprint 036.
3. O gate valida cost audit, maintenance plan e factory state atual.
4. O resultado expõe níveis, critérios e bloqueios de expansão.
5. A política nunca executa live nesta sprint.
