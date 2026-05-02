# SPEC Técnica — Task Runner V0

## Decisão técnica

Implementar o runner em Python puro, com JSON e filesystem local, usando as pastas já existentes em `tasks/`.

## Arquivos previstos

- `app/task_runner.py`
- `app/cli.py`
- `app/panel_data.py`

## Formato mínimo da task

```json
{
  "id": "...",
  "title": "...",
  "description": "...",
  "status": "pending|running|done|failed",
  "risk": "low|medium|high",
  "executor": "manual|local|codex",
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "notes": []
}
```

## Regras de implementação

- gerar `id` seguro e legível;
- criar sempre em `tasks/pending/`;
- mover o arquivo entre pastas ao mudar o status;
- validar JSON antes de mover;
- bloquear path traversal e qualquer caminho arbitrário;
- não sobrescrever task existente;
- não executar comandos externos;
- não chamar Codex;
- manter o painel read-only e compatível com a fila local.

## Contrato da CLI

- `task-create <title> --description ... --risk ... --executor ...`
- `task-list`
- `task-start <id>`
- `task-finish <id>`
- `task-fail <id>`

## Observações de segurança

- a regra crítica fica no backend;
- o frontend/painel apenas exibe o estado;
- o runner não deve ler nem escrever secrets;
- os arquivos válidos são sempre internos ao diretório `tasks/`.

## Controles de segurança

- id do usuário validado por regex restritiva;
- caminho absoluto e path traversal bloqueados;
- symlink bloqueado antes de qualquer leitura;
- JSON validado antes de mover;
- destino nunca é sobrescrito silenciosamente;
- comandos externos não são executados;
- a transição de status só aceita estados de origem explícitos.

## Plano de abuso

- `task-start ../evil` precisa falhar;
- `task-finish inexistente` precisa falhar;
- `task-create` não pode sobrescrever task com id repetido;
- arquivo com JSON inválido precisa ser rejeitado;
- arquivo com `status` incompatível com a pasta precisa falhar.

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool specs/sprints/006-task-runner-v0.json`
- smoke tests da CLI para create/list/start/finish/fail
- erro para id inexistente
- bloqueio de path traversal
- `git diff --check`
