# Panel UX Visual Direction V0

## Decisao

O painel deve evoluir para um command center local do FactoryOS: sobrio, denso, legivel e claramente read-only.

## Auditoria

- O painel atual ja agrega dados reais de Git, tasks, runs, reports, docs e gates.
- A hierarquia visual ainda trata muitos blocos como equivalentes.
- A primeira dobra precisa priorizar decisao operacional: estado da fabrica, projeto atual e proximo passo.
- Reports e evidencias devem ficar mais faceis de encontrar sem esconder informacao.
- Status precisam de badges consistentes, com contraste melhor em tema dev/hacker.
- Mobile deve manter uma coluna legivel, com caminhos longos quebrando sem overflow.

## Direcao visual

- Tema dark utilitario com acentos verdes/ciano discretos.
- Tipografia de sistema, sem dependencia externa.
- Cards compactos com raio pequeno, borda visivel e densidade operacional.
- Navegacao simples por secoes, sem SPA e sem JavaScript obrigatorio.
- Copy direta de ferramenta de fabrica de software, sem slogan vazio.
- Regras criticas continuam no backend e o painel permanece read-only.

## Gates

- no_push=true
- no_deploy=true
- no_paid_api=true
- no_secrets=true
