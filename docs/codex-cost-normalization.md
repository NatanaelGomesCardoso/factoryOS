# Normalização de custo do Codex

## Problema

O FactoryOS já tinha perfis locais e roteador de contexto, mas comandos Codex ainda podiam depender da config global do usuário. Em medições anteriores, o caminho global consumia mais contexto que o caminho lean com `--ignore-user-config`.

Baselines informados:

- Codex lean com `--ignore-user-config`: 23021 tokens.
- Codex repo-aware: 7407 tokens.
- Codex global antes: 32855 tokens.
- Codex global phase2: 24626 tokens.

## Decisão

O caminho principal da fábrica não depende mais de configuração global. Todo comando Codex gerado pelo FactoryOS passa pelo construtor central `build_factoryos_codex_exec_command` e deve conter:

- `--ignore-user-config`;
- `--ephemeral`;
- `--cd <workspace>`;
- `--model <codex_plan.model>`;
- `-c model_reasoning_effort=...`;
- `-c approval_policy=...`;
- `-c sandbox_mode=...`.

O `codex_plan` é a fonte de verdade para modelo, reasoning, sandbox e approval. Execuções automatizadas usam `approval_policy="never"` com `sandbox_mode="workspace-write"`. Execuções manuais ficam em `on-request`.

## Backup global

Antes de alterar `~/.codex/config.toml`, foi criado backup em:

`<CODEX_HOME>/backups/config.toml.factoryos-normalization-20260430-231900.bak`

Restore:

`<CODEX_HOME>/RESTORE_LAST_CONFIG.sh`

A normalização global foi conservadora: default leve preservado, `factoryos-heavy-review` deixou de usar `danger-full-access`, e chaves deprecated de web search foram removidas porque `web_search = "disabled"` já existe no topo.

## Config local

O repo tem `.codex/config.toml` versionado, sem segredo, com perfis:

- `factoryos-lite-default`;
- `factoryos-mini-medium`;
- `factoryos-standard-medium`;
- `factoryos-heavy-review`.

Essa config é fallback humano. O FactoryOS continua preferindo comandos com `--ignore-user-config`.

## Launchers

Scripts locais:

- `scripts/codex-lite.sh`;
- `scripts/codex-mini-medium.sh`;
- `scripts/codex-standard-medium.sh`;
- `scripts/codex-heavy-review.sh`.

Todos usam `codex exec --ignore-user-config --ephemeral --cd`.

## Auditoria recorrente

Comando:

```bash
.venv/bin/python -m app.cli codex-cost-audit
```

O report JSON sai em `reports/codex-cost-audits/`.

Critérios:

- `factoryos_forced_lean <= raw_global_minimal`;
- `factoryos_forced_lean <= 23021` como alvo preferido;
- `factoryos_forced_lean <= 12000` como alvo ideal;
- bloqueado se comandos FactoryOS não tiverem `--ignore-user-config` ou `--ephemeral`.

## Resultado validado

Última prova: `reports/codex-cost-audits/20260430-232907.json`.

- `raw_global_minimal`: 24615 tokens.
- `factoryos_forced_lean`: 543 tokens.
- `factoryos_repo_aware`: 7078 tokens.
- classificação: `ideal`.

Handoff validado em:

`reports/run-handoffs/20260430-233001-20260430-233001-codex-cost-normalization-796c2f.json`

Campos de prova:

- `uses_ignore_user_config: true`;
- `uses_ephemeral: true`;
- `global_config_dependency: false`;
- `source_of_truth: codex_plan`.

## Riscos restantes

- O CLI ainda avisa que `bubblewrap` não está no PATH e usa fallback vendorizado.
- O comando global cru pode continuar caro porque carrega config global e contexto global. A fábrica não usa esse caminho por padrão.
- O context pack pode bloquear execução live quando exceder limite; isso é intencional para impedir contexto excessivo.
- `harness global-doctor --strict` ainda espera o default legado `auto-drive-full-global` com `danger-full-access`; nesta rodada esse check ficou em warning porque o objetivo foi trocar o default global para leve e fazer o FactoryOS independer da config global.
