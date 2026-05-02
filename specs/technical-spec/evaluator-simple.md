# SPEC Técnica — Evaluator simples local

## Decisão técnica

Implementar evaluator em Python puro, sem dependência nova.

## Arquivos prováveis

- `app/evaluator.py`
- `app/cli.py`
- `reports/evaluator-simple-proof.json`

## Entrada

Campos booleanos simples:

- `python_ok`;
- `json_ok`;
- `browser_ok`;
- `security_ok`;
- `high_risk`.

## Saída

JSON com:

- `decision`;
- `risk`;
- `reason`;
- `next_action`.

## Regras de decisão

- se `security_ok=false`, retornar `stopped_security`;
- se `high_risk=true`, retornar `needs_chatgpt_review`;
- se qualquer validação comum falhar, retornar `failed_retryable`;
- se tudo passar, retornar `passed`.

## Validação

- `python -m py_compile app/*.py`;
- comando CLI com caso passed;
- comando CLI com caso security fail;
- comando CLI com caso retryable fail;
- JSON gerado válido.
