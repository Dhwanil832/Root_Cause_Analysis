"""Bounded V3 Evidence Worker orchestration."""
from __future__ import annotations

from dataclasses import asdict, replace
import re
from typing import Any

from .config import WorkerConfig
from .contracts import (
    CandidateLink, ComparisonResult, ComparisonSideResult, Coverage,
    EvidenceAssignment, EvidenceWorkerResult,
    RequestDraft, SearchPassStatus, SearchTrace, SlotResult, WorkPhase,
)
from .ledger import InMemoryWorkLedger
from .ports import CorpusRetriever, EvidencePlanner
from .retrieval import iter_representations
from .validation import (
    EvidenceValidationError, fingerprint, validate_assignment,
    validate_query_plan, validate_request_plan, verify_source_span,
)


_TOPIC_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can",
    "case", "did", "do", "document", "during", "event", "evidence", "find",
    "for", "from", "has", "have", "how", "in", "incident", "information",
    "is", "it", "log", "of", "on", "or", "record", "show", "the", "this",
    "to", "was", "were", "what", "when", "where", "which", "whether", "with",
}


def _topic_terms(slot) -> tuple[str, ...]:
    excluded = set()
    for value in (*slot.entity_ids, *slot.exact_constraints):
        excluded.update(re.findall(r"[a-z0-9]+", value.casefold()))
    excluded.update(re.findall(r"[a-z0-9]+", slot.time_scope.casefold()))
    terms = []
    for token in re.findall(r"[a-z0-9]+", slot.description.casefold()):
        if token in _TOPIC_STOPWORDS or token in excluded or len(token) < 3:
            continue
        token = _normalize_topic_token(token)
        if token not in terms:
            terms.append(token)
    return tuple(terms)


def _normalize_topic_token(token: str) -> str:
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        token = token[:-2]
        return token + "e" if token.endswith(("ic", "ag", "servic")) else token
    if token.endswith("s") and not token.endswith("ss") and len(token) > 4:
        return token[:-1]
    return token


def _contains_literal_facet(text: str, facet: str) -> bool:
    """Match identifiers/constraints as complete literal phrases.

    A plain substring check makes an assigned identifier such as ``V-13``
    match ``V-130``. Treat letters and digits as the token boundary while
    allowing punctuation around the facet in the source passage.
    """
    facet = facet.strip()
    if not facet:
        return False
    pattern = rf"(?<![A-Za-z0-9]){re.escape(facet)}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


