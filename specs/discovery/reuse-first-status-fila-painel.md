# Reuse First Discovery

## Ideia

Adicionar status da fila de tasks no painel local do FactoryOS

## Criado em

2026-04-29T00:35:51

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

# Decisão Reuse First — Status da fila no painel

## Decisão

Usar a estrutura de pastas já existente em `tasks/` como fonte inicial da fila visual.

## Pastas usadas

- `tasks/pending/`
- `tasks/running/`
- `tasks/done/`
- `tasks/failed/`

## Motivo

- já existe no repo;
- não exige banco agora;
- não exige Redis, Celery ou serviço extra;
- mantém a V1 simples;
- permite o painel mostrar progresso sem executar Codex automaticamente.

## Fora do escopo

- executar tarefas automaticamente;
- mover tarefas entre pastas pelo painel;
- editar tarefas pelo painel;
- banco SQLite obrigatório;
- worker paralelo;
- scheduler;
- automação de Codex.

## Próximo passo

Criar PRD, SPEC e Sprint JSON pequenos para o painel apenas ler e exibir a fila.
