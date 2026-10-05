#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-verify}"
if [ "$#" -gt 0 ]; then shift; fi
case "$mode" in
  verify) exec python3 verify.py "$@" ;;
  gpt) exec python3 run_gpt.py "$@" ;;
  qwen|gptoss|granite|hermes|mistral) exec python3 run_local.py "$mode" "$@" ;;
  *) echo 'Usage: bash RUN.sh [verify|gpt|qwen|gptoss|granite|hermes|mistral]' >&2; exit 2 ;;
esac
