# Comandos

Use:

```bash
.venv/bin/python -m app.cli <comando> [opcoes]
```

Esta página lista comandos reais existentes na CLI. Quando um exemplo exige arquivo, use caminhos locais do seu projeto.

## Painel e ajuda

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `help-docs-list` | Lista docs da Ajuda local | `.venv/bin/python -m app.cli help-docs-list` | n/a | não | JSON compacto com `ok` |
| `help-docs-check` | Valida docs, rotas e traversal | `.venv/bin/python -m app.cli help-docs-check --dry-run` | sim | não | `ok:true` |
| `panel-ux-audit` | Audita UX visual do painel | `.venv/bin/python -m app.cli panel-ux-audit --dry-run` | sim | report | JSON/report |
| `panel-usability-check` | Checa usabilidade do painel | `.venv/bin/python -m app.cli panel-usability-check --dry-run` | sim | report | JSON/report |

## Tasks

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `task-create` | Criar task local | `.venv/bin/python -m app.cli task-create "Doc" --description "Ajustar docs"` | não | sim | task em `tasks/pending` |
| `task-list` | Listar tasks | `.venv/bin/python -m app.cli task-list` | n/a | não | JSON com grupos |
| `task-show` | Ver uma task | `.venv/bin/python -m app.cli task-show <task-id>` | n/a | não | JSON da task |
| `task-start` | Mover para running | `.venv/bin/python -m app.cli task-start <task-id>` | não | sim | status running |
| `task-finish` | Mover para done | `.venv/bin/python -m app.cli task-finish <task-id>` | não | sim | status done |
| `task-fail` | Encerrar com falha | `.venv/bin/python -m app.cli task-fail <task-id>` | não | sim | status failed |

## Runs

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `run-create` | Criar run para task | `.venv/bin/python -m app.cli run-create <task-id>` | não | sim | run pending |
| `run-list` | Listar runs | `.venv/bin/python -m app.cli run-list` | n/a | não | JSON com runs |
| `run-show` | Ver run | `.venv/bin/python -m app.cli run-show <run-id>` | n/a | não | JSON da run |
| `run-workspace-prepare` | Preparar worktree | `.venv/bin/python -m app.cli run-workspace-prepare <run-id>` | não | sim | workspace criado/reaproveitado |
| `run-workspace-status` | Ver estado do workspace | `.venv/bin/python -m app.cli run-workspace-status <run-id>` | n/a | não | status JSON |
| `run-workspace-readiness` | Validar prontidão | `.venv/bin/python -m app.cli run-workspace-readiness <run-id>` | n/a | não | decisão local |

## Capsule

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `codex-capsule-create` | Criar cápsula mínima | `.venv/bin/python -m app.cli codex-capsule-create --help` | não | sim | manifest da cápsula |
| `codex-capsule-list` | Listar cápsulas | `.venv/bin/python -m app.cli codex-capsule-list` | n/a | não | JSON compacto |
| `codex-capsule-inspect` | Inspecionar cápsula | `.venv/bin/python -m app.cli codex-capsule-inspect --capsule <path>` | n/a | não | métricas |
| `codex-capsule-run` | Rodar Codex em cápsula | `.venv/bin/python -m app.cli codex-capsule-run --capsule <path> --dry-run` | recomendado | report | report de execução |
| `codex-capsule-diff` | Salvar diff da cápsula | `.venv/bin/python -m app.cli codex-capsule-diff --capsule <path>` | n/a | report | diff/report |
| `codex-capsule-apply` | Gate de aplicação | `.venv/bin/python -m app.cli codex-capsule-apply --capsule <path> --source-root . --dry-run` | sim | report | plano sem aplicar |

## Queue e Factory

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `route` | Classificar tarefa | `.venv/bin/python -m app.cli route "ajustar README"` | n/a | não | decisão JSON |
| `factory-tick` | Tick único auditável | `.venv/bin/python -m app.cli factory-tick --dry-run` | sim | report | report |
| `factory-loop` | Loop controlado | `.venv/bin/python -m app.cli factory-loop --dry-run` | sim | report | report |
| `factory-start` | Execução limitada | `.venv/bin/python -m app.cli factory-start --dry-run` | recomendado | report | report |
| `factory-queue-start` | Planejar fila curta | `.venv/bin/python -m app.cli factory-queue-start --dry-run` | recomendado | report | report |

## MVP

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `project-intake-create` | Criar intake de MVP | `.venv/bin/python -m app.cli project-intake-create --help` | recomendado | report | intake/report |
| `mvp-template-list` | Listar templates | `.venv/bin/python -m app.cli mvp-template-list` | n/a | não | JSON |
| `mvp-build-plan-create` | Criar plano de build | `.venv/bin/python -m app.cli mvp-build-plan-create --help` | recomendado | report | plano |
| `mvp-capsule-build-canary` | Canary pequeno em cápsula | `.venv/bin/python -m app.cli mvp-capsule-build-canary --help` | recomendado | report/cápsula | status |
| `mvp-apply-plan-create` | Plano com gate humano | `.venv/bin/python -m app.cli mvp-apply-plan-create --help` | recomendado | report | plano |
| `mvp-evaluate` | Avaliar workspace MVP | `.venv/bin/python -m app.cli mvp-evaluate --project-name demo --workspace <TMP_DIR>/demo --dry-run` | sim | report | decisão |

