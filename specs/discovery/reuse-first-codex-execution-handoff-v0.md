# Reuse First Discovery

## Ideia

Sprint 011 Codex Execution Handoff V0

## Criado em

2026-04-30T09:46:14-03:00

## Objetivo desta etapa

Antes de montar a execução futura do Codex por run, avaliar padrões maduros para adapter de comando, dry-run first, subprocess seguro, reports locais e possível evolução para `git worktree`.

## O que já existe no repo

- `app/cli.py` como adapter de comandos locais;
- `app/run_workspace.py` com runs persistidas em JSON;
- `app/panel_data.py` com snapshot read-only do painel;
- `reports/` como padrão de reports locais;
- `tasks/` e `runs/` como fonte de verdade em arquivos.

## Alternativas consideradas

| Opção | Tipo | Maturidade | Custo | Risco | Decisão |
|---|---|---|---|---|---|
| Execução automática direta no `run-create` | acoplamento forte | baixa para V0 | baixo | alto | rejeitar |
| daemon ou scheduler | automação contínua | alta, mas pesada | médio/alto | alto | rejeitar |
| adapter local com dry-run first | handoff controlado | suficiente | baixo | baixo | adotar |
| `git worktree` imediato | isolamento real | alta | médio | médio | adiar para evolução |

## Decisão final

- [x] criar adapter local simples;
- [x] usar dry-run como padrão;
- [x] bloquear live por variável de ambiente;
- [x] registrar prompt e report localmente;
- [ ] adotar `git worktree` agora;
- [ ] automatizar execução contínua.

## Justificativa

O FactoryOS já tem runs locais e painel read-only. O próximo corte seguro é preparar o handoff: montar comando, prompt, metadata e report sem executar nada por padrão. Isso evita misturar preparação com execução e mantém o backend como fonte de verdade.

## Próximo passo

Gerar PRD, SPEC técnica, sprint JSON e implementar `run-handoff` e `run-execute` com dry-run first.
