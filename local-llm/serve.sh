#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
exec "$LLM_ROOT/build/bin/llama-server" \
  --model "$LLM_ROOT/models/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf" \
  --alias local-coder --host 127.0.0.1 --port "${PORT:-8080}" \
  --ctx-size "${CONTEXT:-16384}" --parallel 1 \
  --threads "${THREADS:-16}" --threads-batch "${THREADS_BATCH:-32}" \
  --n-gpu-layers 0 --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 "$@"
