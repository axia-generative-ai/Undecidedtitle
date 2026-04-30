#!/usr/bin/env bash
# Pull the Ollama models required by the FactoryGuard AI service.
#
# WBS v1.0 originally specified `qwen3:8b`. The dev environment for this
# project standardises on `qwen3.5:9b`, which is what this script pulls.
# The embedding model `bge-m3` is unchanged.
#
# Usage:
#   bash scripts/pull_models.sh

set -euo pipefail

LLM_MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"
EMBED_MODEL="${EMBEDDING_MODEL:-bge-m3}"

if ! command -v ollama >/dev/null 2>&1; then
    echo "ERROR: ollama CLI not found on PATH." >&2
    echo "Install Ollama from https://ollama.com/download and retry." >&2
    exit 1
fi

echo ">>> Pulling LLM: ${LLM_MODEL}"
ollama pull "${LLM_MODEL}"

echo ">>> Pulling embedding model: ${EMBED_MODEL}"
ollama pull "${EMBED_MODEL}"

echo ">>> Installed models:"
ollama list
