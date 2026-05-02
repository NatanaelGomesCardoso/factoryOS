# Segurança

FactoryOS é local-first e seguro por padrão. Segurança aqui significa controlar onde comandos rodam, o que podem ler, o que podem escrever e quando uma pessoa precisa revisar.

## Ameaças principais

- Vazamento de secrets em frontend, logs, reports, vault ou GitHub.
- Execução automática em projeto errado.
- Deploy ou push não autorizado.
- Uso acidental de API paga.
- Regra crítica implementada no frontend.
- Limpeza apagando report antigo, worktree ou artefato útil.

## Bloqueios padrão

- `no_push`: não fazer push automaticamente.
- `no_deploy`: não fazer deploy automaticamente.
- `no_paid_api`: não usar API paga sem pedido explícito.
- `no_secrets`: não mexer em secrets, tokens, cookies ou credenciais.

## Segredos

Secrets não entram no frontend, nos reports públicos, no Obsidian, em logs compartilhados ou em docs. Se um segredo real aparecer, a correção não é só remover do arquivo: é registrar risco e rotacionar/revogar fora do FactoryOS.

## Revisão de leak público

Antes de qualquer plano de publicação, rode:

```bash
.venv/bin/python -m app.cli public-export-leak-review --dry-run
```

O report redige achados e mostra somente path e categoria. Termos como token, key, secret, password, `.env`, `<FACTORYOS_ROOT>`, `<PROJECT_ROOT>`, `<OBSIDIAN_VAULT>` e caminhos temporários não devem expor valores. Referências de política de segurança podem ser falso positivo, mas `safe_to_push` continua falso até revisão humana.

## Allowlist de paths

Execução controlada deve declarar caminhos permitidos. Cápsulas e runners devem operar em workspaces isolados ou source roots explícitos. Reversa bloqueia alvos protegidos como `<FACTORYOS_ROOT>` e `<PROJECT_ROOT>/harness` para instalação ou mutação automática.

## Frontend não recebe segredo

O painel local é read-only. Ele mostra status, cards, reports e docs. Ele não deve decidir autorização, preço, quota, deploy, transição crítica ou permissão.

## Painel read-only

Rotas de leitura usam allowlist e bloqueiam path traversal, arquivos ocultos, symlink e nomes sensíveis. A Ajuda local só permite slugs conhecidos.

## Limpeza segura

Não apagar reports antigos, worktrees ou artefatos sem plano. Use auditoria e dry-run:

```bash
.venv/bin/python -m app.cli deep-hygiene-audit --dry-run
.venv/bin/python -m app.cli cleanup-plan --audit-report reports/<arquivo>.json --dry-run
.venv/bin/python -m app.cli cleanup-apply --cleanup-plan reports/<arquivo>.json --dry-run
```

## Quando exigir revisão humana

Pare para revisão quando a tarefa envolver autenticação, autorização, pagamento, dados sensíveis, banco de dados, deploy, segurança crítica, alteração estrutural em projeto colaborativo ou instalação live em projeto antigo.
