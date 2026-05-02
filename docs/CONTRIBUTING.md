# Contribuindo

Obrigado por querer contribuir. FactoryOS é local-first e seguro por padrão; contribuições devem preservar isso.

## Como contribuir

1. Leia `README.md` e `docs/README.md`.
2. Rode o painel e os checks locais.
3. Faça mudanças pequenas e reversíveis.
4. Atualize docs e reports quando mudar comportamento.
5. Não faça push ou deploy automático.

## Padrões de segurança

- Não coloque segredo no repo.
- Não coloque regra crítica no frontend.
- Não use API paga sem pedido explícito.
- Não automatize ChatGPT web.
- Não altere configuração global do Codex.
- Pare para revisão humana em auth, autorização, pagamento, dados sensíveis, banco, deploy ou segurança crítica.

## Testes e validação

Validações mínimas para mudança em docs/painel:

```bash
.venv/bin/python -m py_compile app/web.py app/help_center.py app/cli.py
.venv/bin/python -m compileall app ><TMP_DIR>/factoryos-compileall.txt
.venv/bin/python -m app.cli help-docs-check --dry-run
git diff --check
```

## Commits

Use conventional commits quando o mantenedor pedir commit. Exemplo:

```text
feat: add complete documentation and local help center v0
```

## Onde não mexer sem autorização

- Secrets e arquivos `.env`.
- `<CODEX_HOME>/config.toml`.
- `<HARNESS_ROOT>`.
- Worktrees existentes.
- Reports antigos.
- Deploy, push, fetch, pull ou rebase.

## Como adicionar comando novo

1. Implemente a função no módulo certo.
2. Registre subparser em `app/cli.py`.
3. Defina se é dry-run, se altera arquivos e que report gera.
4. Adicione validação.
5. Atualize `docs/COMMANDS.md`.
6. Se aparecer no painel, mantenha read-only e sem secrets.
