"""Solver port and provider-independent result types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..engine_contracts import CausalGraph


@dataclass(frozen=True, slots=True)
class SearchLimits:
    max_depth: int = 3
    max_models: int = 64
    timeout_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class SolverCandidate:
    target_id: str
    proposition_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]
    reported_premise_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    trace: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SearchResult:
    candidates: tuple[SolverCandidate, ...]
    open_frontier_ids: tuple[str, ...]
    status: str
    models_seen: int
    solver_time_seconds: float
    diagnostics: tuple[str, ...] = ()


class CandidateSolver(Protocol):
    def search(self, graph: CausalGraph, target_id: str, limits: SearchLimits) -> SearchResult: ...
