"""Bounded ASP enumeration of conditional candidate explanations."""

from __future__ import annotations

import time

from ..engine_contracts import CausalGraph
from .interface import SearchLimits, SearchResult, SolverCandidate


class ClingoUnavailableError(RuntimeError):
    pass


def compile_program(graph: CausalGraph, target_id: str, max_depth: int) -> tuple[str, dict[str, str], dict[str, str]]:
    """Compile an injection-safe finite graph into a bounded ASP program."""
    prop_map = graph.proposition_map()
    rule_map = graph.rule_map()
    if target_id not in prop_map:
        raise ValueError(f"unknown target proposition {target_id!r}")
    p_symbol = {pid: f"p{i}" for i, pid in enumerate(sorted(prop_map))}
    r_symbol = {rid: f"r{i}" for i, rid in enumerate(sorted(rule_map))}
    lines = [
        f"target({p_symbol[target_id]}).",
        # Generic mechanisms and unknown terms are not incident facts that
        # the solver may assume. They can still be intermediate nodes when
        # incoming rules derive them from other propositions.
        "eligible(P) :- proposition(P), not reported(P).",
        "eligible(P) :- target(P).",
        "reachable(P,0) :- target(P).",
        "has_head(P) :- head(_,P).",
        f"{{ use(R) : head(R,P) }} 1 :- reachable(P,D), eligible(P), D < {int(max_depth)}, has_head(P).",
        f"reachable(B,D+1) :- reachable(H,D), use(R), head(R,H), body(R,B), D < {int(max_depth)}.",
        "used_as_head(P) :- use(R), head(R,P).",
        ":- target(P), not used_as_head(P).",
        "assume(P) :- reachable(P,D), assumable(P), not reported(P), not used_as_head(P), not target(P).",
        ":- assume(P), target(P).",
    ]
    for pid, proposition in prop_map.items():
        lines.append(f"proposition({p_symbol[pid]}).")
        if proposition.kind not in {"system_mechanism", "unknown_term"}:
            lines.append(f"assumable({p_symbol[pid]}).")
        if proposition.case_status == "reported":
            lines.append(f"reported({p_symbol[pid]}).")
    for rule_id, rule in rule_map.items():
        r = r_symbol[rule_id]
        h = p_symbol[rule.consequent_id]
        lines.append(f"head({r},{h}).")
        for antecedent in rule.antecedent_ids:
            lines.append(f"body({r},{p_symbol[antecedent]}).")
    lines.extend(("#show use/1.", "#show assume/1.", "#show reachable/2."))
    return "\n".join(lines), {value: key for key, value in p_symbol.items()}, {value: key for key, value in r_symbol.items()}


class ClingoCandidateSolver:
    def __init__(self) -> None:
        try:
            import clingo
        except ImportError as exc:
            raise ClingoUnavailableError(
                "Clingo is required for SAHS candidate search; install requirements-sahs.txt"
            ) from exc
        self._clingo = clingo

    def search(self, graph: CausalGraph, target_id: str, limits: SearchLimits) -> SearchResult:
        if limits.max_depth < 1 or limits.max_models < 1 or limits.timeout_seconds <= 0:
            raise ValueError("search limits must be positive")
        program, prop_symbols, rule_symbols = compile_program(graph, target_id, limits.max_depth)
        control = self._clingo.Control(["--warn=none"])
        control.configuration.solve.models = str(limits.max_models)
        control.add("base", [], program)
        control.ground([("base", [])])
        models: list[SolverCandidate] = []
        started = time.monotonic()
        handle = control.solve(on_model=lambda model: models.append(
            self._decode(model, target_id, prop_symbols, rule_symbols)
        ), async_=True)
        completed = handle.wait(limits.timeout_seconds)
        if not completed:
            handle.cancel()
        result = handle.get()
        elapsed = time.monotonic() - started
        unique: dict[tuple[tuple[str, ...], tuple[str, ...]], SolverCandidate] = {}
        dead_end_frontiers: set[str] = set()
        propositions = graph.proposition_map()
        rules = graph.rule_map()
        for candidate in models:
            if _selected_rules_are_cyclic(graph, set(candidate.rule_ids)):
                continue
            selected = [rules[item] for item in candidate.rule_ids]
            derived = {item.consequent_id for item in selected}
            used_assumptions = set(candidate.assumptions)
            incomplete = {
                proposition_id for proposition_id in candidate.proposition_ids
                if proposition_id != target_id
                and propositions[proposition_id].case_status != "reported"
                and proposition_id not in derived
                and proposition_id not in used_assumptions
            }
            if incomplete:
                dead_end_frontiers.update(incomplete)
                continue
            reported = tuple(sorted(
                proposition_id for proposition_id in candidate.proposition_ids
                if proposition_id != target_id
                and propositions[proposition_id].case_status == "reported"
            ))
            candidate = SolverCandidate(
                candidate.target_id, candidate.proposition_ids, candidate.rule_ids,
                reported, candidate.assumptions, candidate.trace,
            )
            key = (candidate.rule_ids, candidate.assumptions)
            unique.setdefault(key, candidate)
        candidates = tuple(unique[key] for key in sorted(unique))
        assumption_frontiers = {item for candidate in candidates for item in candidate.assumptions}
        frontiers = tuple(sorted(assumption_frontiers or dead_end_frontiers))
        if not completed or not result.exhausted:
            status = "partial_budget"
        elif candidates:
            status = "completed"
        else:
            status = "no_candidate_under_supplied_rules"
            frontiers = tuple(sorted(dead_end_frontiers)) or (target_id,)
        diagnostics = () if completed else ("Clingo runtime limit reached; returned completed models only",)
        return SearchResult(candidates, frontiers, status, len(models), elapsed, diagnostics)

    @staticmethod
    def _decode(model, target_id: str, prop_symbols: dict[str, str], rule_symbols: dict[str, str]) -> SolverCandidate:
        propositions: set[str] = set()
        rules: set[str] = set()
        assumptions: set[str] = set()
        reported: set[str] = set()
        trace: list[str] = []
        for symbol in model.symbols(shown=True):
            args = [str(item) for item in symbol.arguments]
            if symbol.name == "use" and len(args) == 1:
                rule_id = rule_symbols[args[0]]
                rules.add(rule_id)
                trace.append(f"use:{rule_id}")
            elif symbol.name == "assume" and args:
                assumptions.add(prop_symbols[args[0]])
            elif symbol.name == "reachable" and len(args) == 2:
                propositions.add(prop_symbols[args[0]])
        return SolverCandidate(
            target_id,
            tuple(sorted(propositions)),
            tuple(sorted(rules)),
            tuple(sorted(reported)),
            tuple(sorted(assumptions)),
            tuple(sorted(trace)),
        )


def _selected_rules_are_cyclic(graph: CausalGraph, selected_rule_ids: set[str]) -> bool:
    rules = graph.rule_map()
    edges: dict[str, set[str]] = {}
    for rule_id in selected_rule_ids:
        rule = rules[rule_id]
        edges.setdefault(rule.consequent_id, set()).update(rule.antecedent_ids)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in edges.get(node, ()):
            if child in edges and visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in tuple(edges) if node not in visited)
