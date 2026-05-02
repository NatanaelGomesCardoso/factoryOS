# Factory State Hygiene V0 PRD

## Problema

O FactoryOS acumulou tasks e runs em `running` mesmo depois de entregas e proofs já estarem disponíveis. Isso cria ambiguidade para seleção automática e dificulta saber o que ainda está realmente em aberto.

## Objetivo

Criar uma higiene local, segura e conservadora para:

- auditar tasks e runs por estado;
- identificar itens antigos em `running`;
- cruzar tasks, runs e proofs/reports locais;
- propor um plano seguro de fechamento;
- aplicar fechamento apenas quando a evidência for clara.

## Não objetivos

- apagar arquivos;
- remover worktrees;
- tocar em branches;
- executar Codex live;
- fazer merge, rebase, fetch ou pull;
- integrar GitHub ou Linear;
- criar daemon, scheduler ou App Server;
- limpar histórico antigo de forma agressiva.

## Usuário

Pessoa operando o FactoryOS localmente e precisando entender o estado real da fábrica antes de avançar para o loop V1.

## Fluxo

1. Rodar auditoria de tasks e runs.
2. Identificar itens running antigos.
3. Cruzar com proofs/reports locais.
4. Gerar um plano conservador.
5. Fechar apenas itens `safe_to_close`.
6. Registrar o resultado em reports locais.
7. Manter o painel read-only.

## Critérios de fechamento seguro

- `task-finish` só pode acontecer quando o commit correspondente existir e houver proof/report local;
- `run-finish` só pode acontecer quando o report final existir e a evidência local estiver consistente;
- se houver dúvida, o item fica em `needs_review`;
- nada pode ser apagado;
- nenhum worktree pode ser removido;
- nenhuma execução live pode acontecer.

## Critérios de pronto

- auditoria local funcionando;
- plano conservador funcionando;
- dry-run funcionando;
- execução conservadora disponível apenas para itens claramente seguros;
- report local gerado e validado;
- painel continua read-only;
- Sprint 019 fechada em `done` no final.
