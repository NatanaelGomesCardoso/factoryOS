# Reuse First Discovery

## Ideia

Criar painel web leve para acompanhar progresso do FactoryOS

## Criado em

2026-04-28T22:11:51

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

# Decisão Reuse First — Painel Web Leve do FactoryOS

## Decisão

Usar **FastAPI + Jinja2 + CSS simples** para a primeira versão do painel web local.

## Justificativa

Essa opção é a mais adequada para a V1 porque:

- reaproveita Python, que já é a base do FactoryOS;
- evita build frontend pesado;
- reduz consumo de RAM;
- facilita integração com SQLite, reports, logs e arquivos locais;
- mantém o painel simples para manutenção;
- permite que o Codex implemente com escopo fechado;
- permite evolução futura para HTMX/SSE sem trocar a arquitetura.

## Opções avaliadas

| Opção | Decisão | Motivo |
|---|---|---|
| FastAPI + Jinja2 + CSS | usar na V1 | leve, simples, Python-first, sem build frontend |
| HTMX/SSE | adiar/adaptar depois | útil para tempo real, mas não obrigatório no primeiro painel |
| NiceGUI | usar só como referência | bom para dashboards Python, mas adiciona abstração extra |
| Streamlit | evitar na V1 | melhor para data apps; modelo de rerun não é ideal para painel operacional |
| React/Vite | evitar na V1 | mais pesado e exige pipeline frontend |
| Dify/LangGraph | evitar na V1 | pesados demais para o painel local inicial |

## Escopo do painel V1

O painel inicial deve mostrar:

- status geral do FactoryOS;
- última decisão de rota;
- arquivos em `reports/`;
- tarefas futuras em `tasks/`;
- links para docs/specs;
- aviso claro de que ainda não executa Codex automaticamente.

## Fora do escopo da V1

- login;
- multiusuário;
- deploy;
- websocket obrigatório;
- automação de ChatGPT web;
- troca de contas;
- execução automática de Codex;
- dashboard complexo.

## Próximo passo

Gerar PRD/SPEC pequeno para o painel local e só depois preparar prompt Codex.
