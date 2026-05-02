# PRD — Task Runner V0

## Objetivo

Criar um runner local simples para controlar o ciclo de vida de tasks do FactoryOS sem executar Codex automaticamente.

## Problema

Hoje as tasks existem como pastas no filesystem e o painel já mostra o estado, mas ainda não há um fluxo local padronizado para criar, iniciar, concluir e falhar tasks com validação de JSON e proteção contra paths perigosos.

## Solução V0

Implementar um runner local em Python puro que:

- cria tasks em `tasks/pending/`;
- move tasks entre `pending`, `running`, `done` e `failed`;
- valida o JSON antes de qualquer movimento;
- bloqueia path traversal e caminhos arbitrários;
- lista tasks agrupadas por status;
- mantém o painel consistente com o filesystem.

## Fora do escopo

- executar Codex automaticamente;
- usar Celery, Dramatiq, Prefect ou APScheduler;
- usar banco de dados;
- usar API paga;
- criar UI de edição de task no painel;
- automatizar deploy;
- mexer em secrets.

## Regras de produto

- a task é um arquivo JSON local;
- o `id` deve ser gerado de forma segura e legível;
- não sobrescrever task existente sem erro explícito;
- não aceitar caminho arbitrário do usuário;
- não executar comandos externos;
- não depender de serviços externos.

## Segurança

- regra crítica, transição de estado e validação ficam no backend local;
- o frontend/painel apenas exibe dados já validados;
- nunca aceitar `..`, caminho absoluto ou symlink como entrada;
- nunca ler ou escrever secrets;
- o runner deve falhar de forma explícita para id inexistente ou arquivo inválido.

## Teste de abuso

- tentar `task-start ../evil`;
- tentar `task-finish` para um id inexistente;
- tentar criar task com id duplicado;
- tentar mover JSON fora do contrato;
- validar que o runner não executa comandos externos.

## Critérios de pronto

- `task-create` cria task em `tasks/pending/`;
- `task-start` move de `pending` para `running`;
- `task-finish` move de `running` para `done`;
- `task-fail` move de `pending` ou `running` para `failed`;
- `task-list` mostra todas as tasks por status;
- id inexistente gera erro explícito;
- path traversal é bloqueado;
- o painel reflete contagens reais das pastas.
