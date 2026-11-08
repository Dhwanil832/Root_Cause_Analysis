"""Bounded, mode-aware proposal context and epistemic-boundary instructions."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any

from .engine_contracts import SpecialistAssignment
from .proposal import ProposalRequest


STRICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version", "proposed_propositions", "proposed_rules",
        "clarification_items", "information_gaps",
    ],
    "properties": {
        "schema_version": {"type": "string"},
        "proposed_propositions": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["proposition_id", "text", "kind", "source_refs", "time_scope"],
            "properties": {
                "proposition_id": {"type": "string"},
                "text": {"type": "string"},
                "kind": {"enum": ["case_claim", "incident_event", "component_state", "system_mechanism", "unknown_term", "unknown_condition"]},
                "source_refs": {"type": "array", "items": {"$ref": "#/$defs/source_ref"}},
                "time_scope": {"type": ["string", "null"]},
            },
        }},
        "proposed_rules": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["rule_id", "antecedent_ids", "consequent_id", "relation", "modality", "conditions", "time_constraint", "basis", "source_refs", "source_relation", "vetted_rule_id"],
            "properties": {
                "rule_id": {"type": "string"},
                "antecedent_ids": {"type": "array", "items": {"type": "string"}},
                "consequent_id": {"type": "string"},
                "relation": {"enum": ["may_cause", "contributes_to", "enables", "inhibits", "precedes"]},
                "modality": {"type": "string"},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "time_constraint": {"type": ["string", "null"]},
                "basis": {"enum": ["source_described", "vetted_domain_rule", "model_proposed"]},
                "source_refs": {"type": "array", "items": {"$ref": "#/$defs/source_ref"}},
                "source_relation": {"enum": ["quotation", "paraphrase", "inference", None]},
                "vetted_rule_id": {"type": ["string", "null"]},
            },
        }},
        "clarification_items": {"$ref": "#/$defs/questions"},
        "information_gaps": {"$ref": "#/$defs/questions"},
    },
    "$defs": {
        "source_ref": {
            "type": "object", "additionalProperties": False,
            "required": ["source_id", "source_version", "chunk_id", "exact_text", "source_relation"],
            "properties": {
                "source_id": {"type": "string"}, "source_version": {"type": "string"},
                "chunk_id": {"type": "string"}, "exact_text": {"type": "string"},
                "source_relation": {"enum": ["quotation", "paraphrase", "inference"]},
            },
        },
        "questions": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "question", "why_it_matters", "information_that_could_resolve_it", "linked_proposition_ids", "linked_rule_ids", "linked_candidate_ids", "linked_frontier_ids"],
                "properties": {
                    "id": {"type": "string"}, "question": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "information_that_could_resolve_it": {"type": "string"},
                    "linked_proposition_ids": {"type": "array", "items": {"type": "string"}},
                    "linked_rule_ids": {"type": "array", "items": {"type": "string"}},
                    "linked_candidate_ids": {"type": "array", "items": {"type": "string"}},
                    "linked_frontier_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


# Sent as Ollama's structured-output ``format``. It pins schema_version to the
# only value validate_proposal_batch accepts; Python validation still decides
# what is kept.
PROPOSAL_FORMAT_SCHEMA: dict[str, Any] = {
    **STRICT_SCHEMA,
    "properties": {**STRICT_SCHEMA["properties"], "schema_version": {"const": "1"}},
}

SYSTEM_INSTRUCTIONS = """You are the proposal generator inside SAHS, a bounded abductive Specialist.
Return exactly one JSON object matching the supplied schema. Unknown fields are forbidden.

You propose candidate mechanisms and unresolved conditions; you do not decide what actually happened. New incident_event propositions are always hypothetical in Python. A general source statement such as 'a leaking valve can cause pressure loss' describes only a possible mechanism: it does not establish that the valve leaked or that pressure was lost in this incident. Do not encode source-described possibility as an incident event.

Use only proposition and source IDs in the supplied context. For a source-described rule, cite the exact passage and mark whether the causal relation is quoted, paraphrased, or inferred. A source excerpt is provenance, not proof the relation applied in this incident. For a vetted rule, use only a supplied vetted_rule_id. Do not set truth/status, evidence-impact, confidence, support, contradiction, root-cause, or request-approval fields. Keep alternatives and AND-required antecedents explicit. When a term/configuration is unclear, emit a clarification and continue with bounded provisional alternatives. Incident-information gaps state what remains unknown and what information could resolve it; the Lead decides routing.

