# FactoryOS — Regras para Agentes

## Papéis

- ChatGPT: arquiteto, orquestrador, revisor e criador de specs.
- Codex: executor técnico controlado.
- Ollama/local LLM: triagem, resumo, checklist e validação simples.
- Harness: validação, segurança, memória e integração com o ecossistema local.

## Regras obrigatórias

- Não usar OpenAI API paga.
- Não automatizar ChatGPT web por navegador.
- Não colocar segredo, token, cookie ou credencial no repo.
- Não confiar no frontend para regra crítica.
- Separar backend e frontend.
- Não usar Codex para microtarefas se Python/Ollama resolverem.
- Não fazer commit ou push automático na V1.
- Não fazer deploy automático.
- Rodar validações antes de declarar pronto.

## Segurança

Tarefas envolvendo autenticação, autorização, pagamento, dados sensíveis, banco de dados, deploy ou segurança crítica devem parar para revisão humana/ChatGPT antes de execução.
