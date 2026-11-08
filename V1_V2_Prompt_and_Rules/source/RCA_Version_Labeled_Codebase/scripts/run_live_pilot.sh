#!/bin/sh
# Do not store API secrets here. Use a network-enabled host and environment var.
set -eu
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  printf '%s\n' 'Missing OPENROUTER_API_KEY in environment; no model calls attempted.' >&2
  exit 2
fi
python -m evaluation.run_matrix --mode live \
  --provider openrouter \
  --model "${RCA_OPENROUTER_MODEL:-nvidia/nemotron-3-super-120b-a12b:free}" \
  --max-actions "${RCA_ACTION_BUDGET:-6}" \
  --output "${RCA_OUTPUT_DIR:-outputs/openrouter_pilot}"
