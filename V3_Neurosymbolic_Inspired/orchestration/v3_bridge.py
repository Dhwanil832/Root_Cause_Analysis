"""Joint runner for the standalone CFERP, SAHS, EWV3, and HERA1 packages.

This is a separate V3 runtime boundary. It does not adapt V3 outputs into the
legacy V1/V2 in-memory kernel, whose state and result contracts are different.
The workspace's CFERP workflow is the V3 Lead/state owner; role engines remain
independently replaceable and can use the archive's model transport.
"""
from __future__ import annotations

from typing import Any

from cferp import RoleResult
from cferp.contracts import JobState, Role
from cferp.integration import (ew_assignment_from_cferp, ew_result_to_cferp,
    hera_result_to_cferp, hera_task_from_cferp, sahs_assignment_from_cferp,
    sahs_result_to_cferp)


class V3BridgeError(RuntimeError):
    pass


class WorkflowVersionReader:
    """Supply HERA with versions from the live CFERP case catalog.

    CFERP judges an assignment current by dependency invalidation, not by a
    global board-version match (``CFERPWorkflow._assignment_is_current``).
    While the bridge runs an assignment it sets ``pinned``; the case snapshot
    and board version are then reported as that assignment's own for as long as
    the Lead has not marked it stale. Otherwise the first committed result
    would make every other job queued on the same snapshot look stale. Material
    versions are always live, so a revised document is still detected.
    """
    def __init__(self, workflow: Any):
        self.workflow = workflow
        self.pinned: Any | None = None

    def read(self, case_id: str, material_ids: tuple[str, ...]):
        from hera1 import VersionSnapshot
        if case_id != self.workflow.case_id:
            raise V3BridgeError("HERA requested versions for a different case")
        manifest = self.workflow.lead.manifest()
        snapshot_id, board_version = manifest.case_snapshot_id, str(manifest.board_version)
        pinned = self.pinned
        if pinned is not None:
            item = self.workflow.lead.work.get(pinned.assignment_id)
            if item is not None and item.state != JobState.STALE:
                snapshot_id = pinned.manifest.case_snapshot_id
                board_version = str(pinned.manifest.board_version)
        return VersionSnapshot(
            snapshot_id, board_version,
            {mid: self.workflow.materials[mid].version for mid in material_ids
             if mid in self.workflow.materials},
        )


