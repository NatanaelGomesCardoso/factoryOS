# Deep Project Hygiene & External Artifact Cleanup Audit V0

Esta auditoria prepara a limpeza profunda pós-Sprint 080 sem apagar arquivos.

## Comandos

```bash
./factoryos-deep-hygiene-audit --dry-run
./factoryos-deep-hygiene-audit --dry-run --include-external
```

## Escopo

- Dentro do FactoryOS: caches, logs temporários, arquivos `.tmp`, `.bak`, `.old`, `.pyc`, diretórios de validação gerados e reports grandes.
- Em `<TMP_DIR>`: apenas prefixos explicitamente relacionados a FactoryOS/Codex.
- Em `<USER_HOME>`: pastas iniciadas com `_`.
- Em `<CODE_ROOT>`: outros projetos, repos Git e harness são protegidos.

## Segurança

`safe_delete_candidate` só é emitido para runtime/cache/temp interno do FactoryOS, fora de Git, sem segredo e sem relação com harness/vault. Caminhos externos e pastas iniciadas com `_` ficam em revisão humana.

O report sempre mantém `safe_to_apply=false` na auditoria V0.
