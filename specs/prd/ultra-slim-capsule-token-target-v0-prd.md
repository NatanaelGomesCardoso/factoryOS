# PRD — Ultra Slim Capsule Token Target V0

## Objetivo

Reduzir o canário `execute` de cápsula para `<=7000` tokens ou provar localmente que o menor modo write seguro ainda fica acima do alvo.

## Requisitos

- CLI aceita `--capsule-mode ultra_slim_min`.
- Modo mínimo não inclui docs nem digest.
- Prompt final fica abaixo de `500` bytes no canário.
- Report inclui bytes de prompt, AGENTS, manifest, cápsula total, cápsula sem Git e hooks Git.
- Se `tokens_used > 7000`, report registra `floor_estimate_tokens` e recomendação explícita.

## Fora de Escopo

- Mudança de política live.
- Deploy.
- Aplicação real de patches.
- Uso de API paga.
