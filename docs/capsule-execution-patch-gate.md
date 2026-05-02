# Capsule Execution & Patch Gate V0

## O que é

Fluxo local para executar Codex dentro de uma cápsula, medir o custo real e gerar um plano de exportação controlado.

## Para que serve

- rodar Codex com `cwd` apontando para a cápsula;
- capturar tokens, linhas e bytes de saída;
- salvar diff da cápsula sem imprimir patch bruto;
- comparar cápsula com `source_root` antes de qualquer aplicação;
- manter o `apply` apenas em dry-run nesta sprint.

## Comandos

- `codex-capsule-run`
- `codex-capsule-diff`
- `codex-capsule-export-plan`
- `codex-capsule-apply`

## Gate local

- apenas arquivos permitidos pelo manifest entram no plano;
- arquivos extras da cápsula não são exportados automaticamente;
- o `apply` permanece bloqueado para escrita real nesta versão;
- o canário deve provar economia de tokens sem alterar o repo real.

