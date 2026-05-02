# Panel Information Architecture V0

## Decisao

A tela principal foi reorganizada por finalidade operacional, mantendo HTML/Jinja simples e sem JavaScript obrigatorio.

## Nova ordem

1. Estado da fabrica: higiene, factory start e ultimo tick.
2. Projeto atual: workspaces e reports do projeto.
3. Tasks/fila: pendentes, rodando, concluidas e falhas.
4. Runs/capsulas: run, loop e handoff.
5. Reports/evidencias: reports, docs e discoveries.
6. Seguranca/gates: execution evaluation, review gate e expansion policy.
7. Proximos passos: acao recomendada e commits recentes.

## Politica de simplicidade

- Rotas atuais preservadas.
- Viewer read-only preservado.
- Nenhuma dependencia externa adicionada.
- Nenhuma regra critica foi movida para o frontend.
- Empty states foram mantidos com linguagem operacional.
