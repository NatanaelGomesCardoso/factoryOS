# Artifact / Asset Intake V0

Comando local para planejar e registrar a entrada controlada de artefatos e assets.

## Comandos

- `artifact-intake-plan --project <NAME> --source <PATH> --dry-run`
- `artifact-intake-register --project <NAME> --source <PATH> --dry-run`

## Regras

- somente `--dry-run` nesta V0;
- não copiar arquivo real;
- bloquear extensões perigosas;
- bloquear traversal de path;
- classificar como `image`, `document`, `prompt`, `brief` ou `unknown`;
- manter `no_push=true`, `no_deploy=true`, `no_paid_api=true`, `no_secrets=true`.
