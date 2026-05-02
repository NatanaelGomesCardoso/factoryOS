# Quiet Runner Status Contract

## Objetivo

Separar o status da execução do Codex do status de orçamento de saída. Log capturado grande, truncado ou acima do budget deve ficar visível sem transformar uma execução válida em falso negativo.

## Campos

- `execution_status`: `succeeded`, `failed` ou `timeout`.
- `budget_status`: `ok`, `warn` ou `blocked`.
- `terminal_status`: `ok`, `warn` ou `blocked`.
- `captured_log_status`: `ok`, `warn` ou `blocked`.
- `overall_status`: `succeeded`, `succeeded_with_budget_warnings`, `failed` ou `timeout`.
- `report_ok`: sucesso operacional da execução.
- `budget_ok`: `false` quando o budget ficou bloqueado, mesmo que a execução tenha sucedido.

## Regras

Quando `exit_code=0`, `timeout=false`, JSON final valido e sem erro interno, a execução é `succeeded`. Nessa condição, `overall_status` deve ser `succeeded` ou `succeeded_with_budget_warnings`, nunca `blocked` apenas por `captured_log_status=blocked`.

Timeout continua `execution_status=timeout` e `overall_status=timeout`. Exit code diferente de zero ou erro interno continua `execution_status=failed` e `overall_status=failed`.

Budget/log grande deve aparecer em `budget_status`, `captured_log_status`, `warnings` e `budget_ok`. Isso indica que o report precisa de revisão de orçamento ou limpeza de ruído, mas não exige recovery automático quando a execução terminou com sucesso.

## Recovery

Fazer recovery quando:

- `execution_status=failed`;
- `execution_status=timeout`;
- o JSON estiver ausente, vazio ou inválido;
- houver bloqueio não relacionado a budget, como violação de segurança, terminal visível fora do limite ou arquivo alterado fora do escopo permitido.

Não fazer recovery automático apenas por `budget_status=blocked` quando `execution_status=succeeded` e `overall_status=succeeded_with_budget_warnings`. Nesse caso, revisar logs/proofs, reduzir ruído futuro e manter o sucesso operacional.

## codex-run-result-check

O checker imprime resumo compacto com `json_ok`, `execution_status`, `budget_status`, `overall_status`, `timeout`, `exit_code`, `report_ok` e `budget_ok`.

Retornos:

- `0`: JSON válido e `execution_status=succeeded`, mesmo com budget warning ou blocked.
- `1`: `execution_status=failed` ou `execution_status=timeout`.
- `2`: arquivo ausente, vazio, symlink, JSON inválido ou JSON que não seja objeto.
