# SPEC Técnica - First Real Project Workspace Scaffold V0

## Decisão

Adicionar um comando para criar um workspace local controlado em `workspaces/projects/<slug>`.

## Regras

1. aceitar `--dry-run` ou `--create-workspace`;
2. criar apenas diretório local controlado;
3. gerar `README.md` e `PROJECT_STATE.md`;
4. não instalar dependências;
5. não fazer `git init` por padrão;
6. não fazer push ou deploy;
7. reportar o resultado em `reports/project-workspaces/`.

## Campos principais

- `workspace_path`;
- `created_files`;
- `existing_files`;
- `git_init=false`;
- `no_push=true`;
- `no_deploy=true`.

