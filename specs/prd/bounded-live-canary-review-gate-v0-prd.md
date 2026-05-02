# PRD - Bounded Live Canary Review Gate V0

## Contexto

O bounded live canary da Sprint 035 já foi executado e aprovado. Ainda falta um gate formal de revisão que consolide as evidências e negue qualquer expansão live direta.

## Objetivo

Gerar um review gate estruturado que confirme a aprovação do canário para fins de política futura, mas mantenha `allowed_to_execute_live=false`.

## Requisitos

1. O comando aceita `--run-id` e, se simples, `--report`.
2. O gate localiza o report bounded live canary e a avaliação relacionada.
3. O gate valida cost audit, harness/bwrap, flags de segurança e heads intactos.
4. O gate nunca libera live maior nesta sprint.
5. O resultado final expõe `approved_for_expansion_policy`, `allowed_to_execute_live` e `next_gate_requires_new_sprint`.