## Reversa

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `reversa-global-check` | Verificar Node/npm/Reversa | `.venv/bin/python -m app.cli reversa-global-check` | n/a | não | disponibilidade |
| `reversa-project-plan` | Planejar instalação | `.venv/bin/python -m app.cli reversa-project-plan --target <CODE_ROOT>/projeto --dry-run` | sim | report | plano |
| `reversa-project-install` | Ensaio de install | `.venv/bin/python -m app.cli reversa-project-install --target <CODE_ROOT>/projeto --dry-run` | sim | report | bloqueio live |
| `reversa-project-status` | Ler estado Reversa | `.venv/bin/python -m app.cli reversa-project-status --target <CODE_ROOT>/projeto` | n/a | report | status |
| `reversa-project-sdd-intake` | Classificar SDD | `.venv/bin/python -m app.cli reversa-project-sdd-intake --target <CODE_ROOT>/projeto --dry-run` | sim | report | intake |

## Hygiene, cleanup e release

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `factory-state-audit` | Auditar tasks/runs antigas | `.venv/bin/python -m app.cli factory-state-audit` | n/a | report | hygiene report |
| `factory-state-plan` | Plano conservador | `.venv/bin/python -m app.cli factory-state-plan` | n/a | report | plano |
| `factory-state-apply` | Aplicar ou simular | `.venv/bin/python -m app.cli factory-state-apply --dry-run` | sim | report | sem mutação |
| `deep-hygiene-audit` | Auditoria profunda | `.venv/bin/python -m app.cli deep-hygiene-audit --dry-run` | sim | report | candidatos |
| `cleanup-plan` | Plano de limpeza | `.venv/bin/python -m app.cli cleanup-plan --audit-report reports/x.json --dry-run` | sim | report | plano |
| `cleanup-apply` | Aplicar plano seguro | `.venv/bin/python -m app.cli cleanup-apply --cleanup-plan reports/x.json --dry-run` | recomendado | depende | simulação |
| `cleanup-validate` | Validar fixture | `.venv/bin/python -m app.cli cleanup-validate --dry-run` | sim | report | fixture ok |
| `release-packaging-strategy` | Estratégia de backup e release limpo | `.venv/bin/python -m app.cli release-packaging-strategy --dry-run` | sim | report | `strategy_decision` |
| `clean-public-export-plan` | Planejar export público limpo | `.venv/bin/python -m app.cli clean-public-export-plan --dry-run` | sim | report | `export_decision` |
| `clean-public-export-create` | Simular ou criar export limpo | `.venv/bin/python -m app.cli clean-public-export-create --dry-run` | padrão seguro | report/export | sem sobrescrever |
| `clean-public-export-validate` | Validar export limpo | `.venv/bin/python -m app.cli clean-public-export-validate --dry-run` | sim | report | forbidden count |
| `public-repo-readiness-gate` | Gate final antes do GitHub | `.venv/bin/python -m app.cli public-repo-readiness-gate --dry-run` | sim | report | `readiness_decision` |

## Extended runs

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `extended-cheap-run-plan` | Planejar run barata longa | `.venv/bin/python -m app.cli extended-cheap-run-plan --max-minutes 120 --dry-run` | sim | report | plano |
| `extended-cheap-run-rehearsal` | Ensaiar task-by-task | `.venv/bin/python -m app.cli extended-cheap-run-rehearsal --max-minutes 120 --max-tasks 10 --dry-run` | sim | report | rehearsal |
| `extended-cheap-run-gate` | Manter live bloqueado | `.venv/bin/python -m app.cli extended-cheap-run-gate --dry-run` | sim | report | gate |
| `factory-long-run-plan` | Planejar rodada longa | `.venv/bin/python -m app.cli factory-long-run-plan --target-minutes 30 --max-steps 6` | sim por contrato | report | plano |

## Readiness, audit, security e reliability

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `factoryos-v1-readiness-gate` | Prontidão V1 | `.venv/bin/python -m app.cli factoryos-v1-readiness-gate --dry-run` | sim | report | gate |
| `factoryos-v1-audit` | Auditoria V1 | `.venv/bin/python -m app.cli factoryos-v1-audit --dry-run` | sim | report | audit |
| `factoryos-v1-security-review` | Revisão de segurança V1 | `.venv/bin/python -m app.cli factoryos-v1-security-review --dry-run` | sim | report | security |
| `factoryos-v1-reliability-check` | Confiabilidade V1 | `.venv/bin/python -m app.cli factoryos-v1-reliability-check --dry-run` | sim | report | reliability |
| `factoryos-v1-polish-check` | Lapidação técnica | `.venv/bin/python -m app.cli factoryos-v1-polish-check --dry-run` | sim | report | polish |
| `factoryos-v1-technical-freeze` | Registrar freeze | `.venv/bin/python -m app.cli factoryos-v1-technical-freeze --dry-run` | sim | report | freeze |

## Reports

| Comando | Objetivo | Exemplo seguro | Dry-run | Altera arquivos | Validação esperada |
| --- | --- | --- | --- | --- | --- |
| `report-list` | Listar reports por tipo | `.venv/bin/python -m app.cli report-list factory-start --limit 5` | n/a | não | JSON |
| `report-latest` | Último report válido | `.venv/bin/python -m app.cli report-latest factory-start` | n/a | não | JSON |
| `execution-evaluate` | Avaliar report | `.venv/bin/python -m app.cli execution-evaluate --report reports/x.json` | n/a | report | decisão |
| `execution-close-if-passed` | Fechar se passou | `.venv/bin/python -m app.cli execution-close-if-passed --run-id <run-id> --dry-run` | sim | report | sem fechar |
