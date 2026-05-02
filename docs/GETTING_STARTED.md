# Primeiros passos

Este guia mostra como abrir o FactoryOS no seu computador. Ele não faz deploy, não faz push e não usa API paga.

## O que é

FactoryOS é uma fábrica local de projetos. Ele ajuda a organizar uma ideia, criar tarefas, preparar execução controlada, validar resultado e guardar reports.

## Para que serve

Serve para sair de uma conversa ou PRD e chegar em um projeto verificável, sem depender de automação solta. ChatGPT atua como arquiteto e revisor; Codex atua como executor técnico controlado.

## Como abrir o projeto

```bash
cd <FACTORYOS_ROOT>
```

Veja se o Git está limpo:

```bash
git status --short --branch
```

## Como ativar a `.venv`

Se a `.venv` já existe:

```bash
. .venv/bin/activate
```

Se precisar criar:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Como rodar o painel

```bash
.venv/bin/python -m app.web
```

Abra:

```text
http://127.0.0.1:8787
```

A Ajuda local fica em:

```text
http://127.0.0.1:8787/help
```

## Como validar

Validações básicas:

```bash
.venv/bin/python -m py_compile app/web.py app/help_center.py app/cli.py
.venv/bin/python -m app.cli help-docs-list
.venv/bin/python -m app.cli help-docs-check --dry-run
git diff --check
```

Resultado esperado: comandos terminam sem erro, `/help` responde 200 e tentativa de traversal em `/help/..%2FREADME.md` responde 404.
