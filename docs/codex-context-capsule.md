# Cápsula de Contexto Codex V0

## O que é

A cápsula de contexto é um workspace Git mínimo criado a partir de um `source_root` para executar Codex com menos contexto automático.

## Para que serve

- reduzir custo de prompt em tarefas simples e médias;
- copiar apenas os arquivos incluídos explicitamente;
- carregar um digest de memória recente quando existir;
- manter um manifest local que descreve o que entrou na cápsula;
- permitir inspeção e gate de exportação sem tocar no repo real.

## Regras

- não copiar `reports/` grandes;
- não copiar `.venv/`, `workspaces/`, `node_modules/`, logs grandes ou segredos;
- manter a cápsula como Git repo independente;
- registrar o report local em `reports/codex-context-capsules/`.

## Comandos

- `codex-capsule-create`
- `codex-capsule-list`
- `codex-capsule-inspect`

## Manifest mínimo

- `capsule_version`
- `source_root`
- `label`
- `included_files`
- `excluded_patterns`
- `latest_digest_path`
- `total_bytes`
- `max_context_bytes`
- `created_at`
- `report_path`

