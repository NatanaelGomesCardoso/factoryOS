# Arquitetura

FactoryOS separa backend, painel local, CLI, memória, runner e reports. O painel é read-only; regras críticas ficam no backend e nos comandos locais.

## Visão geral

```mermaid
flowchart TB
  U[Usuario] --> C[ChatGPT arquiteto/revisor]
  C --> D[PRD, SPEC e sprint]
  D --> F[FactoryOS CLI]
  F --> T[Tasks e runs]
  F --> X[Capsules Codex]
  F --> R[Reports locais]
  R --> P[Painel read-only]
  R --> O[Obsidian quando duravel]
```

## Backend e frontend separados

- Backend: `app/*.py`, CLI, validações, leitura segura de arquivos e reports.
- Frontend local: `app/templates/` e `app/static/style.css`.
- Painel: FastAPI em `app/web.py`, sem segredo e sem mutação crítica.

## Módulos principais

- `app/cli.py`: registra comandos reais.
- `app/web.py`: painel local e viewer read-only.
- `app/help_center.py`: allowlist de docs e renderização Markdown segura.
- `app/task_runner.py`: tasks locais.
- `app/run_workspace.py`: runs e worktrees.
- `app/codex_context_capsule.py`: criação e inspeção de cápsulas.
- `app/codex_capsule_execution.py`: execução, diff e export plan de cápsulas.
- `app/reversa_integration.py`: guards e reports para Reversa.
- `app/report_index.py`: listagem e leitura de reports.

## Memória em camadas

```mermaid
flowchart LR
  A[Chat e decisao atual] --> B[Repo: docs, specs, reports]
  B --> C[Obsidian: conhecimento duravel]
  B --> D[Git: snapshot e diff]
  C --> E[Retomada futura]
  D --> E
```

## Fluxo de projeto

```mermaid
sequenceDiagram
  participant User as Usuario
  participant GPT as ChatGPT
  participant FOS as FactoryOS
  participant Codex as Codex/capsule
  participant Reports as Reports
  User->>GPT: ideia, restricoes, objetivo
  GPT->>FOS: PRD/SPEC/sprint
  FOS->>FOS: intake, task, run, plano
  FOS->>Codex: execucao controlada quando necessario
  Codex->>FOS: diff/report
  FOS->>Reports: validacao e evidencia
```

## Fluxo de segurança

```mermaid
flowchart TD
  A[Tarefa] --> B{Toca segredo, auth, pagamento, banco ou deploy?}
  B -- sim --> C[Parar para revisao humana]
  B -- nao --> D[Dry-run e allowlist]
  D --> E[Validacao local]
  E --> F[Report]
  F --> G{Passou?}
  G -- nao --> H[Corrigir ou registrar falha]
  G -- sim --> I[Pronto para proximo gate]
```

## Ciclo Codex/capsule

```mermaid
flowchart LR
  A[Context pack] --> B[Capsule create]
  B --> C[Codex run quiet]
  C --> D[Capsule diff]
  D --> E[Export plan]
  E --> F[Apply dry-run gate]
  F --> G[Revisao humana quando necessario]
```

## Reversa intake

```mermaid
flowchart TB
  A[Projeto antigo] --> B[Target guard]
  B --> C[Reversa status]
  C --> D[SDD intake dry-run]
  D --> E[PRD/SPEC novos]
  E --> F[FactoryOS intake]
```
