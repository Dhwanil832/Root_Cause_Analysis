from dataclasses import replace

import unittest

from sahs.contracts import (
    CandidateLineage,
    CandidateOperation,
    CandidateStatus,
    FrontierAction,
    FrontierHistory,
    InformationNeedHistory,
    InformationNeedStatus,
    SpecialistHistory,
)
from sahs.delta import (
    CandidateProposal,
    apply_candidate_delta,
    build_candidate_delta,
    compute_affected_candidates,
    fingerprint_candidate_graph,
    missing_affected_dispositions,
    select_focal_candidates,
    transition_candidate,
)
from sahs.history import (
    AssignmentFingerprintInput,
    InMemoryRunHistoryStore,
    NoOpDecision,
    RunRecord,
    compute_input_fingerprint,
    detect_no_op,
    validate_history_compatibility,
)
from sahs.state_controller import (
    PreparationStatus,
    prepare_run,
    record_run_result,
)
from sahs.workflow import (
    decide_frontier_action,
    merge_information_needs,
    record_frontier_attempt,
    transition_information_need,
)


def history(*candidates: CandidateLineage) -> SpecialistHistory:
    return SpecialistHistory(
        schema_version="1",
        specialist_scope_id="mechanical",
        history_version="h3",
        case_snapshot_id="case-s2",
        board_version="b7",
        candidates=tuple(candidates),
    )


def sample_fingerprint_input(**updates):
    base = AssignmentFingerprintInput(
        case_id="case-1",
        specialist_scope_id="mechanical",
        case_snapshot_id="case-s2",
        board_version="b7",
        history_version="h3",
        mode="revision",
        focal_proposition_id="event-1",
        operation_goal="develop_mechanism",
        lead_direction={"focus": "upstream", "limits": [2, 3]},
        initial_case_packet=None,
        relevant_graph={"nodes": ["a", "b"], "edges": {"x", "y"}},
        source_bundle=[{"id": "manual-v2", "text": "valve can leak"}],
        relevant_history={"candidates": ["c1"], "open_frontiers": []},
        lead_feedback=[],
        assessor_annotations=[],
        changed_ids=["p1"],
        budgets={"depth": 3, "calls": 1},
        available_proposition_ids=("event-1", "p1", "p9", "pressure"),
    )
    return replace(base, **updates)


