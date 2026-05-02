# First Project Pilot Runbook V0

Runbook operacional para iniciar o primeiro projeto piloto no FactoryOS sem sair do fluxo controlado.

## Comando

- `project-pilot-runbook-create --project <NAME> --dry-run`

## Sequência

1. entrada do projeto;
1. PRD;
1. SPEC;
1. sprint plan;
1. build plan;
1. capsule canary;
1. apply gate humano;
1. workspace scaffold;
1. evaluator;
1. delivery package;
1. Obsidian sync;
1. report retention.

## Pontos de aprovação humana

- entrada do projeto;
- PRD;
- SPEC;
- sprint plan;
- build plan;
- capsule canary;
- apply gate humano;
- delivery package;
- Obsidian sync;
- report retention.

## Nunca automático

- push;
- deploy;
- API paga;
- secrets.

## Regra

- o runbook só planeja o corte inicial;
- qualquer avanço real depende de revisão humana explícita;
- nenhum artefato crítico vai para o frontend.
