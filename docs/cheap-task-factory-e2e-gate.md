# Cheap Task Factory E2E Gate V0

## O que é

Gate ponta a ponta para provar o caminho barato via cápsula em tarefas `docs_only` e `code_small`.

## Para que serve

- confirmar que a policy local escolhe `capsule`;
- criar a cápsula mínima;
- rodar um canário curto dentro da cápsula;
- gerar diff e export-plan sem aplicar nada no repo real;
- consolidar um report final com economia estimada e sinais de segurança.

## Comando

- `cheap-task-factory-e2e --category docs_only --label <LABEL> --dry-run`
- `cheap-task-factory-e2e --category docs_only --label <LABEL> --execute-canary`

