# PRD - Quiet Runner Budget Calibration V0

## Problema

O quiet runner ainda marcava `ok=false` quando o log capturado continha linhas parecidas com diff, mesmo com terminal visível compacto.

## Objetivo

Separar o budget do terminal visível do budget do log capturado para permitir `warn` no captured sem perder a economia do runner.

## Não objetivos

- não executar live;
- não usar API paga;
- não apagar reports antigos;
- não mexer em harness global;
- não relaxar segurança.

## Comandos esperados

- `codex-quiet-run`
- `compact-exec-check`

## Segurança

- stdout e stderr seguem em arquivo;
- captured diff-like lines viram warning quando aceitáveis;
- bloqueio continua para limite forte, segredos, push, deploy ou API paga.

## Critérios de pronto

- report traz status separado de terminal e captured;
- execução pequena real pode sair `ok` ou `ok_with_captured_warnings`;
- comandos antigos seguem funcionando.
