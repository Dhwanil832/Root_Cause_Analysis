"""Strict proposal validation, Python-assigned statuses, and source-span checks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .engine_contracts import (
    CausalGraph,
    CausalRuleCandidate,
    ClarificationItem,
    InformationGap,
    Proposition,
    RejectedFragment,
    SourceChunk,
    SourceReference,
    SpecialistAssignment,
)
from .history import compute_input_fingerprint
from .proposal import ProposalBatch


class ProposalValidationError(ValueError):
    pass


TOP_FIELDS = {
    "schema_version", "proposed_propositions", "proposed_rules",
    "clarification_items", "information_gaps",
}
PROP_FIELDS = {"proposition_id", "text", "kind", "source_refs", "time_scope"}
RULE_FIELDS = {
    "rule_id", "antecedent_ids", "consequent_id", "relation", "modality",
    "conditions", "time_constraint", "basis", "source_refs", "source_relation",
    "vetted_rule_id",
}
REF_FIELDS = {"source_id", "source_version", "chunk_id", "exact_text", "source_relation"}
QUESTION_FIELDS = {
    "id", "question", "why_it_matters", "information_that_could_resolve_it",
    "linked_proposition_ids", "linked_rule_ids", "linked_candidate_ids", "linked_frontier_ids",
}
PROPOSITION_KINDS = {
    "case_claim", "incident_event", "component_state", "system_mechanism",
    "unknown_term", "unknown_condition",
}
RELATIONS = {"may_cause", "contributes_to", "enables", "inhibits", "precedes"}
BASES = {"source_described", "vetted_domain_rule", "model_proposed"}
SOURCE_RELATIONS = {"quotation", "paraphrase", "inference"}


def _fields(value: Any, required: set[str], allowed: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProposalValidationError(f"{name} must be an object")
    missing = required - value.keys()
    unknown = value.keys() - allowed
    if missing:
        raise ProposalValidationError(f"{name} missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ProposalValidationError(f"{name} has forbidden fields: {', '.join(sorted(unknown))}")
    return value


def _text(value: Any, name: str, limit: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ProposalValidationError(f"{name} must be nonempty text of at most {limit} characters")
    return value.strip()


def _string_list(value: Any, name: str, max_items: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ProposalValidationError(f"{name} must be an array of at most {max_items} strings")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ProposalValidationError(f"{name} must contain only nonempty strings")
    if len(set(value)) != len(value):
        raise ProposalValidationError(f"{name} must not contain duplicate IDs")
    return tuple(value)


def _source_ref(value: Any, assignment: SpecialistAssignment) -> SourceReference:
    raw = _fields(value, REF_FIELDS, REF_FIELDS, "source reference")
    for key in ("source_id", "source_version", "chunk_id", "exact_text", "source_relation"):
        _text(raw[key], f"source reference {key}", 12000 if key == "exact_text" else 300)
    if raw["source_relation"] not in SOURCE_RELATIONS:
        raise ProposalValidationError("source reference has invalid source_relation")
    matches = [chunk for chunk in assignment.source_bundle
               if chunk.source_id == raw["source_id"]
               and chunk.source_version == raw["source_version"]
               and chunk.chunk_id == raw["chunk_id"]]
    if len(matches) != 1:
        raise ProposalValidationError("source reference ID/version/chunk is not uniquely present in assignment")
    text = matches[0].text
    excerpt = raw["exact_text"]
    if len(excerpt.strip()) < 8:
        raise ProposalValidationError("source excerpt must contain at least 8 characters")
    first = text.find(excerpt)
    if first < 0:
        raise ProposalValidationError("source excerpt is not an exact substring of the supplied chunk")
    if text.find(excerpt, first + 1) >= 0:
        raise ProposalValidationError("source excerpt occurs more than once; offset is ambiguous")
    return SourceReference(
        source_id=matches[0].source_id,
        source_version=matches[0].source_version,
        chunk_id=matches[0].chunk_id,
        exact_text=excerpt,
        start_offset=first,
        end_offset=first + len(excerpt),
        source_kind=matches[0].source_kind,
        source_relation=raw["source_relation"],
    )


def _refs(value: Any, assignment: SpecialistAssignment, name: str) -> tuple[SourceReference, ...]:
    if not isinstance(value, list) or len(value) > 8:
        raise ProposalValidationError(f"{name} must be an array of at most 8 source references")
    return tuple(_source_ref(item, assignment) for item in value)


def _proposition(value: Any, assignment: SpecialistAssignment) -> Proposition:
    raw = _fields(value, PROP_FIELDS, PROP_FIELDS, "proposition")
    proposition_id = _text(raw["proposition_id"], "proposition_id", 160)
    text = _text(raw["text"], "proposition text")
    kind = raw["kind"]
    if kind not in PROPOSITION_KINDS:
        raise ProposalValidationError(f"unsupported proposition kind {kind!r}")
    refs = _refs(raw["source_refs"], assignment, "proposition source_refs")
    time_scope = raw["time_scope"]
    if time_scope is not None and (not isinstance(time_scope, str) or len(time_scope) > 300):
        raise ProposalValidationError("time_scope must be null or short text")
    # The model has no status field. Python owns the default lifecycle status.
    if kind in {"unknown_term", "unknown_condition"}:
        status = "unresolved"
    elif kind == "system_mechanism":
        status = "not_applicable"
    else:
        status = "hypothetical"
    return Proposition(proposition_id, text, kind, status, refs, time_scope)


def _rule(
    value: Any,
    assignment: SpecialistAssignment,
    known_propositions: set[str],
) -> CausalRuleCandidate:
    raw = _fields(value, RULE_FIELDS, RULE_FIELDS, "causal rule")
    rule_id = _text(raw["rule_id"], "rule_id", 160)
    antecedents = _string_list(raw["antecedent_ids"], "antecedent_ids", 8)
    if not antecedents:
        raise ProposalValidationError("causal rule needs at least one antecedent")
    consequent = _text(raw["consequent_id"], "consequent_id", 160)
    if consequent in antecedents:
        raise ProposalValidationError("self-referential rule is invalid")
    missing = set((*antecedents, consequent)) - known_propositions
    if missing:
        raise ProposalValidationError("unknown proposition IDs: " + ", ".join(sorted(missing)))
    relation = raw["relation"]
    if relation not in RELATIONS:
        raise ProposalValidationError(f"unsupported causal relation {relation!r}")
    modality = _text(raw["modality"], "rule modality", 160)
    conditions = _string_list(raw["conditions"], "rule conditions", 12)
    time_constraint = raw["time_constraint"]
    if time_constraint is not None and (not isinstance(time_constraint, str) or len(time_constraint) > 500):
        raise ProposalValidationError("time_constraint must be null or short text")
    basis = raw["basis"]
    if basis not in BASES:
        raise ProposalValidationError(f"unsupported rule basis {basis!r}")
    refs = _refs(raw["source_refs"], assignment, "rule source_refs")
    source_relation = raw["source_relation"]
    if source_relation is not None and source_relation not in SOURCE_RELATIONS:
        raise ProposalValidationError("invalid rule source_relation")
    vetted_rule_id = raw["vetted_rule_id"]
    supplied_vetted = {item.rule_id: item for item in assignment.vetted_domain_rules}
    if basis == "source_described" and (not refs or source_relation is None):
        raise ProposalValidationError("source-described rule requires source references and source_relation")
    if basis == "vetted_domain_rule":
        if not isinstance(vetted_rule_id, str) or vetted_rule_id not in supplied_vetted:
            raise ProposalValidationError("vetted rule ID was not supplied as vetted domain knowledge")
        vetted = supplied_vetted[vetted_rule_id]
        if (tuple(antecedents), consequent) != (vetted.antecedent_ids, vetted.consequent_id):
            raise ProposalValidationError("proposed rule does not match the supplied vetted rule structure")
        if relation != vetted.relation:
            raise ProposalValidationError("proposed relation differs from supplied vetted rule")
        return replace(vetted, rule_id=rule_id, status="supplied_vetted")
    if basis == "model_proposed" and vetted_rule_id is not None:
        raise ProposalValidationError("model-proposed rule cannot claim a vetted_rule_id")
    return CausalRuleCandidate(
        rule_id, antecedents, consequent, relation, modality, conditions,
        time_constraint, basis, refs, source_relation, "candidate",
    )


def _question(value: Any, kind: str, assignment: SpecialistAssignment,
              known_props: set[str], known_rules: set[str]) -> ClarificationItem | InformationGap:
    raw = _fields(value, QUESTION_FIELDS, QUESTION_FIELDS, f"{kind} item")
    question = _text(raw["question"], "question", 1500)
    why = _text(raw["why_it_matters"], "why_it_matters", 1500)
    resolves = _text(raw["information_that_could_resolve_it"], "information_that_could_resolve_it", 1500)
    props = _string_list(raw["linked_proposition_ids"], "linked_proposition_ids", 30)
    rules = _string_list(raw["linked_rule_ids"], "linked_rule_ids", 30)
    candidates = _string_list(raw["linked_candidate_ids"], "linked_candidate_ids", 30)
    frontiers = _string_list(raw["linked_frontier_ids"], "linked_frontier_ids", 30)
    if set(props) - known_props:
        raise ProposalValidationError("question references unknown propositions")
    if set(rules) - known_rules:
        raise ProposalValidationError("question references unknown rules")
    existing_candidates = set(assignment.history.candidate_map())
    existing_frontiers = {item.frontier_id for item in assignment.history.frontiers}
    if set(candidates) - existing_candidates:
        raise ProposalValidationError("question references unknown candidates")
    if set(frontiers) - existing_frontiers and not all(x.startswith("frontier:") for x in frontiers):
        raise ProposalValidationError("question references unknown frontiers")
    meaning = compute_input_fingerprint({
        "kind": kind, "question": question.casefold(), "why": why.casefold(),
        "resolves": resolves.casefold(),
    })
    generated_id = f"{kind}-" + meaning[:16]
    if kind == "clarification":
        return ClarificationItem(generated_id, question, why, props, rules, candidates)
    return InformationGap(generated_id, question, why, resolves, props, rules, candidates, frontiers)


def _dedupe_questions(items: list[Any]) -> tuple[Any, ...]:
    seen: dict[str, Any] = {}
    for item in items:
        question_text = item.question if isinstance(item, ClarificationItem) else item.unknown
        key = compute_input_fingerprint({
            "type": type(item).__name__, "question": question_text.casefold(),
            "why": item.why_it_matters.casefold(),
        })
        if key not in seen:
            seen[key] = item
            continue
        prior = seen[key]
        updates = {}
        if isinstance(prior, InformationGap):
            resolvers = tuple(dict.fromkeys((
                prior.information_that_could_resolve_it,
                item.information_that_could_resolve_it,
            )))
            updates["information_that_could_resolve_it"] = "; ".join(resolvers)
        seen[key] = replace(
            prior,
            linked_proposition_ids=tuple(sorted(set(prior.linked_proposition_ids) | set(item.linked_proposition_ids))),
            linked_rule_ids=tuple(sorted(set(prior.linked_rule_ids) | set(item.linked_rule_ids))),
            linked_candidate_ids=tuple(sorted(set(prior.linked_candidate_ids) | set(item.linked_candidate_ids))),
            **({"linked_frontier_ids": tuple(sorted(set(prior.linked_frontier_ids) | set(item.linked_frontier_ids)))}
               if isinstance(prior, InformationGap) else {}),
            **updates,
        )
    return tuple(seen[key] for key in sorted(seen))


def validate_proposal_batch(raw: Any, assignment: SpecialistAssignment) -> ProposalBatch:
    """Validate strict top-level shape; reject bad fragments independently."""
    top = _fields(raw, TOP_FIELDS, TOP_FIELDS, "proposal batch")
    if top["schema_version"] != "1":
        raise ProposalValidationError("unsupported proposal schema_version")
    limits = {
        "proposed_propositions": 40,
        "proposed_rules": 40,
        "clarification_items": 20,
        "information_gaps": 20,
    }
    for key, limit in limits.items():
        if not isinstance(top[key], list) or len(top[key]) > limit:
            raise ProposalValidationError(f"{key} must be an array of at most {limit}")

    rejected: list[RejectedFragment] = []
    new_props: list[Proposition] = []
    new_rules: list[CausalRuleCandidate] = []
    existing_props = assignment.relevant_graph.proposition_map()
    existing_rules = assignment.relevant_graph.rule_map()
    prop_ids = set(existing_props)
    rule_ids = set(existing_rules)
    for raw_prop in top["proposed_propositions"]:
        fragment_id = raw_prop.get("proposition_id") if isinstance(raw_prop, dict) else None
        try:
            prop = _proposition(raw_prop, assignment)
            if prop.proposition_id in prop_ids:
                raise ProposalValidationError("duplicate proposition ID")
            prop_ids.add(prop.proposition_id)
            new_props.append(prop)
        except (ProposalValidationError, TypeError, KeyError) as exc:
            rejected.append(RejectedFragment("proposition", fragment_id, str(exc)))

    for raw_rule in top["proposed_rules"]:
        fragment_id = raw_rule.get("rule_id") if isinstance(raw_rule, dict) else None
        try:
            rule = _rule(raw_rule, assignment, prop_ids)
            if rule.rule_id in rule_ids:
                raise ProposalValidationError("duplicate rule ID")
            rule_ids.add(rule.rule_id)
            new_rules.append(rule)
        except (ProposalValidationError, TypeError, KeyError) as exc:
            rejected.append(RejectedFragment("rule", fragment_id, str(exc)))

    known_prop_ids = prop_ids
    known_rule_ids = rule_ids
    clarifications: list[ClarificationItem] = []
    gaps: list[InformationGap] = []
    for kind, key, target in (
        ("clarification", "clarification_items", clarifications),
        ("information_gap", "information_gaps", gaps),
    ):
        for raw_item in top[key]:
            fragment_id = raw_item.get("id") if isinstance(raw_item, dict) else None
            try:
                target.append(_question(raw_item, kind, assignment, known_prop_ids, known_rule_ids))
            except (ProposalValidationError, TypeError, KeyError) as exc:
                rejected.append(RejectedFragment(kind, fragment_id, str(exc)))

    return ProposalBatch(
        "1", tuple(new_props), tuple(new_rules),
        _dedupe_questions(clarifications), _dedupe_questions(gaps), tuple(rejected),
    )


def merge_graph(graph: CausalGraph, proposal: ProposalBatch) -> CausalGraph:
    props = graph.proposition_map()
    rules = graph.rule_map()
    for item in proposal.proposed_propositions:
        props[item.proposition_id] = item
    for item in proposal.proposed_rules:
        rules[item.rule_id] = item
    return CausalGraph(
        tuple(props[key] for key in sorted(props)),
        tuple(rules[key] for key in sorted(rules)),
    )
