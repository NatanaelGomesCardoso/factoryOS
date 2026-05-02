# Segurança — Task Runner V0

## Escopo

Registrar os controles de segurança do Task Runner V0 local do FactoryOS.

## Regra crítica

- regra crítica, permissão e decisão de estado ficam no backend local;
- o frontend/painel apenas exibe o estado já validado;
- segredo, token, cookie e credencial não entram no runner nem no painel;
- o runner não executa comandos externos.

## Controles obrigatórios

- bloquear caminho absoluto;
- bloquear `..`;
- bloquear symlink;
- validar JSON antes de mover;
- rejeitar id inválido ou inexistente;
- não sobrescrever task existente;
- manter arquivos somente em `tasks/pending/`, `tasks/running/`, `tasks/done/` e `tasks/failed/`.

## Teste de abuso

- `task-start ../evil`;
- `task-finish inexistente`;
- `task-fail` em payload corrompido;
- `task-create` com duplicidade;
- arquivo com `status` incompatível com a pasta.

## Gate local

- rodar `harness security-doctor --source-root <FACTORYOS_ROOT> --strict` antes de encerrar a sprint;
- registrar o resultado em `reports/` para auditoria local.

## Observação

Este projeto continua local e read-only na camada do painel. A mutação fica restrita ao runner CLI e ao filesystem permitido.