Propose atomic propositions and rules, not a polished narrative. Return a small set within the supplied budgets. Do not duplicate existing open questions or candidate structures."""


# Conservative: hash-heavy JSON tokenizes near 2 characters per token and prose
# near 3.6, so a typical proposal context is over- rather than under-counted.
CHARS_PER_TOKEN = 3.0


def estimate_prompt_tokens(context: dict[str, Any], system: str = SYSTEM_INSTRUCTIONS) -> int:
    return int((len(system) + len(json.dumps(context, ensure_ascii=False, default=str))) / CHARS_PER_TOKEN)


def _fit_to_budget(context: dict[str, Any], max_prompt_tokens: int) -> list[str]:
    """Shrink the context in place until it fits, least useful material first.

    The schema, the task, the target propositions and the rules touching them
    stay. Each removal is listed so the model and the run record know what was
    left out. A context still over budget after every step is sent as it stands.
    """
    omitted: list[str] = []
    graph = context["relevant_graph"]
    targets = {context["task"]["focal_proposition_id"], *context["task"]["target_proposition_ids"]} - {None}
    near_rules = [r for r in graph["rules"] if targets & {r["consequent_id"], *r["antecedent_ids"]}]
    near_props = targets | {pid for r in near_rules for pid in (r["consequent_id"], *r["antecedent_ids"])}
    cited = {ref["source_id"] for item in (*graph["propositions"], *near_rules)
             if item in near_rules or item["proposition_id"] in targets for ref in item["source_refs"]}
    cited |= {row.get("material_id") for row in context["assessor_annotations"]
              if row.get("effect") != "neutral"}
    sources, annotations = context["source_bundle"], context["assessor_annotations"]

    def compact_refs():
        for item in (*graph["propositions"], *graph["rules"]):
            item["source_refs"] = [{"source_id": r["source_id"]} for r in item["source_refs"]]
        omitted.append("relevant_graph source_refs reduced to source_id")

    def drop(items, item, label):
        items.remove(item)
        omitted.append(label)

    def distant_graph():
        dropped = [r["rule_id"] for r in graph["rules"] if r not in near_rules]
        dropped += [p["proposition_id"] for p in graph["propositions"] if p["proposition_id"] not in near_props]
        graph["rules"] = near_rules
        graph["propositions"] = [p for p in graph["propositions"] if p["proposition_id"] in near_props]
        if dropped:
            omitted.append("relevant_graph items not linked to the targets: " + ", ".join(dropped))

    # Later documents in the bundle go first within each group.
    steps = [compact_refs]
    steps += [lambda s=s: drop(sources, s, f"source_bundle document {s['source_id']}")
              for s in reversed(sources) if s["source_id"] not in cited]
    steps += [lambda a=a: drop(annotations, a, f"assessor annotation {a.get('annotation_id')}")
              for a in annotations if a.get("effect") == "neutral"]
    steps += [distant_graph]
    steps += [lambda s=s: drop(sources, s, f"source_bundle document {s['source_id']}")
              for s in reversed(sources) if s["source_id"] in cited]
    steps += [lambda a=a: drop(annotations, a, f"assessor annotation {a.get('annotation_id')}")
              for a in annotations if a.get("effect") != "neutral"]
    for step in steps:
        if estimate_prompt_tokens(context) <= max_prompt_tokens:
            break
        step()
    return omitted


# Room kept for the short note that tells the model what was left out.
OMISSION_NOTE_TOKENS = 120


def _omission_note(omitted: list[str]) -> list[str]:
    """Counts by kind; the item-by-item list is too long to spend prompt on."""
    counts: dict[str, int] = {}
    for item in omitted:
        if item.startswith("source_bundle document"):
            kind, n = "source_bundle documents", 1
        elif item.startswith("assessor annotation"):
            kind, n = "assessor annotations", 1
        elif item.startswith("relevant_graph items"):
            kind, n = "relevant_graph items not linked to the targets", item.count(",") + 1
        else:
            kind, n = item, 0
        counts[kind] = counts.get(kind, 0) + n
    return [f"{n} {kind} left out" if n else kind for kind, n in counts.items()]


def build_proposal_request(
    assignment: SpecialistAssignment,
    *,
    target_proposition_id: str | None = None,
    task_mode: str | None = None,
    max_source_chars: int = 24000,
    max_prompt_tokens: int | None = None,
) -> ProposalRequest:
    graph = assignment.relevant_graph
    sources = []
    remaining = max_source_chars
    for chunk in assignment.source_bundle:
        if remaining <= 0:
            break
        text = chunk.text[:remaining]
        sources.append({**asdict(chunk), "text": text, "truncated": len(text) < len(chunk.text)})
        remaining -= len(text)
    mode = task_mode or assignment.mode
    context = {
        "schema": STRICT_SCHEMA,
        "task": {
            "mode": mode,
            "operation_goal": assignment.operation_goal,
            "lead_direction": assignment.lead_direction,
            "focal_proposition_id": target_proposition_id or assignment.focal_proposition_id,
            "target_proposition_ids": assignment.target_proposition_ids,
            "budgets": assignment.budgets,
        },
        "initial_case_packet": assignment.initial_case_packet,
        "relevant_graph": asdict(graph),
        "source_bundle": sources,
        "vetted_domain_rules": [asdict(item) for item in assignment.vetted_domain_rules],
        "lead_feedback": list(assignment.lead_feedback),
        "assessor_annotations": list(assignment.assessor_annotations),
        "changed_ids": list(assignment.changed_ids),
        "specialist_history": asdict(assignment.history),
        "epistemic_instructions": {
            "case_status_is_python_assigned": True,
            "assessor_annotations_are_read_only": True,
            "general_mechanism_does_not_establish_incident_occurrence": True,
        },
    }
    omitted: list[str] = []
    if max_prompt_tokens is not None and estimate_prompt_tokens(context) > max_prompt_tokens:
        context = json.loads(json.dumps(context, ensure_ascii=False, default=str))
        omitted = _fit_to_budget(context, max_prompt_tokens - OMISSION_NOTE_TOKENS)
        if omitted:
            # Present only when something was left out, so the model knows the context is partial.
            context["omitted_for_length"] = _omission_note(omitted)
    return ProposalRequest(
        assignment_id=assignment.assignment_id,
        task_mode=mode,
        operation_goal=assignment.operation_goal,
        target_proposition_id=target_proposition_id or assignment.focal_proposition_id,
        context=context,
        omitted=tuple(omitted),
    )
