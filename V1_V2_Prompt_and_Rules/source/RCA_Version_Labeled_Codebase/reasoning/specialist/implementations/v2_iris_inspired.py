"""Ablation: frontier normalization PLUS bounded abductive *question* generation.

Inspired by open-world missing-variable reasoning, but NOT an implementation
of the published IRIS algorithm. Hypotheses are conditional; the new content
is a request to resolve an untested premise, not an asserted cause.
"""
from reasoning.specialist.components.frontier_policy import normalize_with_frontier
from reasoning.specialist.components.abductive_questions import expand_one_gap


def transform(raw,public):
    screened=normalize_with_frontier(raw,public)
    return expand_one_gap(screened,public)
