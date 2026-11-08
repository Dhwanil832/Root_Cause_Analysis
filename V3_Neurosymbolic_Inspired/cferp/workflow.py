"""Full standalone CFERP case workflow layered over the scheduling core.

This module owns state transitions and routing. It does not perform Specialist,
Evidence Worker, Assessor, Intake, or LLM reasoning; those components return
typed packets through the ports represented here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Protocol

from .contracts import (
    CandidateAction, EvidencePacket, InformationSlot, JobState, Need, NeedState,
    OutwardRequest, RequestDisposition, Role, SlotState, VersionManifest,
    WorkItem,
)
from .engine import CFERPError, CFERPLead


_NEGATORS = frozenset({"not", "no", "never", "without", "none", "nor", "neither", "cannot", "unable"})


def statement_meaning(text: str) -> tuple[bool, frozenset[str]] | None:
    """Polarity and stemmed content terms; two statements with the same meaning say the same thing.

    Deliberately strict: "pressure was nominal" and "pressure was low" differ by a
    term, and "plate was engaged" and "plate was not engaged" differ in polarity.
    """
    from ewv3.retrieval import content_terms
    words = re.findall(r"[a-z']+", text.casefold())
    terms = frozenset(content_terms(text))
    if len(terms) < 2:
        return None
    return any(w in _NEGATORS or w.endswith("n't") for w in words), terms


def _question_signature(slots: Iterable[Any], source_scope: Iterable[str] = ()) -> tuple | None:
    """What a need asks: each slot's meaning and record constraints, plus its source scope.

    None when any question is too short to compare, so it is never folded.
    """
    rows = []
    for slot in slots:
        get = slot.get if isinstance(slot, dict) else lambda key, default=None: getattr(slot, key, default)
        meaning = statement_meaning(str(get("description", "") or ""))
        if meaning is None:
            return None
        rows.append((meaning, get("entity_id"), get("time_scope"), get("record_type"),
                     tuple(sorted(get("required_fields", ()) or ()))))
    if not rows:
        return None
    return frozenset(rows), tuple(sorted(str(s) for s in source_scope))


class BranchState(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PARKED = "parked"
    CONTRADICTED = "contradicted"
    SUPERSEDED = "superseded"


class AssessmentEffect(StrEnum):
    SUPPORTS = "supports"
    WEAKENS = "weakens"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    REJECTED_LINK = "rejected_link"


class CaseState(StrEnum):
    OPEN = "open"
    WAITING_EXTERNAL = "waiting_external"
    READY_TO_CLOSE = "ready_to_close"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    text: str
    branch_id: str
    kind: str = "hypothesis"
    incident_status: str = "hypothetical"
    parent_claim_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CausalLink:
    link_id: str
    source_claim_ids: tuple[str, ...]
    target_claim_id: str
    relation: str
    modality: str
    basis: str
    source_refs: tuple[str, ...] = ()
    source_relation: str = "inference"
    status: str = "candidate"
    dependencies: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    time_constraint: str = "unknown"
    source_text: str = ""


@dataclass(frozen=True, slots=True)
class Branch:
    branch_id: str
    claim_ids: tuple[str, ...]
    state: BranchState = BranchState.ACTIVE
    parent_branch_ids: tuple[str, ...] = ()
    reason: str = ""
    revision: int = 1


@dataclass(frozen=True, slots=True)
class BranchTransition:
    transition_id: str
    branch_id: str
    from_state: BranchState
    to_state: BranchState
    reason: str
    related_branch_ids: tuple[str, ...]
    board_version: int


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    material_id: str
    version: str
    content_hash: str
    title: str = ""
    source_kind: str = "unknown"
    readiness: str = "ready"
    searchable_ref: str | None = None
    lineage: str = "unknown"
    provenance_complete: bool = True
    related_claim_ids: tuple[str, ...] = ()
    related_need_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str | None = None


@dataclass(frozen=True, slots=True)
class ClarificationRecord:
    clarification_id: str
    need_id: str
    answer_id: str
    answer_text: str
    source_material_ids: tuple[str, ...]
    assignment_id: str
    assessor_status: str = "pending"


@dataclass(frozen=True, slots=True)
class AssessmentRecord:
    assessment_id: str
    claim_id: str
    material_id: str
    material_version: str
    passage_id: str
    exact_text: str
    effect: AssessmentEffect
    rationale: str
    assignment_id: str
    manifest: VersionManifest
    prior_assessment_ids: tuple[str, ...] = ()
    status: str = "current"
    quote: str = ""  # the Assessor's words from exact_text, when it quoted only part


@dataclass(frozen=True, slots=True)
class CandidateMembershipRecord:
    candidate_id: str
    proposition_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]
    assignment_id: str
    result_id: str
    board_version: int
    status: str = "candidate"


@dataclass(frozen=True, slots=True)
class Assignment:
    assignment_id: str
    role: Role
    owner_id: str
    purpose: str
    target_ids: tuple[str, ...]
    need_ids: tuple[str, ...]
    dependencies: tuple[str, ...]
    manifest: VersionManifest
    context: dict[str, Any] = field(default_factory=dict)
    budget: dict[str, int] = field(default_factory=dict)
    pair_id: str | None = None


@dataclass(frozen=True, slots=True)
class RoleResult:
    """Normalized adapter contract for one returned role packet."""
    result_id: str
    assignment_id: str
    role: Role
    manifest: VersionManifest
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WorkflowAction:
    action_id: str
    role: Role
    owner_id: str
    purpose: str
    target_ids: tuple[str, ...]
    need_ids: tuple[str, ...]
    dependencies: tuple[str, ...]
    manifest: VersionManifest
    priority_tier: int
    pair_id: str | None = None
    budget: dict[str, int] = field(default_factory=dict)


class LeadSemanticAssistant(Protocol):
    """Optional LLM-backed port for semantic ambiguity only.

    Returned suggestions are advisory. CFERP never auto-merges records based
    on an LLM response; a Lead policy decision must still be applied.
    """

    def suggest_matches(self, kind: str, candidate: dict[str, Any],
                        existing: tuple[dict[str, Any], ...]) -> tuple[str, ...]: ...

    def clarify_assignment(self, assignment: Assignment) -> dict[str, Any]: ...


REVISIT_PURPOSE = "revisit affected hypothesis using new Assessor annotations"


class CFERPWorkflow:
    """Case-level Lead workflow with immutable worker assignments and deltas."""

    def __init__(self, case_id: str, *, lead: CFERPLead | None = None,
                 semantic_assistant: LeadSemanticAssistant | None = None,
                 budgets: dict[str, int] | None = None):
        self.lead = lead or CFERPLead(case_id)
        if self.lead.case_id != case_id:
            raise CFERPError("workflow case_id must match its CFERPLead")
        self.case_id = case_id
        self.semantic_assistant = semantic_assistant
        self.default_budgets = budgets or {"llm_calls": 2, "retrieval_calls": 4, "tokens": 12000}
        self.case_state = CaseState.OPEN
        self.claims: dict[str, Claim] = {}
        self.causal_links: dict[str, CausalLink] = {}
        self.branches: dict[str, Branch] = {}
        # Candidate-level graph membership preserves SAHS alternatives even
        # when they share propositions or causal rules.
        self.candidate_memberships: dict[str, list[CandidateMembershipRecord]] = {}
        self.branch_history: list[BranchTransition] = []
        self.materials: dict[str, MaterialRecord] = {}
        self.assessments: dict[str, AssessmentRecord] = {}
        self.clarifications: dict[str, ClarificationRecord] = {}
        self.assignments: dict[str, Assignment] = {}
        self.result_fingerprints: dict[str, str] = {}
        self.result_archive: dict[str, RoleResult] = {}
        self.request_responses: dict[str, list[str]] = {}
        self.request_response_slot_hints: dict[str, dict[str, tuple[str, ...]]] = {}
        self.request_work_sources: dict[str, str] = {}
        self.need_packets: dict[str, EvidencePacket] = {}
        self.pending_need_reuse: dict[str, str] = {}
        # need_id -> (material index version, need version) of its last finished search.
        # The same need is not searched again over the same corpus: it waits for new
        # material or a revised need instead of repeating a search that already ran.
        self.need_last_search: dict[str, tuple[str, int]] = {}
        # A proposed claim that restates a board claim is folded into it: claim_id -> board claim_id.
        # A proposed need asking what an open need already asks is folded the same way.
        self.claim_aliases: dict[str, str] = {}
        self.need_aliases: dict[str, str] = {}
        self.reassessment_queue: set[tuple[str, str, str]] = set()
        self.match_suggestions: dict[str, tuple[str, ...]] = {}
        self.semantic_diagnostics: list[str] = []
        self.similarity_links: list[dict[str, Any]] = []
        self._initialization_events: dict[str, tuple[str, tuple[str, ...]]] = {}
        self.current_result_ref: str | None = None
        self._counter = 0

    def _id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}:{self.case_id}:{self._counter}"

    def _event(self, event_id: str, kind: str, payload: dict[str, Any]) -> None:
        self.lead.ingest_event(event_id, kind, payload)

    def _assignment(self, *, role: Role, owner_id: str, purpose: str,
                    target_ids: Iterable[str] = (), need_ids: Iterable[str] = (),
                    dependencies: Iterable[str] = (), context: dict[str, Any] | None = None,
                    budget: dict[str, int] | None = None, pair_id: str | None = None,
                    priority_tier: int = 3) -> Assignment:
        assignment_id = self._id(f"{role.value}-assignment")
        manifest = self.lead.manifest()
        assignment = Assignment(
            assignment_id, role, owner_id, purpose, tuple(dict.fromkeys(target_ids)),
            tuple(dict.fromkeys(need_ids)), tuple(dict.fromkeys(dependencies)), manifest,
            deepcopy(context or {}), deepcopy(budget or self.default_budgets), pair_id,
        )
        self.assignments[assignment_id] = assignment
        item = WorkItem(
            assignment_id, role, owner_id, assignment.target_ids, assignment.need_ids,
            JobState.QUEUED, priority_tier, len(self.lead.events) + 1,
            dependency_ids=assignment.dependencies, manifest=manifest,
        )
        self.lead.register_work(item)
        return assignment

    def initialize_case(self, *, event_id: str, case_packet: dict[str, Any],
                        specialist_profiles: Iterable[dict[str, Any]],
                        other_profile_id: str = "other") -> tuple[Assignment, ...]:
        """Register initial reported claims and launch cue-selected Specialists.

        Profile entries have {profile_id, cues, direction, owner_id?}. Exact
        normalized cue substring matches launch a profile; ``Other`` is always
        launched as the undocumented-cause coverage profile when configured.
        """
        profiles = tuple(specialist_profiles)
        if not profiles:
            raise CFERPError("initialization requires at least one Specialist profile and the Other profile")
        if not any(str(profile.get("profile_id")) == other_profile_id for profile in profiles):
            raise CFERPError(f"specialist cue map must include the {other_profile_id!r} coverage profile")
        init_payload = {"case_packet": case_packet, "specialist_profiles": profiles,
                        "other_profile_id": other_profile_id}
        init_fingerprint = self._fingerprint_dict("case_initialization", init_payload)
        prior_initialization = self._initialization_events.get(event_id)
        if prior_initialization is not None:
            if prior_initialization[0] != init_fingerprint:
                raise CFERPError("case initialization event ID reused with different content")
            return tuple(self.assignments[aid] for aid in prior_initialization[1])
        reported = tuple(case_packet.get("reported_claims", ()))
        claim_ids = [str(record.get("claim_id", "")) for record in reported]
        if any(not claim_id for claim_id in claim_ids) or len(claim_ids) != len(set(claim_ids)):
            raise CFERPError("initial reported claims need unique non-empty IDs")
        if set(claim_ids) & set(self.claims):
            raise CFERPError("case initialization contains claim IDs already in the board")
        event = self.lead.event(event_id)
        if event is not None:
            raise CFERPError("event ID is already used by a different Lead event")
        self._event(event_id, "case_initialized", init_payload)
        for record in reported:
            claim_id = str(record["claim_id"])
            if claim_id in self.claims:
                raise CFERPError(f"duplicate initial claim {claim_id}")
            self.claims[claim_id] = Claim(
                claim_id, str(record["text"]), str(record.get("branch_id", f"reported:{claim_id}")),
                str(record.get("kind", "case_claim")), "reported",
                provenance=tuple(record.get("provenance", ())),
            )
        text = " ".join(str(v) for v in case_packet.values()).casefold()
        selected = []
        for profile in profiles:
            pid = str(profile["profile_id"])
            cues = tuple(str(c).casefold() for c in profile.get("cues", ()))
            if pid == other_profile_id or any(cue and cue in text for cue in cues):
                selected.append(profile)
        if not selected and profiles:
            selected = [profiles[0]]
        launched = []
        for profile in selected:
            assignment = self._assignment(
                role=Role.SPECIALIST, owner_id=str(profile.get("owner_id", profile["profile_id"])),
                purpose=str(profile.get("direction", "generate initial causal hypotheses")),
                target_ids=tuple(c.claim_id for c in self.claims.values()),
                dependencies=tuple((*[c.claim_id for c in self.claims.values()],
                                    *self._material_dependencies(()))),
                context={"mode": "initial", "case_packet": case_packet,
                         "specialist_profile_id": profile["profile_id"],
                         "source_catalog": tuple(self.materials.values())},
                priority_tier=4,
            )
            launched.append(assignment)
        self._initialization_events[event_id] = (
            init_fingerprint, tuple(assignment.assignment_id for assignment in launched))
        self._queue_available()
        return tuple(launched)

    def _current(self, manifest: VersionManifest) -> bool:
        return manifest == self.lead.manifest()

    def _assignment_is_current(self, assignment: Assignment) -> bool:
        """Use dependency invalidation, not a global-version mismatch, for results."""
        work_item = self.lead.work.get(assignment.assignment_id)
        return work_item is not None and work_item.state != JobState.STALE

    def _validate_result(self, result: RoleResult, expected_role: Role) -> Assignment:
        if result.role != expected_role:
            raise CFERPError("result role does not match the receiving route")
        assignment = self.assignments.get(result.assignment_id)
        if assignment is None or assignment.role != expected_role:
            raise CFERPError("result references an unknown assignment")
        work_item = self.lead.work.get(assignment.assignment_id)
        if work_item is None or work_item.state not in {JobState.RUNNING, JobState.STALE}:
            raise CFERPError("role result is only accepted for a running or stale assignment")
        if result.manifest != assignment.manifest:
            raise CFERPError("result manifest differs from its immutable assignment")
        fingerprint = sha256(json.dumps({"role": result.role.value, "assignment": result.assignment_id,
                                         "manifest": result.manifest, "payload": result.payload},
                                        sort_keys=True, default=str).encode()).hexdigest()
        prior = self.result_fingerprints.get(result.result_id)
        if prior:
            if prior != fingerprint:
                raise CFERPError("result ID reused with different payload")
            raise CFERPError("result already applied")
        return assignment

    def submit_specialist_result(self, result: RoleResult) -> tuple[Assignment, ...]:
        assignment = self._validate_result(result, Role.SPECIALIST)
        if not self._assignment_is_current(assignment):
            self.result_fingerprints[result.result_id] = self._fingerprint(result)
            self.result_archive[result.result_id] = deepcopy(result)
            self._mark_assignment_stale(assignment.assignment_id, result.result_id)
            self._event(result.result_id, "stale_specialist_result", {"assignment_id": assignment.assignment_id})
            return self._requeue_stale_assignment(assignment)
        self._prevalidate_specialist_payload(result.payload)
        before = set(self.assignments)
        self.result_fingerprints[result.result_id] = self._fingerprint(result)
        self.result_archive[result.result_id] = deepcopy(result)
        payload = self._fold_duplicates(result.result_id, result.payload)
        causal_link_count_before = len(self.causal_links)
        new_claims = []
        for row in payload.get("claims", ()):
            claim_id = str(row["claim_id"])
            if claim_id in self.claims:
                existing = self.claims[claim_id]
                if existing.text != str(row["text"]):
                    raise CFERPError("claim ID reused with changed text")
                continue
            branch_id = str(row.get("branch_id", claim_id))
            claim = Claim(
                claim_id, str(row["text"]), branch_id, str(row.get("kind", "hypothesis")),
                "hypothetical" if row.get("kind", "hypothesis") == "incident_event" else "not_applicable",
                tuple(row.get("parent_claim_ids", assignment.target_ids)),
                tuple(row.get("dependency_ids", assignment.dependencies)),
                tuple(row.get("provenance", ())),
            )
            self.claims[claim_id] = claim
            new_claims.append(claim)
        grouped: dict[str, list[str]] = {}
        for claim in new_claims:
            grouped.setdefault(claim.branch_id, []).append(claim.claim_id)
        for branch_id, claim_ids in grouped.items():
            if branch_id not in self.branches:
                parents = tuple(dict.fromkeys(
                    parent for cid in claim_ids for parent in self.claims[cid].parent_claim_ids
                    if parent in self.claims
                ))
                parent_branches = tuple(dict.fromkeys(self.claims[p].branch_id for p in parents))
                self.branches[branch_id] = Branch(branch_id, tuple(claim_ids), parent_branch_ids=parent_branches)
            else:
                branch = self.branches[branch_id]
                self.branches[branch_id] = Branch(branch.branch_id,
                    tuple(dict.fromkeys((*branch.claim_ids, *claim_ids))), branch.state,
                    branch.parent_branch_ids, branch.reason, branch.revision + 1)
        for index, raw_link in enumerate(payload.get("causal_links", ())):
            link_id = str(raw_link.get("link_id") or f"link:{result.result_id}:{index}")
            sources = tuple(raw_link.get("source_claim_ids", raw_link.get("antecedent_ids", ())))
            target = str(raw_link.get("target_claim_id", raw_link.get("consequent_id", "")))
            if not sources or target not in self.claims or set(sources) - set(self.claims):
                raise CFERPError("causal link must reference known source and target claims")
            if link_id in self.causal_links:
                raise CFERPError("duplicate causal link ID")
            self.causal_links[link_id] = CausalLink(
                link_id, sources, target, str(raw_link.get("relation", "may_cause")),
                str(raw_link.get("modality", "may")), str(raw_link.get("basis", "model_proposed")),
                tuple(raw_link.get("source_refs", ())), str(raw_link.get("source_relation", "inference")),
                "candidate", tuple(raw_link.get("dependencies", (*sources, target))),
                tuple(raw_link.get("conditions", ())), str(raw_link.get("time_constraint", "unknown")),
                str(raw_link.get("source_text", "")),
            )
        for membership in payload.get("candidate_memberships", ()):
            candidate_id = str(membership["candidate_id"])
            record = CandidateMembershipRecord(
                candidate_id,
                tuple(dict.fromkeys(str(x) for x in membership.get("proposition_ids", ()))),
                tuple(dict.fromkeys(str(x) for x in membership.get("rule_ids", ()))),
                assignment.assignment_id, result.result_id, assignment.manifest.board_version,
            )
            self.candidate_memberships.setdefault(candidate_id, []).append(record)
        incoming_needs = (*payload.get("needs", ()), *payload.get("clarifications", ()))
        new_need_ids = {
            str(raw.get("need_id") or raw.get("clarification_id") or "")
            for raw in incoming_needs if isinstance(raw, dict)
        } - set(self.lead.needs)
        branch_changes = any(
            operation.get("branch_id") in self.branches
            and self.branches[str(operation["branch_id"])].state.value != str(operation.get("state", ""))
            for operation in payload.get("branch_operations", ())
        )
        has_graph_delta = bool(new_claims or len(self.causal_links) > causal_link_count_before
                               or new_need_ids or branch_changes)
        changed_dependency_ids = {claim.claim_id for claim in new_claims}
        if new_need_ids:
            for raw_need in incoming_needs:
                raw_need_id = str(raw_need.get("need_id") or raw_need.get("clarification_id") or "")
                if raw_need_id in new_need_ids:
                    changed_dependency_ids.update(str(target) for target in raw_need.get(
                        "target_ids", raw_need.get("related_claim_ids", ())) if target)
        if len(self.causal_links) > causal_link_count_before:
            for raw_link in payload.get("causal_links", ()):
                changed_dependency_ids.update(str(item) for item in raw_link.get(
                    "source_claim_ids", raw_link.get("antecedent_ids", ())) if item)
                target = raw_link.get("target_claim_id", raw_link.get("consequent_id"))
                if target:
                    changed_dependency_ids.add(str(target))
        self._event(result.result_id,
            "specialist_delta_committed" if has_graph_delta else "specialist_noop_returned", {
                "assignment_id": assignment.assignment_id,
                "changed_dependency_ids": tuple(sorted(changed_dependency_ids)),
                "provenance_complete": True,
            })
        self.lead.finish_work(assignment.assignment_id, state=JobState.RETURNED, result_ref=result.result_id)
        for index, raw_need in enumerate(payload.get("needs", ())):
            need = self._need_from_payload(raw_need, result.result_id, index)
            if need.need_id not in self.lead.needs:
                self.lead.add_need(need)
        for index, clarification in enumerate(payload.get("clarifications", ())):
            need = self._need_from_payload(clarification, result.result_id, index, origin_kind="specialist_clarification")
            if need.need_id not in self.lead.needs:
                self.lead.add_need(need)
        for operation in payload.get("branch_operations", ()):
            branch_id = str(operation["branch_id"])
            if branch_id in self.branches:
                self.apply_branch_decision(branch_id, BranchState(str(operation["state"])),
                    reason=str(operation["reason"]),
                    related_branch_ids=tuple(operation.get("related_branch_ids", ())))
        self._queue_available()
        return tuple(self.assignments[aid] for aid in self.assignments if aid not in before)

    def _fold_duplicates(self, result_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Fold restated claims and repeated questions into what the board already holds.

        Without this the same claim enters under several IDs, each with its own
        needs, and every arriving document is searched once per copy. References
        to a folded claim are rewritten to the board claim; nothing else changes.
        """
        meanings: dict[tuple[bool, frozenset[str]], str] = {}
        for claim_id, claim in self.claims.items():
            meaning = statement_meaning(claim.text)
            if meaning is not None:
                meanings.setdefault(meaning, claim_id)
        aliases: dict[str, str] = {}
        for row in payload.get("claims", ()):
            claim_id = str(row["claim_id"])
            if claim_id in self.claims:
                continue
            if claim_id in self.claim_aliases:
                aliases[claim_id] = self.claim_aliases[claim_id]
                continue
            meaning = statement_meaning(str(row["text"]))
            if meaning is None:
                continue
            if meaning in meanings:
                aliases[claim_id] = meanings[meaning]
            else:
                meanings[meaning] = claim_id
        every_alias = {**self.claim_aliases, **aliases}

        def rename(ids: Iterable[Any]) -> list[str]:
            return list(dict.fromkeys(every_alias.get(str(i), str(i)) for i in ids))

        def renamed(row: dict[str, Any], *keys: str) -> dict[str, Any]:
            return {**row, **{key: rename(row[key]) for key in keys if key in row}}

        claims = []
        for row in payload.get("claims", ()):
            if str(row["claim_id"]) in aliases:
                continue
            row = renamed(row, "parent_claim_ids", "dependency_ids")
            if "parent_claim_ids" in row:
                row["parent_claim_ids"] = [p for p in row["parent_claim_ids"] if p != str(row["claim_id"])]
            claims.append(row)
        links = []
        for raw in payload.get("causal_links", ()):
            raw = renamed(raw, "source_claim_ids", "antecedent_ids", "dependencies")
            for key in ("target_claim_id", "consequent_id"):
                if key in raw:
                    raw[key] = every_alias.get(str(raw[key]), str(raw[key]))
            sources = raw.get("source_claim_ids", raw.get("antecedent_ids", ()))
            if str(raw.get("target_claim_id", raw.get("consequent_id", ""))) in sources:
                continue  # folding made it a claim causing itself
            links.append(raw)

        asked: dict[tuple, tuple[str, frozenset[str]]] = {}
        for need in self.lead.needs.values():
            signature = _question_signature(need.slots, need.source_scope)
            if signature is not None and need.state not in {
                    NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL,
                    NeedState.SUPERSEDED, NeedState.REJECTED}:
                asked.setdefault(signature, (need.need_id, frozenset(need.target_ids)))
        folded_needs: dict[str, str] = {}
        kept_needs: dict[str, list[dict[str, Any]]] = {"needs": [], "clarifications": []}
        for kind in kept_needs:
            for index, raw in enumerate(payload.get(kind, ())):
                raw = renamed(raw, "target_ids", "related_claim_ids")
                need_id = str(raw.get("need_id") or raw.get("clarification_id") or f"{kind}:{index}")
                targets = frozenset(raw.get("target_ids") or raw.get("related_claim_ids") or ())
                signature = _question_signature(
                    raw.get("slots") or [{"description": raw.get("description", raw.get("question", ""))}],
                    raw.get("source_scope", ()))
                prior = asked.get(signature) if signature is not None else None
                if prior is not None and targets <= prior[1] and need_id not in self.lead.needs:
                    folded_needs[need_id] = prior[0]
                    continue
                if signature is not None:
                    asked.setdefault(signature, (need_id, targets))
                kept_needs[kind].append(raw)

        if not (every_alias or folded_needs):
            return payload
        if aliases or folded_needs:
            self.claim_aliases.update(aliases)
            self.need_aliases.update(folded_needs)
            self._event(f"{result_id}:folded", "duplicates_folded", {
                "claim_aliases": dict(sorted(aliases.items())),
                "need_aliases": dict(sorted(folded_needs.items())),
            })
        memberships = [renamed(m, "proposition_ids") for m in payload.get("candidate_memberships", ())]
        return {**payload, "claims": claims, "causal_links": links, **kept_needs,
                "candidate_memberships": memberships}

    def _prevalidate_specialist_payload(self, payload: dict[str, Any]) -> None:
        claims = tuple(payload.get("claims", ()))
        batch_ids = [str(row.get("claim_id", "")) for row in claims]
        if any(not cid for cid in batch_ids) or len(batch_ids) != len(set(batch_ids)):
            raise CFERPError("Specialist proposal needs unique non-empty claim IDs")
        proposed = set(batch_ids)
        known = set(self.claims) | set(self.claim_aliases) | proposed
        allowed_kinds = {"case_claim", "incident_event", "component_state", "system_mechanism",
                         "unknown_term", "unknown_condition", "hypothesis"}
        for row in claims:
            claim_id = str(row["claim_id"])
            text = str(row.get("text", "")).strip()
            if not text:
                raise CFERPError(f"claim {claim_id} has empty text")
            if claim_id in self.claims and self.claims[claim_id].text != text:
                raise CFERPError(f"claim ID reused with changed text: {claim_id}")
            kind = str(row.get("kind", "hypothesis"))
            if kind not in allowed_kinds:
                raise CFERPError(f"unsupported proposition kind: {kind}")
            if set(row.get("parent_claim_ids", ())) - known:
                raise CFERPError(f"claim {claim_id} references an unknown parent claim")
        for raw_link in payload.get("causal_links", ()):
            sources = tuple(raw_link.get("source_claim_ids", raw_link.get("antecedent_ids", ())))
            target = str(raw_link.get("target_claim_id", raw_link.get("consequent_id", "")))
            if not sources or target not in known or set(sources) - known:
                raise CFERPError("causal link must reference known source and target claims")
            if str(raw_link.get("relation", "may_cause")) not in {
                "may_cause", "contributes_to", "enables", "inhibits", "precedes"
            }:
                raise CFERPError("causal link has an unsupported relation")
            basis = str(raw_link.get("basis", "model_proposed"))
            if basis not in {"source_described", "vetted_domain_rule", "model_proposed"}:
                raise CFERPError("causal link has an unsupported basis")
            source_refs = tuple(raw_link.get("source_refs", ()))
            if set(source_refs) - set(self.materials):
                raise CFERPError("causal link references a material not in the assignment corpus")
            source_relation = str(raw_link.get("source_relation", "inference"))
            if source_relation not in {"quotation", "paraphrase", "inference"}:
                raise CFERPError("causal link has an unsupported source relation")
            if basis == "source_described":
                if not source_refs or not str(raw_link.get("source_text", "")).strip():
                    raise CFERPError("source-described link needs a source ID and exact passage")
                if not any(str(raw_link["source_text"]) in self.materials[mid].content
                           for mid in source_refs if self.materials[mid].content is not None):
                    raise CFERPError("source-described passage is not present in the supplied material")
        need_ids = []
        for index, raw_need in enumerate((*payload.get("needs", ()), *payload.get("clarifications", ()))):
            need_id = str(raw_need.get("need_id") or f"need:pending:{index}")
            need_ids.append(need_id)
            targets = tuple(raw_need.get("target_ids", raw_need.get("related_claim_ids", ())))
            if set(targets) - known:
                raise CFERPError(f"need {need_id} references an unknown target claim")
            slots = raw_need.get("slots", ())
            slot_ids = [str(slot.get("slot_id") or f"{need_id}:slot:{i}") for i, slot in enumerate(slots)]
            if len(slot_ids) != len(set(slot_ids)):
                raise CFERPError(f"need {need_id} has duplicate slot IDs")
        if len(need_ids) != len(set(need_ids)):
            raise CFERPError("Specialist result has duplicate need IDs")
        for operation in payload.get("branch_operations", ()):
            if str(operation.get("state", "")) not in {state.value for state in BranchState}:
                raise CFERPError("branch operation has an invalid state")
            if not str(operation.get("reason", "")).strip():
                raise CFERPError("branch operation requires a reason")
            if str(operation.get("branch_id", "")) not in set(self.branches) | {
                str(row.get("branch_id", row.get("claim_id", ""))) for row in claims
            }:
                raise CFERPError("branch operation references an unknown branch")
        memberships = tuple(payload.get("candidate_memberships", ()))
        candidate_ids = [str(item.get("candidate_id", "")) for item in memberships]
        if any(not cid for cid in candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            raise CFERPError("candidate membership needs unique non-empty candidate IDs")
        allowed_propositions = set(self.claims) | proposed
        allowed_rules = set(self.causal_links) | {
            str(row.get("link_id") or f"link:pending:{index}")
            for index, row in enumerate(payload.get("causal_links", ()))
        }
        for membership in memberships:
            proposition_ids = set(membership.get("proposition_ids", ()))
            rule_ids = set(membership.get("rule_ids", ()))
            if not proposition_ids or proposition_ids - allowed_propositions:
                raise CFERPError("candidate membership references unknown propositions")
            if rule_ids - allowed_rules:
                raise CFERPError("candidate membership references unknown causal rules")

    def _fingerprint(self, result: RoleResult) -> str:
        return sha256(json.dumps({"role": result.role.value, "assignment": result.assignment_id,
                                  "manifest": result.manifest, "payload": result.payload},
                                 sort_keys=True, default=str).encode()).hexdigest()

    def _need_from_payload(self, raw: dict[str, Any], origin_id: str, index: int,
                           origin_kind: str = "specialist_gap") -> Need:
        need_id = str(raw.get("need_id") or f"need:{origin_id}:{index}")
        slots = tuple(InformationSlot(
            str(slot.get("slot_id") or f"{need_id}:slot:{i}"), str(slot.get("description", "")),
            slot.get("entity_id"), slot.get("time_scope"), slot.get("record_type"),
            tuple(slot.get("required_fields", ())),
        ) for i, slot in enumerate(raw.get("slots", ())))
        if not slots:
            slots = (InformationSlot(f"{need_id}:slot:0", str(raw.get("description", raw.get("question", "")))),)
        targets = tuple(raw.get("target_ids", ()))
        if not targets:
            targets = tuple(cid for cid in raw.get("related_claim_ids", ()) if cid in self.claims)
        return Need(need_id, str(raw.get("origin_kind", origin_kind)), str(raw.get("origin_id", origin_id)),
                    targets, slots, source_scope=tuple(raw.get("source_scope", ())))

    def _material_dependencies(self, source_scope: Iterable[str]) -> tuple[str, ...]:
        if source_scope:
            return tuple(f"{sid}:{self.materials[sid].version}" for sid in source_scope if sid in self.materials)
        return tuple(f"{m.material_id}:{m.version}" for m in self.materials.values())

    def submit_worker_result(self, result: RoleResult) -> tuple[Assignment, ...]:
        assignment = self._validate_result(result, Role.EVIDENCE_WORKER)
        if not self._assignment_is_current(assignment):
            self.result_fingerprints[result.result_id] = self._fingerprint(result)
            self.result_archive[result.result_id] = deepcopy(result)
            self._mark_assignment_stale(assignment.assignment_id, result.result_id)
            self._event(result.result_id, "stale_worker_result", {"assignment_id": assignment.assignment_id})
            if self._search_cap_reached_for(assignment.target_ids,
                                            self._active_searches_per_claim(excluding=assignment.assignment_id)):
                return ()  # reissued by the queue once a slot on its claim frees
            return self._requeue_stale_assignment(assignment)
        self._prevalidate_worker_payload(result.payload, assignment)
        before = set(self.assignments)
        need_ids = set(assignment.need_ids)
        pending_assessor: list[Assignment] = []
        prepared_requests = tuple(self._request_from_draft(draft, assignment, index)
                                  for index, draft in enumerate(result.payload.get("requests", ())))
        request_map = dict(self.lead.requests)
        for request in prepared_requests:
            previous = request_map.get(request.request_id)
            if previous is not None and previous != request:
                raise CFERPError("request ID reused with different content")
            request_map[request.request_id] = request
        prepared_packets = []
        packet_ids = set(self.evidence_packets) | set(self.lead.packets)
        for packet_index, raw_packet in enumerate(result.payload.get("packets", ())):
            request_id = str(raw_packet.get("request_id", ""))
            if request_id and request_id not in request_map:
                raise CFERPError(f"worker packet references unknown request {request_id}")
            target_ids = tuple(raw_packet.get("target_ids", assignment.target_ids))
            for target in target_ids:
                if target not in self.claims:
                    raise CFERPError(f"worker packet references unknown claim {target}")
            for link in raw_packet.get("candidate_links", ()):
                self._validate_material_link(link)
            packet_id = str(raw_packet.get("packet_id") or f"packet:{result.result_id}:{packet_index}")
            if packet_id in packet_ids:
                raise CFERPError(f"duplicate evidence packet ID {packet_id}")
            packet_ids.add(packet_id)
            packet = EvidencePacket(
                packet_id, request_id or f"need:{next(iter(need_ids), 'unlinked')}",
                target_ids, tuple(raw_packet.get("covered_slot_ids", ())),
                tuple(raw_packet.get("source_scope", ())), tuple(raw_packet.get("entity_ids", ())),
                raw_packet.get("time_scope"), tuple(raw_packet.get("record_types", ())),
                tuple(tuple(x) for x in raw_packet.get("source_versions", ())),
                str(raw_packet.get("searched_material_index_version", result.manifest.material_index_version)),
                self._packet_payload(raw_packet),
                slot_payloads=tuple(raw_packet.get("slot_payloads", ())),
            )
            if request_id:
                request = request_map[request_id]
                if (tuple(sorted(packet.target_ids)) != tuple(sorted(request.target_ids))
                        or not packet.covered_slot_ids
                        or not set(packet.covered_slot_ids).issubset(request.slot_ids)):
                    raise CFERPError("worker packet target/slots do not match its request")
                mismatches = self.lead._packet_non_slot_mismatches(packet, request)
                if mismatches:
                    raise CFERPError("worker packet scope/snapshot does not match request: " + ", ".join(mismatches))
            prepared_packets.append((packet, raw_packet, bool(request_id)))
        for answer in result.payload.get("clarification_answers", ()):
            if str(answer.get("need_id", "")) not in self.lead.needs:
                raise CFERPError("clarification answer references an unknown need")
            if set(answer.get("source_material_ids", ())) - set(self.materials):
                raise CFERPError("clarification answer references an unknown source material")
        self.result_fingerprints[result.result_id] = self._fingerprint(result)
        self.result_archive[result.result_id] = deepcopy(result)
        for request in prepared_requests:
            if request.request_id not in self.lead.requests:
                self.lead.add_request(request)
        covered_pairs = self._covered_pairs()
        skipped_pairs: list[str] = []
        for packet, raw_packet, has_request in prepared_packets:
            request_id = packet.request_id
            if has_request:
                self.lead.register_packet(packet)
            # Packets used for assessment need not be outward-request packets;
            # retain them in workflow storage if no outward request owns them.
            self.evidence_packets[packet.packet_id] = packet
            for need_id in assignment.need_ids:
                self.need_packets[need_id] = packet
            for link_index, link in enumerate(raw_packet.get("candidate_links", ())):
                claim_id = str(link["claim_id"])
                material_id = str(link["material_id"])
                pair = self._pair_key(claim_id, material_id, str(link["material_version"]),
                                      str(link.get("exact_text", "")))
                if pair in covered_pairs:
                    # The same claim and passage was already assessed, or is queued,
                    # through another search: the packet keeps the link, no new job.
                    skipped_pairs.append(str(link.get("passage_id", "")))
                    continue
                covered_pairs.add(pair)
                assessment_assignment = self._assignment(
                    role=Role.ASSESSOR, owner_id=f"assessor-pair:{assignment.owner_id}",
                    purpose="assess this exact claim–material passage relationship",
                    target_ids=(claim_id,), need_ids=tuple(link.get("need_ids", assignment.need_ids)),
                    dependencies=(claim_id, f"{material_id}:{link['material_version']}"),
                    context={"task_kind": "evidence_review", "packet_id": packet.packet_id,
                             "candidate_link": deepcopy(link), "claim": self.claims[claim_id],
                             "material": self.materials[material_id],
                             "source_work_item_id": assignment.assignment_id},
                    pair_id=assignment.owner_id, priority_tier=1,
                )
                pending_assessor.append(assessment_assignment)
        for req in prepared_requests:
            # Request review must see the exact retrieval candidates from the
            # same worker result. Without this, the Assessor cannot determine
            # whether the proposed request is redundant or still targets an
            # unresolved information gap.
            existing_candidate_links = []
            request_need_ids = set(req.origin_ids)
            for _packet, raw_packet, _has_request in prepared_packets:
                for link in raw_packet.get("candidate_links", ()):
                    link_need_ids = set(link.get("need_ids", assignment.need_ids))
                    if not link_need_ids.intersection(request_need_ids):
                        continue
                    existing_candidate_links.append({
                        "candidate_link_id": str(link.get("passage_id", "")),
                        "source_id": str(link.get("material_id", "")),
                        "source_version": str(link.get("material_version", "")),
                        "slot_id": str(link.get("slot_id", "")),
                        "exact_text": str(link.get("exact_text", "")),
                        "start_offset": link.get("start_offset"),
                        "end_offset": link.get("end_offset"),
                    })
            review_assignment = self._assignment(
                role=Role.ASSESSOR, owner_id=f"assessor-pair:{assignment.owner_id}",
                purpose="review a proposed outward information request",
                target_ids=req.target_ids, need_ids=tuple(n for n in req.origin_ids if n in self.lead.needs),
                dependencies=tuple((*req.target_ids, *req.origin_ids)),
                context={"task_kind": "request_review", "request": req,
                         "source_work_item_id": assignment.assignment_id,
                         "existing_candidate_links": existing_candidate_links},
                pair_id=assignment.owner_id, priority_tier=2,
            )
            pending_assessor.append(review_assignment)
            self.request_work_sources[req.request_id] = assignment.assignment_id
        for index, answer in enumerate(result.payload.get("clarification_answers", ())):
            need_id = str(answer.get("need_id", ""))
            if need_id not in self.lead.needs:
                raise CFERPError("clarification answer references an unknown need")
            answer_id = str(answer.get("answer_id") or f"answer:{result.result_id}:{index}")
            clarification_id = str(answer.get("clarification_id") or f"clarification:{need_id}")
            if clarification_id in self.clarifications and self.clarifications[clarification_id].answer_id != answer_id:
                clarification_id = f"{clarification_id}:{answer_id}"
            source_ids = tuple(answer.get("source_material_ids", ()))
            if set(source_ids) - set(self.materials):
                raise CFERPError("clarification answer references an unknown source material")
            record = ClarificationRecord(clarification_id, need_id, answer_id,
                str(answer.get("answer_text", "")), source_ids, assignment.assignment_id)
            self.clarifications[clarification_id] = record
            need = self.lead.needs[need_id]
            review = self._assignment(
                role=Role.ASSESSOR, owner_id=f"assessor-pair:{assignment.owner_id}",
                purpose="verify a clarification answer before returning it to the Specialist",
                target_ids=need.target_ids, need_ids=(need_id,),
                dependencies=tuple((*need.target_ids, need_id,
                                    *(f"{sid}:{self.materials[sid].version}" for sid in source_ids))),
                context={"task_kind": "clarification_review", "clarification": record,
                         "source_work_item_id": assignment.assignment_id},
                pair_id=assignment.owner_id, priority_tier=1)
            pending_assessor.append(review)
        for need_id in assignment.need_ids:
            need = self.lead.needs.get(need_id)
            if need is not None:
                self.need_last_search[need_id] = (assignment.manifest.material_index_version, need.version)
        self.lead.finish_work(assignment.assignment_id,
                              state=JobState.AWAITING_ASSESSOR if pending_assessor else JobState.RETURNED,
                              result_ref=result.result_id)
        self._event(result.result_id, "worker_result_received", {
            "assignment_id": assignment.assignment_id,
            "assessment_assignments": tuple(a.assignment_id for a in pending_assessor),
            "already_assessed_passage_ids": tuple(skipped_pairs),
        })
        for target_need_id, source_need_id in tuple(self.pending_need_reuse.items()):
            if source_need_id not in assignment.need_ids:
                continue
            if self._reuse_need_packet(source_need_id, target_need_id):
                self.pending_need_reuse.pop(target_need_id, None)
            else:
                self.pending_need_reuse.pop(target_need_id, None)
        self._queue_available()
        return tuple(self.assignments[aid] for aid in self.assignments if aid not in before)

    @staticmethod
    def _pair_key(claim_id: str, material_id: str, material_version: str, exact_text: str) -> tuple[str, ...]:
        return (claim_id, material_id, material_version, " ".join(exact_text.split()))

    def _covered_pairs(self) -> set[tuple[str, ...]]:
        """Claim-passage pairs with a current assessment or an assessor job not yet finished."""
        covered = {self._pair_key(a.claim_id, a.material_id, a.material_version, a.exact_text)
                   for a in self.assessments.values() if a.status == "current"}
        waiting = {JobState.QUEUED, JobState.RUNNING}
        for assignment in self.assignments.values():
            link = assignment.context.get("candidate_link") if assignment.role == Role.ASSESSOR else None
            item = self.lead.work.get(assignment.assignment_id)
            if isinstance(link, dict) and item is not None and item.state in waiting:
                covered.add(self._pair_key(str(link["claim_id"]), str(link["material_id"]),
                                           str(link["material_version"]), str(link.get("exact_text", ""))))
        return covered

    def _prevalidate_worker_payload(self, payload: dict[str, Any], assignment: Assignment) -> None:
        """Keep every EW result inside its immutable target/need/slot assignment."""
        assigned_targets = set(assignment.target_ids)
        assigned_needs = set(assignment.need_ids)
        need_slots: dict[str, set[str]] = {}
        for need_id in assigned_needs:
            need = self.lead.needs.get(need_id)
            if need is None:
                raise CFERPError("Evidence Worker assignment references an unknown need")
            need_slots[need_id] = {slot.slot_id for slot in need.slots}
        assigned_slots = set().union(*need_slots.values()) if need_slots else set()
        requests = {}
        for index, draft in enumerate(payload.get("requests", ())):
            request = self._request_from_draft(draft, assignment, index)
            if request.request_id in requests or request.request_id in self.lead.requests:
                existing = self.lead.requests.get(request.request_id)
                if existing != request:
                    raise CFERPError("request ID reused with different content")
                raise CFERPError("worker result repeats an existing request ID")
            if not request.target_ids or not set(request.target_ids).issubset(assigned_targets):
                raise CFERPError("request targets exceed the Evidence Worker assignment")
            if not request.origin_ids or not set(request.origin_ids).issubset(assigned_needs):
                raise CFERPError("request origins exceed the Evidence Worker assignment")
            request_slots = set().union(*(need_slots[nid] for nid in request.origin_ids))
            if not set(request.slot_ids).issubset(request_slots):
                raise CFERPError("request slots exceed the assigned information needs")
            requests[request.request_id] = request
        for raw_packet in payload.get("packets", ()):
            targets = set(raw_packet.get("target_ids", assignment.target_ids))
            if not targets or not targets.issubset(assigned_targets):
                raise CFERPError("worker packet targets exceed the Evidence Worker assignment")
            request_id = str(raw_packet.get("request_id", ""))
            packet_slots = set(raw_packet.get("covered_slot_ids", ()))
            if request_id:
                request = requests.get(request_id)
                if request is None and request_id != assignment.context.get("request_id"):
                    raise CFERPError("worker packet request is outside the assignment")
                allowed_slots = set(request.slot_ids) if request else assigned_slots
            else:
                allowed_slots = assigned_slots
            if packet_slots and not packet_slots.issubset(allowed_slots):
                raise CFERPError("worker packet slots exceed the Evidence Worker assignment")
            for link in raw_packet.get("candidate_links", ()):
                claim_id = str(link.get("claim_id", ""))
                link_needs = set(link.get("need_ids", assignment.need_ids))
                if claim_id not in assigned_targets:
                    raise CFERPError("candidate link claim exceeds the Evidence Worker assignment")
                if not link_needs or not link_needs.issubset(assigned_needs):
                    raise CFERPError("candidate link needs exceed the Evidence Worker assignment")
                if not any(claim_id in self.lead.needs[nid].target_ids for nid in link_needs):
                    raise CFERPError("candidate link claim is unrelated to its assigned need")
        for answer in payload.get("clarification_answers", ()):
            need_id = str(answer.get("need_id", ""))
            if need_id not in assigned_needs:
                raise CFERPError("clarification answer need exceeds the Evidence Worker assignment")

    @property
    def evidence_packets(self) -> dict[str, EvidencePacket]:
        if not hasattr(self, "_evidence_packets"):
            self._evidence_packets = {}
        return self._evidence_packets

    @staticmethod
    def _packet_payload(raw_packet: dict[str, Any]) -> Any:
        payload = deepcopy(raw_packet.get("result_payload", {}))
        if not isinstance(payload, dict):
            payload = {"result": payload}
        if "candidate_links" not in payload and raw_packet.get("candidate_links"):
            payload["candidate_links"] = deepcopy(raw_packet["candidate_links"])
        if "requests" not in payload and raw_packet.get("requests"):
            payload["requests"] = deepcopy(raw_packet["requests"])
        return payload

    @staticmethod
    def _candidate_links_from_packet(packet: EvidencePacket) -> tuple[dict[str, Any], ...]:
        """Read links from full packets and per-slot partial-reuse payloads."""
        payload = packet.result_payload if isinstance(packet.result_payload, dict) else {}
        found = list(payload.get("candidate_links", ()))
        for _, slot_payload in packet.slot_payloads:
            if isinstance(slot_payload, dict):
                found.extend(slot_payload.get("candidate_links", ()))
                nested = slot_payload.get("result_payload")
                if isinstance(nested, dict):
                    found.extend(nested.get("candidate_links", ()))
        slot_payloads = payload.get("reused_slot_payloads", {})
        if isinstance(slot_payloads, dict):
            for slot_payload in slot_payloads.values():
                if isinstance(slot_payload, dict):
                    found.extend(slot_payload.get("candidate_links", ()))
                    nested = slot_payload.get("result_payload")
                    if isinstance(nested, dict):
                        found.extend(nested.get("candidate_links", ()))
        deduplicated = []
        seen = set()
        for link in found:
            key = (link.get("claim_id"), link.get("material_id"), link.get("material_version"),
                   link.get("passage_id"), link.get("exact_text"))
            if key not in seen:
                seen.add(key)
                deduplicated.append(deepcopy(link))
        return tuple(deduplicated)

    def _validate_material_link(self, link: dict[str, Any]) -> None:
        required = {"claim_id", "material_id", "material_version", "passage_id", "exact_text"}
        missing = required - set(link)
        if missing:
            raise CFERPError(f"candidate link missing fields: {sorted(missing)}")
        claim_id, material_id = str(link["claim_id"]), str(link["material_id"])
        if claim_id not in self.claims or material_id not in self.materials:
            raise CFERPError("candidate link references unknown claim or material")
        material = self.materials[material_id]
        if material.version != str(link["material_version"]):
            raise CFERPError("candidate link references a non-current material version")
        exact = str(link["exact_text"])
        content = link.get("source_text") or material.content
        if content is not None and exact not in str(content):
            raise CFERPError("candidate passage does not match supplied source text")
        start, end = link.get("start_offset"), link.get("end_offset")
        if start is not None or end is not None:
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
                raise CFERPError("candidate passage offsets must be a valid half-open span")
            if content is not None and str(content)[start:end] != exact:
                raise CFERPError("candidate passage offsets do not match exact_text")

    def _request_from_draft(self, draft: dict[str, Any], assignment: Assignment,
                            index: int) -> OutwardRequest:
        request_id = str(draft.get("request_id") or f"request:{assignment.assignment_id}:{index}")
        target_ids = tuple(draft.get("target_ids", assignment.target_ids))
        origin_ids = tuple(draft.get("origin_ids", assignment.need_ids))
        slot_ids = tuple(draft.get("slot_ids", ()))
        if not slot_ids:
            raise CFERPError("request draft must identify at least one information slot")
        for target in target_ids:
            if target not in self.claims:
                raise CFERPError(f"request references unknown claim {target}")
        for need_id in origin_ids:
            if need_id not in self.lead.needs:
                raise CFERPError(f"request references unknown need {need_id}")
        return OutwardRequest(
            request_id, origin_ids, target_ids, slot_ids, str(draft.get("wording", draft.get("question_or_document", ""))),
            str(draft.get("request_kind", draft.get("request_type", "question"))),
            tuple(draft.get("source_scope", ())), tuple(draft.get("entity_ids", draft.get("entity_scope", ()))),
            draft.get("time_scope"), tuple(draft.get("record_types", ())),
            tuple(tuple(x) for x in draft.get("source_versions", ())),
            self.lead.material_index_version, RequestDisposition.ASSESSOR_REVIEW,
        )

    def submit_assessor_result(self, result: RoleResult) -> tuple[Assignment, ...]:
        assignment = self._validate_result(result, Role.ASSESSOR)
        if not self._assignment_is_current(assignment):
            self.result_fingerprints[result.result_id] = self._fingerprint(result)
            self.result_archive[result.result_id] = deepcopy(result)
            self._mark_assignment_stale(assignment.assignment_id, result.result_id)
            self._event(result.result_id, "stale_assessor_result", {"assignment_id": assignment.assignment_id})
            return self._requeue_stale_assignment(assignment)
        self._prevalidate_assessor_payload(result.payload, assignment)
        before = set(self.assignments)
        self.result_fingerprints[result.result_id] = self._fingerprint(result)
        self.result_archive[result.result_id] = deepcopy(result)
        payload = result.payload
        if payload.get("task_kind") == "request_review":
            request_id = str(payload["request_id"])
            disposition = str(payload["disposition"])
            self.lead.apply_request_review(request_id, disposition)
            source_work_id = assignment.context.get("source_work_item_id")
            if source_work_id and source_work_id in self.lead.work and disposition == "revise":
                self.lead.transition_work(source_work_id, JobState.SUPERSEDED,
                                          result_ref=result.result_id,
                                          reason="replaced by a revision assignment: " +
                                          str(payload.get("feedback", "Assessor requested revision")))
                source = self.assignments[source_work_id]
                self._assignment(
                    role=Role.EVIDENCE_WORKER, owner_id=source.owner_id,
                    purpose="revise search/request using Assessor feedback",
                    target_ids=source.target_ids, need_ids=source.need_ids,
                    dependencies=source.dependencies,
                    context={"revision_of": source_work_id, "assessor_feedback": payload.get("feedback", ""),
                             "revised_request": payload.get("revised_request", ""),
                             "prior_assignment": source}, budget=source.budget,
                    pair_id=source.pair_id, priority_tier=2,
                )
            elif source_work_id and source_work_id in self.lead.work and disposition == "reject":
                self.lead.transition_work(source_work_id, JobState.COMPLETE, result_ref=result.result_id)
            # Passing is eligibility only; the Lead still explicitly sends it.
        elif payload.get("task_kind") == "clarification_review":
            clarification_id = str(payload["clarification_id"])
            record = self.clarifications.get(clarification_id)
            if record is None:
                raise CFERPError("Assessor result references an unknown clarification")
            decision = str(payload.get("decision", "ambiguous"))
            if decision not in {"accepted", "partially_accepted", "rejected", "ambiguous"}:
                raise CFERPError("clarification decision must preserve its review outcome")
            updated_record = replace(record, assessor_status=decision)
            self.clarifications[clarification_id] = updated_record
            # Only a usable answer should trigger Specialist revision. An
            # ambiguous, conflicting, unanswered, or rejected answer remains
            # visible for Lead reconciliation without creating a false update.
            if decision in {"accepted", "partially_accepted"}:
                need = self.lead.needs[record.need_id]
                self._assignment(
                    role=Role.SPECIALIST, owner_id="lead-routed",
                    purpose="revise or continue the hypothesis using the Assessor-reviewed clarification",
                    target_ids=need.target_ids, need_ids=(record.need_id,),
                    dependencies=tuple((*need.target_ids, f"clarification:{clarification_id}")),
                    context={"mode": "revision", "clarification": updated_record,
                             "assessor_context": deepcopy(payload)}, priority_tier=2,
                )
        else:
            records = payload.get("assessments", ())
            if not records:
                records = (payload,)
            for idx, row in enumerate(records):
                claim_id, material_id = str(row["claim_id"]), str(row["material_id"])
                if claim_id not in self.claims or material_id not in self.materials:
                    raise CFERPError("Assessor result references unknown claim or material")
                material = self.materials[material_id]
                version = str(row.get("material_version", material.version))
                if version != material.version:
                    raise CFERPError("Assessor result uses a stale material version")
                effect = AssessmentEffect(str(row["effect"]))
                assessment_id = str(row.get("assessment_id") or f"assessment:{result.result_id}:{idx}")
                prior_ids = tuple(row.get("reassesses", ()))
                for prior_id in prior_ids:
                    prior = self.assessments.get(prior_id)
                    if prior is None or (prior.claim_id, prior.material_id) != (claim_id, material_id):
                        raise CFERPError("reassessment must cite a prior assessment for the same claim/material pair")
                    self.assessments[prior_id] = AssessmentRecord(
                        prior.assessment_id, prior.claim_id, prior.material_id, prior.material_version,
                        prior.passage_id, prior.exact_text, prior.effect, prior.rationale,
                        prior.assignment_id, prior.manifest, prior.prior_assessment_ids, "superseded_by_reassessment")
                record = AssessmentRecord(
                    assessment_id, claim_id, material_id, version, str(row.get("passage_id", "")),
                    str(row.get("exact_text", "")), effect, str(row.get("rationale", "")),
                    assignment.assignment_id, result.manifest, prior_ids,
                    quote=str(row.get("quote", "")),
                )
                if assessment_id in self.assessments:
                    raise CFERPError("duplicate assessment_id")
                self.assessments[assessment_id] = record
                source_work_id = assignment.context.get("source_work_item_id")
                if effect == AssessmentEffect.REJECTED_LINK and source_work_id in self.lead.work:
                    self.lead.transition_work(source_work_id, JobState.SUPERSEDED,
                                              result_ref=result.result_id,
                                              reason="replaced by a revision assignment: " +
                                              str(row.get("rationale", "Candidate link rejected")))
                    source = self.assignments[source_work_id]
                    self._assignment(
                        role=Role.EVIDENCE_WORKER, owner_id=source.owner_id,
                        purpose="revise retrieval after the Assessor rejected a candidate link",
                        target_ids=source.target_ids, need_ids=source.need_ids,
                        dependencies=source.dependencies,
                        context={"revision_of": source_work_id, "assessor_feedback": row.get("rationale", ""),
                                 "prior_assignment": source}, budget=source.budget,
                        pair_id=source.pair_id, priority_tier=2,
                    )
        self.lead.finish_work(assignment.assignment_id, state=JobState.RETURNED, result_ref=result.result_id)
        event_kind = "request_review_committed" if payload.get("task_kind") == "request_review" else (
            "assessor_clarification_committed" if payload.get("task_kind") == "clarification_review"
            else "assessor_annotation_committed")
        self._event(result.result_id, event_kind, {
            "assignment_id": assignment.assignment_id,
            "assessment_ids": tuple(a.assessment_id for a in self.assessments.values()
                                     if a.assignment_id == assignment.assignment_id),
            "request_id": payload.get("request_id"),
            "clarification_id": payload.get("clarification_id"),
            "changed_dependency_ids": tuple(dict.fromkeys(
                str(row.get("claim_id")) for row in payload.get("assessments", (payload,))
                if row.get("claim_id")
            )),
        })
        # New/changed annotations trigger focused Specialist review. Assessment
        # effects never directly change branch state.
        created = []
        affected_claims = tuple(dict.fromkeys(
            str(row.get("claim_id")) for row in payload.get("assessments", (payload,))
            if row.get("claim_id") in self.claims
        ))
        if affected_claims and payload.get("task_kind") not in {"request_review", "clarification_review"}:
            self._supersede_pending_revisits(affected_claims, result.result_id)
            created.append(self._assignment(
                role=Role.SPECIALIST, owner_id="lead-routed", purpose=REVISIT_PURPOSE,
                target_ids=affected_claims,
                dependencies=tuple((*affected_claims, *self._material_dependencies(()),
                                    *(f"assessment:{aid}" for aid in self.assessments))),
                context={"mode": "revision", "assessor_annotations": tuple(
                    a for a in self.assessments.values() if a.claim_id in affected_claims
                ), "source_catalog": tuple(self.materials.values())}, priority_tier=2,
            ))
        self._queue_available()
        self._settle_source_worker(assignment.context.get("source_work_item_id"))
        return tuple(self.assignments[aid] for aid in self.assignments if aid not in before)

    def _supersede_pending_revisits(self, claim_ids: tuple[str, ...], result_ref: str) -> None:
        """Retire earlier revisit jobs for the same claims before queuing the newest.

        A revisit carries the Assessor annotations known when it was created, and
        reissuing a stale one keeps that old set. Only the newest is useful, so
        older queued or stale ones (not yet started) are superseded rather than
        piling up. A running revisit keeps its slot and is refreshed when its
        result returns.
        """
        for work_id, item in tuple(self.lead.work.items()):
            assignment = self.assignments.get(work_id)
            if (assignment is None or assignment.role != Role.SPECIALIST
                    or assignment.purpose != REVISIT_PURPOSE
                    or set(assignment.target_ids) != set(claim_ids)
                    or item.state not in {JobState.QUEUED, JobState.STALE}
                    or self.lead.is_executing(work_id)):
                continue
            self.lead.transition_work(work_id, JobState.SUPERSEDED, result_ref=result_ref,
                                      reason="replaced by a newer revisit with later Assessor annotations")

    def _prevalidate_assessor_payload(self, payload: dict[str, Any], assignment: Assignment) -> None:
        task_kind = payload.get("task_kind", "evidence_review")
        expected_kind = assignment.context.get("task_kind", "evidence_review")
        if task_kind != expected_kind:
            raise CFERPError("Assessor result task kind does not match its assignment")
        if task_kind == "request_review":
            request_id = str(payload.get("request_id", ""))
            assigned_request = assignment.context.get("request")
            assigned_request_id = getattr(assigned_request, "request_id", None)
            if assigned_request_id is not None and request_id != assigned_request_id:
                raise CFERPError("request review result does not match its assigned request")
            if request_id not in self.lead.requests:
                raise CFERPError("request review references an unknown request")
            if payload.get("disposition") not in {"pass", "revise", "reject"}:
                raise CFERPError("request review disposition must be pass, revise, or reject")
            return
        if task_kind == "clarification_review":
            clarification_id = str(payload.get("clarification_id", ""))
            assigned_clarification = assignment.context.get("clarification")
            assigned_id = getattr(assigned_clarification, "clarification_id", None)
            if assigned_id is not None and clarification_id != assigned_id:
                raise CFERPError("clarification result does not match its assigned answer")
            if clarification_id not in self.clarifications:
                raise CFERPError("clarification review references an unknown answer")
            if payload.get("decision", "ambiguous") not in {
                "accepted", "partially_accepted", "rejected", "ambiguous"
            }:
                raise CFERPError("invalid clarification review decision")
            return
        if task_kind not in {"evidence_review", "reassessment_triage"}:
            raise CFERPError("unsupported Assessor task kind")
        rows = tuple(payload.get("assessments", ())) or (payload,)
        assigned_link = assignment.context.get("candidate_link") if task_kind == "evidence_review" else None
        if task_kind == "evidence_review" and not isinstance(assigned_link, dict):
            raise CFERPError("evidence review assignment is missing its candidate passage")
        assigned_material = assignment.context.get("material") if task_kind == "reassessment_triage" else None
        assigned_prior_ids = set(assignment.context.get("prior_assessment_ids", ()))
        assessment_ids = []
        for index, row in enumerate(rows):
            claim_id, material_id = str(row.get("claim_id", "")), str(row.get("material_id", ""))
            if claim_id not in self.claims or material_id not in self.materials:
                raise CFERPError("Assessor result references an unknown claim or material")
            if claim_id not in assignment.target_ids:
                raise CFERPError("Assessor result claim is outside the assigned target scope")
            if task_kind == "evidence_review":
                expected = assigned_link
                if (claim_id != str(expected.get("claim_id", ""))
                        or material_id != str(expected.get("material_id", ""))
                        or str(row.get("material_version", "")) != str(expected.get("material_version", ""))
                        or str(row.get("passage_id", "")) != str(expected.get("passage_id", ""))
                        or str(row.get("exact_text", "")) != str(expected.get("exact_text", ""))):
                    raise CFERPError("Assessor evidence result differs from its assigned candidate passage")
            elif task_kind == "reassessment_triage":
                if (assigned_material is None or material_id != assigned_material.material_id
                        or str(row.get("material_version", "")) != str(assigned_material.version)):
                    raise CFERPError("reassessment result differs from its assigned material version")
                if not set(row.get("reassesses", ())).issubset(assigned_prior_ids):
                    raise CFERPError("reassessment result cites an assessment outside its assignment")
            material = self.materials[material_id]
            version = str(row.get("material_version", material.version))
            if version != material.version:
                raise CFERPError("Assessor result uses a stale material version")
            try:
                AssessmentEffect(str(row["effect"]))
            except (KeyError, ValueError) as exc:
                raise CFERPError("Assessor result has an invalid evidence effect") from exc
            assessment_id = str(row.get("assessment_id") or f"assessment:pending:{index}")
            assessment_ids.append(assessment_id)
            exact = str(row.get("exact_text", ""))
            if exact and material.content is not None and exact not in material.content:
                raise CFERPError("Assessor passage is not present in the supplied material")
            start, end = row.get("start_offset"), row.get("end_offset")
            if start is not None or end is not None:
                if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
                    raise CFERPError("Assessor passage offsets must be a valid half-open span")
                if material.content is not None and material.content[start:end] != exact:
                    raise CFERPError("Assessor passage offsets do not match exact_text")
            for prior_id in row.get("reassesses", ()):
                prior = self.assessments.get(str(prior_id))
                if prior is None or (prior.claim_id, prior.material_id) != (claim_id, material_id):
                    raise CFERPError("reassessment must cite an earlier assessment for the same claim/material pair")
        if len(assessment_ids) != len(set(assessment_ids)) or set(assessment_ids) & set(self.assessments):
            raise CFERPError("duplicate assessment IDs in result")

    def _settle_source_worker(self, source_work_id: str | None) -> None:
        if not source_work_id or source_work_id not in self.lead.work:
            return
        source_item = self.lead.work[source_work_id]
        if source_item.state in {JobState.COMPLETE, JobState.FAILED, JobState.STALE, JobState.SUPERSEDED}:
            return
        for aid, assignment in self.assignments.items():
            if assignment.role != Role.ASSESSOR or assignment.context.get("source_work_item_id") != source_work_id:
                continue
            if self.lead.work[aid].state in {JobState.QUEUED, JobState.RUNNING,
                    JobState.AWAITING_ASSESSOR, JobState.NEEDS_REVISION}:
                return
        linked_requests = [rid for rid, source in self.request_work_sources.items() if source == source_work_id]
        states = [self.lead.requests[rid].state for rid in linked_requests if rid in self.lead.requests]
        if any(state in {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                         RequestDisposition.PARTIALLY_ANSWERED, RequestDisposition.APPROVED,
                         RequestDisposition.READY_TO_SEND, RequestDisposition.DISPATCH_PENDING,
                         RequestDisposition.WITHDRAWAL_PENDING, RequestDisposition.ASSESSOR_REVIEW,
                         RequestDisposition.REVISION, RequestDisposition.PROPOSED} for state in states):
            return
        if source_item.state in {JobState.AWAITING_ASSESSOR, JobState.NEEDS_REVISION, JobState.RETURNED}:
            self.lead.transition_work(source_work_id, JobState.COMPLETE,
                                      result_ref=source_item.result_ref)

    def register_material(self, *, event_id: str, material: MaterialRecord) -> tuple[Assignment, ...]:
        """Register material for future searches and route only known impacts."""
        prior_assignment_ids = set(self.assignments)
        prior_event = self.lead.event(event_id)
        if prior_event is not None:
            event_payload = prior_event.payload
            if (prior_event.kind in {"material_registered", "material_revised", "duplicate_material_observed"}
                    and event_payload.get("material_id") == material.material_id
                    and event_payload.get("version") == material.version
                    and event_payload.get("content_hash") == material.content_hash):
                return ()
            raise CFERPError("event_id reused with different material content or event type")
        prior = self.materials.get(material.material_id)
        if prior and prior.version == material.version and prior.content_hash == material.content_hash:
            self._event(event_id, "duplicate_material_observed", {"material_id": material.material_id,
                         "version": material.version, "content_hash": material.content_hash})
            return ()
        material = self._match_material_scope(material)
        if not material.provenance_complete and not material.related_need_ids:
            open_need_ids = tuple(n.need_id for n in self.lead.needs.values() if n.state not in {
                NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL, NeedState.SUPERSEDED, NeedState.REJECTED
            })
            material = replace(material, related_need_ids=open_need_ids)
            if not open_need_ids:
                active_claims = tuple(dict.fromkeys(
                    claim_id for branch in self.branches.values() if branch.state == BranchState.ACTIVE
                    for claim_id in branch.claim_ids
                ))
                material = replace(material, related_claim_ids=tuple(dict.fromkeys(
                    (*material.related_claim_ids, *active_claims))))
        unknown_needs = set(material.related_need_ids) - set(self.lead.needs)
        unknown_claims = set(material.related_claim_ids) - set(self.claims)
        if unknown_needs or unknown_claims:
            raise CFERPError(f"Intake material has unknown references: needs={sorted(unknown_needs)}, claims={sorted(unknown_claims)}")
        self.lead.ingest_event(event_id, "material_revised" if prior else "material_registered", {
            "material_id": material.material_id, "version": material.version,
            "content_hash": material.content_hash,
            "material_index_version": f"materials:{len(self.materials) + (1 if prior is None else 0)}:{material.version}",
            "changed_dependency_ids": (material.material_id,),
            # A brand-new document changes no input of existing work: no job depends on
            # it yet, and it is checked against every open need by the searches queued
            # below. Only a revision of known material can invalidate work broadly.
            "provenance_complete": material.provenance_complete if prior is not None else True,
        })
        # Commit the catalog only after the event ledger accepted the event.
        # A replay conflict therefore cannot leave a catalog/version split.
        self.materials[material.material_id] = deepcopy(material)
        affected = []
        # Reassess existing judgments only when the revised material is the
        # material those judgments used. New documents go through EW retrieval
        # first so HERA gets precise candidate passages.
        if prior is not None:
            for assessment in tuple(self.assessments.values()):
                if assessment.material_id == material.material_id and assessment.status == "current":
                    self.reassessment_queue.add((assessment.assessment_id, assessment.claim_id, material.material_id))
                    affected.append(assessment.claim_id)
        for claim_id in material.related_claim_ids:
            if claim_id in self.claims:
                affected.append(claim_id)
        assignments = []
        for need in self.lead.needs.values():
            if need.state in {NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL, NeedState.SUPERSEDED, NeedState.REJECTED}:
                continue
            # New material is visible in every subsequent assignment. Rerun only
            # needs linked by Intake metadata or work already invalidated.
            was_invalidated = any(
                need.need_id in self.lead.work[wid].need_ids for wid in self.lead.last_event_affected_work_ids
            )
            if was_invalidated:
                # A stale queued assignment is refreshed below; an in-flight
                # call keeps its slot and is refreshed when its stale result returns.
                continue
            if need.need_id in material.related_need_ids:
                already_queued = any(
                    item.role == Role.EVIDENCE_WORKER and need.need_id in item.need_ids
                    and item.state in {JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                                       JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL}
                    and self.assignments[item.work_id].manifest == self.lead.manifest()
                    for item in self.lead.work.values() if item.work_id in self.assignments
                )
                if already_queued:
                    continue
                if self._search_cap_reached(need, self._active_searches_per_claim()):
                    continue  # searched over the whole corpus once a slot on its claim frees
                assignments.append(self._assignment(
                    role=Role.EVIDENCE_WORKER, owner_id=f"ew-pair:{need.need_id}",
                    purpose="search newly registered material for the open need",
                    target_ids=need.target_ids, need_ids=(need.need_id,),
                    dependencies=tuple((*need.target_ids, need.need_id, f"{material.material_id}:{material.version}")),
                    context={"need": need, "new_material_id": material.material_id,
                             "material_catalog_snapshot": self.lead.manifest()}, priority_tier=2,
                ))
        for claim_id in dict.fromkeys(affected):
            prior_ids = tuple(aid for aid, cid, mid in self.reassessment_queue
                              if cid == claim_id and mid == material.material_id)
            if not prior_ids:
                # New material can be searched for a known relevant claim, but
                # does not receive a direct evidence verdict from the Lead.
                related_need = next((n for n in self.lead.needs.values()
                                     if claim_id in n.target_ids and n.state not in {
                                         NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL,
                                         NeedState.SUPERSEDED, NeedState.REJECTED}), None)
                if related_need:
                    continue
                need_id = f"need:material:{material.material_id}:{claim_id}"
                if need_id not in self.lead.needs:
                    self.lead.add_need(Need(need_id, "material_arrival", material.material_id,
                        (claim_id,), (InformationSlot(f"{need_id}:passages",
                            f"Find passages in {material.title or material.material_id} relevant to {self.claims[claim_id].text}",
                            entity_id=None),), source_scope=(material.material_id,)))
                continue
            assignments.append(self._assignment(
                role=Role.ASSESSOR, owner_id="lead-routed",
                purpose="reassess prior claim–material judgments against a revised source version",
                target_ids=(claim_id,), need_ids=material.related_need_ids,
                dependencies=(claim_id, f"{material.material_id}:{material.version}"),
                context={"task_kind": "reassessment_triage", "material": material,
                         "prior_assessment_ids": prior_ids,
                         "prior_assessments": tuple(self.assessments[aid] for aid in prior_ids)},
                priority_tier=1,
            ))
        self._queue_available()
        return tuple(self.assignments[aid] for aid in self.assignments if aid not in prior_assignment_ids)

    def _match_material_scope(self, material: MaterialRecord) -> MaterialRecord:
        """Use optional semantic matching to nominate, never judge, affected work."""
        if self.semantic_assistant is None or material.related_need_ids or material.related_claim_ids:
            return material
        expected_manifest = self.lead.manifest()
        candidates = []
        for need in self.lead.needs.values():
            if need.state not in {NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL,
                                  NeedState.SUPERSEDED, NeedState.REJECTED}:
                candidates.append({"id": f"need:{need.need_id}", "text": " ".join(
                    [slot.description for slot in need.slots])})
        for claim in self.claims.values():
            branch = self.branches.get(claim.branch_id)
            if branch and branch.state == BranchState.ACTIVE:
                candidates.append({"id": f"claim:{claim.claim_id}", "text": claim.text})
        if not candidates:
            return material
        record = {"id": material.material_id, "title": material.title,
                  "source_kind": material.source_kind, "metadata": material.metadata}
        matches = self.suggest_semantic_matches(kind="material_scope", candidate=record,
                                                existing=candidates,
                                                expected_manifest=expected_manifest)
        need_ids = tuple(mid.removeprefix("need:") for mid in matches if mid.startswith("need:"))
        claim_ids = tuple(mid.removeprefix("claim:") for mid in matches if mid.startswith("claim:"))
        return replace(material, related_need_ids=need_ids, related_claim_ids=claim_ids)

    def register_external_response(self, *, event_id: str, request_id: str,
                                   material: MaterialRecord,
                                   answered_slot_ids: Iterable[str] = ()) -> tuple[Assignment, ...]:
        if request_id not in self.lead.requests:
            raise CFERPError("external response references unknown request")
        request = self.lead.requests[request_id]
        material = MaterialRecord(
            material.material_id, material.version, material.content_hash, material.title,
            material.source_kind, material.readiness, material.searchable_ref, material.lineage,
            material.provenance_complete, tuple(dict.fromkeys((*material.related_claim_ids, *request.target_ids))),
            tuple(dict.fromkeys((*material.related_need_ids, *(x for x in request.origin_ids if x in self.lead.needs)))),
            material.metadata, material.content,
        )
        created = list(self.register_material(event_id=event_id, material=material))
        answered = tuple(set(answered_slot_ids) & set(request.slot_ids))
        response_ids = self.request_responses.setdefault(request_id, [])
        if material.material_id not in response_ids:
            response_ids.append(material.material_id)
        self.request_response_slot_hints.setdefault(request_id, {})[material.material_id] = answered
        # A response can be partial or misleading. The Lead records receipt;
        # the Worker searches it and the Assessor judges the result before any
        # need slot or request is marked answered.
        self.lead.record_external_response(request_id, material.material_id, allow_late=True)
        for need_id in (n for n in request.origin_ids if n in self.lead.needs):
            source_work_id = self.request_work_sources.get(request_id)
            if source_work_id and self.lead.work[source_work_id].state == JobState.WAITING_EXTERNAL:
                self.lead.transition_work(source_work_id, JobState.COMPLETE, result_ref=material.material_id)
        # The response's content is not accepted as resolving a need until the
        # Evidence Worker and Assessor have processed it.
        created.extend(self._queue_available())
        unique = {assignment.assignment_id: assignment for assignment in created}
        return tuple(unique.values())

    def _queue_available(self) -> tuple[Assignment, ...]:
        before = set(self.assignments)
        already_reissued = {a.context.get("reissued_from") for a in self.assignments.values()
                            if a.context.get("reissued_from")}
        searching = self._active_searches_per_claim()
        held_need_ids: set[str] = set()
        for work_id, item in tuple(self.lead.work.items()):
            if (item.state != JobState.STALE or self.lead.is_executing(work_id)
                    or work_id in already_reissued):
                continue
            assignment = self.assignments.get(work_id)
            if assignment is None:
                continue
            if assignment.role == Role.EVIDENCE_WORKER:
                if self._search_cap_reached_for(assignment.target_ids, searching):
                    held_need_ids.update(assignment.need_ids)  # reissued once a slot on its claim frees
                    continue
                if self._requeue_stale_assignment(assignment):
                    for target in assignment.target_ids:
                        searching[target] = searching.get(target, 0) + 1
                continue
            self._requeue_stale_assignment(assignment)
        active_need_ids = held_need_ids | {
            need_id for item in self.lead.work.values()
            if item.role == Role.EVIDENCE_WORKER and item.state in {
                JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
            }
            for need_id in item.need_ids
        }
        searching = self._active_searches_per_claim()
        for need in self.lead.needs.values():
            if need.state in {NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL, NeedState.SUPERSEDED, NeedState.REJECTED}:
                continue
            known_targets = [target for target in need.target_ids if target in self.claims]
            if known_targets and not any(
                self.branches.get(self.claims[target].branch_id) is None
                or self.branches[self.claims[target].branch_id].state == BranchState.ACTIVE
                for target in known_targets
            ):
                continue
            open_slots = tuple(slot.slot_id for slot in need.slots if slot.state in {SlotState.OPEN, SlotState.IN_PROCESS})
            if not open_slots or need.need_id in active_need_ids:
                continue
            if self.need_last_search.get(need.need_id) == (self.lead.manifest().material_index_version, need.version):
                continue
            if self._search_cap_reached(need, searching):
                continue  # queued once a search on the same claim settles
            source_assignment = self._find_reusable_need_assignment(need)
            if source_assignment is not None:
                source_need_id = source_assignment.need_ids[0]
                if source_need_id in self.need_packets and self._reuse_need_packet(source_need_id, need.need_id):
                    continue
                source_state = self.lead.work[source_assignment.assignment_id].state
                if source_state in {JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                                    JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL}:
                    self.pending_need_reuse[need.need_id] = source_need_id
                    continue
            self._assignment(
                role=Role.EVIDENCE_WORKER, owner_id=f"ew-pair:{need.need_id}",
                purpose="search the current registered corpus for this information need",
                target_ids=need.target_ids, need_ids=(need.need_id,),
                dependencies=tuple((*need.target_ids, f"need:{need.need_id}:v{need.version}",
                                    *self._material_dependencies(need.source_scope))),
                context={"need": need, "open_slot_ids": open_slots,
                         "material_catalog_snapshot": self.lead.manifest(),
                         "source_catalog": tuple(self.materials.values())},
                pair_id=f"pair:{need.need_id}", priority_tier=3,
            )
            for target in need.target_ids:
                searching[target] = searching.get(target, 0) + 1
        return tuple(self.assignments[aid] for aid in self.assignments.keys() - before)

    # Searches queued or running at once for any one claim. Further needs on that
    # claim wait their turn, so the job budget also reaches the Assessor.
    MAX_ACTIVE_SEARCHES_PER_CLAIM = 2

    def _active_searches_per_claim(self, excluding: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.lead.work.values():
            if item.work_id != excluding and item.role == Role.EVIDENCE_WORKER and (
                    item.state in {JobState.QUEUED, JobState.RUNNING}
                    or (item.state == JobState.STALE and self.lead.is_executing(item.work_id))):
                for target in item.target_ids:
                    counts[target] = counts.get(target, 0) + 1
        return counts

    def _search_cap_reached(self, need: Need, searching: dict[str, int]) -> bool:
        return self._search_cap_reached_for(need.target_ids, searching)

    def _search_cap_reached_for(self, target_ids: Iterable[str], searching: dict[str, int]) -> bool:
        return any(searching.get(t, 0) >= self.MAX_ACTIVE_SEARCHES_PER_CLAIM for t in target_ids)

    def _need_search_compatible(self, left: Need, right: Need,
                                left_manifest: VersionManifest,
                                right_manifest: VersionManifest) -> bool:
        same_search_snapshot = (
            left_manifest.case_id == right_manifest.case_id
            and left_manifest.material_index_version == right_manifest.material_index_version
            and left_manifest.source_versions == right_manifest.source_versions
        )
        if (not same_search_snapshot or left.target_ids != right.target_ids
                or left.source_scope != right.source_scope):
            return False
        def signature(need: Need):
            return tuple(sorted((slot.slot_id, slot.description, slot.entity_id,
                                 slot.time_scope, slot.record_type,
                                 tuple(sorted(slot.required_fields))) for slot in need.slots))
        return signature(left) == signature(right)

    def _find_reusable_need_assignment(self, target: Need) -> Assignment | None:
        for assignment in self.assignments.values():
            if assignment.role != Role.EVIDENCE_WORKER or len(assignment.need_ids) != 1:
                continue
            source_need_id = assignment.need_ids[0]
            if source_need_id == target.need_id or source_need_id not in self.lead.needs:
                continue
            source_need = self.lead.needs[source_need_id]
            if self._need_search_compatible(source_need, target, assignment.manifest,
                                             self.lead.manifest()):
                return assignment
        return None

    def _reuse_need_packet(self, source_need_id: str, target_need_id: str) -> bool:
        packet = self.need_packets.get(source_need_id)
        target = self.lead.needs.get(target_need_id)
        source = self.lead.needs.get(source_need_id)
        if packet is None or target is None or source is None:
            return False
        source_assignment = next((a for a in self.assignments.values()
                                  if a.role == Role.EVIDENCE_WORKER and a.need_ids == (source_need_id,)), None)
        target_assignment = next((a for a in self.assignments.values()
                                  if a.role == Role.EVIDENCE_WORKER and a.need_ids == (target_need_id,)), None)
        if source_assignment is None or target_assignment is not None:
            return False
        if not self._need_search_compatible(source, target, source_assignment.manifest, self.lead.manifest()):
            return False
        if (tuple(sorted(packet.target_ids)) != tuple(sorted(target.target_ids))
                or tuple(sorted(packet.covered_slot_ids)) != tuple(sorted(slot.slot_id for slot in target.slots))
                or tuple(sorted(packet.source_scope)) != tuple(sorted(target.source_scope))
                or packet.searched_material_index_version != self.lead.material_index_version
                or tuple(sorted(packet.source_versions)) != tuple(sorted(source_assignment.manifest.source_versions))):
            return False
        expected_entities = tuple(sorted({slot.entity_id for slot in target.slots if slot.entity_id}))
        expected_times = {slot.time_scope for slot in target.slots if slot.time_scope}
        expected_records = tuple(sorted({slot.record_type for slot in target.slots if slot.record_type}))
        expected_time = next(iter(expected_times)) if len(expected_times) == 1 else None
        if (tuple(sorted(packet.entity_ids)) != expected_entities
                or packet.time_scope != expected_time
                or tuple(sorted(packet.record_types)) != expected_records):
            return False
        source_payload = packet.result_payload if isinstance(packet.result_payload, dict) else {}
        if not source_payload.get("candidate_links"):
            return False
        packet_id = self._id("packet-reuse")
        payload = deepcopy(packet.result_payload)
        if isinstance(payload, dict):
            links = []
            for link in payload.get("candidate_links", ()):
                cloned_link = deepcopy(link)
                cloned_link["need_ids"] = (target_need_id,)
                links.append(cloned_link)
            payload["candidate_links"] = links
            payload["reused_for_need_id"] = target_need_id
        clone = replace(packet, packet_id=packet_id, request_id=f"need:{target_need_id}",
                        result_payload=payload, slot_payloads=deepcopy(packet.slot_payloads),
                        parent_packet_id=packet.packet_id)
        self.need_packets[target_need_id] = clone
        self.evidence_packets[packet_id] = clone
        reused = self._assignment(
            role=Role.EVIDENCE_WORKER, owner_id=f"ew-pair:{target_need_id}",
            purpose="reuse an exact compatible search result while preserving this need's identity",
            target_ids=target.target_ids, need_ids=(target_need_id,),
            dependencies=tuple((*target.target_ids, f"need:{target_need_id}:v{target.version}",
                                *(f"{sid}:{ver}" for sid, ver, _ in clone.source_versions))),
            context={"reused_packet_id": clone.packet_id,
                     "copied_from_need_id": source_need_id,
                     "copied_from_packet_id": packet.packet_id,
                     "need": target}, pair_id=f"pair:{target_need_id}", priority_tier=2,
        )
        self.lead.start_work(reused.assignment_id)
        self.lead.finish_work(reused.assignment_id, state=JobState.AWAITING_ASSESSOR,
                              result_ref=clone.packet_id)
        payload_obj = clone.result_payload if isinstance(clone.result_payload, dict) else {}
        for link in payload_obj.get("candidate_links", ()):
            self._validate_material_link(link)
            claim_id, material_id = str(link["claim_id"]), str(link["material_id"])
            self._assignment(
                role=Role.ASSESSOR, owner_id=f"assessor-pair:{reused.owner_id}",
                purpose="assess a reused passage for this distinct information need",
                target_ids=(claim_id,), need_ids=(target_need_id,),
                dependencies=(claim_id, f"{material_id}:{link['material_version']}"),
                context={"task_kind": "evidence_review", "candidate_link": deepcopy(link),
                         "packet_id": clone.packet_id, "source_work_item_id": reused.assignment_id},
                pair_id=reused.owner_id, priority_tier=1,
            )
        return True

    def suggest_semantic_matches(self, *, kind: str, candidate: dict[str, Any],
                                 existing: Iterable[dict[str, Any]],
                                 expected_manifest: VersionManifest | None = None) -> tuple[str, ...]:
        if self.semantic_assistant is None:
            return ()
        existing = tuple(deepcopy(tuple(existing)))
        manifest = expected_manifest or self.lead.manifest()
        try:
            raw_matches = self.semantic_assistant.suggest_matches(kind, deepcopy(candidate), existing)
        except Exception as exc:
            self.semantic_diagnostics.append(f"semantic_match_failed:{type(exc).__name__}")
            return ()
        if self.lead.manifest() != manifest:
            self.semantic_diagnostics.append("semantic_match_stale_snapshot")
            return ()
        if (not isinstance(raw_matches, (tuple, list))
                or not all(isinstance(item, str) for item in raw_matches)):
            self.semantic_diagnostics.append("semantic_match_malformed_response")
            return ()
        matches = tuple(dict.fromkeys(raw_matches))
        allowed = {str(row.get("id")) for row in existing if row.get("id") is not None}
        if set(matches) - allowed:
            self.semantic_diagnostics.append("semantic_match_out_of_scope_ids")
            return ()
        self.match_suggestions[self._fingerprint_dict(kind, candidate)] = matches
        return matches

    @staticmethod
    def _fingerprint_dict(kind: str, payload: dict[str, Any]) -> str:
        return sha256(json.dumps({"kind": kind, "payload": payload}, sort_keys=True, default=str).encode()).hexdigest()

    def apply_branch_decision(self, branch_id: str, state: BranchState, *, reason: str,
                              related_branch_ids: Iterable[str] = ()) -> BranchTransition:
        if branch_id not in self.branches:
            raise CFERPError("unknown branch")
        if not reason.strip():
            raise CFERPError("branch transition requires a reason")
        branch = self.branches[branch_id]
        transition = BranchTransition(self._id("branch-transition"), branch_id, branch.state,
                                       state, reason, tuple(related_branch_ids), self.lead.board_version + 1)
        self.branches[branch_id] = Branch(branch.branch_id, branch.claim_ids, state,
                                          branch.parent_branch_ids, reason, branch.revision + 1)
        self.branch_history.append(transition)
        changed = tuple((*branch.claim_ids, f"branch:{branch_id}"))
        self._event(transition.transition_id, "board_changed", {
            "changed_dependency_ids": changed, "reason": reason,
        })
        branch_claims = set(branch.claim_ids)
        if state == BranchState.ACTIVE:
            for need in tuple(self.lead.needs.values()):
                if not need.target_ids or not set(need.target_ids).issubset(branch_claims):
                    continue
                reopen = tuple(slot.slot_id for slot in need.slots if slot.state == SlotState.SUPERSEDED)
                if reopen:
                    self.lead.reopen_need_slots(need.need_id, reopen,
                                                reason=f"branch {branch_id} reactivated: {reason}")
        else:
            for need in tuple(self.lead.needs.values()):
                if not need.target_ids or not set(need.target_ids).issubset(branch_claims):
                    continue
                also_active = any(
                    claim_id in self.claims
                    and self.claims[claim_id].branch_id != branch_id
                    and self.branches.get(self.claims[claim_id].branch_id) is not None
                    and self.branches[self.claims[claim_id].branch_id].state == BranchState.ACTIVE
                    for claim_id in need.target_ids
                )
                if not also_active:
                    updates = {slot.slot_id: (SlotState.SUPERSEDED, ()) for slot in need.slots
                               if slot.state in {SlotState.OPEN, SlotState.IN_PROCESS}}
                    if updates:
                        self.lead.update_need_slots(need.need_id, updates)
            for request_id, request in tuple(self.lead.requests.items()):
                if not request.target_ids or not set(request.target_ids).issubset(branch_claims):
                    continue
                shared_active = any(
                    claim_id in self.claims
                    and self.claims[claim_id].branch_id != branch_id
                    and self.branches.get(self.claims[claim_id].branch_id) is not None
                    and self.branches[self.claims[claim_id].branch_id].state == BranchState.ACTIVE
                    for claim_id in request.target_ids
                )
                if shared_active:
                    continue
                if request.state in {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                                     RequestDisposition.PARTIALLY_ANSWERED, RequestDisposition.DISPATCH_PENDING,
                                     RequestDisposition.WITHDRAWAL_PENDING}:
                    if request.state != RequestDisposition.WITHDRAWAL_PENDING:
                        self.lead.submit_dispatch(request_id, "withdraw")
                else:
                    self.lead.supersede_unsent_request(request_id,
                        reason=f"target branch {branch_id} became {state.value}: {reason}")
        # Work shared with another active branch remains eligible. Only work
        # explicitly dependent solely on this branch's claims is invalidated.
        if state != BranchState.ACTIVE:
            for wid, item in tuple(self.lead.work.items()):
                if item.state not in {JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                                      JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL, JobState.STALE}:
                    continue
                deps = set(item.dependency_ids) | set(item.target_ids)
                branch_deps = {cid for cid in deps if cid in self.claims and self.claims[cid].branch_id == branch_id}
                other_active = {cid for cid in deps if cid in self.claims
                                and self.branches.get(self.claims[cid].branch_id) is not None
                                and self.branches[self.claims[cid].branch_id].state == BranchState.ACTIVE
                                and self.claims[cid].branch_id != branch_id}
                if branch_deps and not other_active:
                    if item.state == JobState.RUNNING or wid in self.lead._executing_work_ids:
                        continue  # preserve the live slot; discard its stale result on return
                    else:
                        self.lead.transition_work(wid, JobState.SUPERSEDED,
                            result_ref=item.result_ref,
                            reason=f"branch {branch_id} became {state.value}: {reason}")
        self._queue_available()
        return transition

    def record_similarity_link(self, *, kind: str, record_ids: Iterable[str], rationale: str,
                               reuse_packet_id: str | None = None) -> dict[str, Any]:
        """Record a Lead-approved similarity link without collapsing identities.

        For overlapping outward requests, the only reuse permitted is an exact
        compatible packet copy. Request IDs, wording, origins, and histories
        always remain separate.
        """
        record_ids = tuple(dict.fromkeys(record_ids))
        if len(record_ids) < 2 or not rationale.strip():
            raise CFERPError("similarity link requires at least two IDs and a rationale")
        if kind in {"request", "outward_request"}:
            if set(record_ids) - set(self.lead.requests):
                raise CFERPError("similarity link references an unknown outward request")
        link = {"kind": kind, "record_ids": record_ids, "rationale": rationale,
                "reuse_packet_id": reuse_packet_id}
        self.similarity_links.append(link)
        self._event(self._id("similarity"), "semantic_similarity_linked", link)
        return deepcopy(link)

    def reuse_search_packet(self, *, source_packet_id: str, target_request_id: str,
                            new_packet_id: str) -> tuple[EvidencePacket, Assignment, tuple[Assignment, ...]]:
        """Copy A's compatible EW packet for A′ and give A′ its own review path."""
        source_packet = self.lead.packets[source_packet_id]
        request = self.lead.requests[target_request_id]
        current_manifest = self.lead.manifest()
        if (source_packet.searched_material_index_version != current_manifest.material_index_version
                or request.material_index_version != current_manifest.material_index_version):
            raise CFERPError("packet cannot be reused after the material index changed; run a fresh search")
        current_sources = {source_id: (version, content_hash)
                           for source_id, version, content_hash in current_manifest.source_versions}
        stale_sources = [source_id for source_id, version, content_hash in source_packet.source_versions
                         if current_sources.get(source_id) != (version, content_hash)]
        if stale_sources:
            raise CFERPError("packet cannot be reused after source revisions: " + ", ".join(stale_sources))
        source_links = self._candidate_links_from_packet(source_packet)
        for link in source_links:
            self._validate_material_link(link)
        packet = self.lead.clone_packet_for_request(source_packet_id, target_request_id,
                                                   new_packet_id=new_packet_id)
        self.evidence_packets[new_packet_id] = packet
        request = self.lead.requests[target_request_id]
        need_ids = tuple(x for x in request.origin_ids if x in self.lead.needs)
        ew_assignment = self._assignment(
            role=Role.EVIDENCE_WORKER, owner_id=f"ew-pair:{target_request_id}",
            purpose="return a compatible reused search packet for this distinct request",
            target_ids=request.target_ids, need_ids=need_ids,
            dependencies=tuple((*request.target_ids, *request.origin_ids,
                                *(f"{sid}:{ver}" for sid, ver, _ in packet.source_versions))),
            context={"reused_packet_id": new_packet_id, "copied_from_packet_id": source_packet_id,
                     "request_id": target_request_id}, pair_id=f"pair:{target_request_id}", priority_tier=2,
        )
        self.lead.start_work(ew_assignment.assignment_id)
        self.lead.finish_work(ew_assignment.assignment_id, state=JobState.AWAITING_ASSESSOR,
                              result_ref=new_packet_id)
        self.request_work_sources[target_request_id] = ew_assignment.assignment_id
        reviews = []
        for raw_link in self._candidate_links_from_packet(packet):
            link = deepcopy(raw_link)
            if need_ids:
                link["need_ids"] = need_ids
            self._validate_material_link(link)
            claim_id, material_id = str(link["claim_id"]), str(link["material_id"])
            reviews.append(self._assignment(
                role=Role.ASSESSOR, owner_id=f"assessor-pair:{ew_assignment.owner_id}",
                purpose="assess a reused passage for this request's claim–material relation",
                target_ids=(claim_id,), need_ids=need_ids,
                dependencies=(claim_id, f"{material_id}:{link['material_version']}"),
                context={"task_kind": "evidence_review", "candidate_link": deepcopy(link),
                         "packet_id": new_packet_id, "source_work_item_id": ew_assignment.assignment_id},
                pair_id=ew_assignment.owner_id, priority_tier=1,
            ))
        reviews.append(self._assignment(
            role=Role.ASSESSOR, owner_id=f"assessor-pair:{ew_assignment.owner_id}",
            purpose="review the reused search result and proposed request wording for this request",
            target_ids=request.target_ids, need_ids=need_ids,
            dependencies=tuple((*request.target_ids, *request.origin_ids)),
            context={"task_kind": "request_review", "request": request,
                     "packet": packet, "source_work_item_id": ew_assignment.assignment_id},
            pair_id=ew_assignment.owner_id, priority_tier=2,
        ))
        return packet, ew_assignment, tuple(reviews)

    def refine_ambiguous_assignment(self, assignment_id: str) -> Assignment:
        """Ask the optional LLM port to refine an unclear assignment in-bounds."""
        if self.semantic_assistant is None:
            raise CFERPError("no semantic assistant is configured")
        assignment = self.assignments[assignment_id]
        if not self._current(assignment.manifest):
            raise CFERPError("cannot refine an assignment based on a stale snapshot")
        if self.lead.work[assignment_id].state != JobState.QUEUED:
            raise CFERPError("only queued assignments can be refined")
        try:
            suggestion = self.semantic_assistant.clarify_assignment(deepcopy(assignment))
        except Exception as exc:
            self.semantic_diagnostics.append(f"assignment_refinement_failed:{type(exc).__name__}")
            return assignment
        if not self._current(assignment.manifest):
            raise CFERPError("case snapshot changed while the semantic assistant was refining the assignment")
        if self.lead.work[assignment_id].state != JobState.QUEUED:
            raise CFERPError("assignment is no longer queued after semantic refinement")
        if not isinstance(suggestion, dict):
            raise CFERPError("semantic helper response must be an object")
        allowed_fields = {"purpose", "target_ids", "need_ids", "context_additions"}
        if set(suggestion) - allowed_fields:
            raise CFERPError("semantic helper returned unsupported assignment fields")
        raw_targets = suggestion.get("target_ids", assignment.target_ids)
        raw_needs = suggestion.get("need_ids", assignment.need_ids)
        if (not isinstance(raw_targets, (tuple, list)) or not all(isinstance(x, str) for x in raw_targets)
                or not isinstance(raw_needs, (tuple, list)) or not all(isinstance(x, str) for x in raw_needs)):
            raise CFERPError("semantic helper target_ids and need_ids must be lists of IDs")
        targets = tuple(dict.fromkeys(raw_targets))
        needs = tuple(dict.fromkeys(raw_needs))
        if set(targets) - set(assignment.target_ids) or set(needs) - set(assignment.need_ids):
            raise CFERPError("semantic helper cannot expand assignment targets or needs")
        if (assignment.target_ids or assignment.need_ids) and not (targets or needs):
            raise CFERPError("semantic helper cannot remove all assignment targets and needs")
        purpose = suggestion.get("purpose", assignment.purpose)
        if not isinstance(purpose, str) or not purpose.strip():
            raise CFERPError("semantic helper purpose must be non-empty text")
        additions = suggestion.get("context_additions", {})
        if not isinstance(additions, dict) or set(additions) - {"routing_note"}:
            raise CFERPError("semantic helper context additions may contain only routing_note")
        if "routing_note" in additions and not isinstance(additions["routing_note"], str):
            raise CFERPError("semantic helper routing_note must be text")
        context = deepcopy(assignment.context)
        context.update(deepcopy(additions))
        refined = self._assignment(
            role=assignment.role, owner_id=assignment.owner_id,
            purpose=purpose,
            target_ids=targets, need_ids=needs, dependencies=assignment.dependencies,
            context={**context, "refined_from": assignment_id}, budget=assignment.budget,
            pair_id=assignment.pair_id,
            priority_tier=self.lead.work[assignment_id].priority_tier,
        )
        self.lead.transition_work(assignment_id, JobState.SUPERSEDED,
                                 reason=f"replaced by refined assignment {refined.assignment_id}")
        return refined

    def _requeue_stale_assignment(self, assignment: Assignment) -> tuple[Assignment, ...]:
        """Retain a stale result, then issue a fresh assignment at current versions."""
        known_targets = [target for target in assignment.target_ids if target in self.claims]
        if known_targets and not any(
            self.branches.get(self.claims[target].branch_id) is None
            or self.branches[self.claims[target].branch_id].state == BranchState.ACTIVE
            for target in known_targets
        ):
            return ()
        if assignment.role == Role.ASSESSOR and assignment.context.get("task_kind") == "request_review":
            purpose = "re-review the request against the current case snapshot"
        elif assignment.role == Role.ASSESSOR:
            purpose = "reassess the claim–material relationship against current versions"
        elif assignment.role == Role.SPECIALIST:
            purpose = assignment.purpose
        else:
            purpose = assignment.purpose
        context = {**deepcopy(assignment.context), "reissued_from": assignment.assignment_id,
                   "prior_stale_manifest": assignment.manifest}
        dependencies = assignment.dependencies
        if assignment.role == Role.SPECIALIST:
            context["source_catalog"] = tuple(self.materials.values())
            dependencies = tuple(dict.fromkeys((*assignment.target_ids, *self._material_dependencies(()))))
        elif assignment.role == Role.EVIDENCE_WORKER:
            context["source_catalog"] = tuple(self.materials.values())
            context["material_catalog_snapshot"] = self.lead.manifest()
            current_needs = tuple(self.lead.needs[nid] for nid in assignment.need_ids if nid in self.lead.needs)
            if len(current_needs) == 1:
                context["need"] = current_needs[0]
            elif current_needs:
                context["needs"] = current_needs
            dependencies = tuple(dict.fromkeys((
                *assignment.target_ids, *assignment.need_ids,
                *(f"need:{need.need_id}:v{need.version}" for need in current_needs),
                *(dep for need in current_needs for dep in self._material_dependencies(need.source_scope)),
            )))
        fresh = self._assignment(
            role=assignment.role, owner_id=assignment.owner_id, purpose=purpose,
            target_ids=assignment.target_ids, need_ids=assignment.need_ids,
            dependencies=dependencies, context=context,
            budget=assignment.budget, pair_id=assignment.pair_id,
            priority_tier=1 if assignment.role == Role.ASSESSOR else 2,
        )
        return (fresh,)

    def _mark_assignment_stale(self, assignment_id: str, result_id: str) -> None:
        item = self.lead.work[assignment_id]
        if item.state == JobState.RUNNING:
            self.lead.finish_work(assignment_id, state=JobState.STALE, result_ref=result_id)
        elif item.state != JobState.STALE:
            self.lead.transition_work(assignment_id, JobState.STALE,
                                      result_ref=result_id, reason="result was based on an old snapshot")

    def workflow_actions(self) -> tuple[WorkflowAction, ...]:
        return tuple(WorkflowAction(
            item.work_id, item.role, item.owner_id, self.assignments[item.work_id].purpose,
            item.target_ids, item.need_ids, item.dependency_ids, item.manifest or self.lead.manifest(),
            item.priority_tier, self.assignments[item.work_id].pair_id,
            self.assignments[item.work_id].budget,
        ) for item in self.lead.work.values() if item.state == JobState.QUEUED)

    def schedule(self, *, ambiguous: bool = False, planner=None) -> tuple[Assignment, ...]:
        # A queued assignment has not called its worker yet, so it is safe to
        # reissue it against the latest board/material snapshot. The low-level
        # scheduler correctly refuses stale manifests; refresh them here so a
        # parallel result cannot strand otherwise-unaffected queued work.
        current_manifest = self.lead.manifest()
        refreshed = False
        for work_id, item in tuple(self.lead.work.items()):
            assignment = self.assignments.get(work_id)
            if (item.state != JobState.QUEUED or assignment is None
                    or assignment.manifest == current_manifest):
                continue
            try:
                self.lead.release_reservation(work_id)
            except CFERPError:
                # Most queued work has not been reserved yet. A missing
                # reservation is expected; other state changes are handled by
                # the transition below.
                pass
            self.lead.transition_work(
                work_id, JobState.STALE,
                reason="assignment snapshot changed before worker execution",
            )
            refreshed = True
        if refreshed:
            self._queue_available()
        actions = self.workflow_actions()
        selected = self.lead.schedule(tuple(CandidateAction(
            action.action_id, action.role, action.target_ids, action.need_ids,
            action.priority_tier, 1, action.dependencies,
            self.lead.work[action.action_id].created_sequence, action.manifest,
        ) for action in actions), planner=planner, ambiguous=ambiguous)
        return tuple(self.assignments[action.action_id] for action in selected)

    def start_assignment(self, assignment_id: str):
        return self.lead.start_work(assignment_id)

    def fail_assignment(self, assignment_id: str, reason: str) -> None:
        """End a running assignment whose role result was rejected, committing nothing.

        The job is FAILED and frees its slot; its output never reaches the board.
        If it was the last open Assessor job of a Worker pass, that pass settles
        as it would after a returned result. The claim or passage it covered
        stays unassessed, and the event log records why.
        """
        assignment = self.assignments[assignment_id]
        self.lead.finish_work(assignment_id, state=JobState.FAILED)
        self._event(f"assignment-failed:{assignment_id}", "assignment_failed", {
            "assignment_id": assignment_id, "role": assignment.role.value, "reason": reason})
        self._settle_source_worker(assignment.context.get("source_work_item_id"))

    def send_approved_request(self, request_id: str):
        """Lead authorizes an Assessor-passed request and hands it to Intake."""
        self.lead.queue_approved_request(request_id)
        action = self.lead.submit_dispatch(request_id, "send")
        return action

    def mark_request_reviewed_answer(self, request_id: str) -> OutwardRequest:
        """Lead closes a request after its response has passed Worker/Assessor review."""
        return self.lead.mark_request_answered(request_id)

    def acknowledge_request_dispatch(self, action_id: str, *, success: bool):
        action = self.lead.dispatch_actions[action_id]
        request = self.lead.acknowledge_dispatch(action_id, success=success)
        if action.action == "send" and success:
            if request.state == RequestDisposition.SENT:
                request = self.lead.mark_waiting_response(request.request_id)
            source_work_id = self.request_work_sources.get(request.request_id)
            if source_work_id and self.lead.work[source_work_id].state == JobState.AWAITING_ASSESSOR:
                self.lead.transition_work(source_work_id, JobState.WAITING_EXTERNAL,
                                          result_ref=action_id)
        elif action.action == "withdraw" and success and request.state == RequestDisposition.WITHDRAWN:
            source_work_id = self.request_work_sources.get(request.request_id)
            if source_work_id and self.lead.work[source_work_id].state == JobState.WAITING_EXTERNAL:
                self.lead.transition_work(source_work_id, JobState.SUPERSEDED,
                                          result_ref=action_id,
                                          reason="outward request was withdrawn")
        return request

    def resolve_need_slots(self, need_id: str,
                           slot_updates: dict[str, tuple[SlotState, tuple[str, ...]]]) -> Need:
        """Lead records explicit outcomes after role review; arrival alone is insufficient."""
        need = self.lead.update_need_slots(need_id, slot_updates)
        self._event(self._id("need-update"), "need_slots_updated", {
            "need_id": need_id, "need_version": need.version,
            "slot_updates": {sid: (state.value, refs) for sid, (state, refs) in slot_updates.items()},
        })
        return need

    def current_result(self) -> dict[str, Any]:
        pending_needs = tuple(n.need_id for n in self.lead.needs.values() if n.state not in {
            NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL, NeedState.REJECTED, NeedState.SUPERSEDED
        })
        active_work = tuple(w.work_id for w in self.lead.work.values() if w.state in {
            JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
            JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
        })
        pending_requests = tuple(r.request_id for r in self.lead.requests.values() if r.state in {
            RequestDisposition.PROPOSED, RequestDisposition.ASSESSOR_REVIEW,
            RequestDisposition.REVISION, RequestDisposition.APPROVED,
            RequestDisposition.READY_TO_SEND, RequestDisposition.DISPATCH_PENDING,
            RequestDisposition.SENT, RequestDisposition.WITHDRAWAL_PENDING,
            RequestDisposition.WAITING_RESPONSE, RequestDisposition.PARTIALLY_ANSWERED,
        })
        pending_external = any(self.lead.requests[rid].state in {
            RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
            RequestDisposition.PARTIALLY_ANSWERED,
        } for rid in pending_requests)
        if self.case_state == CaseState.CLOSED:
            state = CaseState.CLOSED
        elif not pending_needs and not active_work and not pending_requests:
            state = CaseState.READY_TO_CLOSE
        elif pending_external and not any(self.lead.work[wid].state in {
            JobState.QUEUED, JobState.RUNNING,
        } for wid in active_work):
            state = CaseState.WAITING_EXTERNAL
        else:
            state = CaseState.OPEN
        return {
            "case_id": self.case_id, "state": state.value,
            "case_snapshot_id": self.lead.case_snapshot_id,
            "board_version": self.lead.board_version,
            "branches": tuple(deepcopy(tuple(self.branches.values()))),
            "claims": tuple(deepcopy(tuple(self.claims.values()))),
            "causal_links": tuple(deepcopy(tuple(self.causal_links.values()))),
            "assessments": tuple(deepcopy(tuple(self.assessments.values()))),
            "open_need_ids": pending_needs, "active_work_ids": active_work,
            "open_request_ids": pending_requests,
            "current_result_ref": self.current_result_ref,
        }

    def close_case(self, *, result_ref: str) -> None:
        open_needs = [n.need_id for n in self.lead.needs.values() if n.state not in {
            NeedState.RESOLVED, NeedState.RESOLVED_BY_MATERIAL, NeedState.REJECTED, NeedState.SUPERSEDED
        }]
        active_work = [w.work_id for w in self.lead.work.values() if w.state in {
            JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
            JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
        }]
        open_requests = [r.request_id for r in self.lead.requests.values() if r.state in {
            RequestDisposition.PROPOSED, RequestDisposition.ASSESSOR_REVIEW,
            RequestDisposition.REVISION, RequestDisposition.APPROVED,
            RequestDisposition.READY_TO_SEND, RequestDisposition.DISPATCH_PENDING,
            RequestDisposition.SENT, RequestDisposition.WITHDRAWAL_PENDING,
            RequestDisposition.WAITING_RESPONSE, RequestDisposition.PARTIALLY_ANSWERED,
        }]
        if open_needs or active_work or open_requests:
            raise CFERPError("case cannot close with open needs, active work, or open requests")
        if not result_ref:
            raise CFERPError("closure requires a current-result reference")
        self.case_state = CaseState.CLOSED
        self.current_result_ref = result_ref
        self._event(self._id("case-closed"), "case_closed", {"result_ref": result_ref})


__all__ = [
    "AssessmentEffect", "AssessmentRecord", "Assignment", "Branch", "BranchState", "CausalLink",
    "BranchTransition", "CaseState", "Claim", "CFERPWorkflow", "LeadSemanticAssistant",
    "ClarificationRecord", "MaterialRecord", "RoleResult", "WorkflowAction",
]
