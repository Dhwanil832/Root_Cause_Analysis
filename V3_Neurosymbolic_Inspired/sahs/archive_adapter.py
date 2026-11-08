"""Boundary adapter for the supplied RCA V1/V2 Investigator and model client.

This adapter reuses only the archive's Specialist model transport and public
case snapshot. It does not call V1/V2 frontier normalization and does not
commit into the archive's shared kernel/board.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .config import SpecialistConfig
from .contracts import CandidateStatus, SpecialistHistory
from .engine import SpecialistEngine
from .engine_contracts import (
    CausalGraph,
    CausalRuleCandidate,
    Proposition,
    SourceChunk,
    SpecialistAssignment,
)
from .history import InMemoryRunHistoryStore, RunHistoryStore
from .proposal import OpenAICompatibleProposalGenerator
from .prompt_builder import SYSTEM_INSTRUCTIONS
from .solver.clingo_solver import ClingoCandidateSolver


class ArchiveSpecialistAdapter:
    """Run SAHS using the archive's configured Specialist transport.

    The caller supplies `history` returned by the previous SAHS run. When
    omitted, a compatible empty history is created for the current snapshot.
    The method is side-effect-free with respect to archive board state.
    """

    def __init__(
        self,
        investigator: Any,
        *,
        history_store: RunHistoryStore | None = None,
        config: SpecialistConfig | None = None,
        solver: Any | None = None,
    ) -> None:
        models = getattr(investigator, "_models", None)
        model = models.get("specialist") if isinstance(models, dict) else None
        if model is None:
            raise ValueError("archive Investigator has no configured Specialist model")
        self.investigator = investigator
        self.model = model
        self.history_store = history_store or InMemoryRunHistoryStore()
        self.config = config or SpecialistConfig()
        self.solver = solver or ClingoCandidateSolver()
        self.proposer = _AuditedArchiveProposalGenerator(investigator, model)
        self.engine = SpecialistEngine(self.proposer, self.solver, self.history_store, self.config)

    def run(self, assignment: SpecialistAssignment):
        return self.engine.run(assignment)

    @staticmethod
    def assignment_from_archive(
        investigator: Any,
        *,
        assignment_id: str,
        operation_goal: str,
        lead_direction: Any,
        history: SpecialistHistory | None = None,
        mode: str | None = None,
        focal_proposition_id: str | None = None,
        target_proposition_ids: tuple[str, ...] = (),
        changed_ids: tuple[str, ...] = (),
        explicitly_targeted_candidate_ids: tuple[str, ...] = (),
        lead_feedback: tuple[Any, ...] = (),
        assessor_annotations: tuple[Any, ...] = (),
        budgets: dict[str, Any] | None = None,
        specialist_scope_id: str = "specialist:general",
    ) -> SpecialistAssignment:
        session = investigator.session
        kernel = session.kernel
        revision = int(kernel.revision)
        board_version = f"b{revision}"
        case_snapshot_id = f"{session.case_id}:r{revision}"
        if history is None:
            history = SpecialistHistory(
                schema_version="1",
                specialist_scope_id=specialist_scope_id,
                history_version="h0",
                case_snapshot_id=case_snapshot_id,
                board_version=board_version,
            )
        if mode is None:
            mode = "revision" if history.candidates else "initial"

        propositions: dict[str, Proposition] = {}
        rules: dict[str, CausalRuleCandidate] = {}
        claims = investigator._claim_projection() if callable(getattr(investigator, "_claim_projection", None)) else list(investigator.claims.values())
        for claim in claims:
            claim_id = str(claim.get("claim_id") or "").strip()
            if not claim_id:
                continue
            label = str(claim.get("semantic_label") or claim.get("key") or claim_id)
            positive = claim.get("positive", True)
            # Preserve polarity in the proposition text. A reported negative
            # claim is still a report; it must not be rewritten as an unknown
            # positive claim by the adapter.
            if positive is False:
                label = f"It was reported that {label} did not occur"
            propositions[claim_id] = Proposition(
                claim_id, label, "case_claim", "reported",
                time_scope=str(claim.get("scope") or "incident"),
            )

        focal_text = getattr(investigator, "focal_event", "")
        if isinstance(focal_text, str) and focal_text.strip() and "not yet received" not in focal_text.casefold():
            focal_id = "archive:focal-event"
            propositions.setdefault(focal_id, Proposition(
                focal_id, focal_text.strip(), "incident_event", "reported", time_scope="incident"
            ))
            if mode == "initial" and not target_proposition_ids:
                target_proposition_ids = (focal_id,)

        for hypothesis in getattr(investigator, "hypotheses", {}).values():
            hypothesis_id = str(hypothesis.get("id") or hypothesis.get("hypothesis_id") or "").strip()
            if hypothesis_id:
                propositions[hypothesis_id] = Proposition(
                    hypothesis_id,
                    str(hypothesis.get("summary") or hypothesis.get("text") or hypothesis_id),
                    "incident_event", "hypothetical",
                )

        for gap in getattr(investigator, "gaps", {}).values():
            gap_id = str(gap.get("id") or gap.get("gap_id") or "").strip()
            if gap_id:
                propositions.setdefault(gap_id, Proposition(
                    gap_id, str(gap.get("question") or gap.get("semantic_label") or gap_id),
                    "unknown_condition", "unresolved",
                ))

        for index, rule in enumerate(kernel.rules):
            rule_id = f"archive-rule:{rule.id}"
            antecedents = tuple(key.label() for key in rule.premises)
            consequent = rule.conclusion.label()
            for key in (*rule.premises, rule.conclusion):
                proposition_id = key.label()
                propositions.setdefault(proposition_id, Proposition(
                    proposition_id, key.proposition, "case_claim", "unresolved",
                    time_scope=key.event_scope,
                ))
            rules[rule_id] = CausalRuleCandidate(
                rule_id=rule_id,
                antecedent_ids=antecedents,
                consequent_id=consequent,
                relation="contributes_to",
                modality="conditional",
                conditions=(str(rule.warrant),) if rule.warrant else (),
                basis="model_proposed",
                status="candidate",
            )

        sources = []
        for source_id, document in sorted(session.documents.items()):
            source = kernel.sources.get(source_id)
            version = str(source.version if source else 1)
            origin = str(document.get("origin") or "case_document")
            sources.append(SourceChunk(source_id, version, f"{source_id}:0", str(document.get("text") or ""), origin))

        graph = CausalGraph(
            tuple(propositions[key] for key in sorted(propositions)),
            tuple(rules[key] for key in sorted(rules)),
        )
        case_packet = None
        if mode == "initial":
            case_packet = {
                "focal_event": focal_text,
                "claims": claims,
                "case_id": session.case_id,
            }
        return SpecialistAssignment(
            schema_version="1",
            assignment_id=assignment_id,
            case_id=session.case_id,
            specialist_scope_id=specialist_scope_id,
            case_snapshot_id=case_snapshot_id,
            board_version=board_version,
            history_version=history.history_version,
            mode=mode,
            operation_goal=operation_goal,
            lead_direction=lead_direction,
            relevant_graph=graph,
            source_bundle=tuple(sources),
            history=history,
            focal_proposition_id=focal_proposition_id,
            target_proposition_ids=tuple(target_proposition_ids),
            available_proposition_ids=tuple(sorted(graph.proposition_map())),
            initial_case_packet=case_packet,
            lead_feedback=tuple(lead_feedback),
            assessor_annotations=tuple(assessor_annotations),
            changed_ids=tuple(changed_ids),
            explicitly_targeted_candidate_ids=tuple(explicitly_targeted_candidate_ids),
            budgets=budgets or {},
        )


class _AuditedArchiveProposalGenerator(OpenAICompatibleProposalGenerator):
    def __init__(self, investigator: Any, model: Any) -> None:
        super().__init__(model, SYSTEM_INSTRUCTIONS)
        self.investigator = investigator

    def propose(self, request):
        before = len(getattr(self.model, "calls", ()))
        result = super().propose(request)
        calls = getattr(self.model, "calls", ())
        if len(calls) > before:
            record = calls[-1]
            if hasattr(self.investigator, "model_calls"):
                self.investigator.model_calls.append(record)
            if hasattr(self.investigator, "model_input_history"):
                self.investigator.model_input_history.append({
                    "role": "specialist_v3_sahs",
                    "task": "sahs_proposal",
                    "attempt": 0,
                    "payload": request.context,
                    "prompt_sha256": __import__("hashlib").sha256(self.system_prompt.encode()).hexdigest(),
                    "model": getattr(record, "model", "unknown"),
                    "actual_provider_completion": getattr(record, "actual_call_performed", None),
                })
            if hasattr(self.investigator, "last_model_name"):
                self.investigator.last_model_name = getattr(record, "model", "unknown")
        return result
