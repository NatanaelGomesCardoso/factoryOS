# PRD - Quiet Runner First Real Sprint Execution V0

## Problema

Precisamos provar que o quiet runner não serve só para dry-run ou canários abstratos: ele precisa executar uma mudança real pequena com saída compacta e controle de arquivos.

## Objetivo

Executar um canário real mínimo que crie apenas `reports/quiet-runner-first-real-sprint/canary.txt`.

## Não objetivos

- não fazer deploy;
- não fazer push;
- não usar API paga;
- não tocar em segredos;
- não alterar mais de um arquivo.

## Segurança

- `changed_files_ok` deve ser verdadeiro;
- `no_push`, `no_deploy`, `no_paid_api` e `no_secrets` devem ser verdadeiros;
- qualquer arquivo fora da allowlist bloqueia o canário.

## Critérios de pronto

- report do canário mostra status separado de terminal e captured;
- somente o arquivo canário é alterado;
- a execução termina com terminal compacto.
