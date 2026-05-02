# Expanded Bounded Live Canary V0

Objetivo: executar um canário live expandido em worktree isolado, com limite de 30 minutos e até 6 steps, sem push, deploy, API paga ou secrets.

## Fluxo

1. validar rehearsal recente da mesma run;
2. validar review gate de expansão aprovado;
3. executar o canário em passos sequenciais e bounded;
4. registrar report, token summary e heads antes/depois;
5. validar que somente arquivos permitidos foram alterados;
6. gerar evaluation formal e, se necessário, pedir revisão humana.

## Regra De Limite

- canários antigos e não expandidos continuam presos a `max_steps <= 3`;
- `expanded-bounded-live-canary` só aceita `max_steps <= 6` quando o gate aprovado em `reports/expanded-long-run-reviews/` existir para a mesma `run_id`;
- `max_minutes` continua limitado a `30` mesmo no caminho expandido.

## Segurança

- regra crítica permanece no servidor e no gate local;
- o comando exige `--bounded`, `--canary`, `--cost-aware`, `--no-push`, `--no-deploy`, `--no-paid-api` e `--no-secrets`;
- o caminho expandido exige também revisão aprovada para a run antes de liberar `max_steps=6`;
- a leitura do snapshot de workspace e da validação usa normalização segura, com `workspace`, `readiness`, `sync_plan` e flags derivadas, nunca `KeyError`;
- o report precisa provar `master_head_before == master_head_after`;
- `executed_live=true` só vale quando todas as verificações passam.
- o loop de steps precisa avançar de `1` até `max_steps` e só então aplicar a checagem final de conclusão completa;
- a checagem `todos os steps solicitados foram concluídos` acontece apenas após o loop terminar, nunca antes.
- cada tentativa precisa usar `attempt_id` próprio;
- os arquivos de step precisam ficar em `reports/expanded-bounded-live-canary/attempts/<attempt_id>/`;
- o prompt de cada step precisa apontar exatamente para o arquivo permitido da tentativa atual;
- a validação do step lê o arquivo criado dentro do worktree e exige o conteúdo obrigatório do canário;
- a validação de diff por step precisa ignorar arquivos de tentativas anteriores;
- arquivos legados em `reports/expanded-bounded-live-canary/step-N.txt` não são apagados, mas não entram no diff da tentativa atual;
- `allowed_files` deve refletir apenas a whitelist da tentativa atual.

## Preflight Estrutural

- a validação estrutural do comando precisa conseguir confirmar gates e snapshot sem acionar live real;
- se o snapshot de workspace estiver ausente, o bloqueio deve ser `expanded live canary blocked: workspace snapshot ausente.`;
- `max_steps=7` continua bloqueado antes de qualquer execução;
- a ausência das safety flags obrigatórias continua bloqueando o request.

## Saída

- report em `reports/expanded-bounded-live-canary/`;
- evaluation em `reports/post-expansion-evaluations/`;
- arquivos de step por tentativa em `reports/expanded-bounded-live-canary/attempts/<attempt_id>/`;
- `changed_files` representa somente arquivos da tentativa atual;
- `global_changed_files` e `ignored_old_step_files` podem aparecer como diagnóstico quando houver arquivos antigos no worktree;
- plano de rollback apenas em dry-run.
