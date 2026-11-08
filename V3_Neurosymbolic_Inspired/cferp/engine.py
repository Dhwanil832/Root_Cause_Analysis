"""In-memory CFERP reference engine.

This is a deterministic orchestration core with an optional injected planner
port for ambiguous action ordering. Persistence and agent transports remain
ports for an archive adapter.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from types import MappingProxyType
from threading import RLock
from typing import Iterable

from .contracts import (
    CandidateAction, DispatchAction, InformationSlot, JobState, LeadEvent,
    Need, NeedState, OutwardRequest, RequestDisposition, Role, SlotState,
    VersionManifest, WorkItem,
)
from .planner import LeadPlanner, get_planner_decision


class CFERPError(ValueError):
    pass


def _stable_fingerprint(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


class CFERPLead:
    """Single-writer case ledger with idempotent event and dispatch handling."""

    def __init__(self, case_id: str, *, concurrency: dict[Role, int] | None = None,
                 global_concurrency: int = 8):
        if not case_id:
            raise CFERPError("case_id is required")
        self.case_id = case_id
        self.concurrency = concurrency or {
            Role.SPECIALIST: 3, Role.EVIDENCE_WORKER: 2, Role.ASSESSOR: 2,
        }
        self.global_concurrency = global_concurrency
        if global_concurrency < 1 or any(v < 0 for v in self.concurrency.values()):
            raise CFERPError("concurrency limits must be non-negative and global limit positive")
        self._events: list[LeadEvent] = []
        self._event_fingerprints: dict[str, str] = {}
        self._needs: dict[str, Need] = {}
        self._requests: dict[str, OutwardRequest] = {}
        self._packets: dict[str, object] = {}
        self._work: dict[str, WorkItem] = {}
        self._dispatch_actions: dict[str, DispatchAction] = {}
        self._dispatch_ack_records: dict[str, bool] = {}
        self._branch_history: list[dict] = []
        self.slot_history: dict[str, list[dict]] = {}
        self._scheduled_reservations: dict[str, Role] = {}
        self._reserved_action_details: dict[str, CandidateAction] = {}
        self._executing_work_ids: set[str] = set()
        self._action_first_seen: dict[str, int] = {}
        self._action_fingerprints: dict[str, str] = {}
        self._schedule_round = 0
        self._starvation_rounds = 5
        self.last_event_affected_work_ids: tuple[str, ...] = ()
        self.last_invalidated_action_ids: tuple[str, ...] = ()
        self.last_planner_called = False
        self.last_planner_accepted = False
        self.last_planner_diagnostics: tuple[str, ...] = ()
        self.case_snapshot_id = "case:0"
        self.board_version = 0
        self.material_index_version = "materials:0"
        self._latest_dependency_versions: dict[str, str] = {}
        self._latest_source_versions: dict[str, tuple[str, str]] = {}
        self._sequence = 0
        self._lock = RLock()

    @property
    def events(self) -> tuple[LeadEvent, ...]:
        """Return detached event copies so callers cannot mutate the log."""
        with self._lock:
            return tuple(deepcopy(self._events))

    def event(self, event_id: str) -> LeadEvent | None:
        """Return one detached event by stable ID, if it has been accepted."""
        with self._lock:
            event = next((item for item in self._events if item.event_id == event_id), None)
            return deepcopy(event) if event is not None else None

    @property
    def needs(self):
        with self._lock:
            return MappingProxyType(dict(self._needs))

    @property
    def requests(self):
        with self._lock:
            return MappingProxyType(dict(self._requests))

    @property
    def packets(self):
        with self._lock:
            return MappingProxyType(deepcopy(self._packets))

    @property
    def work(self):
        with self._lock:
            return MappingProxyType(dict(self._work))

    @property
    def dispatch_actions(self):
        with self._lock:
            return MappingProxyType(dict(self._dispatch_actions))

    @property
    def branch_history(self):
        with self._lock:
            return tuple(deepcopy(self._branch_history))

    def manifest(self, source_versions: Iterable[tuple[str, str, str]] | None = None) -> VersionManifest:
        if source_versions is None:
            source_versions = tuple((source_id, version, content_hash)
                                    for source_id, (version, content_hash) in self._latest_source_versions.items())
        return VersionManifest(self.case_id, self.case_snapshot_id, self.board_version,
                               self.material_index_version, tuple(sorted(source_versions)))

    def ingest_event(self, event_id: str, kind: str, payload: dict) -> LeadEvent:
        """Append once. Replayed IDs are no-ops; changed replay payloads fail."""
        if not event_id or not kind:
            raise CFERPError("event_id and kind are required")
        fp = _stable_fingerprint({"kind": kind, "payload": payload})
        with self._lock:
            prior = self._event_fingerprints.get(event_id)
            if prior is not None:
                if prior != fp:
                    raise CFERPError("event_id reused with different payload")
                return deepcopy(next(e for e in self._events if e.event_id == event_id))
            self._sequence += 1
            event = LeadEvent(event_id, kind, deepcopy(payload), self._sequence)
            self._events.append(event)
            self._event_fingerprints[event_id] = fp
            if kind in {"material_registered", "material_revised"}:
                self.material_index_version = str(payload.get("material_index_version", f"materials:{self._sequence}"))
                self.case_snapshot_id = str(payload.get("case_snapshot_id", f"case:{self._sequence}"))
                material_id = payload.get("material_id") or payload.get("source_id")
                material_version = payload.get("version") or payload.get("source_version")
                if material_id and material_version:
                    version_token = str(material_version)
                    self._latest_dependency_versions[str(material_id)] = version_token
                    content_hash = payload.get("content_hash") or payload.get("source_hash") or ""
                    self._latest_source_versions[str(material_id)] = (version_token, str(content_hash))
                changed_ids = payload.get("changed_dependency_ids")
                if changed_ids is None:
                    changed_ids = ()
                elif isinstance(changed_ids, str):
                    changed_ids = (changed_ids,)
                else:
                    changed_ids = tuple(changed_ids)
                if material_id:
                    changed_ids = tuple(dict.fromkeys((*changed_ids, str(material_id))))
                for dependency in changed_ids:
                    head, separator, tail = str(dependency).rpartition(":")
                    if separator:
                        self._latest_dependency_versions[head] = tail
                self.last_event_affected_work_ids = self.stale_dependents(
                    changed_ids, reason=f"{kind} changed the material snapshot",
                    provenance_complete=bool(payload.get("provenance_complete", bool(changed_ids))),
                )
            elif kind in {"case_initialized", "board_changed", "specialist_delta_committed", "assessor_annotation_committed"}:
                self.board_version += 1
                self.case_snapshot_id = str(payload.get("case_snapshot_id", f"case:{self._sequence}"))
                changed_ids = payload.get("changed_dependency_ids")
                if kind == "assessor_annotation_committed":
                    affected_roles = {Role.SPECIALIST}
                elif kind == "specialist_delta_committed":
                    # A Specialist result is a proposal from an immutable
                    # snapshot. Keep sibling Specialist runs live so the Lead
                    # can reconcile their parallel proposals; invalidate only
                    # downstream Evidence Worker/Assessor work that depends on
                    # the changed graph material.
                    affected_roles = {Role.EVIDENCE_WORKER, Role.ASSESSOR}
                else:
                    affected_roles = None
                self.last_event_affected_work_ids = self.stale_dependents(
                    changed_ids or (), reason=f"{kind} changed the board",
                    provenance_complete=bool(payload.get("provenance_complete", bool(changed_ids))),
                    roles=affected_roles,
                )
            return deepcopy(event)

    def add_need(self, need: Need) -> None:
        with self._lock:
            if need.need_id in self._needs:
                raise CFERPError(f"duplicate need_id {need.need_id}")
            if not need.slots or len({s.slot_id for s in need.slots}) != len(need.slots):
                raise CFERPError("need must have unique, non-empty information slots")
            self._needs[need.need_id] = need
            self.slot_history[need.need_id] = [
                {"slot_id": slot.slot_id, "from": None, "to": slot.state.value,
                 "resolution_refs": slot.resolution_refs, "version": need.version}
                for slot in need.slots
            ]

    def add_request(self, request: OutwardRequest) -> None:
        with self._lock:
            if request.request_id in self._requests:
                raise CFERPError(f"duplicate request_id {request.request_id}")
            if not request.slot_ids:
                raise CFERPError("outward request must name at least one typed slot")
            self._requests[request.request_id] = request

    def update_need_slots(self, need_id: str, slot_updates: dict[str, tuple[SlotState, tuple[str, ...]]]) -> Need:
        """Update only named slots, preserving unresolved parts of a compound need."""
        with self._lock:
            need = self._needs[need_id]
            unknown = set(slot_updates) - {s.slot_id for s in need.slots}
            if unknown:
                raise CFERPError(f"unknown information slots: {sorted(unknown)}")
            if not slot_updates:
                raise CFERPError("slot update must contain at least one slot")
            old_slots = {s.slot_id: s for s in need.slots}
            slots = tuple(
                replace(s, state=slot_updates[s.slot_id][0],
                        resolution_refs=tuple(sorted(set(s.resolution_refs) | set(slot_updates[s.slot_id][1]))))
                if s.slot_id in slot_updates else s for s in need.slots
            )
            states = {s.state for s in slots}
            terminal_success = {SlotState.RESOLVED_BY_MATERIAL, SlotState.ANSWERED}
            terminal_dispositions = terminal_success | {SlotState.REJECTED, SlotState.SUPERSEDED}
            for slot in slots:
                old = old_slots[slot.slot_id]
                if slot.state != old.state:
                    allowed = old.state in {SlotState.OPEN, SlotState.IN_PROCESS}
                    if not allowed:
                        raise CFERPError(f"slot {slot.slot_id} is terminal; use reopen_need_slots before changing it")
                    if old.state == SlotState.OPEN and slot.state == SlotState.OPEN:
                        continue
            if states == {SlotState.SUPERSEDED}:
                state = NeedState.SUPERSEDED
            elif states == {SlotState.REJECTED}:
                state = NeedState.REJECTED
            elif states <= terminal_dispositions and states.issubset(terminal_success | {SlotState.REJECTED}):
                state = NeedState.RESOLVED_BY_MATERIAL if all(s.state == SlotState.RESOLVED_BY_MATERIAL for s in slots) else NeedState.RESOLVED
            elif any(s.state in terminal_dispositions for s in slots):
                state = NeedState.PARTIALLY_RESOLVED
            else:
                state = NeedState.OPEN
            for slot in slots:
                old = old_slots[slot.slot_id]
                if slot != old:
                    self.slot_history[need_id].append({
                        "slot_id": slot.slot_id, "from": old.state.value,
                        "to": slot.state.value, "resolution_refs": slot.resolution_refs,
                        "version": need.version + 1,
                    })
            updated = replace(need, slots=slots, state=state, version=need.version + 1)
            self._needs[need_id] = updated
            return updated

    def reopen_need_slots(self, need_id: str, slot_ids: Iterable[str], *, reason: str) -> Need:
        """Reopen settled slots explicitly while retaining their prior history."""
        slot_ids = tuple(sorted(set(slot_ids)))
        if not reason.strip():
            raise CFERPError("reopening requires a reason")
        with self._lock:
            need = self._needs[need_id]
            known = {slot.slot_id for slot in need.slots}
            if not slot_ids or not set(slot_ids).issubset(known):
                raise CFERPError("reopen requires known information slots")
            updated_slots = []
            for slot in need.slots:
                if slot.slot_id not in slot_ids:
                    updated_slots.append(slot)
                    continue
                if slot.state in {SlotState.OPEN, SlotState.IN_PROCESS}:
                    raise CFERPError(f"slot {slot.slot_id} is already open")
                updated_slots.append(replace(slot, state=SlotState.OPEN, resolution_refs=()))
                self.slot_history[need_id].append({
                    "slot_id": slot.slot_id, "from": slot.state.value,
                    "to": SlotState.OPEN.value, "resolution_refs": (),
                    "reason": reason, "version": need.version + 1,
                })
            state = NeedState.PARTIALLY_RESOLVED if any(
                slot.state in {SlotState.ANSWERED, SlotState.RESOLVED_BY_MATERIAL,
                               SlotState.REJECTED, SlotState.SUPERSEDED}
                for slot in updated_slots
            ) else NeedState.OPEN
            updated = replace(need, slots=tuple(updated_slots), state=state, version=need.version + 1)
            self._needs[need_id] = updated
            return updated

    @staticmethod
    def packet_compatibility(packet, request: OutwardRequest) -> tuple[bool, str]:
        """Strict exact-slot compatibility; never merge request identity or wording."""
        checks = {
            "targets": tuple(sorted(packet.target_ids)) == tuple(sorted(request.target_ids)),
            "typed slots": tuple(sorted(packet.covered_slot_ids)) == tuple(sorted(request.slot_ids)),
            "source scope": tuple(sorted(packet.source_scope)) == tuple(sorted(request.source_scope)),
            "entity scope": tuple(sorted(packet.entity_ids)) == tuple(sorted(request.entity_ids)),
            "time scope": packet.time_scope == request.time_scope,
            "record types": tuple(sorted(packet.record_types)) == tuple(sorted(request.record_types)),
            "source versions": tuple(sorted(packet.source_versions)) == tuple(sorted(request.source_versions)),
            "material index snapshot": packet.searched_material_index_version == request.material_index_version,
        }
        failed = [label for label, ok in checks.items() if not ok]
        return not failed, ", ".join(failed)

    @staticmethod
    def _packet_non_slot_mismatches(packet, request: OutwardRequest) -> tuple[str, ...]:
        checks = {
            "targets": tuple(sorted(packet.target_ids)) == tuple(sorted(request.target_ids)),
            "source scope": tuple(sorted(packet.source_scope)) == tuple(sorted(request.source_scope)),
            "entity scope": tuple(sorted(packet.entity_ids)) == tuple(sorted(request.entity_ids)),
            "time scope": packet.time_scope == request.time_scope,
            "record types": tuple(sorted(packet.record_types)) == tuple(sorted(request.record_types)),
            "source versions": tuple(sorted(packet.source_versions)) == tuple(sorted(request.source_versions)),
            "material index snapshot": packet.searched_material_index_version == request.material_index_version,
        }
        return tuple(label for label, matches in checks.items() if not matches)

    def clone_packet_for_request(self, source_packet_id: str, target_request_id: str, *, new_packet_id: str):
        """Copy A's search result for A′ after a strict compatibility check."""
        with self._lock:
            packet = self._packets[source_packet_id]
            request = self._requests[target_request_id]
            if request.state in {RequestDisposition.REJECTED, RequestDisposition.ANSWERED,
                                 RequestDisposition.WITHDRAWN, RequestDisposition.SUPERSEDED,
                                 RequestDisposition.PARTIALLY_ANSWERED}:
                raise CFERPError("cannot reuse a packet for a terminal request")
            if new_packet_id in self._packets:
                raise CFERPError("new packet ID already exists")
            compatible, reason = self.packet_compatibility(packet, request)
            partial_slots: tuple[str, ...] = ()
            if not compatible:
                # Partial slot reuse is safe only when the source packet carries
                # a separately attributable result for every reused slot.
                non_slot_checks = self._packet_non_slot_mismatches(packet, request)
                overlap = set(packet.covered_slot_ids) & set(request.slot_ids)
                per_slot = dict(getattr(packet, "slot_payloads", ()))
                if not non_slot_checks and overlap and overlap.issubset(per_slot):
                    compatible, partial_slots = True, tuple(sorted(overlap))
            if not compatible:
                raise CFERPError(f"packet cannot be reused: incompatible {reason}")
            if partial_slots:
                slot_payloads = tuple((sid, deepcopy(dict(packet.slot_payloads)[sid])) for sid in partial_slots)
                clone = replace(packet, packet_id=new_packet_id, request_id=target_request_id,
                                covered_slot_ids=partial_slots, slot_payloads=slot_payloads,
                                result_payload={"reused_slot_payloads": dict(slot_payloads),
                                                "uncovered_slot_ids": tuple(sorted(set(request.slot_ids) - set(partial_slots)))},
                                is_partial_reuse=True, parent_packet_id=source_packet_id)
            else:
                clone = replace(packet, packet_id=new_packet_id, request_id=target_request_id,
                                result_payload=deepcopy(packet.result_payload),
                                slot_payloads=deepcopy(getattr(packet, "slot_payloads", ())),
                                parent_packet_id=source_packet_id)
            self._packets[new_packet_id] = clone
            self._requests[target_request_id] = replace(
                request, current_packet_id=new_packet_id,
                packet_history=request.packet_history + (new_packet_id,),
            )
            return deepcopy(clone)

    def register_packet(self, packet) -> None:
        with self._lock:
            if packet.packet_id in self._packets:
                raise CFERPError("duplicate packet_id")
            if packet.request_id not in self._requests:
                raise CFERPError("packet references unknown request")
            request = self._requests[packet.request_id]
            if request.state in {RequestDisposition.REJECTED, RequestDisposition.ANSWERED,
                                 RequestDisposition.WITHDRAWN, RequestDisposition.SUPERSEDED,
                                 RequestDisposition.PARTIALLY_ANSWERED}:
                raise CFERPError("cannot attach a new current packet to a terminal request")
            if tuple(sorted(packet.target_ids)) != tuple(sorted(request.target_ids)):
                raise CFERPError("packet target_ids do not match its request")
            if not set(packet.covered_slot_ids) or not set(packet.covered_slot_ids).issubset(request.slot_ids):
                raise CFERPError("packet covered slots must be a non-empty subset of its request slots")
            slot_payload_ids = [slot_id for slot_id, _ in getattr(packet, "slot_payloads", ())]
            if len(slot_payload_ids) != len(set(slot_payload_ids)) or not set(slot_payload_ids).issubset(packet.covered_slot_ids):
                raise CFERPError("packet slot_payloads must have unique IDs contained in covered_slot_ids")
            mismatches = self._packet_non_slot_mismatches(packet, request)
            if mismatches:
                raise CFERPError(f"packet scope/snapshot does not match its request: {', '.join(mismatches)}")
            self._packets[packet.packet_id] = deepcopy(packet)
            req = request
            self._requests[req.request_id] = replace(req, current_packet_id=packet.packet_id,
                                                     packet_history=req.packet_history + (packet.packet_id,))

    def apply_request_review(self, request_id: str, disposition: str) -> OutwardRequest:
        """Record HERA's per-request disposition; Lead still controls dispatch."""
        mapping = {
            "pass": RequestDisposition.APPROVED,
            "revise": RequestDisposition.REVISION,
            "reject": RequestDisposition.REJECTED,
        }
        if disposition not in mapping:
            raise CFERPError("request review must be pass, revise, or reject")
        with self._lock:
            req = self._requests[request_id]
            if req.state not in {RequestDisposition.PROPOSED, RequestDisposition.ASSESSOR_REVIEW,
                                 RequestDisposition.REVISION}:
                raise CFERPError("request is not awaiting or returned from Assessor review")
            updated = replace(req, state=mapping[disposition])
            self._requests[request_id] = updated
            return updated

    def queue_approved_request(self, request_id: str) -> OutwardRequest:
        """Lead explicitly authorizes an Assessor-approved request for Intake."""
        with self._lock:
            req = self._requests[request_id]
            if req.state != RequestDisposition.APPROVED:
                raise CFERPError("only an Assessor-approved request can be queued")
            updated = replace(req, state=RequestDisposition.READY_TO_SEND)
            self._requests[request_id] = updated
            return updated

    def register_work(self, item: WorkItem) -> None:
        with self._lock:
            if item.work_id in self._work:
                raise CFERPError("duplicate work_id")
            self._work[item.work_id] = item

    def stale_dependents(self, changed_dependency_ids: Iterable[str], *, reason: str,
                         provenance_complete: bool = True,
                         roles: Iterable[Role] | None = None) -> tuple[str, ...]:
        """Invalidate directly dependent active jobs; missing provenance fails broad."""
        changed = set(changed_dependency_ids)
        role_filter = set(roles) if roles is not None else None
        affected = []
        active = {JobState.QUEUED, JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                  JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL}
        def family(dependency_id: str) -> str:
            # Stable material identity survives version changes: D1:v1 and
            # D1:v2 belong to the same dependency family.
            head, separator, _tail = dependency_id.rpartition(":")
            return head if separator else dependency_id
        changed_families = {family(item) for item in changed}
        invalidated_actions = []
        with self._lock:
            for wid, item in list(self._work.items()):
                if role_filter is not None and item.role not in role_filter:
                    continue
                dependent = bool(changed.intersection(item.dependency_ids)) or any(
                    family(dependency) in changed_families for dependency in item.dependency_ids
                )
                conservative = not provenance_complete and item.state in active
                if item.state in active and (dependent or conservative):
                    self._work[wid] = replace(item, state=JobState.STALE,
                                              stale_reason=reason if dependent else f"{reason}; dependency provenance incomplete")
                    affected.append(wid)
            for action_id, action in list(self._reserved_action_details.items()):
                if role_filter is not None and action.role not in role_filter:
                    continue
                depends = bool(changed.intersection(action.dependency_ids)) or any(
                    family(dependency) in changed_families for dependency in action.dependency_ids
                )
                if depends or not provenance_complete:
                    self._scheduled_reservations.pop(action_id, None)
                    self._reserved_action_details.pop(action_id, None)
                    invalidated_actions.append(action_id)
                    item = self._work.get(action_id)
                    if item and item.state == JobState.QUEUED:
                        self._work[action_id] = replace(item, state=JobState.STALE,
                                                        stale_reason=reason if depends else f"{reason}; dependency provenance incomplete")
                        affected.append(action_id)
            self.last_invalidated_action_ids = tuple(sorted(invalidated_actions))
        return tuple(sorted(affected))

    def submit_dispatch(self, request_id: str, action: str) -> DispatchAction:
        """Create ordered, idempotent send/withdraw action for Intake."""
        if action not in {"send", "withdraw"}:
            raise CFERPError("dispatch action must be send or withdraw")
        with self._lock:
            req = self._requests[request_id]
            if action == "send" and req.state not in {RequestDisposition.READY_TO_SEND, RequestDisposition.DISPATCH_FAILED}:
                raise CFERPError("request is not ready to send")
            if action == "withdraw" and req.state not in {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                                                          RequestDisposition.DISPATCH_PENDING, RequestDisposition.WITHDRAWAL_PENDING}:
                raise CFERPError("request has no potentially sent dispatch to withdraw")
            if action == "withdraw":
                pending_withdrawals = [
                    item for item in self._dispatch_actions.values()
                    if item.request_id == request_id and item.action == "withdraw"
                    and item.target_send_sequence not in req.acknowledged_withdrawn_send_ids
                    and item.action_id not in self._dispatch_ack_records
                ]
                if pending_withdrawals:
                    return max(pending_withdrawals, key=lambda item: item.sequence)
                unresolved_cancelled_sends = [
                    seq for seq in req.acknowledged_withdrawn_send_ids
                    if any(a.request_id == request_id and a.action == "send" and a.sequence == seq
                           and a.action_id not in self._dispatch_ack_records
                           for a in self._dispatch_actions.values())
                ]
                if unresolved_cancelled_sends and not req.withdrawal_required_send_ids:
                    prior = [a for a in self._dispatch_actions.values()
                             if a.request_id == request_id and a.action == "withdraw"
                             and a.target_send_sequence in unresolved_cancelled_sends
                             and self._dispatch_ack_records.get(a.action_id) is True]
                    if prior:
                        return max(prior, key=lambda item: item.sequence)
                    raise CFERPError("withdrawal already submitted for pending send; await Intake ACK")
            sequence = req.latest_dispatch_sequence + 1
            key = f"{self.case_id}:{request_id}:v{req.request_version}:{action}:{sequence}"
            action_id = f"dispatch:{request_id}:{sequence}:{action}"
            target_send = None
            if action == "withdraw":
                pending_or_sent = [seq for seq in req.withdrawal_required_send_ids]
                if not pending_or_sent:
                    pending_or_sent = [
                        item.sequence for item in self._dispatch_actions.values()
                        if item.request_id == request_id and item.action == "send"
                        and item.sequence not in req.acknowledged_withdrawn_send_ids
                        and (item.action_id not in self._dispatch_ack_records
                             or self._dispatch_ack_records[item.action_id] is True)
                    ]
                target_send = max(pending_or_sent, default=None)
                if target_send is None:
                    raise CFERPError("no send action exists to withdraw")
            dispatch = DispatchAction(action_id, request_id, sequence, action, key, target_send)
            self._dispatch_actions[action_id] = dispatch
            new_state = RequestDisposition.DISPATCH_PENDING if action == "send" else RequestDisposition.WITHDRAWAL_PENDING
            required_withdrawals = req.withdrawal_required_send_ids
            if action == "withdraw":
                required_withdrawals = tuple(sorted(set(required_withdrawals) | {target_send}))
            self._requests[request_id] = replace(req, state=new_state, latest_dispatch_sequence=sequence,
                                                withdrawal_required_send_ids=required_withdrawals,
                                                idempotency_keys=req.idempotency_keys + (key,))
            return dispatch

    def acknowledge_dispatch(self, action_id: str, *, success: bool) -> OutwardRequest:
        """Apply Intake ACK by action sequence; delayed ACKs cannot erase newer state."""
        with self._lock:
            action = self._dispatch_actions[action_id]
            req = self._requests[action.request_id]
            if action_id in self._dispatch_ack_records:
                if self._dispatch_ack_records[action_id] != success:
                    raise CFERPError("conflicting duplicate dispatch ACK")
                return req
            self._dispatch_ack_records[action_id] = success
            if action.action == "send":
                if success:
                    sent_ids = tuple(sorted(set(req.acknowledged_sent_ids) | {action.sequence}))
                    req = replace(req, last_acknowledged_send_sequence=max(req.last_acknowledged_send_sequence, action.sequence),
                                  acknowledged_sent_ids=sent_ids)
                    if action.sequence in req.acknowledged_withdrawn_send_ids:
                        # A send ACK later than its withdrawal ACK means it was
                        # actually delivered after cancellation; require a new
                        # withdrawal confirmation for this send occurrence.
                        req = replace(req, acknowledged_withdrawn_send_ids=tuple(
                            item for item in req.acknowledged_withdrawn_send_ids if item != action.sequence
                        ), withdrawal_required_send_ids=tuple(sorted(set(req.withdrawal_required_send_ids) | {action.sequence})))
                else:
                    # A confirmed failed send does not need cancellation. Keep
                    # intent for any other send attempts still pending/sent.
                    req = replace(req, withdrawal_required_send_ids=tuple(
                        sid for sid in req.withdrawal_required_send_ids if sid != action.sequence
                    ))
            else:
                if success:
                    req = replace(req, last_acknowledged_withdrawal_sequence=max(req.last_acknowledged_withdrawal_sequence, action.sequence))
                    withdrawn_ids = tuple(sorted(set(req.acknowledged_withdrawn_send_ids) | {action.target_send_sequence}))
                    req = replace(req, acknowledged_withdrawn_send_ids=withdrawn_ids,
                                  withdrawal_required_send_ids=tuple(
                                      sid for sid in req.withdrawal_required_send_ids if sid != action.target_send_sequence
                                  ))
            req = replace(req, state=self._reconciled_delivery_state(req))
            self._requests[req.request_id] = req
            return req

    def mark_waiting_response(self, request_id: str) -> OutwardRequest:
        """Mark a successfully delivered request as awaiting an external reply."""
        with self._lock:
            request = self._requests[request_id]
            if request.state != RequestDisposition.SENT:
                raise CFERPError("only a confirmed sent request can await a response")
            updated = replace(request, state=RequestDisposition.WAITING_RESPONSE)
            self._requests[request_id] = updated
            return updated

    def record_external_response(self, request_id: str, material_id: str, *, allow_late: bool = False) -> OutwardRequest:
        """Record receipt without treating the response as an assessed answer."""
        if not material_id:
            raise CFERPError("response material ID is required")
        with self._lock:
            request = self._requests[request_id]
            deliverable_states = {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                                  RequestDisposition.PARTIALLY_ANSWERED}
            if request.state not in deliverable_states and not allow_late:
                raise CFERPError("response can only attach to a delivered request")
            updated = replace(request,
                              state=(RequestDisposition.PARTIALLY_ANSWERED
                                     if request.state in deliverable_states else request.state),
                              response_material_ids=tuple(dict.fromkeys(
                                  (*request.response_material_ids, material_id))))
            self._requests[request_id] = updated
            return updated

    def mark_request_answered(self, request_id: str) -> OutwardRequest:
        """Close a request only after the Lead has accepted its reviewed response."""
        with self._lock:
            request = self._requests[request_id]
            if request.state not in {RequestDisposition.PARTIALLY_ANSWERED, RequestDisposition.WAITING_RESPONSE}:
                raise CFERPError("only an awaiting or partially answered request can be completed")
            if not request.response_material_ids:
                raise CFERPError("request cannot be completed before a response is registered")
            updated = replace(request, state=RequestDisposition.ANSWERED)
            self._requests[request_id] = updated
            return updated

    def supersede_unsent_request(self, request_id: str, *, reason: str) -> OutwardRequest:
        """End an unsent request whose sole target branch is no longer active."""
        if not reason.strip():
            raise CFERPError("request supersession requires a reason")
        with self._lock:
            request = self._requests[request_id]
            if request.state in {RequestDisposition.SENT, RequestDisposition.WAITING_RESPONSE,
                                 RequestDisposition.PARTIALLY_ANSWERED, RequestDisposition.DISPATCH_PENDING,
                                 RequestDisposition.WITHDRAWAL_PENDING}:
                raise CFERPError("delivered or possibly delivered request needs withdrawal reconciliation")
            if request.state in {RequestDisposition.ANSWERED, RequestDisposition.REJECTED,
                                 RequestDisposition.WITHDRAWN, RequestDisposition.SUPERSEDED}:
                return request
            updated = replace(request, state=RequestDisposition.SUPERSEDED,
                              request_version=request.request_version + 1)
            self._requests[request_id] = updated
            return updated

    def _reconciled_delivery_state(self, request: OutwardRequest) -> RequestDisposition:
        sends = [a for a in self._dispatch_actions.values() if a.request_id == request.request_id and a.action == "send"]
        successes = {a.sequence for a in sends if self._dispatch_ack_records.get(a.action_id) is True}
        pending = {a.sequence for a in sends if a.action_id not in self._dispatch_ack_records}
        active_delivered = successes - set(request.acknowledged_withdrawn_send_ids)
        withdrawal_pending = any(
            a.request_id == request.request_id and a.action == "withdraw"
            and a.action_id not in self._dispatch_ack_records
            and a.target_send_sequence in (active_delivered | pending)
            for a in self._dispatch_actions.values()
        ) or bool(request.withdrawal_required_send_ids) or bool(pending & set(request.acknowledged_withdrawn_send_ids))
        if active_delivered:
            return RequestDisposition.WITHDRAWAL_PENDING if withdrawal_pending else RequestDisposition.SENT
        if pending:
            return RequestDisposition.WITHDRAWAL_PENDING if withdrawal_pending else RequestDisposition.DISPATCH_PENDING
        if successes and successes.issubset(set(request.acknowledged_withdrawn_send_ids)):
            return RequestDisposition.WITHDRAWN
        if sends:
            return RequestDisposition.DISPATCH_FAILED
        return request.state

    def update_request_slots(self, request_id: str, remaining_slot_ids: Iterable[str], *, new_request_id: str,
                             wording: str | None = None) -> OutwardRequest:
        """Preserve parent; create a child request for only unresolved slots."""
        with self._lock:
            parent = self._requests[request_id]
            remaining = tuple(sorted(set(remaining_slot_ids)))
            if not remaining:
                self._requests[request_id] = replace(parent, state=RequestDisposition.ANSWERED)
                return self._requests[request_id]
            if not set(remaining).issubset(parent.slot_ids):
                raise CFERPError("child request slots must be a subset of parent slots")
            if new_request_id in self._requests:
                raise CFERPError(f"duplicate request_id {new_request_id}")
            if parent.state in {RequestDisposition.REJECTED, RequestDisposition.WITHDRAWN,
                                RequestDisposition.ANSWERED, RequestDisposition.SUPERSEDED}:
                raise CFERPError("cannot create a follow-up from a terminal request")
            if parent.state == RequestDisposition.PARTIALLY_ANSWERED:
                raise CFERPError("create follow-up only once from the original request")
            self._requests[request_id] = replace(parent, state=RequestDisposition.PARTIALLY_ANSWERED)
            child = replace(parent, request_id=new_request_id, slot_ids=remaining,
                            wording=wording or parent.wording, state=RequestDisposition.PROPOSED,
                            current_packet_id=None, packet_history=(), request_version=1,
                            latest_dispatch_sequence=0, last_acknowledged_send_sequence=0,
                            last_acknowledged_withdrawal_sequence=0, acknowledged_sent_ids=(),
                            acknowledged_withdrawn_send_ids=(), withdrawal_required_send_ids=(),
                            idempotency_keys=())
            self.add_request(child)
            return child

    def schedule(self, actions: Iterable[CandidateAction], *, planner: LeadPlanner | None = None,
                 ambiguous: bool = False) -> tuple[CandidateAction, ...]:
        """Choose eligible work deterministically under per-role and global caps.

        Lower priority_tier is more urgent; aging eventually promotes work
        deferred by higher tiers. Older actions win ties. Selected actions are
        reserved atomically, so repeated scheduler calls cannot dispatch them
        twice. Caller supplies only actions whose dependencies
        are satisfied and whose source manifests are current.
        """
        candidate_map = {}
        for action in actions:
            previous = candidate_map.get(action.action_id)
            if previous is not None and previous != action:
                raise CFERPError(f"conflicting CandidateAction payloads share ID {action.action_id}")
            candidate_map[action.action_id] = action
        candidates = tuple(candidate_map.values())
        with self._lock:
            planning_manifest = self.manifest()
            for action in candidates:
                fingerprint = _stable_fingerprint(action)
                prior = self._action_fingerprints.get(action.action_id)
                if prior is not None and prior != fingerprint:
                    raise CFERPError(f"CandidateAction ID reused with changed payload: {action.action_id}")
                self._action_fingerprints[action.action_id] = fingerprint
            eligible = []
            stale_action_ids = []
            for action in candidates:
                stale_manifest = action.manifest is not None and not self._manifest_is_current(action.manifest, planning_manifest)
                stale_dependency = False
                for dependency in action.dependency_ids:
                    head, separator, tail = dependency.rpartition(":")
                    if head in self._latest_dependency_versions:
                        if not separator or tail != self._latest_dependency_versions[head]:
                            stale_dependency = True
                            break
                if stale_manifest or stale_dependency:
                    stale_action_ids.append(action.action_id)
                else:
                    eligible.append(action)
        candidates = tuple(eligible)
        preplanner_diagnostics = tuple(f"stale_candidate_action:{item}" for item in stale_action_ids)
        planner_decision = get_planner_decision(
            actions=candidates, manifest=planning_manifest, planner=planner, ambiguous=ambiguous,
        )
        if preplanner_diagnostics:
            planner_decision = replace(planner_decision, diagnostics=preplanner_diagnostics + planner_decision.diagnostics)
        with self._lock:
            if self.manifest() != planning_manifest:
                planner_decision = replace(
                    planner_decision, accepted=False, rank_by_action_id=(),
                    diagnostics=planner_decision.diagnostics + ("case_changed_during_planner_call",),
                )
            self.last_planner_called = planner_decision.called
            self.last_planner_accepted = planner_decision.accepted
            self.last_planner_diagnostics = planner_decision.diagnostics
            if "case_changed_during_planner_call" in planner_decision.diagnostics:
                return ()
            self._schedule_round += 1
            executing_ids = self._executing_work_ids | {
                wid for wid, item in self._work.items() if item.state in {
                    JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                    JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
                }
            }
            running = [self._work[wid] for wid in executing_ids if wid in self._work]
            role_counts = {role: sum(w.role == role for w in running) for role in Role}
            free_reservation_ids = set(self._scheduled_reservations) - executing_ids
            for action_id in free_reservation_ids:
                role = self._scheduled_reservations[action_id]
                role_counts[role] = role_counts.get(role, 0) + 1
            total = len(running) + len(free_reservation_ids)
            pending_actions = []
            for action in candidates:
                existing_work = self._work.get(action.action_id)
                if (action.action_id in self._scheduled_reservations
                        or (existing_work is not None and existing_work.state != JobState.QUEUED)):
                    continue
                self._action_first_seen.setdefault(action.action_id, self._schedule_round)
                pending_actions.append(action)
            selected: list[CandidateAction] = []
            rank_map = dict(planner_decision.rank_by_action_id) if planner_decision.accepted else {}
            def queue_key(action):
                wait_rounds = self._schedule_round - self._action_first_seen[action.action_id]
                effective_tier = max(0, action.priority_tier - wait_rounds // self._starvation_rounds)
                age = action.created_sequence or self._action_first_seen[action.action_id]
                return effective_tier, age, rank_map.get(action.action_id, 0), action.cost, action.action_id
            for action in sorted(pending_actions, key=queue_key):
                if total >= self.global_concurrency:
                    break
                cap = self.concurrency.get(action.role, 0)
                if role_counts.get(action.role, 0) >= cap:
                    continue
                selected.append(action)
                self._scheduled_reservations[action.action_id] = action.role
                self._reserved_action_details[action.action_id] = action
                role_counts[action.role] = role_counts.get(action.role, 0) + 1
                total += 1
            return tuple(selected)

    def _manifest_is_current(self, candidate: VersionManifest, current: VersionManifest) -> bool:
        if (candidate.case_id != current.case_id
                or candidate.case_snapshot_id != current.case_snapshot_id
                or candidate.board_version != current.board_version
                or candidate.material_index_version != current.material_index_version):
            return False
        for source_id, version, content_hash in candidate.source_versions:
            if self._latest_source_versions.get(source_id) != (version, content_hash):
                return False
        return True

    def release_reservation(self, action_id: str) -> None:
        """Return an unstarted selected action to its caller-owned queue."""
        with self._lock:
            if action_id not in self._scheduled_reservations:
                raise CFERPError("action has no scheduler reservation")
            del self._scheduled_reservations[action_id]
            self._reserved_action_details.pop(action_id, None)

    def register_scheduled_work(self, action_id: str, item: WorkItem) -> None:
        """Bind a reserved action to a queued work item while retaining its slot."""
        with self._lock:
            role = self._scheduled_reservations.get(action_id)
            if role is None:
                raise CFERPError("action must be reserved before work registration")
            if item.work_id != action_id or item.role != role or item.state != JobState.QUEUED:
                raise CFERPError("work item must match reserved action ID/role and start queued")
            action = self._reserved_action_details[action_id]
            if (tuple(item.target_ids) != tuple(action.target_ids)
                    or tuple(item.need_ids) != tuple(action.need_ids)
                    or tuple(item.dependency_ids) != tuple(action.dependency_ids)):
                raise CFERPError("work item scope/dependencies must match the reserved action")
            if item.work_id in self._work:
                raise CFERPError("duplicate work_id")
            self._work[item.work_id] = item

    def can_start(self, work_id: str) -> bool:
        """Whether queued work fits the role and global concurrency limits now."""
        with self._lock:
            item = self._work[work_id]
            return item.state == JobState.QUEUED and not self._concurrency_blocked(item, work_id)

    def _concurrency_blocked(self, item: WorkItem, work_id: str) -> bool:
        executing_ids = self._executing_work_ids | {
            wid for wid, work_item in self._work.items() if work_item.state in {
                JobState.RUNNING, JobState.AWAITING_ASSESSOR,
                JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
            }
        }
        other_reservations = set(self._scheduled_reservations) - executing_ids - {work_id}
        role_running = sum(self._work[wid].role == item.role for wid in executing_ids if wid in self._work)
        role_running += sum(self._scheduled_reservations[action_id] == item.role
                            for action_id in other_reservations)
        total_running = len(executing_ids) + len(other_reservations)
        return (role_running >= self.concurrency.get(item.role, 0)
                or total_running >= self.global_concurrency)

    def start_work(self, work_id: str) -> WorkItem:
        with self._lock:
            item = self._work[work_id]
            if item.state != JobState.QUEUED:
                raise CFERPError("only queued work can start")
            if self._concurrency_blocked(item, work_id):
                raise CFERPError("concurrency limit reached")
            updated = replace(item, state=JobState.RUNNING)
            self._work[work_id] = updated
            self._scheduled_reservations.pop(work_id, None)
            self._reserved_action_details.pop(work_id, None)
            self._executing_work_ids.add(work_id)
            return updated

    def finish_work(self, work_id: str, *, state: JobState = JobState.COMPLETE,
                    result_ref: str | None = None) -> WorkItem:
        """Finish a running assignment or record its failure, freeing its slot."""
        if state not in {JobState.COMPLETE, JobState.FAILED, JobState.RETURNED,
                         JobState.AWAITING_ASSESSOR, JobState.NEEDS_REVISION,
                         JobState.WAITING_EXTERNAL, JobState.STALE, JobState.SUPERSEDED}:
            raise CFERPError("finish state must be a non-running result state")
        with self._lock:
            item = self._work[work_id]
            if work_id not in self._executing_work_ids and item.state != JobState.RUNNING:
                raise CFERPError("only running work can finish")
            final_state = JobState.STALE if item.state == JobState.STALE else state
            updated = replace(item, state=final_state, result_ref=result_ref)
            self._work[work_id] = updated
            self._executing_work_ids.discard(work_id)
            return updated

    def transition_work(self, work_id: str, state: JobState, *, result_ref: str | None = None,
                        reason: str | None = None) -> WorkItem:
        """Move non-running work through a Lead-owned lifecycle transition."""
        terminal = {JobState.COMPLETE, JobState.FAILED, JobState.SUPERSEDED}
        allowed = {
            JobState.QUEUED: {JobState.STALE, JobState.SUPERSEDED, JobState.FAILED},
            JobState.RETURNED: {JobState.AWAITING_ASSESSOR, JobState.NEEDS_REVISION,
                                JobState.WAITING_EXTERNAL, JobState.COMPLETE,
                                JobState.STALE, JobState.SUPERSEDED},
            JobState.AWAITING_ASSESSOR: {JobState.NEEDS_REVISION, JobState.WAITING_EXTERNAL,
                                         JobState.COMPLETE, JobState.STALE, JobState.SUPERSEDED},
            JobState.NEEDS_REVISION: {JobState.QUEUED, JobState.SUPERSEDED, JobState.STALE},
            JobState.WAITING_EXTERNAL: {JobState.QUEUED, JobState.COMPLETE,
                                        JobState.STALE, JobState.SUPERSEDED},
            JobState.STALE: {JobState.SUPERSEDED, JobState.COMPLETE},
        }
        with self._lock:
            item = self._work[work_id]
            if item.state in terminal or state not in allowed.get(item.state, set()):
                raise CFERPError(f"illegal work transition {item.state.value} -> {state.value}")
            updated = replace(item, state=state, result_ref=result_ref,
                              stale_reason=reason if state == JobState.STALE else item.stale_reason)
            self._work[work_id] = updated
            return updated

    def is_executing(self, work_id: str) -> bool:
        """Whether the host has started a worker call that has not returned."""
        with self._lock:
            return work_id in self._executing_work_ids

