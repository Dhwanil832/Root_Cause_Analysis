"""Orthogonal work-phase and request-state transitions for V3 handoffs.

This ledger is an in-memory reference implementation. Replace it with durable
transactional storage before concurrent production use.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from threading import RLock

from .contracts import WorkPhase


class RequestPhase(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted_to_assessor"
    RETURNED = "returned_for_revision"
    APPROVED = "approved_by_assessor"
    QUEUED = "queued_by_lead"
    SENT = "sent"
    AWAITING_RESPONSE = "awaiting_response"
    PARTIAL = "partially_answered"
    RESPONSE = "response_registered"
    REJECTED = "rejected"
    CANCELED = "canceled"
    CLOSED = "closed_by_lead"


@dataclass(frozen=True, slots=True)
class RequestLifecycle:
    request_id: str
    phase: RequestPhase = RequestPhase.DRAFT
    response_pending: bool = False


@dataclass(frozen=True, slots=True)
class WorkItemLifecycle:
    work_item_id: str
    phase: WorkPhase = WorkPhase.OPEN
    requests: tuple[RequestLifecycle, ...] = ()
    active_attempt_id: str | None = None
    version: int = 0

    def request_map(self):
        return {request.request_id: request for request in self.requests}


class InvalidTransition(ValueError):
    pass


class WorkItemLifecycleStore:
    """Atomic in-memory transition store with event idempotency."""

    def __init__(self):
        self._lock = RLock()
        self._states: dict[str, WorkItemLifecycle] = {}
        self._events: dict[tuple[str, str], tuple[str, WorkItemLifecycle]] = {}

    def create(self, work_item_id: str) -> WorkItemLifecycle:
        with self._lock:
            return self._states.setdefault(work_item_id, WorkItemLifecycle(work_item_id))

    def get(self, work_item_id: str) -> WorkItemLifecycle:
        with self._lock:
            return self._states[work_item_id]

    def apply(self, work_item_id: str, event_id: str, event: str, *,
              request_id: str | None = None, attempt_id: str | None = None,
              input_fingerprint: str) -> WorkItemLifecycle:
        key = (work_item_id, event_id)
        with self._lock:
            if key in self._events:
                prior_fp, prior_state = self._events[key]
                if prior_fp != input_fingerprint:
                    raise InvalidTransition("event_id reused with changed event payload")
                return prior_state
            state = self._states.setdefault(work_item_id, WorkItemLifecycle(work_item_id))
            new_state = self._transition(state, event, request_id, attempt_id)
            new_state = replace(new_state, version=state.version + 1)
            self._states[work_item_id] = new_state
            self._events[key] = (input_fingerprint, new_state)
            return new_state

    @staticmethod
    def _transition(state, event, request_id, attempt_id):
        phase = state.phase
        requests = state.request_map()
        active = state.active_attempt_id

        def set_request(new_phase, *, response_pending=None):
            if not request_id or request_id not in requests:
                raise InvalidTransition("event references unknown request_id")
            changes = {"phase": new_phase}
            if response_pending is not None:
                changes["response_pending"] = response_pending
            requests[request_id] = replace(requests[request_id], **changes)

        if event == "add_request":
            if not request_id or request_id in requests:
                raise InvalidTransition("new request needs a unique request_id")
            requests[request_id] = RequestLifecycle(request_id)
        elif event == "assign":
            if phase not in {WorkPhase.OPEN, WorkPhase.BLOCKED, WorkPhase.RESUMABLE}:
                raise InvalidTransition(f"cannot assign from {phase.value}")
            phase = WorkPhase.READY
        elif event == "start_attempt":
            if phase not in {WorkPhase.READY, WorkPhase.RESUMABLE} or active is not None:
                raise InvalidTransition("work item is not ready for an attempt")
            if not attempt_id:
                raise InvalidTransition("attempt_id required")
            active, phase = attempt_id, WorkPhase.RUNNING
        elif event == "worker_return":
            if phase != WorkPhase.RUNNING or active is None:
                raise InvalidTransition("no active attempt to return")
            active, phase = None, WorkPhase.AWAITING_ASSESSOR
        elif event == "assessor_return":
            if phase != WorkPhase.AWAITING_ASSESSOR:
                raise InvalidTransition("work item is not awaiting Assessor")
            phase = WorkPhase.RESUMABLE
        elif event == "assessor_complete":
            if phase != WorkPhase.AWAITING_ASSESSOR:
                raise InvalidTransition("work item is not awaiting Assessor")
            phase = WorkPhase.AWAITING_LEAD
        elif event == "submit_request":
            if not request_id or request_id not in requests or requests[request_id].phase not in {
                RequestPhase.DRAFT, RequestPhase.RETURNED
            }:
                raise InvalidTransition("request is not ready for Assessor submission")
            set_request(RequestPhase.SUBMITTED)
        elif event == "return_request":
            if not request_id or request_id not in requests or requests[request_id].phase != RequestPhase.SUBMITTED:
                raise InvalidTransition("request is not under Assessor review")
            set_request(RequestPhase.RETURNED)
        elif event == "reject_request":
            if not request_id or request_id not in requests or requests[request_id].phase not in {
                RequestPhase.SUBMITTED, RequestPhase.RETURNED, RequestPhase.APPROVED
            }:
                raise InvalidTransition("request cannot be rejected in this state")
            set_request(RequestPhase.REJECTED)
        elif event == "approve_request":
            if not request_id or request_id not in requests or requests[request_id].phase not in {
                RequestPhase.SUBMITTED, RequestPhase.RETURNED
            }:
                raise InvalidTransition("request is not eligible for Assessor approval")
            set_request(RequestPhase.APPROVED)
        elif event == "queue_request":
            if not request_id or request_id not in requests or requests[request_id].phase != RequestPhase.APPROVED:
                raise InvalidTransition("request is not approved")
            set_request(RequestPhase.QUEUED)
        elif event == "send_request":
            if not request_id or request_id not in requests or requests[request_id].phase != RequestPhase.QUEUED:
                raise InvalidTransition("request is not queued by Lead")
            set_request(RequestPhase.AWAITING_RESPONSE)
            if phase == WorkPhase.AWAITING_LEAD:
                phase = WorkPhase.WAITING_EXTERNAL
        elif event == "register_response":
            if not request_id or request_id not in requests or requests[request_id].phase not in {
                RequestPhase.AWAITING_RESPONSE, RequestPhase.PARTIAL
            }:
                raise InvalidTransition("request is not awaiting a response")
            if requests[request_id].response_pending:
                raise InvalidTransition("previous response must be routed before another response is registered")
            set_request(RequestPhase.PARTIAL, response_pending=True)
        elif event == "complete_response":
            if not request_id or request_id not in requests or requests[request_id].phase not in {
                RequestPhase.AWAITING_RESPONSE, RequestPhase.PARTIAL
            }:
                raise InvalidTransition("request cannot be marked response-registered")
            if requests[request_id].response_pending:
                raise InvalidTransition("previous response must be routed before another response is registered")
            set_request(RequestPhase.RESPONSE, response_pending=True)
        elif event == "route_response":
            if phase not in {WorkPhase.WAITING_EXTERNAL, WorkPhase.AWAITING_LEAD}:
                raise InvalidTransition("work item is not ready to route a response")
            if not request_id or request_id not in requests or not requests[request_id].response_pending:
                raise InvalidTransition("route_response requires a newly registered response for request_id")
            requests[request_id] = replace(requests[request_id], response_pending=False)
            phase = WorkPhase.READY
        elif event == "wait_for_remaining_requests":
            if phase != WorkPhase.AWAITING_LEAD or not any(
                r.phase == RequestPhase.AWAITING_RESPONSE for r in requests.values()
            ):
                raise InvalidTransition("no pending external request to wait for")
            phase = WorkPhase.WAITING_EXTERNAL
        elif event == "hold_stale":
            if phase in {WorkPhase.CLOSED, WorkPhase.CANCELED}:
                raise InvalidTransition("terminal work item cannot be held")
            active, phase = None, WorkPhase.HELD
        elif event in {"close", "cancel"}:
            if phase == WorkPhase.RUNNING:
                raise InvalidTransition("cannot close/cancel while an attempt is active")
            phase = WorkPhase.CLOSED if event == "close" else WorkPhase.CANCELED
        else:
            raise InvalidTransition(f"unknown event {event!r}")

        return WorkItemLifecycle(state.work_item_id, phase,
                                 tuple(requests[k] for k in sorted(requests)), active)

