# SPEC Tecnica - Memory Digest & Context Retrieval V0

## Componentes

- `app/memory_digest.py`
- `app/codex_context_router.py`
- `app/codex_handoff.py`
- `app/cli.py`

## Digest schema

```json
{
  "ok": true,
  "digest_version": "v0",
  "title": "...",
  "sprint": "040",
  "created_at": "...",
  "source_reports": [],
  "commits": [],
  "decision": "...",
  "summary": "...",
  "key_files": [],
  "main_reports": [],
  "risks": [],
  "next_step": "...",
  "token_summary": {},
  "do_not_expand_by_default": true
}
```

## Regras

- digest JSON recomendado abaixo de 20 KB;
- digest Markdown recomendado abaixo de 150 linhas;
- se exceder, registrar warning;
- router deve preferir o digest mais recente;
- reports grandes só entram quando o digest não existir ou não for suficiente.

## Validação

- `python -m py_compile app/*.py`
- `python -m compileall app`
- `python -m json.tool specs/sprints/041-memory-digest-context-retrieval-v0.json`
- `python -m app.cli memory-digest-create --title ... --source-report ... --sprint 040`
- `python -m app.cli memory-digest-latest`
- `python -m app.cli memory-digest-list --limit 5`
- `python -m app.cli codex-context --run-id <RUN_ID>`

## Fora de escopo

- banco novo;
- serviço externo;
- live Codex;
- deploy;
- API paga.
