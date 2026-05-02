# PRD — Status da fila no painel

## Objetivo

Adicionar ao painel local V1 uma seção read-only para mostrar o estado da fila de tasks do FactoryOS.

## Problema

Hoje o operador precisa olhar pastas no terminal para saber se existem tarefas pendentes, rodando, concluídas ou com falha.

## Solução V1

Ler as pastas `tasks/pending`, `tasks/running`, `tasks/done` e `tasks/failed` e mostrar contagem/lista no painel.

## Funcionalidades

- mostrar quantidade de tasks pendentes;
- mostrar quantidade de tasks rodando;
- mostrar quantidade de tasks concluídas;
- mostrar quantidade de tasks com falha;
- listar alguns arquivos recentes por status;
- manter painel read-only.

## Fora do escopo

- criar worker;
- executar Codex;
- mover task de status;
- editar task pelo painel;
- banco obrigatório;
- autenticação.

## Critérios de pronto

- painel mostra seção de fila;
- contagens aparecem mesmo se pastas estiverem vazias;
- página continua abrindo em `127.0.0.1:8787`;
- `/health` continua funcionando;
- nenhuma escrita de arquivo é feita pelo painel.
