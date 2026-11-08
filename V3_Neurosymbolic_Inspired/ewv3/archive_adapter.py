"""Read-only adapter for the supplied RCA archive's model and public documents.

This adapter is not registered in the archive's V1/V2 registry. It can be
selected by a future V3 integration without changing current behavior.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from dataclasses import asdict

from .contracts import (
    CorpusManifest, EvidenceAssignment, EvidenceWorkerResult, InformationNeed,
    SearchPassStatus, SourceUnit, WorkPhase,
)
from .engine import EvidenceWorkerEngine
from .ledger import InMemoryWorkLedger
from .ports import CorpusRetriever
from .proposal import ArchiveEvidencePlanner
from .retrieval import InMemoryRetriever
from .validation import fingerprint


class ArchiveEvidenceWorkerAdapter:
    def __init__(self, investigator: Any, *, retriever: CorpusRetriever | None = None,
                 ledger: InMemoryWorkLedger | None = None, config=None) -> None:
        models = getattr(investigator, "_models", None)
        model = models.get("evidence_worker") if isinstance(models, dict) else None
        if model is None:
            raise ValueError("archive Investigator has no configured Evidence Worker model")
        self.investigator = investigator
        self.planner = ArchiveEvidencePlanner(model, audit_sink=investigator)
        self.engine = EvidenceWorkerEngine(self.planner, retriever or InMemoryRetriever(),
                                           ledger=ledger, config=config)

    def run(self, assignment: EvidenceAssignment):
        current = self.assignment_from_archive(
            self.investigator,
            assignment_id=assignment.assignment_id,
            work_item_id=assignment.work_item_id,
            event_id=assignment.event_id,
            needs=assignment.needs,
            budgets=assignment.budgets,
        )
        if self._snapshot_changed(current, assignment):
            return self._held_result(assignment, "archive board or corpus was stale before the run")

        result = self.engine.run(assignment)
        current = self.assignment_from_archive(
            self.investigator,
            assignment_id=assignment.assignment_id,
            work_item_id=assignment.work_item_id,
            event_id=assignment.event_id,
            needs=assignment.needs,
            budgets=assignment.budgets,
        )
        changed = self._snapshot_changed(current, assignment)
        if changed:
            result = replace(result, status="held_for_reconciliation",
                             work_phase=WorkPhase.HELD,
                             diagnostics=(*result.diagnostics,
                                          "archive board or corpus changed during the run"))
            self.engine.ledger.finish(assignment.work_item_id, assignment.event_id,
                                      fingerprint(asdict(assignment)), result)
        return result

    @staticmethod
    def _snapshot_changed(current: EvidenceAssignment, assignment: EvidenceAssignment) -> bool:
        return (
            current.case_snapshot_id != assignment.case_snapshot_id
            or current.board_version != assignment.board_version
            or current.manifest.corpus_snapshot_id != assignment.manifest.corpus_snapshot_id
            or current.manifest.material_catalog_version != assignment.manifest.material_catalog_version
            or current.manifest.representation_version != assignment.manifest.representation_version
        )

    @staticmethod
    def _held_result(assignment: EvidenceAssignment, diagnostic: str) -> EvidenceWorkerResult:
        return EvidenceWorkerResult(
            schema_version="1", assignment_id=assignment.assignment_id,
            work_item_id=assignment.work_item_id, event_id=assignment.event_id,
            case_snapshot_id=assignment.case_snapshot_id, board_version=assignment.board_version,
            corpus_snapshot_id=assignment.manifest.corpus_snapshot_id,
            material_catalog_version=assignment.manifest.material_catalog_version,
            representation_version=assignment.manifest.representation_version,
            status="held_for_reconciliation", work_phase=WorkPhase.HELD,
            search_pass_status=SearchPassStatus.BLOCKED, diagnostics=(diagnostic,),
        )

    @staticmethod
    def assignment_from_archive(investigator: Any, *, assignment_id: str,
                                work_item_id: str, event_id: str,
                                needs: tuple[InformationNeed, ...],
                                budgets: dict[str, int] | None = None) -> EvidenceAssignment:
        session = investigator.session
        kernel = session.kernel
        revision = int(kernel.revision)
        docs = getattr(session, "documents", {})
        sources = []
        version_parts = []
        for source_id, document in sorted(docs.items()):
            source_meta = kernel.sources.get(source_id)
            version = str(getattr(source_meta, "version", 1))
            text = str(document.get("text") or "")
            rep_id = f"{source_id}:v{version}:text-v1"
            text_hash = __import__("hashlib").sha256(text.encode("utf-8")).hexdigest()
            version_parts.append((source_id, version, text_hash))
            sources.append(SourceUnit(
                source_id=str(source_id), source_version=version,
                representation_id=rep_id,
                title=str(document.get("title") or document.get("name") or source_id),
                text=text,
                source_kind=str(document.get("origin") or "case_document"),
                searchable=bool(text), readiness="ready" if text else "empty",
                origin=str(document.get("origin") or ""),
                lineage=str(document.get("lineage") or "unknown"),
                metadata={k: v for k, v in document.items() if k not in {"text", "title", "name"}},
            ))
        import hashlib, json
        digest = hashlib.sha256(json.dumps(version_parts, sort_keys=True).encode()).hexdigest()[:16]
        case_id = str(getattr(session, "case_id", "unknown-case"))
        case_snapshot_id = f"{case_id}:r{revision}"
        manifest = CorpusManifest(
            corpus_snapshot_id=f"{case_id}:corpus:{digest}",
            material_catalog_version=f"catalog:{digest}",
            representation_version=f"representations:{digest}",
            completeness_status="registered_scope_only",
            completeness_basis="archive adapter can inspect currently registered session documents only",
            expected_source_ids=tuple(str(x) for x in docs),
        )
        return EvidenceAssignment(
            schema_version="1", assignment_id=assignment_id,
            work_item_id=work_item_id, event_id=event_id, case_id=case_id,
            case_snapshot_id=case_snapshot_id, board_version=f"b{revision}",
            manifest=manifest, needs=needs, sources=tuple(sources),
            allowed_source_ids=tuple(s.source_id for s in sources),
            budgets=budgets or {},
        )
