# PRD - Memory Digest & Context Retrieval V0

## Problema

O FactoryOS está acumulando muito contexto porque o router e o handoff podem acabar puxando reports demais para a mesma retomada.

## Objetivo

Criar um digest curto de memória e fazer o router preferir esse digest antes de abrir reports grandes.

## Não objetivos

- não criar banco novo;
- não criar serviço externo;
- não usar API paga;
- não expor segredo;
- não copiar reports gigantes para o digest.

## Comandos esperados

- `python -m app.cli memory-digest-create --title <TITLE> --source-report <PATH> --sprint <N>`
- `python -m app.cli memory-digest-latest`
- `python -m app.cli memory-digest-list --limit <N>`

## Segurança

- digest deve ficar curto;
- digest deve ser versionado localmente;
- digest não deve conter segredo;
- reports grandes entram só quando o digest não for suficiente.

## Critérios de pronto

- digest JSON e MD gerados;
- latest e list funcionam;
- `codex-context` expõe digest curto;
- router evita reports grandes quando digest atende;
- repo segue validando com `git diff --check`.
