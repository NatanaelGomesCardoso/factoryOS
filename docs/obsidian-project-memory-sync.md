# Obsidian Project Memory Sync V0

Sincronização curta e segura de memória do projeto para o vault local.

## Comandos

- `obsidian-project-sync --project <NAME> --dry-run`
- `obsidian-project-sync --project <NAME> --write`

## Regras

- `--dry-run` é o padrão;
- `--write` só com flag explícita;
- destino permitido apenas dentro de `<OBSIDIAN_VAULT>/10-Projetos/FactoryOS/`;
- nota curta, sem logs grandes e sem segredos;
- manter `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`.
