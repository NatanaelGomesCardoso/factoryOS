# Reuse First Discovery

## Ideia

Criar evaluator simples local para classificar resultados de validações do FactoryOS

## Criado em

2026-04-29T00:43:38

## Objetivo desta etapa

Antes de criar arquitetura, PRD, SPEC, Sprint JSON ou prompt para Codex, o ChatGPT deve pesquisar soluções maduras existentes para evitar reinventar a roda.

## Responsabilidade

- ChatGPT: pesquisar, comparar, decidir e gerar a recomendação.
- FactoryOS: registrar o discovery e organizar o fluxo.
- Codex: não deve fazer pesquisa ampla; deve executar somente depois da decisão.

## O que pesquisar

- bibliotecas maduras;
- frameworks;
- SDKs;
- templates;
- ferramentas open source;
- projetos/repositórios validados;
- plugins/extensões;
- padrões consolidados.

## Critérios de avaliação

Para cada opção encontrada, avaliar:

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

## Tabela de análise

| Opção | Tipo | Licença | Maturidade | Custo | Risco | Decisão |
|---|---|---|---|---|---|---|
| A preencher pelo ChatGPT |  |  |  |  |  |  |

## Decisão final

Escolher uma opção:

- [ ] usar pronto;
- [ ] adaptar;
- [ ] usar como referência;
- [ ] criar pequeno customizado;
- [ ] adiar.

## Justificativa

A preencher pelo ChatGPT.

## Impacto no PRD/SPEC

A preencher pelo ChatGPT.

## Próximo passo

Depois deste discovery preenchido, gerar:

1. PRD;
2. SPEC;
3. Sprint JSON;
4. prompt fechado para Codex, se necessário.

---

# Decisão Reuse First — Evaluator simples local

## Decisão

Criar evaluator pequeno em Python puro na V1.

## Motivo

- a primeira versão precisa apenas classificar resultados simples;
- não precisa LangGraph, Dify, Redis, Celery ou banco;
- reduz dependências e risco;
- economiza Codex;
- facilita testes locais.

## Entrada esperada

Um conjunto simples de sinais:

- python_ok;
- json_ok;
- browser_ok;
- security_ok;
- git_clean ou git_expected_dirty;
- notes.

## Saída esperada

Uma decisão em JSON:

- passed;
- failed_retryable;
- needs_codex;
- needs_chatgpt_review;
- stopped_security.

## Fora do escopo

- executar Codex;
- rodar Playwright;
- criar fila real;
- usar banco;
- tomar decisão de deploy;
- corrigir código automaticamente.
