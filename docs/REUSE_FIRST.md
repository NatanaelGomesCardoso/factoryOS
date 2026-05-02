# Reuse First — Não Reinventar a Roda

## Objetivo

Antes de criar ferramenta, módulo, arquitetura, app, SaaS, automação, dashboard ou funcionalidade grande do zero, o FactoryOS deve executar uma etapa de descoberta chamada **Reuse First**.

A ideia é evitar desperdício de tempo, tokens e risco técnico.

## Responsabilidade

A pesquisa ampla fica principalmente com o **ChatGPT**.

O Codex não deve gastar tokens fazendo pesquisa aberta na internet. O Codex deve receber uma decisão já consolidada e atuar como executor técnico local.

## Fluxo

1. O usuário descreve o objetivo.
2. ChatGPT pesquisa e avalia soluções existentes.
3. ChatGPT separa:
   - usar pronto;
   - adaptar;
   - usar como referência;
   - criar pequeno customizado;
   - adiar.
4. ChatGPT gera PRD, SPEC, Sprint JSON e prompts fechados.
5. Codex implementa apenas o que foi aprovado.

## Critérios de avaliação

Avaliar cada solução por:

- maturidade;
- licença;
- manutenção;
- segurança;
- custo;
- dependência de API paga;
- simplicidade;
- compatibilidade com WSL/local;
- integração com Codex/harness;
- esforço de adaptação.

## Referências úteis

Estas ferramentas podem servir como inspiração ou base, mas não devem ser adicionadas à V1 sem necessidade clara:

- OpenHands Software Agent SDK;
- Aider;
- Plandex;
- Cline;
- Roo Code;
- Continue;
- LangGraph;
- SWE-agent;
- Agent Orchestrator;
- RouteLLM;
- Dify;
- MetaGPT;
- Copier;
- Dev Containers;
- Renovate;
- Trivy;
- OpenAPI Generator;
- OpenTelemetry;
- Dagger.

## Decisão para a V1

Na V1, o FactoryOS não fará web scraping nem pesquisa automática ampla.

A pesquisa real será feita pelo ChatGPT, e a decisão será registrada no repositório em documentação ou arquivos de discovery.

## Regra para o Codex

O Codex deve receber:

- objetivo claro;
- solução escolhida;
- escopo permitido;
- arquivos permitidos;
- critérios de pronto;
- validações;
- proibições;
- relatório final esperado.

O Codex não deve iniciar uma implementação grande sem decisão Reuse First registrada.
