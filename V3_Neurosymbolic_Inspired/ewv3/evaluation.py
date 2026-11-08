"""Separate relevance, alternative coverage, attribution, and cost metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import EvidenceWorkerResult, SourceUnit


@dataclass(frozen=True, slots=True)
class GoldPassage:
    slot_id: str
    source_id: str
    representation_id: str
    start_offset: int
    end_offset: int


def evaluate_comparison_result(
    result: EvidenceWorkerResult,
    gold_passages: Iterable[GoldPassage],
    *,
    elapsed_ms: float,
    source_units: Iterable[SourceUnit] = (),
    cutoff: int = 5,
) -> dict[str, object]:
    """Score retrieved passages without scoring evidence impact or truth.

    A passage is relevant only when it covers a gold span assigned to that
    slot. Comparison coverage asks whether every alternative surfaced at
    least one gold-relevant passage. Location accuracy is exact source,
    representation, and offset coverage. Cost values are measured separately.
    """
    gold = tuple(gold_passages)
    source_by_id = {source.source_id: source for source in source_units}
    returned_hits = 0
    relevant_count = 0
    relevant_gold_found: set[tuple[str, str, str, int, int]] = set()
    side_hit_counts: dict[str, int] = {}
    attributed_links = 0
    gold_span_hits = 0
    location_checked_links = 0
    valid_source_locations = 0
    reciprocal_ranks: list[float] = []

    for slot_result in result.slot_results:
        links = slot_result.candidate_links[:cutoff]
        returned_hits += len(links)
        first_rank = None
        side_relevant = 0
        for rank, link in enumerate(links, start=1):
            location_checked_links += 1
            source = source_by_id.get(link.source_id)
            if source is not None:
                representation = next((rep for rep in source.representations
                                       if rep.representation_id == link.representation_id), None)
                text = (representation.text if representation else
                        source.text if not source.representations else None)
                text_location_valid = (
                    text is not None and link.start_offset is not None and link.end_offset is not None
                    and 0 <= link.start_offset < link.end_offset <= len(text)
                    and text[link.start_offset:link.end_offset] == link.exact_text
                )
                visual_context = link.structural_context
                visual_location_valid = (
                    link.start_offset is None and link.end_offset is None
                    and bool(visual_context.get("page") is not None
                             or visual_context.get("bounding_box") is not None
                             or visual_context.get("region_id")
                             or visual_context.get("content_ref"))
                )
                if text_location_valid or visual_location_valid:
                    valid_source_locations += 1
            source_matches = [g for g in gold if g.slot_id == slot_result.slot_id
                              and g.source_id == link.source_id
                              and g.representation_id == link.representation_id]
            if source_matches:
                attributed_links += 1
                located = [g for g in source_matches
                           if link.start_offset is not None and link.end_offset is not None
                           and link.start_offset <= g.start_offset and link.end_offset >= g.end_offset]
                if located:
                    gold_span_hits += 1
                    relevant_count += 1
                    side_relevant += 1
                    if first_rank is None:
                        first_rank = rank
                    for g in located:
                        relevant_gold_found.add((g.slot_id, g.source_id, g.representation_id,
                                                 g.start_offset, g.end_offset))
        side_hit_counts[slot_result.slot_id] = side_relevant
        if first_rank is not None:
            reciprocal_ranks.append(1.0 / first_rank)

    comparison_sides = [side.slot_id for group in result.comparison_results for side in group.sides]
    sides_with_gold_hit = sum(side_hit_counts.get(slot_id, 0) > 0 for slot_id in comparison_sides)
    comparison_groups = len(result.comparison_results)
    complete_groups = sum(
        all(side_hit_counts.get(side.slot_id, 0) > 0 for side in group.sides)
        for group in result.comparison_results
    )
    return {
        "passage_relevance": {
            "precision_at_cutoff": relevant_count / returned_hits if returned_hits else 0.0,
            "recall_at_cutoff": len(relevant_gold_found) / len(gold) if gold else 0.0,
            "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks)
            if reciprocal_ranks else 0.0,
            "cutoff": cutoff,
        },
        "alternative_coverage": {
            "sides_with_relevant_candidate": sides_with_gold_hit,
            "assigned_sides": len(comparison_sides),
            "side_retrieval_rate": sides_with_gold_hit / len(comparison_sides)
            if comparison_sides else 0.0,
            "groups_with_all_alternatives_retrieved": complete_groups,
            "comparison_groups": comparison_groups,
            "complete_group_rate": complete_groups / comparison_groups
            if comparison_groups else 0.0,
            "worker_statuses": [group.status for group in result.comparison_results],
        },
        "source_location": {
            "location_checked_links": location_checked_links,
            "valid_source_locations": valid_source_locations,
            "source_location_validity_rate": valid_source_locations / location_checked_links
            if location_checked_links else 0.0,
            "source_attribution_precision": attributed_links / returned_hits if returned_hits else 0.0,
            "source_attributed_links": attributed_links,
            "links_covering_gold_span": gold_span_hits,
            "gold_span_precision": gold_span_hits / attributed_links
            if attributed_links else 0.0,
            "gold_passage_location_recall": len(relevant_gold_found) / len(gold) if gold else 0.0,
        },
        "cost": {
            "elapsed_ms": round(max(0.0, elapsed_ms), 3),
            "retrieval_calls": result.resource_usage.get("query_calls", 0),
            "retriever_backend_calls": result.resource_usage.get("retriever_backend_calls", 0),
            "planner_calls": result.resource_usage.get("planner_calls", 0),
            "followup_planner_calls": result.resource_usage.get("followup_planner_calls", 0),
            "reranked_candidates": result.resource_usage.get("reranked_candidates", 0),
            "model_tokens": result.resource_usage.get("model_tokens", None),
            "model_token_cost_note": "null means the configured planner did not expose token usage",
        },
    }
