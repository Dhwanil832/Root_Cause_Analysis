"""Graph-aware proposal policy: structural checks + question/hypothesis linking.

No missing event is treated as an observed fact, and no model-generated causal
inference bypasses the source/justification engine.
"""
from reasoning.specialist.components.frontier_policy import normalize_with_frontier


def transform(raw,public):
    return normalize_with_frontier(raw,public)
