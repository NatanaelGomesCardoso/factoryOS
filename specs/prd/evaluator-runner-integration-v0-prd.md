# PRD - Evaluator Runner Integration V0

## Objetivo

Permitir avaliar uma task localmente, registrar o resultado em JSON no disco e exibir o ultimo resultado da task no painel.

## Problema

O task runner e o evaluator ja existem, mas ainda vivem separados. Hoje e possivel registrar e mover tasks, e tambem avaliar sinais simples, mas nao existe um fluxo unificado para avaliar uma task especifica e persistir esse resultado localmente.

## Solucao V0

Adicionar uma integracao local minima:

- um comando futuro `task-evaluate <id>`;
- geracao de um report JSON por task em `reports/task-evaluations/`;
- reaproveitamento do evaluator atual em Python puro;
- exibicao do ultimo resultado da task no painel;
- manutencao do painel como read-only.

## Fora de escopo

- execucao automatica de Codex;
- Celery, Prefect, APScheduler ou worker externo;
- scheduling;
- fila distribuida;
- subprocesso para rodar outra ferramenta;
- API paga;
- banco de dados;
- escrita arbitraria fora do caminho definido pela SPEC.

## Regras de produto

- avaliar uma task nao deve mudar o status da task;
- o report da avaliacao deve ser local e legivel;
- o painel deve mostrar o ultimo resultado sem permitir mutacao;
- o fluxo deve continuar local-first;
- o caminho do report deve permanecer relativo ao repo;
- nenhuma regra critica pode depender do frontend.

## Segurança

- validar id com regex restritiva;
- bloquear path traversal e caminho absoluto;
- rejeitar symlink;
- nao executar comandos externos;
- nao chamar Codex;
- nao aceitar caminho arbitrario para salvar report;
- nao expor caminho absoluto no JSON ou no painel;
- manter o painel read-only.

## Casos de abuso

- tentar `task-evaluate ../evil`;
- tentar `task-evaluate <TMP_DIR>/evil`;
- tentar `task-evaluate inexistente`;
- avaliar task em `pending`;
- avaliar task em `running`;
- avaliar task em `done`;
- avaliar task em `failed`;
- tentar salvar report fora de `reports/task-evaluations/`;
- tentar reutilizar o fluxo para acionar Codex;
- tentar ler ou exibir caminho absoluto.

## Criterios de pronto

- existe um comando futuro `task-evaluate <id>`;
- o comando gera um JSON de avaliacao por task;
- o JSON inclui decisao, risco, motivo, proxima acao e checks falhos;
- o report fica em `reports/task-evaluations/` ou caminho equivalente definido na SPEC;
- o painel mostra o ultimo resultado da task;
- o painel continua read-only;
- abuso e estados invalidos sao tratados com erro explicito.
