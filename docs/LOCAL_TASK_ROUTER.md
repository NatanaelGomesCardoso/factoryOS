# Local Task Router

## Objetivo

O Local Task Router decide se uma tarefa deve ser resolvida localmente, enviada ao Codex ou parada para revisão humana/ChatGPT.

## Por que existe

Abrir o Codex para microtarefas consome uma quantidade alta de contexto. Em probes locais, tarefas triviais custaram cerca de 25k input tokens. Por isso, o FactoryOS deve tentar resolver tarefas simples com Python, templates ou Ollama antes de chamar Codex.

## Decisões possíveis

### local_only

Use quando a tarefa for simples:

- documentação;
- README;
- checklist;
- resumo;
- copy/texto;
- JSON simples;
- organização sem regra crítica.

### codex_needed

Use quando a tarefa exigir:

- editar código;
- corrigir bug;
- rodar teste;
- implementar feature;
- alterar backend/frontend;
- refatorar.

### human_review

Use quando envolver:

- autenticação;
- autorização;
- login;
- sessão;
- pagamento;
- dados sensíveis;
- banco de dados crítico;
- migração;
- deploy;
- produção;
- segurança crítica.

## Regra principal

As regras Python de segurança sempre vencem a LLM local.

A LLM local pode ajudar, mas não é fonte de verdade.
