#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT_DIR/.venv/bin/python" -m py_compile "$ROOT_DIR"/app/*.py
"$ROOT_DIR/.venv/bin/python" -m app.cli factoryos-v1-security-review --dry-run ><TMP_DIR>/factoryos-security-boundary-review.out
harness security-doctor --source-root "$ROOT_DIR" --strict
git -C "$ROOT_DIR" diff --check
