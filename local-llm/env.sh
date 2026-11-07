#!/usr/bin/env bash
LLM_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export HOME="$LLM_ROOT/home"
export TMPDIR="$LLM_ROOT/tmp"
export XDG_CACHE_HOME="$LLM_ROOT/cache"
export XDG_CONFIG_HOME="$LLM_ROOT/config"
export XDG_DATA_HOME="$LLM_ROOT/data"
export HF_HOME="$LLM_ROOT/cache/huggingface"
export LLAMA_CACHE="$LLM_ROOT/cache/llama.cpp"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$HOME" "$TMPDIR" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME"
