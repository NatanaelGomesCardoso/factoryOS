# PRD - Codex Execution Handoff V0

## Problema

O FactoryOS já consegue criar runs locais, mas ainda não possui um handoff controlado para preparar a execução futura do Codex com prompt, comando, budgets e report local.

## Objetivo

Criar um fluxo local e seguro para montar o handoff de uma run existente, com modo dry-run por padrão e live bloqueado por variável de ambiente.

## Não objetivos

- não executar Codex automaticamente no fluxo normal;
- não criar loop;
- não criar daemon;
- não criar scheduler;
- não criar App Server;
- não criar MCP;
- não integrar GitHub ou Linear;
- não fazer deploy;
- não usar API paga;
- não criar `factory-start` ainda.

## Usuário

Quem opera o FactoryOS localmente e precisa preparar uma run para execução futura sem perder rastreabilidade, segurança e validação.

## Comandos esperados

- `python -m app.cli run-handoff <run-id>`
- `python -m app.cli run-execute <run-id> --dry-run`
- `python -m app.cli run-execute <run-id> --live`

## Segurança

- validar `run_id`;
- bloquear path traversal;
- exigir run existente em `running`;
- manter `shell=False`;
- impedir live sem `FACTORYOS_ENABLE_LIVE_CODEX=1`;
- não registrar segredos, tokens, cookies ou credenciais;
- não expor caminho absoluto desnecessário;
- manter frontend e painel apenas leitura;
- manter backend como fonte de verdade.

## Gate local de segurança

O comportamento seguro padrão do produto é:

- `run-execute` sem flag roda em dry-run;
- `run-execute --live` fica bloqueado sem `FACTORYOS_ENABLE_LIVE_CODEX=1`;
- o frontend nunca decide execução, caminho ou permissões;
- a regra crítica, permissões e validações ficam no backend;
- o painel só mostra snapshot e não cria mutação.

## Budgets

Usar o budget existente da run:

- `max_codex_runs`;
- `max_retry_attempts`;
- `max_changed_files`;
- `max_minutes`;
- `model`;
- `reasoning_effort`;
- `stop_on_security_risk`.

## Critérios de pronto

- `run-handoff` gera prompt e report locais;
- `run-execute --dry-run` gera report sem executar Codex;
- `run-execute --live` falha sem a variável de ambiente;
- report JSON e prompt existem em `reports/run-handoffs/`;
- o painel continua read-only e mostra o último handoff;
- a execução live não é usada nos testes desta sprint;
- o repo continua validando com `git diff --check`.
