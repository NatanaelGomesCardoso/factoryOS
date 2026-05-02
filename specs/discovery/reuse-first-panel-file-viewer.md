# Reuse First Discovery

## Ideia

Visualização segura read-only de arquivos docs e reports no painel local do FactoryOS

## Criado em

2026-04-29T01:04:09

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

# Decisão Reuse First — Panel File Viewer

## Decisão

Criar viewer pequeno e próprio usando a stack atual: FastAPI + Jinja2 + CSS simples.

## Opções avaliadas

- FastAPI + Jinja2 atual: usar.
- StaticFiles direto para reports/docs: não usar, pois expõe diretórios amplos demais.
- Biblioteca de Markdown/renderização externa: adiar.
- File browser genérico pronto: não usar na V1, pois aumenta risco e escopo.

## Motivo

A V1 precisa apenas exibir texto de arquivos locais conhecidos. A stack atual já resolve isso sem dependência nova.

## Regra de segurança

A regra crítica deve ficar no backend. O frontend só mostra links. O backend decide se o arquivo pode ou não ser aberto.

## Regras obrigatórias da implementação

- permitir apenas áreas conhecidas;
- bloquear caminho absoluto;
- bloquear ..;
- bloquear symlink;
- bloquear arquivo oculto;
- bloquear nomes e sufixos sensíveis;
- limitar tamanho do arquivo;
- exibir conteúdo como texto escapado;
- nunca executar conteúdo do arquivo;
- manter painel read-only.

## Decisão final

- [x] criar pequeno customizado.

## Impacto no PRD/SPEC

O PRD e a SPEC devem focar em uma rota backend segura para leitura read-only de arquivos permitidos.
