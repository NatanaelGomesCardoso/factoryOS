# PRD - Expanded Bounded Live Canary V0

## Objetivo

Executar um canário live bounded expandido com até 6 steps e até 30 minutos, preservando os gates de segurança e o custo controlado.

## Requisitos

1. exigir `--bounded`, `--canary`, `--cost-aware`, `--no-push`, `--no-deploy`, `--no-paid-api` e `--no-secrets`;
2. validar rehearsal recente e review gate aprovado para a mesma run;
3. gerar report em `reports/expanded-bounded-live-canary/`;
4. registrar `changed_files`, `allowed_files`, `disallowed_files`, heads, token summary e decisão final;
5. só considerar `executed_live=true` quando todos os gates passarem.

## Segurança

- não confiar no frontend;
- não permitir push, deploy, API paga ou secrets;
- não aceitar alteração fora da whitelist de arquivos;
- manter a decisão final auditável em report.
