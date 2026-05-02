# Guia de uso

Este guia explica como usar o FactoryOS no dia a dia.

## Iniciar projeto novo

1. Escreva a ideia em linguagem simples.
2. Use ChatGPT para criar PRD, SPEC e sprints.
3. Use `project-intake-create` para transformar documentos em intake local.
4. Use `mvp-build-plan-create --dry-run` para planejar.
5. Use cápsula ou run controlada somente depois de validar o plano.

Exemplo seguro:

```bash
.venv/bin/python -m app.cli project-intake-create --project-name meu-projeto --prd docs/prd.md --spec docs/spec.md --sprints specs/sprints --dry-run
```

## Retomar projeto antigo

Use Reversa quando o projeto já existe e precisa ser entendido antes de mexer.

Fluxo seguro:

```bash
.venv/bin/python -m app.cli reversa-global-check
.venv/bin/python -m app.cli reversa-project-plan --target <CODE_ROOT>/projeto-antigo --dry-run
.venv/bin/python -m app.cli reversa-project-status --target <CODE_ROOT>/projeto-antigo
.venv/bin/python -m app.cli reversa-project-sdd-intake --target <CODE_ROOT>/projeto-antigo --dry-run
```

## Usar Reversa

Reversa serve para mapear estrutura, estado e artefatos de um projeto antigo. No FactoryOS V0, comandos de Reversa são guardados por alvo, bloqueiam `factoryos` e `harness` por padrão e não fazem instalação live.

## Ler reports

Reports ficam em `reports/`. Eles são evidência local: dizem o comando, o estado, a decisão e o próximo passo.

Comandos úteis:

```bash
.venv/bin/python -m app.cli report-list factory-start --limit 5
.venv/bin/python -m app.cli report-latest factory-start
```

## Onde aprovar ou revisar

Revise antes de qualquer ação que toque:

- autenticação;
- autorização;
- pagamento;
- dados sensíveis;
- banco de dados;
- deploy;
- secrets;
- mudança estrutural em projeto de outra pessoa.

O FactoryOS gera planos e reports; a aprovação humana decide quando sair do dry-run.