class EvidenceWorkerEngine:
    def __init__(self, planner: EvidencePlanner, retriever: CorpusRetriever,
                 *, ledger: InMemoryWorkLedger | None = None,
                 config: WorkerConfig | None = None) -> None:
        self.planner = planner
        self.retriever = retriever
        self.ledger = ledger or InMemoryWorkLedger()
        self.config = config or WorkerConfig()

    def run(self, assignment: EvidenceAssignment) -> EvidenceWorkerResult:
        input_fp = fingerprint(asdict(assignment))
        claim, previous = self.ledger.begin(assignment.work_item_id, assignment.event_id, input_fp)
        if claim == "duplicate":
            return previous
        if claim == "conflict":
            return self._result(assignment, "invalid_input", WorkPhase.BLOCKED,
                                SearchPassStatus.BLOCKED,
                                ("event_id was reused with different assignment content",))
        if claim == "busy":
            return self._result(assignment, "work_item_busy", WorkPhase.AWAITING_LEAD,
                                SearchPassStatus.BLOCKED, ("work item already has an active attempt",))
        try:
            result = self._run_claimed(assignment)
            self.ledger.finish(assignment.work_item_id, assignment.event_id, input_fp, result)
            return result
        except Exception:
            self.ledger.abandon(assignment.work_item_id)
            raise

    def _run_claimed(self, a: EvidenceAssignment) -> EvidenceWorkerResult:
        try:
            validate_assignment(a, max_sources=self.config.max_sources,
                                max_text_chars=self.config.max_text_chars)
        except EvidenceValidationError as exc:
            return self._result(a, "invalid_input", WorkPhase.BLOCKED,
                                SearchPassStatus.BLOCKED, (str(exc),))

        allowed = set(a.allowed_source_ids) if a.allowed_source_ids else {s.source_id for s in a.sources}
        sources = tuple(s for s in a.sources if s.source_id in allowed)
        source_map = {s.source_id: s for s in sources}
        searchable = tuple(s for s in sources if s.searchable and s.readiness == "ready"
                           and iter_representations(s))
        readiness_limited = len(searchable) != len(sources) or bool(a.manifest.failed_source_ids or a.manifest.pending_source_ids)
        representation_map = {
            (source.source_id, rep.representation_id): rep
            for source in searchable for rep in iter_representations(source)
        }
        planner_calls = 0
        try:
            planner_calls += 1
            raw_plan = self.planner.plan_queries(a)
            query_map = validate_query_plan(raw_plan, a, self.config.max_queries_per_slot)
        except Exception as exc:
            return self._result(a, "generation_failed", WorkPhase.AWAITING_LEAD,
                                SearchPassStatus.BLOCKED,
                                (f"query planning failed: {type(exc).__name__}: {exc}",))

        traces: list[SearchTrace] = []
        slot_hits: dict[str, list[tuple[Any, str]]] = {
            slot.slot_id: [] for need in a.needs for slot in need.slots
        }
        # Keep the strongest retrieval score for a passage seen through more
        # than one query instead of freezing the first query's score.
        used_candidates: dict[tuple[str, str, str, str, str, int, int], tuple[str, int]] = {}
        query_count = 0
        search_limited = False
        partial_slots: set[str] = set()
        budget_slots: set[str] = set()
        initial_queries = {sid: tuple(qs) for sid, qs in query_map.items()}
        query_count, new_traces, hit_partial, hit_budget = self._execute_search_pass(
            a, query_map, pass_number=1, query_origin="initial", source_map=source_map,
            searchable=searchable, representation_map=representation_map,
            slot_hits=slot_hits, used_candidates=used_candidates, query_count=query_count,
        )
        traces.extend(new_traces)
        partial_slots.update(hit_partial)
        budget_slots.update(hit_budget)
        search_limited = bool(partial_slots or budget_slots)

        # One result-aware refinement pass. A relevant candidate is a retrieval
        # result, not proof that the assigned information need is complete, so
        # the planner receives every slot and its first-pass feedback.
        first_results = self._make_slot_results(
            a, slot_hits, source_map, representation_map, partial_slots,
            budget_slots, readiness_limited, searchable, sources,
        )
        refinement_slot_ids = {r.slot_id for r in first_results}
        refine = getattr(self.planner, "refine_queries", None)
        diagnostics: list[str] = []
        followup_calls = 0
        if (refinement_slot_ids and self.config.max_followup_plans
                and planner_calls < self.config.max_query_calls and callable(refine)
                and query_count < a.budgets.get("max_search_calls", 100)):
            feedback = self._refinement_feedback(first_results, initial_queries, traces)
            try:
                planner_calls += 1
                followup_calls += 1
                raw_refined = refine(a, tuple(sorted(refinement_slot_ids)), feedback)
                refined = validate_query_plan(
                    raw_refined, a, self.config.max_followup_queries_per_slot,
                    allowed_slot_ids=refinement_slot_ids,
                )
                # Ignore accidental repeats; deterministic initial queries are
                # also excluded so the extra planner call buys new search.
                refined = {
                    sid: tuple(q for q in qs if q not in set(initial_queries.get(sid, ()))
                               and q != self._deterministic_query(self._slot_by_id(a, sid)))
                    for sid, qs in refined.items()
                }
                if any(refined.values()):
                    query_count, new_traces, hit_partial, hit_budget = self._execute_search_pass(
                        a, refined, pass_number=2, query_origin="result_refinement",
                        source_map=source_map, searchable=searchable,
                        representation_map=representation_map, slot_hits=slot_hits,
                        used_candidates=used_candidates, query_count=query_count,
                    )
                    traces.extend(new_traces)
                    partial_slots.update(hit_partial)
                    budget_slots.update(hit_budget)
                    search_limited = search_limited or bool(hit_partial or hit_budget)
            except Exception as exc:
                diagnostics.append(f"bounded query refinement unavailable: {type(exc).__name__}: {exc}")
        elif refinement_slot_ids and self.config.max_followup_plans and planner_calls < self.config.max_query_calls and not callable(refine):
            diagnostics.append("bounded query refinement unavailable: planner has no refine_queries method")

        results = self._make_slot_results(
            a, slot_hits, source_map, representation_map, partial_slots,
            budget_slots, readiness_limited, searchable, sources,
        )
        graded_answered: set[str] = set()
        grade = getattr(self.planner, "grade_candidates", None)
        if self.config.grade_candidates and callable(grade) and any(r.candidate_links for r in results):
            planner_calls += 1
            results, graded_answered, grade_notes = self._grade_results(a, results, grade)
            diagnostics.extend(grade_notes)
        comparison_results = self._make_comparison_results(a, results)

        # Retrieval coverage says whether passages were found in the corpus; it
        # does not close the Lead-owned information need. Let the request
        # planner inspect every slot and decide whether additional material is
        # useful, including when a partial or general candidate was retrieved.
        # A slot whose question a held passage already answers or contradicts is
        # not requested again: the material is in the pool.
        requestable_slots = {slot.slot_id for need in a.needs for slot in need.slots} - graded_answered
        requests: tuple[RequestDraft, ...] = ()
        if requestable_slots and self.config.max_request_drafts and self.config.max_request_calls:
            summaries = tuple({
                "slot_id": r.slot_id,
                "coverage": r.coverage.value,
                "reason": r.reason,
                "candidate_links": tuple({
                    "candidate_link_id": link.candidate_link_id,
                    "source_id": link.source_id,
                    "source_version": link.source_version,
                    "representation_id": link.representation_id,
                    "start_offset": link.start_offset,
                    "end_offset": link.end_offset,
                    "exact_text": link.exact_text[:1500],
                    "source_kind": link.source_kind,
                    "modality": link.modality,
                    "matched_facets": link.matched_facets,
                    "missing_facets": link.mismatched_facets,
                    "matched_topic_terms": link.matched_topic_terms,
                    "missing_topic_terms": link.missing_topic_terms,
                } for link in r.candidate_links),
                "searched_source_ids": tuple(dict.fromkeys(
                    source_id for trace in traces if trace.slot_id == r.slot_id
                    for source_id in trace.source_ids_searched)),
            } for r in results if r.slot_id in requestable_slots)
            try:
                planner_calls += 1
                raw_requests = self.planner.draft_requests(a, tuple(sorted(requestable_slots)), summaries)
                rows, rejected_requests = validate_request_plan(
                    raw_requests, a, requestable_slots, self.config.max_request_drafts)
                diagnostics.extend(rejected_requests)
                requests = tuple(RequestDraft(
                    request_id=row["request_id"], request_type=row["request_type"],
                    slot_ids=tuple(row["slot_ids"]), question_or_document=row["request"],
                    requested_fields=tuple(row["requested_fields"]),
                    why_it_may_help=row["why_it_may_help"],
                    searched_scope=tuple(dict.fromkeys(
                        source_id for trace in traces if trace.slot_id in row["slot_ids"]
                        for source_id in trace.source_ids_searched)),
                    limits=tuple(x for x in ("assigned corpus only",) if readiness_limited or search_limited),
                ) for row in rows)
            except Exception as exc:
                diagnostics.append(f"request drafting unavailable: {type(exc).__name__}: {exc}")
        elif requestable_slots:
            diagnostics.append("request drafting disabled by worker configuration")

        pass_status = SearchPassStatus.PARTIAL if (readiness_limited or search_limited) else SearchPassStatus.COMPLETE
        status = "ready_for_assessor" if any(r.candidate_links for r in results) or requests else "no_candidate_in_scope"
        return EvidenceWorkerResult(
            schema_version="1", assignment_id=a.assignment_id,
            work_item_id=a.work_item_id, event_id=a.event_id,
            case_snapshot_id=a.case_snapshot_id, board_version=a.board_version,
            corpus_snapshot_id=a.manifest.corpus_snapshot_id,
            material_catalog_version=a.manifest.material_catalog_version,
            representation_version=a.manifest.representation_version,
            status=status, work_phase=WorkPhase.AWAITING_ASSESSOR if status == "ready_for_assessor" else WorkPhase.AWAITING_LEAD,
            search_pass_status=pass_status, slot_results=tuple(results),
            comparison_results=comparison_results,
            preserved_candidate_links=tuple(
                link for link in a.prior_candidate_links
                if any(link.need_id == need.need_id and link.slot_id == slot.slot_id
                       for need in a.needs for slot in need.slots)
            ),
            request_drafts=requests, traces=tuple(traces), diagnostics=tuple(diagnostics),
            resource_usage={"query_calls": query_count, "candidate_links": sum(len(r.candidate_links) for r in results),
                            "request_drafts": len(requests), "planner_calls": planner_calls,
                            "followup_planner_calls": followup_calls,
                            "retriever_backend_calls": sum(t.backend_count for t in traces),
                            "reranked_candidates": sum(t.returned_hit_count for t in traces
                                                       if t.reranker_version),
                            "retriever_version": self.retriever.version},
        )

    def _grade_results(self, a, results, grade):
        """Have the model under test grade each slot's candidates; keep min_grade and above.

        Returns the filtered results, the slot IDs a kept passage answers or
        contradicts, and diagnostics. If grading fails or returns nothing usable
        for a slot, that slot keeps its retrieval order, capped, so a bad reply
        never deletes evidence silently.
        """
        from .prompts import GRADE_ROLES
        slot_map = {slot.slot_id: slot for need in a.needs for slot in need.slots}
        need_map = {need.need_id: need for need in a.needs}
        rows = tuple({
            "slot_id": r.slot_id,
            "question": slot_map[r.slot_id].description,
            "target_claim": need_map[r.need_id].target_claim if r.need_id in need_map else "",
            "candidates": [{
                "candidate_link_id": link.candidate_link_id,
                "document": link.structural_context.get("document_title") or link.title,
                "document_details": link.structural_context.get("document_details", []),
                "section": link.structural_context.get("section", ""),
                "passage": link.structural_context.get("readable_text") or link.exact_text,
                "before": link.structural_context.get("before", ""),
                "after": link.structural_context.get("after", ""),
            } for link in r.candidate_links],
        } for r in results if r.candidate_links)
        notes: list[str] = []
        try:
            raw = grade(a, rows)
            grades = raw.get("grades") if isinstance(raw, dict) else None
            if not isinstance(grades, list):
                raise ValueError("grades must be a list")
        except Exception as exc:
            notes.append(f"candidate grading unavailable: {type(exc).__name__}: {exc}")
            grades = []
        known = {link.candidate_link_id for r in results for link in r.candidate_links}
        by_id: dict[str, tuple[int, str]] = {}
        for row in grades:
            if not isinstance(row, dict):
                continue
            cid, value, role = row.get("candidate_link_id"), row.get("grade"), row.get("role")
            if cid in known and type(value) is int and 0 <= value <= 3 and cid not in by_id:
                by_id[cid] = (value, role if role in GRADE_ROLES else "background")
        rejected = sum(1 for row in grades if not (isinstance(row, dict) and row.get("candidate_link_id") in by_id))
        if rejected:
            notes.append(f"candidate grading: {rejected} grade rows ignored (unknown id, duplicate, or bad value)")
        answered: set[str] = set()
        filtered = []
        for r in results:
            if not r.candidate_links:
                filtered.append(r)
                continue
            graded = [link for link in r.candidate_links if link.candidate_link_id in by_id]
            if not graded:
                notes.append(f"candidate grading returned no grades for slot {r.slot_id}; kept retrieval order")
                filtered.append(replace(r, candidate_links=r.candidate_links[:self.config.max_assessed_per_slot]))
                continue
            kept = []
            for position, link in enumerate(r.candidate_links):
                value, role = by_id.get(link.candidate_link_id, (0, "unrelated"))
                if value >= self.config.min_grade:
                    kept.append((-value, position, replace(link, structural_context={
                        **link.structural_context, "reader_grade": value, "reader_role": role})))
                    if role in {"answers", "contradicts"} and value == 3:
                        answered.add(r.slot_id)
            kept.sort(key=lambda item: item[:2])
            links = tuple(item[2] for item in kept[:self.config.max_assessed_per_slot])
            if links:
                filtered.append(replace(r, candidate_links=links))
            else:
                coverage = r.coverage if r.coverage in {Coverage.PARTIAL, Coverage.BUDGET_EXHAUSTED} else Coverage.NO_MATCH_IN_SCOPE
                filtered.append(replace(r, candidate_links=(), coverage=coverage,
                                        reason="retrieved passages were judged not relevant to this slot"))
        return filtered, answered, notes

    @staticmethod
    def _slot_by_id(a, slot_id):
        return next(slot for need in a.needs for slot in need.slots if slot.slot_id == slot_id)

    @staticmethod
    def _make_comparison_results(a, slot_results):
        by_need_slot = {(result.need_id, result.slot_id): result for result in slot_results}
        output = []
        for need in a.needs:
            for comparison in need.comparisons:
                sides = tuple(ComparisonSideResult(
                    slot_id=slot_id,
                    retrieval_coverage=by_need_slot[(need.need_id, slot_id)].coverage.value,
                    candidate_link_ids=tuple(
                        link.candidate_link_id
                        for link in by_need_slot[(need.need_id, slot_id)].candidate_links
                    ),
                ) for slot_id in comparison.slot_ids)
                coverages = [side.retrieval_coverage for side in sides]
                limited = any(x in {Coverage.PARTIAL.value, Coverage.BUDGET_EXHAUSTED.value,
                                    Coverage.NOT_SEARCHABLE.value, Coverage.BLOCKED.value}
                              for x in coverages)
                candidates = [bool(side.candidate_link_ids) for side in sides]
                if limited:
                    status = "budget_or_readiness_limited"
                elif all(candidates):
                    status = "all_alternatives_have_candidates"
                elif any(candidates):
                    status = "some_alternatives_missing_candidates"
                else:
                    status = "no_alternative_has_candidates"
                output.append(ComparisonResult(
                    comparison_id=comparison.comparison_id,
                    need_id=need.need_id,
                    comparison_dimension=comparison.comparison_dimension,
                    sides=sides,
                    status=status,
                ))
        return tuple(output)

    @staticmethod
    def _deterministic_query(slot) -> str:
        return " ".join((slot.description, *slot.entity_ids,
                          slot.time_scope, *slot.exact_constraints)).strip()[:500]

    def _execute_search_pass(self, a, query_map, *, pass_number, query_origin,
                             source_map, searchable, representation_map, slot_hits,
                             used_candidates, query_count):
        traces = []
        partial_slots: set[str] = set()
        budget_slots: set[str] = set()
        limit = a.budgets.get("max_search_calls", 100)
        queues: list[list[tuple[Any, Any, str, str]]] = []
        for need in a.needs:
            for slot in need.slots:
                queries = list(query_map.get(slot.slot_id, ()))
                if pass_number == 1:
                    deterministic = self._deterministic_query(slot)
                    if deterministic and deterministic not in queries:
                        queries.insert(0, deterministic)
                    if not queries:
                        queries = [slot.description[:500]]
                    query_limit = self.config.max_queries_per_slot
                else:
                    query_limit = self.config.max_followup_queries_per_slot
                queue = [(need, slot, channel, query)
                         for query in queries[:query_limit]
                         for channel in self.config.channels]
                queues.append(queue)

        # Round-robin across slots. A tight global budget must not let the
        # first alternative consume all retrieval calls before its comparator
        # receives even one search.
        max_queue_depth = max((len(queue) for queue in queues), default=0)
        for depth in range(max_queue_depth):
            for queue in queues:
                if depth >= len(queue):
                    continue
                need, slot, channel, query = queue[depth]
                if query_count >= limit:
                    budget_slots.add(slot.slot_id)
                    partial_slots.add(slot.slot_id)
                    continue
                query_count += 1
                batch = self.retriever.search(
                    query, channel=channel, sources=searchable,
                    limit=self.config.max_candidates_per_slot,
                )
                for hit in batch:
                    source = source_map.get(hit.source_id)
                    rep_key = (hit.source_id, hit.representation_id)
                    if source is None or rep_key not in representation_map:
                        continue
                    key = (need.need_id, slot.slot_id, source.source_id,
                           source.source_version, hit.representation_id,
                           hit.start_offset, hit.end_offset)
                    if key not in used_candidates:
                        used_candidates[key] = (slot.slot_id, len(slot_hits[slot.slot_id]))
                        slot_hits[slot.slot_id].append((hit, query))
                    else:
                        prior_slot, prior_index = used_candidates[key]
                        prior_hit, _prior_query = slot_hits[prior_slot][prior_index]
                        if hit.score > prior_hit.score:
                            slot_hits[prior_slot][prior_index] = (hit, query)
                traces.append(SearchTrace(
                    need.need_id, slot.slot_id,
                    a.manifest.corpus_snapshot_id,
                    a.manifest.material_catalog_version,
                    a.manifest.representation_version,
                    channel, query,
                    tuple(s.source_id for s in searchable),
                    tuple(h.source_id for h in batch),
                    "candidate_cap_reached" if len(batch) >= self.config.max_candidates_per_slot
                    else "channel_complete",
                    self.retriever.version, pass_number, query_origin,
                    len(batch), getattr(self.retriever, "backend_count", 1),
                    getattr(self.retriever, "backend_versions", (self.retriever.version,)),
                    getattr(self.retriever, "reranker_version", ""),
                ))
                if len(batch) >= self.config.max_candidates_per_slot:
                    partial_slots.add(slot.slot_id)
        return query_count, traces, partial_slots, budget_slots

    def _make_slot_results(self, a, slot_hits, source_map, representation_map,
                           partial_slots, budget_slots, readiness_limited,
                           searchable, sources):
        results = []
        for need in a.needs:
            for slot in need.slots:
                links = self._candidate_links(
                    a, need.need_id, slot, slot_hits[slot.slot_id],
                    source_map, representation_map,
                )
                topic_terms = _topic_terms(slot)
                qualifying = any(
                    not link.mismatched_facets
                    and (not topic_terms or link.matched_topic_terms)
                    for link in links
                )
                if links and qualifying:
                    coverage = Coverage.CANDIDATE_FOUND
                elif links:
                    coverage = Coverage.PARTIAL
                elif slot.slot_id in budget_slots:
                    coverage = Coverage.BUDGET_EXHAUSTED
                elif not searchable and sources:
                    coverage = Coverage.NOT_SEARCHABLE
                elif slot.slot_id in partial_slots or readiness_limited:
                    coverage = Coverage.PARTIAL
                else:
                    coverage = Coverage.NO_MATCH_IN_SCOPE
                if links and not qualifying:
                    missing = sorted({facet for link in links for facet in link.mismatched_facets})
                    entity_links = [link for link in links if not link.mismatched_facets]
                    topic_links = [link for link in links if link.matched_topic_terms]
                    if topic_terms and topic_links and entity_links:
                        reason = "no single candidate passage contains both the assigned entity/constraints and a slot-topic term"
                    elif missing:
                        reason = "candidate passage found, but assigned entity/constraint facets are absent: " + ", ".join(missing)
                    else:
                        reason = "candidate passage found, but no slot-topic term appears in the candidate passage"
                else:
                    reason = "" if links else ("search budget or source readiness limited coverage"
                                               if coverage in {Coverage.PARTIAL, Coverage.BUDGET_EXHAUSTED}
                                               else "no matching passage in searchable assigned scope")
                results.append(SlotResult(need.need_id, slot.slot_id, coverage, links, reason))
        return results

    @staticmethod
    def _refinement_feedback(results, initial_queries, traces):
        feedback = []
        for result in results:
            feedback.append({
                "slot_id": result.slot_id,
                "coverage": result.coverage.value,
                "retrieval_coverage_only": True,
                "first_pass_queries": tuple(initial_queries.get(result.slot_id, ())),
                "returned_candidates": tuple({
                    "candidate_link_id": link.candidate_link_id,
                    "source_id": link.source_id,
                    "source_version": link.source_version,
                    "representation_id": link.representation_id,
                    "start_offset": link.start_offset,
                    "end_offset": link.end_offset,
                    "exact_text": link.exact_text[:1500],
                    "source_kind": link.source_kind,
                    "modality": link.modality,
                    "matched_facets": link.matched_facets,
                    "missing_facets": link.mismatched_facets,
                    "matched_topic_terms": link.matched_topic_terms,
                    "missing_topic_terms": link.missing_topic_terms,
                } for link in result.candidate_links),
                "searched_source_ids": tuple(dict.fromkeys(
                    source_id for trace in traces if trace.slot_id == result.slot_id
                    for source_id in trace.source_ids_searched)),
            })
        return tuple(feedback)

    def _candidate_links(self, a, need_id, slot, hits, sources, representations):
        links = []
        # Rank before capping: hits arrive in query order, and a later query can
        # find a better passage than the first query's weakest one.
        ranked = sorted(enumerate(hits), key=lambda item: (-item[1][0].score, item[0]))
        for _index, (hit, _query) in ranked[:self.config.max_links_for_grading]:
            source = sources[hit.source_id]
            representation = representations.get((hit.source_id, hit.representation_id))
            if representation is None:
                continue
            if hit.start_offset is None and hit.end_offset is None:
                has_visual_locator = bool(
                    representation.content_ref
                    or representation.structural_context.get("page") is not None
                    or representation.structural_context.get("bounding_box") is not None
                    or representation.structural_context.get("region_id")
                )
                if representation.modality not in {"image", "figure", "chart", "visual", "figure_ocr"} or not has_visual_locator:
                    continue
                exact = ""
            else:
                try:
                    exact = verify_source_span(source, hit.start_offset, hit.end_offset, hit.excerpt,
                                              representation_text=representation.text)
                except EvidenceValidationError:
                    continue
            # Constraint match is local to the returned passage. A mention of
            # the requested entity elsewhere in a long document must not make
            # an unrelated passage look incident-specific.
            matched = tuple(x for x in (*slot.entity_ids, *slot.exact_constraints)
                            if _contains_literal_facet(exact, x))
            mismatched = tuple(x for x in (*slot.entity_ids, *slot.exact_constraints) if x not in matched)
            topic_terms = _topic_terms(slot)
            passage_terms = {_normalize_topic_token(x) for x in re.findall(r"[a-z0-9]+", exact.casefold())}
            matched_topic = tuple(x for x in topic_terms if x in passage_terms)
            missing_topic = tuple(x for x in topic_terms if x not in passage_terms)
            seed = (a.assignment_id, need_id, slot.slot_id, source.source_id,
                    source.source_version, source.representation_id, hit.start_offset, hit.end_offset)
            links.append(CandidateLink(
                candidate_link_id="cl:" + fingerprint(seed)[:20], need_id=need_id,
                slot_id=slot.slot_id, source_id=source.source_id,
                source_version=source.source_version, representation_id=hit.representation_id,
                start_offset=hit.start_offset, end_offset=hit.end_offset, exact_text=exact,
                title=source.title, source_kind=source.source_kind, channel=hit.channel,
                score=hit.score, matched_facets=matched, mismatched_facets=mismatched,
                matched_topic_terms=matched_topic, missing_topic_terms=missing_topic,
                structural_context={**source.metadata, **representation.structural_context,
                                    **(hit.structural_context or {})},
                lineage=source.lineage,
                ocr_confidence=source.metadata.get("ocr_confidence"),
                modality=hit.modality or representation.modality,
                retrieval_channels=hit.channels or (hit.channel,),
                score_semantics=hit.score_semantics,
            ))
        # Query order is a planner artifact, not a relevance ranking. Put
        # passages that satisfy the assigned constraints and slot topic first;
        # use the backend score only as a tie-breaker (scores across channels
        # and queries are not necessarily calibrated against one another).
        links.sort(key=lambda link: (
            not bool(link.matched_topic_terms),
            bool(link.mismatched_facets),
            -len(link.matched_facets),
            -len(link.matched_topic_terms),
            -link.score,
            link.source_id,
            link.representation_id,
            link.start_offset if link.start_offset is not None else -1,
        ))
        return tuple(links)

    @staticmethod
    def _result(a, status, phase, pass_status, diagnostics):
        return EvidenceWorkerResult(
            schema_version="1", assignment_id=a.assignment_id,
            work_item_id=a.work_item_id, event_id=a.event_id,
            case_snapshot_id=a.case_snapshot_id, board_version=a.board_version,
            corpus_snapshot_id=a.manifest.corpus_snapshot_id,
            material_catalog_version=a.manifest.material_catalog_version,
            representation_version=a.manifest.representation_version,
            status=status, work_phase=phase, search_pass_status=pass_status,
            diagnostics=tuple(diagnostics),
        )
