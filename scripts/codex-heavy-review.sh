#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <diretorio> <prompt...>" >&2
  exit 2
fi

workspace="$1"
shift
prompt="$*"

if [[ ! -d "$workspace" ]]; then
  echo "Diretorio inexistente: $workspace" >&2
  exit 2
fi

codex exec \
  --ignore-user-config \
  --ephemeral \
  --cd "$workspace" \
  --model "gpt-5.4" \
  -c 'model_reasoning_effort="high"' \
  -c 'approval_policy="on-request"' \
  -c 'sandbox_mode="workspace-write"' \
  "$prompt"
