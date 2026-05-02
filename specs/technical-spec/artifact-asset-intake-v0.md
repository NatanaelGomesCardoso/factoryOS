# SPEC Técnica - Artifact / Asset Intake V0

## Fluxo

1. validar `project` e `source`;
2. resolver path com segurança;
3. bloquear extensões perigosas e traversal;
4. classificar itens;
5. gravar report local em `reports/artifact-intakes/`.

## Segurança

- somente dry-run;
- sem cópia real;
- sem segredos;
- sem deploy.