class TestSAHSState(unittest.TestCase):
    def test_fingerprint_is_stable_to_mapping_and_set_order(self):
        first = sample_fingerprint_input()
        second = replace(
            first,
            lead_direction={"limits": [2, 3], "focus": "upstream"},
            relevant_graph={"edges": {"y", "x"}, "nodes": ["a", "b"]},
            budgets={"calls": 1, "depth": 3},
        )
        assert compute_input_fingerprint(first) == compute_input_fingerprint(second)


    def test_fingerprint_changes_when_case_or_board_snapshot_changes(self):
        original = compute_input_fingerprint(sample_fingerprint_input())
        new_board = compute_input_fingerprint(
            sample_fingerprint_input(board_version="b8")
        )
        new_case = compute_input_fingerprint(
            sample_fingerprint_input(case_snapshot_id="case-s3")
        )
        assert original != new_board
        assert original != new_case

    def test_history_sequence_bump_alone_does_not_change_semantic_fingerprint(self):
        original = compute_input_fingerprint(sample_fingerprint_input())
        advanced_sequence = compute_input_fingerprint(
            sample_fingerprint_input(history_version="h4")
        )
        changed_history_content = compute_input_fingerprint(
            sample_fingerprint_input(
                history_version="h4",
                relevant_history={"candidates": ["c1", "c2"], "open_frontiers": []},
            )
        )
        assert original == advanced_sequence
        assert original != changed_history_content


    def test_exact_completed_assignment_returns_no_op(self):
        store = InMemoryRunHistoryStore()
        fingerprint = compute_input_fingerprint(sample_fingerprint_input())
        store.record_completed(
            RunRecord("a-1", fingerprint, "result-1", "completed", reusable=True)
        )
        result = detect_no_op(
            assignment_id="a-1", input_fingerprint=fingerprint, store=store
        )
        assert result.decision == NoOpDecision.NO_OP
        assert result.prior_result_reference == "result-1"


    def test_semantically_identical_assignment_can_reuse_prior_result(self):
        store = InMemoryRunHistoryStore()
        fingerprint = compute_input_fingerprint(sample_fingerprint_input())
        store.record_completed(
            RunRecord("a-1", fingerprint, "result-1", "completed", reusable=True)
        )
        result = detect_no_op(
            assignment_id="a-retry-with-new-id",
            input_fingerprint=fingerprint,
            store=store,
        )
        assert result.decision == NoOpDecision.NO_OP
        assert result.prior_result_reference == "result-1"


    def test_reused_assignment_id_with_changed_input_fails_closed(self):
        store = InMemoryRunHistoryStore()
        original = compute_input_fingerprint(sample_fingerprint_input())
        changed = compute_input_fingerprint(sample_fingerprint_input(board_version="b8"))
        store.record_completed(RunRecord("a-1", original, "result-1", "completed"))
        result = detect_no_op(assignment_id="a-1", input_fingerprint=changed, store=store)
        assert result.decision == NoOpDecision.ASSIGNMENT_ID_CONFLICT


    def test_non_reusable_record_does_not_suppress_retry(self):
        store = InMemoryRunHistoryStore()
        fingerprint = compute_input_fingerprint(sample_fingerprint_input())
        store.record_completed(
            RunRecord("a-1", fingerprint, "partial-1", "generation_failed", reusable=False)
        )
        result = detect_no_op(
            assignment_id="a-1", input_fingerprint=fingerprint, store=store
        )
        assert result.decision == NoOpDecision.RUN


    def test_history_version_mismatch_is_reported(self):
        current = history()
        assert validate_history_compatibility(
            current,
            specialist_scope_id="mechanical",
            case_snapshot_id="case-s2",
            board_version="b7",
            history_version="h4",
        ) == ("history_version: history has 'h3', assignment has 'h4'",)


    def test_affected_candidates_include_dependencies_and_lineage_descendants(self):
        prior = CandidateLineage(
            "c1", dependent_proposition_ids=frozenset({"p1"}),
            content_fingerprint="f1",
        )
        child = CandidateLineage(
            "c2", parent_candidate_ids=("c1",),
            dependent_rule_ids=frozenset({"r2"}), content_fingerprint="f2",
        )
        unrelated = CandidateLineage(
            "c3", dependent_proposition_ids=frozenset({"p9"}),
            content_fingerprint="f3",
        )
        affected = compute_affected_candidates(history(prior, child, unrelated), {"p1"})
        assert affected == ("c1", "c2")


    def test_annotation_source_and_information_need_ids_affect_branch(self):
        candidate = CandidateLineage(
            "c1",
            dependent_annotation_ids=frozenset({"ann-1"}),
            dependent_source_ids=frozenset({"manual-v2"}),
            dependent_information_need_ids=frozenset({"need-3"}),
            content_fingerprint="f1",
        )
        current = history(candidate)
        assert compute_affected_candidates(current, {"ann-1"}) == ("c1",)
        assert compute_affected_candidates(current, {"manual-v2"}) == ("c1",)
        assert compute_affected_candidates(current, {"need-3"}) == ("c1",)


    def test_advance_focal_selection_is_separate_from_changed_branches(self):
        c1 = CandidateLineage("c1", dependent_proposition_ids=frozenset({"pressure"}))
        child = CandidateLineage(
            "c2", parent_candidate_ids=("c1",),
            dependent_proposition_ids=frozenset({"beam-fall"}),
        )
        current = history(c1, child)
        assert select_focal_candidates(current, "pressure") == ("c1", "c2")
        assert compute_affected_candidates(current, set()) == ()

    def test_focal_selection_skips_superseded_and_requires_explicit_parked_reopen(self):
        superseded = CandidateLineage(
            "old", dependent_proposition_ids=frozenset({"pressure"}),
            status=CandidateStatus.SUPERSEDED,
        )
        active = CandidateLineage(
            "merged", parent_candidate_ids=("old",),
            dependent_proposition_ids=frozenset({"pressure"}),
        )
        parked = CandidateLineage(
            "parked", dependent_proposition_ids=frozenset({"pressure"}),
            status=CandidateStatus.PARKED,
        )
        current = history(superseded, active, parked)
        self.assertEqual(select_focal_candidates(current, "pressure"), ("merged",))
        self.assertEqual(
            select_focal_candidates(current, "pressure", {"parked"}),
            ("merged", "parked"),
        )
        self.assertEqual(
            select_focal_candidates(current, "pressure", {"old"}),
            ("merged", "old"),
        )
        self.assertEqual(compute_affected_candidates(current, set(), {"old"}), ("merged", "old"))

    def test_changed_dependency_does_not_require_disposition_of_superseded_history(self):
        superseded = CandidateLineage(
            "old", dependent_proposition_ids=frozenset({"source-v1"}),
            status=CandidateStatus.SUPERSEDED,
        )
        active_child = CandidateLineage("new", parent_candidate_ids=("old",))
        current = history(superseded, active_child)
        self.assertEqual(compute_affected_candidates(current, {"source-v1"}), ("new",))


    def test_candidate_graph_fingerprint_is_python_computed_and_order_stable(self):
        first = fingerprint_candidate_graph(
            propositions={"p1": "pressure loss"},
            rules={"r1": {"antecedent": "leak", "consequent": "p1"}},
            assumptions={"leak"},
            source_refs={"manual-v1"},
        )
        second = fingerprint_candidate_graph(
            propositions={"p1": "pressure loss"},
            rules={"r1": {"consequent": "p1", "antecedent": "leak"}},
            assumptions={"leak"},
            source_refs={"manual-v1"},
        )
        assert first == second


    def test_affected_candidate_must_receive_an_explicit_disposition(self):
        current = history(CandidateLineage("c1", content_fingerprint="f1"))
        assert missing_affected_dispositions({"c1"}, ()) == ("c1",)
        unchanged = build_candidate_delta(
            assignment_id="a-disposition",
            history=current,
            proposals=[CandidateProposal("f1", revises_candidate_id="c1")],
        )
        assert missing_affected_dispositions({"c1"}, unchanged) == ()


    def test_explicit_target_is_affected_even_without_dependency_intersection(self):
        c1 = CandidateLineage("c1", dependent_proposition_ids=frozenset({"p1"}))
        assert compute_affected_candidates(history(c1), set(), {"c1"}) == ("c1",)


    def test_candidate_create_and_exact_duplicate_collapse(self):
        empty = history()
        proposals = [
            CandidateProposal("graph-hash", dependent_proposition_ids=frozenset({"p1"})),
            CandidateProposal("graph-hash", dependent_proposition_ids=frozenset({"p1"})),
        ]
        delta = build_candidate_delta(
            assignment_id="a-1", history=empty, proposals=proposals
        )
        assert len(delta) == 1
        assert delta[0].operation == CandidateOperation.CREATE
        assert delta[0].candidate.candidate_id.startswith("sahs-")


    def test_unchanged_candidate_is_referenced_not_recreated(self):
        prior = CandidateLineage("c1", content_fingerprint="same")
        delta = build_candidate_delta(
            assignment_id="a-1",
            history=history(prior),
            proposals=[CandidateProposal("same")],
        )
        assert len(delta) == 1
        assert delta[0].operation == CandidateOperation.UNCHANGED
        assert delta[0].candidate.candidate_id == "c1"


    def test_revision_creates_lineage_and_supersedes_old_revision(self):
        prior = CandidateLineage(
            "c1", revision=2, content_fingerprint="old",
            dependent_proposition_ids=frozenset({"p1"}),
        )
        delta = build_candidate_delta(
            assignment_id="a-2",
            history=history(prior),
            proposals=[
                CandidateProposal(
                    "new", dependent_proposition_ids=frozenset({"p1", "p2"}),
                    revises_candidate_id="c1",
                )
            ],
            invalidated_by_ids={"p2"},
        )
        assert delta[0].operation == CandidateOperation.REVISE
        assert delta[0].candidate.revision == 3
        assert delta[0].candidate.parent_candidate_ids == ("c1",)
        updated = apply_candidate_delta(history(prior), delta, new_history_version="h4")
        assert updated.candidate_map()["c1"].status == CandidateStatus.SUPERSEDED
        assert updated.candidate_map()[delta[0].candidate.candidate_id].status == CandidateStatus.ACTIVE
        assert updated.history_version == "h4"


    def test_reopen_only_accepts_inactive_candidate(self):
        parked = CandidateLineage(
            "c1", revision=1, content_fingerprint="old", status=CandidateStatus.PARKED
        )
        delta = build_candidate_delta(
            assignment_id="a-3",
            history=history(parked),
            proposals=[CandidateProposal("new", reopens_candidate_id="c1")],
        )
        assert delta[0].operation == CandidateOperation.REOPEN
        assert delta[0].candidate.parent_candidate_ids == ("c1",)
        active = CandidateLineage("active", content_fingerprint="old")
        with self.assertRaisesRegex(ValueError, "only an inactive"):
            build_candidate_delta(
                assignment_id="a-3",
                history=history(active),
                proposals=[CandidateProposal("new", reopens_candidate_id="active")],
            )

    def test_reopen_with_unchanged_content_reactivates_existing_candidate(self):
        parked = CandidateLineage(
            "parked", content_fingerprint="same", status=CandidateStatus.PARKED,
        )
        current = history(parked)
        delta = build_candidate_delta(
            assignment_id="a-reopen-same",
            history=current,
            proposals=[CandidateProposal("same", reopens_candidate_id="parked")],
        )
        self.assertEqual(delta[0].operation, CandidateOperation.REOPEN)
        self.assertEqual(delta[0].candidate.candidate_id, "parked")
        updated = apply_candidate_delta(current, delta, new_history_version="h4")
        self.assertEqual(updated.candidate_map()["parked"].status, CandidateStatus.ACTIVE)

    def test_reopen_refreshes_dependencies_used_for_future_invalidation(self):
        parked = CandidateLineage(
            "parked", content_fingerprint="same", status=CandidateStatus.PARKED,
            dependent_annotation_ids=frozenset({"ann-old"}),
        )
        current = history(parked)
        delta = build_candidate_delta(
            assignment_id="a-reopen-refresh",
            history=current,
            proposals=[CandidateProposal(
                "same", reopens_candidate_id="parked",
                dependent_annotation_ids=frozenset({"ann-new"}),
                dependent_information_need_ids=frozenset({"need-new"}),
            )],
        )
        updated = apply_candidate_delta(current, delta, new_history_version="h4")
        reopened = updated.candidate_map()["parked"]
        self.assertEqual(reopened.dependent_annotation_ids, frozenset({"ann-new"}))
        self.assertEqual(reopened.dependent_information_need_ids, frozenset({"need-new"}))
        self.assertEqual(compute_affected_candidates(updated, {"ann-new"}), ("parked",))

    def test_revision_converging_on_active_candidate_merges_lineage(self):
        old = CandidateLineage("old", content_fingerprint="old-fp")
        existing = CandidateLineage(
            "existing", content_fingerprint="new-fp",
            dependent_proposition_ids=frozenset({"p-existing"}),
        )
        current = history(old, existing)
        delta = build_candidate_delta(
            assignment_id="a-converge",
            history=current,
            proposals=[CandidateProposal(
                "new-fp", revises_candidate_id="old",
                dependent_proposition_ids=frozenset({"p-revision"}),
            )],
        )
        self.assertEqual(len(delta), 1)
        self.assertEqual(delta[0].operation, CandidateOperation.MERGE)
        self.assertEqual(delta[0].candidate.candidate_id, "existing")
        self.assertEqual(missing_affected_dispositions({"old"}, delta), ())
        updated = apply_candidate_delta(current, delta, new_history_version="h4")
        self.assertEqual(updated.candidate_map()["old"].status, CandidateStatus.SUPERSEDED)
        merged = updated.candidate_map()["existing"]
        self.assertEqual(merged.status, CandidateStatus.ACTIVE)
        self.assertIn("old", merged.parent_candidate_ids)
        self.assertEqual(merged.dependent_proposition_ids, frozenset({"p-existing", "p-revision"}))

    def test_candidate_ids_do_not_depend_on_proposal_order(self):
        current = history()
        proposals = [CandidateProposal("left"), CandidateProposal("right")]
        first = build_candidate_delta(
            assignment_id="a-order", history=current, proposals=proposals
        )
        reversed_order = build_candidate_delta(
            assignment_id="a-order", history=current, proposals=list(reversed(proposals))
        )
        by_content_first = {item.candidate.content_fingerprint: item.candidate.candidate_id for item in first}
        by_content_second = {item.candidate.content_fingerprint: item.candidate.candidate_id for item in reversed_order}
        self.assertEqual(by_content_first, by_content_second)


    def test_invalid_parent_and_empty_fingerprint_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown parent"):
            build_candidate_delta(
                assignment_id="a-4",
                history=history(),
                proposals=[CandidateProposal("x", parent_candidate_ids=("missing",))],
            )
        with self.assertRaisesRegex(ValueError, "content fingerprint"):
            build_candidate_delta(
                assignment_id="a-4", history=history(), proposals=[CandidateProposal("")]
            )

    def test_park_transition_is_local_and_does_not_change_evidence_state(self):
        active = CandidateLineage("c1", content_fingerprint="f1")
        current = history(active)
        delta = transition_candidate(
            current,
            "c1",
            CandidateOperation.PARK,
            reason_code="no_useful_expansion_within_budget",
            invalidated_by_ids={"p2"},
        )
        updated = apply_candidate_delta(current, [delta], new_history_version="h4")
        self.assertEqual(updated.candidate_map()["c1"].status, CandidateStatus.PARKED)
        self.assertEqual(delta.invalidated_by_ids, ("p2",))
        with self.assertRaisesRegex(ValueError, "park or supersede"):
            transition_candidate(current, "c1", CandidateOperation.REVISE, reason_code="bad")


    def test_frontier_waits_on_pending_need_and_reopens_when_dependency_changes(self):
        frontier = FrontierHistory(
            frontier_id="f1",
            target_proposition_id="pressure",
            expanded_before=True,
            dependency_ids=frozenset({"valve-state"}),
            linked_need_ids=("need-1",),
            last_direction_fingerprint="dir-a",
        )
        self.assertEqual(
            decide_frontier_action(
                frontier,
                direction_fingerprint="dir-a",
                pending_information_need_ids={"need-1"},
                expansion_budget_remaining=1,
                lead_authorized=True,
            ),
            FrontierAction.WAIT,
        )
        self.assertEqual(
            decide_frontier_action(
                frontier,
                direction_fingerprint="dir-a",
                changed_ids={"valve-state"},
                expansion_budget_remaining=1,
                lead_authorized=True,
            ),
            FrontierAction.REOPEN_AND_EXPAND,
        )
        self.assertEqual(
            decide_frontier_action(
                frontier,
                direction_fingerprint="dir-b",
                expansion_budget_remaining=0,
                lead_authorized=True,
            ),
            FrontierAction.DEFER,
        )

    def test_changed_frontier_dependency_precedes_unanswered_linked_need(self):
        frontier = FrontierHistory(
            frontier_id="f1", target_proposition_id="pressure",
            expanded_before=True, dependency_ids=frozenset({"valve-state"}),
            linked_need_ids=("need-1",), last_direction_fingerprint="dir-a",
        )
        self.assertEqual(
            decide_frontier_action(
                frontier,
                direction_fingerprint="dir-a",
                changed_ids={"valve-state"},
                pending_information_need_ids={"need-1"},
                expansion_budget_remaining=1,
                lead_authorized=True,
            ),
            FrontierAction.REOPEN_AND_EXPAND,
        )

    def test_frontier_direction_identity_includes_operation_goal(self):
        direction_fingerprint = compute_input_fingerprint({
            "mode": "advance",
            "focal_proposition_id": "pressure",
            "operation_goal": "develop_mechanism",
            "lead_direction": {"focus": "upstream"},
        })
        current = SpecialistHistory(
            schema_version="1", specialist_scope_id="mechanical",
            history_version="h3", case_snapshot_id="case-s2", board_version="b7",
            frontiers=(FrontierHistory(
                "f-pressure", "pressure", expanded_before=True,
                last_direction_fingerprint=direction_fingerprint,
            ),),
        )
        prepared = prepare_run(
            assignment_id="a-new-goal",
            fingerprint_input=sample_fingerprint_input(
                mode="advance", focal_proposition_id="pressure",
                operation_goal="generate_alternatives",
                lead_direction={"focus": "upstream"},
                budgets={"max_targeted_expansion_calls": 1},
            ),
            history=current,
            store=InMemoryRunHistoryStore(),
        )
        self.assertEqual(prepared.status, PreparationStatus.READY)
        self.assertEqual(prepared.frontier_action, FrontierAction.EXPAND)


    def test_frontier_attempt_updates_history_and_expansion_budget(self):
        current = history()
        updated = record_frontier_attempt(
            current,
            frontier_id="f-pressure",
            target_proposition_id="pressure",
            candidate_ids={"c1"},
            direction_fingerprint="dir-a",
            assignment_id="advance-1",
            outcome="expanded",
            dependency_ids={"p-pressure", "r-valve"},
            linked_need_ids={"need-1"},
            expansion_calls_used=1,
            new_history_version="h4",
        )
        self.assertEqual(updated.prior_expansion_budget_usage, 1)
        self.assertTrue(updated.frontiers[0].expanded_before)
        self.assertEqual(updated.frontiers[0].last_attempt_id, "advance-1")

    def test_successful_expansion_with_zero_extra_calls_is_not_repeated(self):
        current = history()
        updated = record_frontier_attempt(
            current,
            frontier_id="f-pressure",
            target_proposition_id="pressure",
            candidate_ids=(),
            direction_fingerprint="dir-a",
            assignment_id="advance-1",
            outcome="expanded",
            expansion_calls_used=0,
            new_history_version="h4",
        )
        frontier = updated.frontiers[0]
        self.assertTrue(frontier.expanded_before)
        self.assertEqual(
            decide_frontier_action(
                frontier,
                direction_fingerprint="dir-a",
                expansion_budget_remaining=1,
                lead_authorized=True,
            ),
            FrontierAction.WAIT,
        )

    def test_completed_no_candidate_search_is_not_repeated_without_new_information(self):
        current = record_frontier_attempt(
            history(), frontier_id="f-pressure", target_proposition_id="pressure",
            candidate_ids=(), direction_fingerprint="dir-a", assignment_id="advance-1",
            outcome="no_candidate_under_supplied_rules", expansion_calls_used=1,
            new_history_version="h4",
        )
        self.assertTrue(current.frontiers[0].expanded_before)
        self.assertEqual(
            decide_frontier_action(
                current.frontiers[0], direction_fingerprint="dir-a",
                expansion_budget_remaining=1, lead_authorized=True,
            ),
            FrontierAction.WAIT,
        )

    def test_recording_reopened_frontier_preserves_pending_need_links(self):
        current = SpecialistHistory(
            schema_version="1", specialist_scope_id="mechanical",
            history_version="h3", case_snapshot_id="case-s2", board_version="b7",
            frontiers=(FrontierHistory(
                "f-pressure", "pressure", linked_need_ids=("need-pending",),
            ),),
        )
        updated = record_frontier_attempt(
            current, frontier_id="f-pressure", target_proposition_id="pressure",
            candidate_ids=(), direction_fingerprint="dir-b", assignment_id="advance-2",
            outcome="reopen_and_expand", expansion_calls_used=1,
            new_history_version="h4",
        )
        self.assertEqual(updated.frontiers[0].linked_need_ids, ("need-pending",))

    def test_frontier_remembers_directions_across_a_b_a(self):
        current = history()
        for index, direction in enumerate(("dir-a", "dir-b"), start=1):
            current = record_frontier_attempt(
                current,
                frontier_id="f-pressure",
                target_proposition_id="pressure",
                candidate_ids=(),
                direction_fingerprint=direction,
                assignment_id=f"advance-{index}",
                outcome="expanded",
                expansion_calls_used=1,
                new_history_version=f"h{index + 3}",
            )
        self.assertEqual(
            decide_frontier_action(
                current.frontiers[0],
                direction_fingerprint="dir-a",
                expansion_budget_remaining=1,
                lead_authorized=True,
            ),
            FrontierAction.WAIT,
        )


    def test_information_needs_merge_deduplicate_and_transition(self):
        current = history()
        first_need = InformationNeedHistory(
            "need-1", linked_candidate_ids=("c1",), target_unknown_id="u1",
            workflow_status=InformationNeedStatus.PENDING.value,
            meaning_fingerprint="meaning-valve-leak",
        )
        current = merge_information_needs(
            current, [first_need], new_history_version="h4"
        )
        duplicate = InformationNeedHistory(
            "need-2", linked_candidate_ids=("c2",), linked_frontier_ids=("f1",),
            target_unknown_id="u1", meaning_fingerprint="meaning-valve-leak",
        )
        current = merge_information_needs(
            current, [duplicate], new_history_version="h5"
        )
        self.assertEqual(len(current.information_needs), 1)
        self.assertEqual(current.information_needs[0].linked_candidate_ids, ("c1", "c2"))
        self.assertEqual(current.information_needs[0].linked_frontier_ids, ("f1",))
        current = transition_information_need(
            current,
            need_id="need-1",
            new_status=InformationNeedStatus.ANSWERED,
            new_history_version="h6",
            material_or_request_ids={"doc-9"},
        )
        self.assertEqual(current.information_needs[0].workflow_status, "answered")
        self.assertEqual(current.information_needs[0].material_or_request_ids, ("doc-9",))
        with self.assertRaisesRegex(ValueError, "invalid information-need transition"):
            transition_information_need(
                current,
                need_id="need-1",
                new_status=InformationNeedStatus.PENDING,
                new_history_version="h7",
            )


    def test_input_fingerprint_rejects_nan_and_unsupported_objects(self):
        with self.assertRaisesRegex(ValueError, "NaN"):
            compute_input_fingerprint({"x": float("nan")})
        with self.assertRaisesRegex(TypeError, "unsupported"):
            compute_input_fingerprint({"x": object()})

    def test_prepare_run_fails_stale_history_before_downstream_work(self):
        current = history()
        payload = sample_fingerprint_input(board_version="b8")
        prepared = prepare_run(
            assignment_id="a-stale",
            fingerprint_input=payload,
            history=current,
            store=InMemoryRunHistoryStore(),
            changed_ids={"p1"},
        )
        self.assertEqual(prepared.status, PreparationStatus.STALE_INPUT)
        self.assertEqual(prepared.affected_candidate_ids, ())

    def test_prepare_run_rejects_unknown_revision_target_and_negative_budget(self):
        current = history()
        bad_revision = prepare_run(
            assignment_id="a-bad-target",
            fingerprint_input=sample_fingerprint_input(
                focal_proposition_id=None,
                explicitly_targeted_candidate_ids=("misspelled-candidate",),
            ),
            history=current,
            store=InMemoryRunHistoryStore(),
        )
        self.assertEqual(bad_revision.status, PreparationStatus.INVALID_INPUT)
        self.assertIn("unknown targeted candidate", bad_revision.diagnostics[0])

        bad_budget = prepare_run(
            assignment_id="a-negative-budget",
            fingerprint_input=sample_fingerprint_input(
                mode="advance",
                focal_proposition_id="pressure",
                budgets={"max_targeted_expansion_calls": -1},
            ),
            history=current,
            store=InMemoryRunHistoryStore(),
        )
        self.assertEqual(bad_budget.status, PreparationStatus.INVALID_INPUT)

    def test_prepare_run_returns_affected_branches_and_records_result(self):
        c1 = CandidateLineage(
            "c1", dependent_proposition_ids=frozenset({"p1"}),
            content_fingerprint="f1",
        )
        current = history(c1)
        payload = sample_fingerprint_input()
        store = InMemoryRunHistoryStore()
        prepared = prepare_run(
            assignment_id="a-ready",
            fingerprint_input=payload,
            history=current,
            store=store,
            changed_ids={"p1"},
        )
        self.assertEqual(prepared.status, PreparationStatus.READY)
        self.assertEqual(prepared.affected_candidate_ids, ("c1",))
        unchanged_delta = build_candidate_delta(
            assignment_id="a-ready",
            history=current,
            proposals=[CandidateProposal("f1", revises_candidate_id="c1")],
        )
        record_run_result(
            assignment_id="a-ready",
            preparation=prepared,
            result_reference="result-ready",
            run_status="completed",
            store=store,
            reusable=True,
            candidate_deltas=unchanged_delta,
        )
        repeated = prepare_run(
            assignment_id="a-ready",
            fingerprint_input=payload,
            history=current,
            store=store,
        )
        self.assertEqual(repeated.status, PreparationStatus.NO_OP)
        self.assertEqual(repeated.prior_result_reference, "result-ready")

    def test_history_sequence_only_bump_does_not_force_recomputation(self):
        store = InMemoryRunHistoryStore()
        initial_payload = sample_fingerprint_input()
        initial_history = history()
        first = prepare_run(
            assignment_id="a-history-sequence",
            fingerprint_input=initial_payload,
            history=initial_history,
            store=store,
        )
        record_run_result(
            assignment_id="a-history-sequence",
            preparation=first,
            result_reference="result-history-sequence",
            run_status="completed",
            store=store,
            reusable=True,
        )
        updated_payload = sample_fingerprint_input(history_version="h4")
        updated_history = replace(initial_history, history_version="h4")
        second = prepare_run(
            assignment_id="a-history-sequence-retry",
            fingerprint_input=updated_payload,
            history=updated_history,
            store=store,
        )
        self.assertEqual(second.status, PreparationStatus.NO_OP)
        self.assertEqual(second.prior_result_reference, "result-history-sequence")

    def test_prepare_run_does_not_cache_nonreusable_result(self):
        current = history()
        payload = sample_fingerprint_input()
        store = InMemoryRunHistoryStore()
        prepared = prepare_run(
            assignment_id="a-retryable",
            fingerprint_input=payload,
            history=current,
            store=store,
        )
        record_run_result(
            assignment_id="a-retryable",
            preparation=prepared,
            result_reference="failure",
            run_status="generation_failed",
            store=store,
            reusable=False,
        )
        retry = prepare_run(
            assignment_id="a-retryable",
            fingerprint_input=payload,
            history=current,
            store=store,
        )
        self.assertEqual(retry.status, PreparationStatus.READY)

if __name__ == "__main__":
    unittest.main()
