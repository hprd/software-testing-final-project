#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
cmake -S "$LLM_ROOT/llama.cpp" -B "$LLM_ROOT/build" \
  -DCMAKE_C_COMPILER="${CC:-gcc}" \
  -DCMAKE_CXX_COMPILER="${CXX:-g++}" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CUDA=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_OPENSSL=OFF -DGGML_CCACHE=OFF
cmake --build "$LLM_ROOT/build" --parallel 16 --target llama-server llama-cli
