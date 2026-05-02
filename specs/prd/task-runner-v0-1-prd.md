# PRD - Task Runner V0.1

## Objetivo

Melhorar a usabilidade operacional do Task Runner local do FactoryOS sem mudar a arquitetura base em Python puro, JSON e filesystem.

## Problema

O runner V0 controla o ciclo de vida das tasks, mas ainda falta ergonomia para operacao diaria: localizar uma task especifica, registrar notas sem mutar estado e abrir o JSON correspondente no painel com seguranca.

## Solucao V0.1

Adicionar pequenas melhorias de uso humano:

- `task-show <id>` para inspecionar uma task em qualquer status;
- `task-note <id> "texto"` para registrar anotacoes sem alterar o status;
- link seguro "Ver" no painel para abrir o JSON da task;
- exibicao mais util da fila com titulo, risk, executor e `updated_at` quando disponivel.

## Fora do escopo

- executar Codex automaticamente;
- usar Celery, Dramatiq, Prefect ou APScheduler;
- usar banco de dados;
- usar API paga;
- criar editor de task no painel;
- automatizar deploy;
- expor secrets ou caminhos absolutos.

## Regras de produto

- a task continua sendo um JSON local;
- o `id` continua legivel e seguro;
- `task-note` nao altera status nem pasta;
- o painel continua read-only;
- o viewer usa apenas a rota backend segura existente;
- nenhuma regra critica fica no frontend.

## Segurança

- bloquear path traversal, caminho absoluto e symlink;
- nao aceitar `task-show ../evil` nem `task-note ../evil`;
- nao abrir secrets;
- nao executar comandos externos;
- nao chamar Codex;
- validar JSON antes e depois da escrita de notas;
- manter o caminho exibido relativo ao repo.

## Teste de abuso

- tentar `task-show ../evil`;
- tentar `task-note ../evil "texto"`;
- tentar `task-show inexistente`;
- tentar `task-note inexistente "texto"`;
- tentar `task-note <id> ""`;
- tentar abrir `GET /view/tasks/../requirements.txt`;
- tentar abrir task JSON por um caminho fora de `tasks/`.

## Criterios de pronto

- `task-show` retorna JSON da task encontrada em `pending`, `running`, `done` ou `failed`;
- `task-show` falha explicitamente para id inexistente;
- `task-note` adiciona a nota ao array `notes`;
- `task-note` atualiza `updated_at` e preserva status e pasta;
- o painel mostra titulo, risk, executor e `updated_at` quando disponivel;
- o painel oferece link "Ver" para o JSON da task;
- a rota de viewer aceita apenas caminhos seguros dentro de `tasks/`;
- o painel continua sem acoes de mutacao.