class V3PackageBridge:
    """Execute queued CFERP work with injected standalone role engines.

    The host injects the LLM-backed engines. This class owns only translation,
    execution order, and returning normalized role deltas to the Lead.
    """
    def __init__(self, workflow: Any, *, specialist_engine: Any,
                 evidence_worker_engine: Any, assessor_engine: Any,
                 max_job_failures: int = 0):
        self.workflow = workflow
        # A role engine that reports its own output as rejected ends that job as
        # FAILED instead of the run, up to this many times. 0 aborts on the first.
        self.max_job_failures = max_job_failures
        self.job_failures: list[dict[str, Any]] = []
        self.specialist_engine = specialist_engine
        self.evidence_worker_engine = evidence_worker_engine
        self.assessor_engine = assessor_engine
        self.completed: list[tuple[str, str]] = []
        # Specialist prompts trimmed to leave room for the answer: what was left out, per job.
        self.prompt_omissions: list[dict[str, Any]] = []

    @classmethod
    def from_models(cls, workflow: Any, *, specialist_model: Any,
                    evidence_worker_model: Any, assessor_model: Any,
                    retriever: Any | None = None, specialist_config: Any | None = None,
                    worker_config: Any | None = None, assessor_config: Any | None = None):
        """Wire the three package model ports to archive-style ``ask`` clients."""
        from sahs.config import SpecialistConfig
        from sahs.history import InMemoryRunHistoryStore
        from sahs.proposal import OpenAICompatibleProposalGenerator
        from sahs.solver.clingo_solver import ClingoCandidateSolver
        from sahs.engine import SpecialistEngine
        from ewv3.config import WorkerConfig
        from ewv3.engine import EvidenceWorkerEngine
        from ewv3.proposal import ArchiveEvidencePlanner
        from ewv3.retrieval import default_retriever
        from hera1 import Hera1Engine
        from hera1.config import AssessorConfig
        from hera1.proposal import AskModelAdapter

        specialist = SpecialistEngine(OpenAICompatibleProposalGenerator(specialist_model),
            ClingoCandidateSolver(), InMemoryRunHistoryStore(), specialist_config or SpecialistConfig())
        worker = EvidenceWorkerEngine(ArchiveEvidencePlanner(evidence_worker_model),
            retriever or default_retriever(), config=worker_config or WorkerConfig())
        assessor = Hera1Engine(AskModelAdapter(assessor_model), WorkflowVersionReader(workflow),
            config=assessor_config or AssessorConfig())
        return cls(workflow, specialist_engine=specialist,
                   evidence_worker_engine=worker, assessor_engine=assessor)

    @classmethod
    def from_archive_config(cls, workflow: Any, config: dict[str, Any], *,
                            retriever: Any | None = None):
        """Use the archive's configured provider/model for each V3 role."""
        from shared.llm.factory import create_model_client
        llm = config["llm"]
        clients = {}
        for role in ("specialist", "evidence_worker", "assessor"):
            role_config = config["agents"][role]
            clients[role] = create_model_client(
                provider=role_config.get("provider", llm["provider"]),
                model=role_config.get("model", llm["model"]),
                base_url=role_config.get("base_url", llm.get("base_url")),
                timeout=llm.get("timeout", 120),
                response_format=llm.get("response_format", "json_object"),
                retries=llm.get("retries", 1),
            )
        return cls.from_models(workflow, specialist_model=clients["specialist"],
            evidence_worker_model=clients["evidence_worker"],
            assessor_model=clients["assessor"], retriever=retriever)

    def execute(self, assignment_id: str):
        assignment = self.workflow.assignments.get(assignment_id)
        if assignment is None:
            raise V3BridgeError(f"unknown Lead assignment {assignment_id}")
        state = self.workflow.lead.work[assignment_id].state
        if state == JobState.QUEUED:
            self.workflow.start_assignment(assignment_id)
        elif state != JobState.RUNNING:
            raise V3BridgeError(f"assignment {assignment_id} is not runnable: {state}")

        if assignment.role == Role.SPECIALIST:
            typed = sahs_assignment_from_cferp(assignment, self.workflow)
            output = self.specialist_engine.run(typed)
            omitted = (getattr(output, "resource_usage", None) or {}).get("prompt_omissions")
            if omitted:
                self.prompt_omissions.append({"assignment_id": assignment_id, "omitted": list(omitted)})
            if output.status not in {"completed", "open_frontier", "partial_budget",
                                     "no_candidate_under_supplied_rules", "no_op"}:
                created = self._reject(assignment, output.status,
                    f"SAHS rejected Lead assignment {assignment_id}: {output.status}: {output.diagnostics}")
            else:
                packet = sahs_result_to_cferp(output, assignment)
                created = self.workflow.submit_specialist_result(packet)
        elif assignment.role == Role.EVIDENCE_WORKER:
            typed = ew_assignment_from_cferp(assignment, self.workflow)
            output = self.evidence_worker_engine.run(typed)
            if output.status == "no_candidate_in_scope" and output.slot_results:
                # Searched and found nothing relevant: a finding about coverage,
                # not a failed job. Nothing is sent to the Assessor.
                packet = ew_result_to_cferp(output, assignment)
                created = self.workflow.submit_worker_result(packet)
            elif output.status != "ready_for_assessor":
                created = self._reject(assignment, output.status,
                    f"EWV3 did not return an assessor packet: {output.status}: {output.diagnostics}")
            else:
                packet = ew_result_to_cferp(output, assignment)
                created = self.workflow.submit_worker_result(packet)
        elif assignment.role == Role.ASSESSOR:
            task = hera_task_from_cferp(assignment, self.workflow)
            reader = getattr(self.assessor_engine, "versions", None)
            pin = isinstance(reader, WorkflowVersionReader)
            if pin:
                reader.pinned = assignment
            try:
                output = self.assessor_engine.run(task)
            finally:
                if pin:
                    reader.pinned = None
            if output.status == "stale":
                created = self._submit_stale_assessor(assignment, task, output)
            elif output.status != "completed":
                created = self._reject(assignment, output.status,
                    f"HERA returned {output.status} for {assignment_id}: {tuple(output.diagnostics)}")
            else:
                packet = hera_result_to_cferp(output, task, assignment)
                created = self.workflow.submit_assessor_result(packet)
        else:
            raise V3BridgeError(f"unsupported Lead role: {assignment.role}")

        self.completed.append((assignment_id, assignment.role.value))
        return output, tuple(created)

    def _reject(self, assignment: Any, status: str, message: str) -> tuple:
        """Record a role result its own engine rejected, then let the run continue.

        Only an engine-reported rejection comes here. A commit-gate or adapter
        error, or a disagreement between HERA and CFERP, still raises: those
        point at the harness, not at one bad model reply. Nothing is committed
        for the job, and it never counts as evidence.
        """
        if len(self.job_failures) >= self.max_job_failures:
            limit = f" (job failure limit {self.max_job_failures} reached)" if self.max_job_failures else ""
            raise V3BridgeError(message + limit)
        self.workflow.fail_assignment(assignment.assignment_id, message)
        self.job_failures.append({
            "assignment_id": assignment.assignment_id, "role": assignment.role.value,
            "task_kind": assignment.context.get("task_kind"), "status": status,
            "target_ids": list(assignment.target_ids), "message": message})
        return ()

    def _submit_stale_assessor(self, assignment: Any, task: Any, output: Any):
        """Hand a stale HERA result to CFERP's requeue path, if CFERP agrees.

        CFERP only requeues work the Lead has marked stale. If HERA reports
        stale input but CFERP still holds the assignment as current, the two
        disagree about the inputs; fail with HERA's reason, never commit.
        """
        item = self.workflow.lead.work[assignment.assignment_id]
        if item.state != JobState.STALE:
            raise V3BridgeError(
                f"HERA reported stale input for {assignment.assignment_id} but CFERP still "
                f"holds it as {item.state.value}: {tuple(getattr(output, 'diagnostics', ()))}")
        stale = RoleResult(f"hera:{task.task_id}", assignment.assignment_id, Role.ASSESSOR,
                           assignment.manifest, {"task_kind": task.task_kind})
        return self.workflow.submit_assessor_result(stale)

    def run_ready(self, *, max_jobs: int = 100,
                  roles: set[Role] | None = None) -> tuple[tuple[str, str], ...]:
        """Drain runnable specialist/worker/assessor assignments in Lead order.

        Work waiting for an external response or a Lead decision remains open;
        the caller can register that event and invoke this method again. Queued
        work that no concurrency slot can take yet also stays queued.
        """
        if max_jobs < 1:
            raise ValueError("max_jobs must be positive")
        start_count = len(self.completed)
        while len(self.completed) - start_count < max_jobs:
            ready = [item for item in self.workflow.lead.work.values()
                     if item.state == JobState.QUEUED and item.work_id in self.workflow.assignments
                     and (roles is None or item.role in roles)]
            if not ready:
                break
            # CFERP sequence is the stable tie-breaker after its priority queue.
            ready.sort(key=lambda item: (item.priority_tier, item.created_sequence))
            # A job whose role slot is full waits for a running or awaiting job
            # to finish; it must not block runnable work queued behind it.
            startable = next((item for item in ready if self.workflow.lead.can_start(item.work_id)), None)
            if startable is None:
                break
            self.execute(startable.work_id)
        return tuple(self.completed[start_count:])
