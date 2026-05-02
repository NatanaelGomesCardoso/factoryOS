# Reuse First Discovery

## Ideia

Isolated Run Workspace V0

## Objetivo desta etapa

Decidir quais padroes maduros podem ser reaproveitados para criar workspaces isolados por run no FactoryOS, sem acoplar ainda a execucao automatica do Codex.

## Contexto

- A Sprint 009 consolidou a control plane documental do FactoryOS.
- A Sprint 010 precisa preparar isolamento local, metadata e rastreabilidade sem daemon, scheduler ou App Server.
- O fluxo continua local-first e read-only no painel.

## O que pesquisar

- repositorios com workspace por task ou por job;
- uso simples de diretorios separados versus `git worktree`;
- metadata JSON de run;
- budgets por run;
- estados de ciclo de vida;
- guardrails de path traversal e escrita local;
- como expor a ultima run sem transformar o painel em camada de verdade.

## Critérios de avaliação

Para cada padrao encontrado, avaliar:

- simplicidade;
- compatibilidade com local-first;
- risco de seguranca;
- necessidade de Git worktree;
- auditabilidade;
- facilidade de rollback;
- custo operacional;
- adequacao a um V0 manual.

## Decisão de reuse

- [ ] usar pronto;
- [ ] adaptar;
- [x] usar como referência;
- [ ] criar pequeno customizado;
- [ ] adiar.

## Justificativa

Para o V0, diretorios locais com metadata JSON resolvem o problema imediato com menos risco do que adicionar worktree ou automacao mais cedo. `git worktree` fica como evolucao possivel, mas nao precisa entrar agora para validar o modelo operacional.

## Impacto esperado no PRD/SPEC

- definir criacao, listagem, consulta, finalizacao e falha de runs;
- registrar budgets e estado da run;
- preservar workspace local por run;
- manter o painel apenas como leitura;
- bloquear path traversal e escrita fora das areas permitidas.

## Próximo passo

Gerar o PRD, a SPEC tecnica e o Sprint JSON da Sprint 010.
