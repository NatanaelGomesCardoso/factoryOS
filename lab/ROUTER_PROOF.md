# FactoryOS Local Task Router — Proof

## Objetivo

Validar um roteador local barato para decidir quando chamar ou não o Codex.

## Resultado esperado

- Tarefas simples de documentação/copy não devem chamar Codex.
- Bugfix de código deve chamar Codex.
- Auth, segurança, pagamento, banco, deploy ou dados sensíveis devem parar para revisão humana/ChatGPT antes de qualquer execução.

## Casos validados

- docs_readme -> local_only
- small_bugfix -> codex_needed
- auth_security -> human_review
- frontend_copy -> local_only

## Conclusão

O roteador local com regras Python + Ollama pode economizar chamadas Codex e proteger áreas críticas.

## Limite

A LLM local não é fonte de verdade. Regras Python de segurança sempre vencem.
