# PRD - Codex CLI Output Suppression & Quiet Runner V0

## Problema

Saídas grandes de Codex ainda custam caro quando `diff`, JSON gigante ou summaries longos entram no terminal.

## Objetivo

Criar um runner local silencioso que capture logs em arquivo, reporte métricas compactas e não exponha patch bruto no terminal.

## Não objetivos

- não executar live sem gate;
- não instalar dependências externas;
- não usar API paga;
- não apagar reports antigos;
- não alterar harness global.

## Comandos esperados

- `codex-quiet-run`
- `codex-quiet-ab-report`

## Segurança

- stdout e stderr sempre em arquivo;
- diff-like lines registradas, nunca expostas brutas;
- `--execute` só com `FACTORYOS_ENABLE_QUIET_CODEX=1`;
- sem segredos em logs ou reports.

## Critérios de pronto

- dry-run gera report compacto;
- execute canary pequeno funciona ou bloqueia com motivo seguro;
- report inclui tokens, bytes, linhas e diff-like lines;
- CLI continua sem output gigante.
