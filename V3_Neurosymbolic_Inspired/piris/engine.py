"""Bounded orchestration for the standalone PIRIS Intake package."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from uuid import uuid4

from .contracts import (
    ExtractionResult, IncomingItem, IntakeAssignment, IntakeResult, IntakeState,
    InterpretationRequest, ItemSuggestion, LinkBasis, LinkRecord,
    MaterialArrivalEvent, MaterialProcessingUpdate, MaterialRecord,
    RequestReference, SubmissionItemRecord,
)
from .ports import ContentParser, IntakeInterpreter, MaterialIndexer, UnsafeContentError
from .store import InMemoryIntakeStore


class IntakeEngine:
    """Register incoming material, prepare searchable renditions, and notify the Lead.

    The engine never judges evidence, changes the causal board, or contacts the
    submitter. Store/parser/indexer/interpreter ports are replaceable.
    """

    def __init__(self, *, parser: ContentParser, indexer: MaterialIndexer,
                 store: InMemoryIntakeStore | None = None,
                 interpreter: IntakeInterpreter | None = None,
                 safety_scanner=None, max_interpretation_items: int = 20,
                 max_open_requests_for_interpretation: int = 50,
                 max_interpretation_chars: int = 12000) -> None:
        if min(max_interpretation_items, max_open_requests_for_interpretation,
               max_interpretation_chars) < 1:
            raise ValueError("interpretation limits must be positive")
        self.parser = parser
        self.indexer = indexer
        self.store = store or InMemoryIntakeStore()
        self.interpreter = interpreter
        self.safety_scanner = safety_scanner
        self.max_interpretation_items = max_interpretation_items
        self.max_open_requests_for_interpretation = max_open_requests_for_interpretation
        self.max_interpretation_chars = max_interpretation_chars

    def run(self, assignment: IntakeAssignment) -> IntakeResult:
        errors = self._validate_assignment(assignment)
        if errors:
            return self._failure(assignment, IntakeState.FAILED, tuple(errors))

        fingerprint = self.store.fingerprint({
            "case_id": assignment.case_id,
            "case_snapshot_id": assignment.case_snapshot_id,
            "sender_id": assignment.sender_id,
            "metadata": assignment.metadata,
            "items": [
                (i.item_id, sha256(i.content).hexdigest(), i.media_type, i.filename,
                 i.declared_kind, i.declared_request_id, i.declared_revision_of,
                 i.metadata) for i in assignment.items
            ],
        })
        claim, previous = self.store.begin(assignment.submission_id, fingerprint)
        if claim == "duplicate":
            return previous
        if claim == "conflict":
            return self._failure(assignment, IntakeState.FAILED,
                                 ("submission_id_reused_with_different_content",))
        if claim == "busy":
            return self._failure(assignment, IntakeState.RECEIVED,
                                 ("submission_processing_already_in_progress",))

        try:
            result = self._process(assignment)
            self.store.finish(result)
            return result
        except Exception:
            self.store.abandon(assignment.submission_id)
            raise

    def complete_indexing(self, material_id: str, *, status: str,
                          detail: str = "") -> MaterialProcessingUpdate:
        """Record an async index completion and return a Lead-facing update event."""
        if status not in {"ready", "partial", "failed"}:
            raise ValueError("index completion status must be ready, partial, or failed")
        material = self.store.get_material(material_id)
        if material is None:
            raise KeyError(f"unknown material_id: {material_id}")
        current_record = self.store.indexed_record(material_id) or {}
        current_status = current_record.get("status", material.index_status)
        if current_status in {"ready", "partial", "failed"}:
            if current_status != status:
                raise ValueError(
                    f"indexing already completed as {current_status}; a new index attempt is required"
                )
            event_id = f"index-update:{material_id}:{material.version_id}:{status}"
            existing = next((event for event in self.store.processing_updates()
                             if event.event_id == event_id), None)
            if existing is not None:
                return existing
            raise ValueError("no pending indexing operation exists for this material")
        if status in {"ready", "partial"} and (
            not material.extraction.text
            or material.extraction.status not in {"ready", "partial"}
        ):
            raise ValueError("material has no valid extracted text to index")
        updated = replace(material, index_status=status)
        self.store.update_material(updated)
        index_record = self.store.indexed_record(material_id) or {}
        index_record.update({"status": status, "version_id": material.version_id,
                             "detail": detail})
        self.store.index_material(material_id, index_record)
        event = MaterialProcessingUpdate(
            event_id=f"index-update:{material_id}:{material.version_id}:{status}",
            case_id=material.case_id, material_id=material_id,
            version_id=material.version_id, submission_ids=material.submission_ids,
            processing_stage="indexing", status=status, detail=detail,
        )
        return self.store.record_processing_update(event)

    def _process(self, a: IntakeAssignment) -> IntakeResult:
        request_map = {r.request_id: r for r in a.request_catalog}
        pending = tuple(r for r in a.request_catalog
                        if r.status.casefold() in {"pending", "open", "active", "waiting_external"})
        digest_by_item = {item.item_id: sha256(item.content).hexdigest() for item in a.items}
        item_records: list[SubmissionItemRecord] = []
        processed_materials: dict[str, MaterialRecord] = {}
        item_materials: dict[str, MaterialRecord] = {}
        diagnostics: list[str] = []
        quarantined_ids: set[str] = set()
        index_calls = 0
        parser_calls = 0
        for item in a.items:
            digest = digest_by_item[item.item_id]
            safe, safety_warning = self._check_safety(item)
            with self.store.material_identity_lock(a.case_id, digest, item.media_type):
                existing = self.store.get_material_by_digest(a.case_id, digest, item.media_type)
                if existing is not None:
                    material, created = existing, False
                    if safe and a.submission_id not in material.submission_ids:
                        material = self.store.add_submission_to_material(material.material_id, a.submission_id)
                    if safety_warning:
                        diagnostics.append(f"{item.item_id}:{safety_warning}")
                    if not safe:
                        quarantined_ids.add(item.item_id)
                        diagnostics.append(f"{item.item_id}:duplicate_content_quarantined_for_this_submission")
                    elif (material.extraction.status == "failed"
                          or (material.extraction.status == "unsupported"
                              and self._unsupported_parser_changed(
                                  item.media_type, material.extraction
                              ))):
                        # A prior parser outage, unsupported format, or quarantine
                        # must not permanently poison an otherwise safe material.
                        parser_calls += 1
                        material = replace(material, extraction=self._extract(item))
                        self.store.update_material(material)
                else:
                    parser_calls += int(safe)
                    extraction = self._extract(item) if safe else ExtractionResult(
                        status="failed", parser_name="not_run",
                        warnings=(safety_warning or "content_quarantined",))
                    material_id = f"mat_{uuid4().hex}"
                    revision_of, _revision_status = self._revision_link(
                        a.case_id, item.declared_revision_of, material_id
                    )
                    material = MaterialRecord(
                        material_id=material_id, case_id=a.case_id, content_digest=digest,
                        media_type=item.media_type, filename=item.filename,
                        declared_kind=item.declared_kind, content=item.content,
                        version_id=f"sha256:{digest}", revision_of=revision_of,
                        extraction=extraction, submission_ids=(a.submission_id,),
                        created_at=a.received_at,
                    )
                    material, created = self.store.add_material_if_absent(material)
                    if not created:
                        material = self.store.add_submission_to_material(material.material_id, a.submission_id)
                    if safety_warning:
                        diagnostics.append(f"{item.item_id}:{safety_warning}")
                    if not safe:
                        quarantined_ids.add(item.item_id)

            if material.material_id not in processed_materials:
                material, indexed_call = self._ensure_indexed(material, diagnostics)
                index_calls += int(indexed_call)
                self.store.update_material(material)
                processed_materials[material.material_id] = material
            else:
                material = processed_materials[material.material_id]
            item_materials[item.item_id] = material

            links = self._links(item, None, request_map, pending, diagnostics)
            rev_of, rev_status = self._revision_link(a.case_id, item.declared_revision_of,
                                                     material.material_id)
            if not created and item.declared_revision_of:
                rev_of, rev_status = None, "same_content_no_new_version"
            item_warnings = list(material.extraction.warnings)
            if safety_warning:
                item_warnings.append(safety_warning)
            if rev_status != "none":
                item_warnings.append(f"revision_link:{rev_status}")
            item_records.append(SubmissionItemRecord(
                item_id=item.item_id, material_id=material.material_id,
                content_digest=digest, media_type=item.media_type, filename=item.filename,
                declared_kind=item.declared_kind,
                suggested_kind="", links=links,
                declared_revision_of=item.declared_revision_of,
                revision_link_status=rev_status,
                exact_duplicate_content=not created,
                extraction_status=material.extraction.status,
                index_status=self.store.indexed_record(material.material_id).get("status", "failed")
                    if self.store.indexed_record(material.material_id) else "failed",
                quarantined=item.item_id in quarantined_ids,
                warnings=tuple(dict.fromkeys(item_warnings)),
            ))

        eligible_item_materials = {item_id: material for item_id, material in item_materials.items()
                                   if item_id not in quarantined_ids}
        suggestions = self._interpret(a, pending, eligible_item_materials, diagnostics)
        suggestion_map = {s.item_id: s for s in suggestions}
        item_records = [replace(
            record,
            suggested_kind=suggestion_map[record.item_id].suggested_kind,
            links=self._links(
                next(i for i in a.items if i.item_id == record.item_id),
                suggestion_map[record.item_id], request_map, pending, diagnostics,
            ),
        ) if record.item_id in suggestion_map else record for record in item_records]

        states = {r.extraction_status for r in item_records}
        indexed_states = {r.index_status for r in item_records}
        if (not quarantined_ids and all(s == "ready" for s in states)
                and all(s == "ready" for s in indexed_states)):
            state = IntakeState.READY
        elif (not quarantined_ids and any(s == "pending" for s in indexed_states)
              and all(s in {"ready", "partial"} for s in states)
              and all(s in {"ready", "pending"} for s in indexed_states)):
            state = IntakeState.REGISTERED
        else:
            state = IntakeState.PARTIAL

        event = MaterialArrivalEvent(
            event_id=f"arrival:{a.submission_id}", case_id=a.case_id,
            case_snapshot_id=a.case_snapshot_id, submission_id=a.submission_id,
            received_at=a.received_at, sender_id=a.sender_id, state=state,
            item_records=tuple(item_records), warnings=tuple(diagnostics),
        )
        interpreter_eligible = any(
            item.item_id in eligible_item_materials
            and (not item.declared_kind or
                 (item.media_type.startswith("text/") and not item.declared_request_id))
            for item in a.items
        )
        result = IntakeResult(
            schema_version="1", submission_id=a.submission_id, event=event,
            materials=tuple(processed_materials.values()), diagnostics=tuple(diagnostics),
            resource_usage={
                "items_received": len(a.items),
                "parser_calls": parser_calls,
                "interpreter_calls": int(bool(self.interpreter and interpreter_eligible)),
                "index_calls": index_calls,
            },
        )
        return result

    def _interpret(self, a: IntakeAssignment,
                   pending: tuple[RequestReference, ...],
                   item_materials: dict[str, MaterialRecord],
                   diagnostics: list[str]) -> tuple[ItemSuggestion, ...]:
        if not self.interpreter or not self._needs_interpretation(a):
            return ()
        eligible = [i for i in a.items if i.item_id in item_materials
                    and (not i.declared_kind or not i.declared_request_id)]
        if len(eligible) > self.max_interpretation_items:
            diagnostics.append("metadata_interpretation_item_limit_reached")
            diagnostics.append(f"metadata_interpretation_items_omitted:{len(eligible) - self.max_interpretation_items}")
        if len(pending) > self.max_open_requests_for_interpretation:
            diagnostics.append("metadata_interpretation_request_limit_reached")
            diagnostics.append(f"metadata_interpretation_requests_omitted:{len(pending) - self.max_open_requests_for_interpretation}")
        if any(len(item_materials[i.item_id].extraction.text) > self.max_interpretation_chars
               for i in eligible):
            diagnostics.append("metadata_interpretation_text_limit_reached")
        inputs = tuple(InterpretationRequest(
            item_id=i.item_id, filename=i.filename, media_type=i.media_type,
            declared_kind=i.declared_kind,
            extracted_text=item_materials[i.item_id].extraction.text[:self.max_interpretation_chars],
        ) for i in eligible[:self.max_interpretation_items])
        if not inputs:
            return ()
        selected_requests = pending[:self.max_open_requests_for_interpretation]
        bounded_requests = tuple(
            replace(request, description=request.description[:1000])
            for request in selected_requests
        )
        if any(len(request.description) > 1000 for request in selected_requests):
            diagnostics.append("metadata_interpretation_request_description_limit_reached")
        try:
            raw = self.interpreter.interpret(inputs, bounded_requests)
        except Exception as exc:
            diagnostics.append(f"metadata_interpretation_failed:{type(exc).__name__}")
            return ()
        if not isinstance(raw, (tuple, list)):
            diagnostics.append("invalid_metadata_interpreter_result")
            return ()
        # A model may only annotate items actually included in its request,
        # including when the context was truncated to meet the configured cap.
        valid_ids = {item.item_id for item in inputs}
        out: list[ItemSuggestion] = []
        suggestions_by_item: dict[str, int] = {}
        for suggestion in raw:
            if isinstance(suggestion, ItemSuggestion) and isinstance(suggestion.item_id, str):
                suggestions_by_item[suggestion.item_id] = suggestions_by_item.get(suggestion.item_id, 0) + 1
        for suggestion in raw:
            if (not isinstance(suggestion, ItemSuggestion)
                    or not isinstance(suggestion.item_id, str)
                    or not isinstance(suggestion.suggested_kind, str)
                    or not isinstance(suggestion.request_ids, (tuple, list))
                    or not all(isinstance(rid, str) for rid in suggestion.request_ids)
                    or not isinstance(suggestion.note, str)):
                diagnostics.append("invalid_metadata_suggestion_discarded")
                continue
            if suggestion.item_id not in valid_ids:
                diagnostics.append("metadata_suggestion_unknown_or_duplicate_item_id")
                continue
            if suggestions_by_item.get(suggestion.item_id, 0) > 1:
                diagnostics.append(f"{suggestion.item_id}:duplicate_metadata_suggestions_discarded")
                continue
            if len(suggestion.suggested_kind) > 200 or len(suggestion.note) > 1000:
                diagnostics.append(f"{suggestion.item_id}:oversized_metadata_suggestion_discarded")
                continue
            # Only currently open requests can be suggested by the model.
            allowed = {r.request_id for r in pending}
            if any(rid not in allowed for rid in suggestion.request_ids):
                diagnostics.append(f"{suggestion.item_id}:invalid_model_request_link_discarded")
            out.append(replace(suggestion,
                               request_ids=tuple(rid for rid in suggestion.request_ids if rid in allowed)))
        return tuple(out)

    @staticmethod
    def _needs_interpretation(a: IntakeAssignment) -> bool:
        return any(not item.declared_kind or
                   (item.media_type.startswith("text/") and not item.declared_request_id)
                   for item in a.items)

    def _check_safety(self, item: IncomingItem) -> tuple[bool, str]:
        if not self.safety_scanner:
            return True, ""
        try:
            verdict = self.safety_scanner.scan(item.content, item.media_type, item.filename)
            if verdict is False:
                return False, "content_quarantined_by_safety_scanner"
            if verdict is not True:
                return False, "safety_scanner_invalid_verdict"
            return True, ""
        except UnsafeContentError as exc:
            return False, f"content_quarantined:{type(exc).__name__}"
        except Exception as exc:
            # Fail closed for parsing/indexing if the safety gate itself failed.
            return False, f"safety_scan_failed:{type(exc).__name__}"

    def _extract(self, item: IncomingItem) -> ExtractionResult:
        try:
            result = self.parser.parse(item)
            return self._validate_extraction(result)
        except Exception as exc:
            return ExtractionResult(status="failed", parser_name=type(self.parser).__name__,
                                   warnings=(f"parser_error:{type(exc).__name__}",))

    def _parser_signature(self, media_type: str) -> tuple[str, str]:
        registry = getattr(self.parser, "parsers", None)
        parser = registry.get(media_type) if isinstance(registry, dict) else None
        if parser is None and (media_type.startswith("text/") or media_type == "application/json"):
            parser = getattr(self.parser, "text_parser", None)
        if parser is None:
            parser = self.parser
        return (type(parser).__name__, str(getattr(parser, "version", "")))

    def _unsupported_parser_changed(self, media_type: str,
                                    extraction: ExtractionResult) -> bool:
        parser_name, parser_version = self._parser_signature(media_type)
        if extraction.parser_name == "ParserRouter":
            return parser_name != "ParserRouter" or bool(parser_version)
        return bool(parser_version and parser_version != extraction.parser_version)

    @staticmethod
    def _validate_extraction(result: ExtractionResult) -> ExtractionResult:
        warnings = list(result.warnings)
        if result.status not in {"ready", "partial", "unsupported", "failed"}:
            return ExtractionResult(status="failed", parser_name=result.parser_name,
                                   parser_version=result.parser_version,
                                   warnings=tuple(warnings + ["invalid_parser_status"]))
        ids: set[str] = set()
        for segment in result.segments:
            if not segment.segment_id or segment.segment_id in ids:
                warnings.append("duplicate_or_empty_segment_id")
                return replace(result, status="failed", warnings=tuple(warnings))
            ids.add(segment.segment_id)
            loc = segment.location
            if loc.page is not None and (type(loc.page) is not int or loc.page < 1):
                warnings.append(f"invalid_source_page:{segment.segment_id}")
                return replace(result, status="failed", warnings=tuple(warnings))
            if (loc.start_offset is not None or loc.end_offset is not None):
                if (type(loc.start_offset) is not int or type(loc.end_offset) is not int
                    or not (
                    0 <= loc.start_offset <= loc.end_offset <= len(result.text)
                    )):
                    warnings.append(f"invalid_source_offsets:{segment.segment_id}")
                    return replace(result, status="failed", warnings=tuple(warnings))
                if result.text[loc.start_offset:loc.end_offset] != segment.text:
                    warnings.append(f"source_span_mismatch:{segment.segment_id}")
                    return replace(result, status="failed", warnings=tuple(warnings))
        return replace(result, warnings=tuple(dict.fromkeys(warnings)))

    def _ensure_indexed(self, material: MaterialRecord,
                        diagnostics: list[str]) -> tuple[MaterialRecord, bool]:
        with self.store.material_operation_lock(material.material_id):
            # Re-read after acquiring the lock: another submission may have
            # completed indexing while this run was waiting.
            current = self.store.get_material(material.material_id) or material
            return self._ensure_indexed_locked(current, diagnostics)

    def _ensure_indexed_locked(self, material: MaterialRecord,
                               diagnostics: list[str]) -> tuple[MaterialRecord, bool]:
        existing = self.store.indexed_record(material.material_id)
        indexer_version = getattr(self.indexer, "version", "unknown")
        if (existing and existing.get("version_id") == material.version_id
                and existing.get("indexer_version") == indexer_version
                and existing.get("status") in {"ready", "partial", "pending"}):
            return replace(material, index_status=existing["status"]), False
        extraction = material.extraction
        if extraction.status not in {"ready", "partial"} or not extraction.text:
            self.store.index_material(material.material_id, {
                "status": "failed", "version_id": material.version_id,
                "reason": "no_searchable_extraction",
            })
            return replace(material, index_status="failed"), False
        try:
            status = self.indexer.index(
                material_id=material.material_id, version_id=material.version_id,
                representation_id=f"{material.material_id}:{extraction.parser_name}:{extraction.parser_version}",
                text=extraction.text, segments=extraction.segments,
            )
            if status not in {"ready", "partial", "pending", "failed"}:
                status = "failed"
                diagnostics.append(f"{material.material_id}:invalid_indexer_status")
            self.store.index_material(material.material_id, {
                "status": status, "version_id": material.version_id,
                "indexer_version": indexer_version,
            })
            if status != "ready":
                diagnostics.append(f"{material.material_id}:index_{status}")
        except Exception as exc:
            self.store.index_material(material.material_id, {
                "status": "failed", "version_id": material.version_id,
                "error": type(exc).__name__,
            })
            diagnostics.append(f"{material.material_id}:index_error:{type(exc).__name__}")
            status = "failed"
        return replace(material, index_status=status), True

    def _revision_link(self, case_id: str, declared_parent: str | None,
                       current_material_id: str) -> tuple[str | None, str]:
        if not declared_parent:
            return None, "none"
        if declared_parent == current_material_id:
            return None, "invalid_self_reference"
        parent = self.store.get_material(declared_parent)
        if not parent or parent.case_id != case_id:
            return None, "unresolved_declared_revision_parent"
        return declared_parent, "linked"

    @staticmethod
    def _links(item: IncomingItem, suggestion: ItemSuggestion | None,
               requests: dict[str, RequestReference], pending: tuple[RequestReference, ...],
               diagnostics: list[str]) -> tuple[LinkRecord, ...]:
        links: list[LinkRecord] = []
        if item.declared_request_id:
            ref = requests.get(item.declared_request_id)
            if ref:
                links.append(LinkRecord(ref.request_id, LinkBasis.SUBMITTER_DECLARED, ref.status))
            else:
                diagnostics.append(f"{item.item_id}:declared_request_link_unknown")
        if suggestion:
            pending_map = {r.request_id: r for r in pending}
            for rid in suggestion.request_ids:
                ref = pending_map.get(rid)
                if ref and not any(x.request_id == rid for x in links):
                    links.append(LinkRecord(rid, LinkBasis.MODEL_SUGGESTED,
                                            ref.status, suggestion.note))
        return tuple(links)

    @staticmethod
    def _validate_assignment(a: IntakeAssignment) -> list[str]:
        errors: list[str] = []
        if not isinstance(a, IntakeAssignment):
            return ["assignment_must_be_IntakeAssignment"]
        if a.schema_version != "1":
            errors.append("unsupported_schema_version")
        for field_name in ("case_id", "case_snapshot_id", "submission_id", "received_at"):
            value = getattr(a, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"missing_{field_name}")
        if not isinstance(a.items, (tuple, list)) or not a.items:
            errors.append("submission_has_no_items")
        if not isinstance(a.sender_id, str):
            errors.append("sender_id_must_be_string")
        if not isinstance(a.metadata, dict):
            errors.append("assignment_metadata_must_be_object")
        else:
            try:
                InMemoryIntakeStore.fingerprint(a.metadata)
            except (TypeError, ValueError):
                errors.append("assignment_metadata_must_be_json_compatible")
        ids: list[str] = []
        for item in a.items if isinstance(a.items, (tuple, list)) else ():
            if not isinstance(item, IncomingItem):
                errors.append("invalid_item_record")
                continue
            if not isinstance(item.item_id, str) or not item.item_id.strip():
                errors.append("item_id_missing")
            else:
                ids.append(item.item_id)
            if not isinstance(item.content, bytes):
                errors.append(f"{item.item_id}:content_must_be_bytes")
            for name in ("media_type", "filename", "declared_kind"):
                if not isinstance(getattr(item, name), str):
                    errors.append(f"{item.item_id}:invalid_{name}")
            for name in ("declared_request_id", "declared_revision_of"):
                value = getattr(item, name)
                if value is not None and (not isinstance(value, str) or not value.strip()):
                    errors.append(f"{item.item_id}:invalid_{name}")
            if not isinstance(item.metadata, dict):
                errors.append(f"{item.item_id}:metadata_must_be_object")
            else:
                try:
                    InMemoryIntakeStore.fingerprint(item.metadata)
                except (TypeError, ValueError):
                    errors.append(f"{item.item_id}:metadata_must_be_json_compatible")
        if len(ids) != len(set(ids)):
            errors.append("duplicate_item_id")
        if not isinstance(a.request_catalog, (tuple, list)):
            errors.append("request_catalog_must_be_sequence")
        else:
            request_ids: list[str] = []
            for request in a.request_catalog:
                if not isinstance(request, RequestReference):
                    errors.append("invalid_request_record")
                    continue
                if not isinstance(request.request_id, str) or not request.request_id.strip():
                    errors.append("request_id_missing")
                else:
                    request_ids.append(request.request_id)
                if not isinstance(request.status, str) or not isinstance(request.description, str):
                    errors.append("invalid_request_fields")
            if len(request_ids) != len(set(request_ids)):
                errors.append("duplicate_request_id")
        return errors

    @staticmethod
    def _failure(a: IntakeAssignment, state: IntakeState,
                 diagnostics: tuple[str, ...]) -> IntakeResult:
        if not isinstance(a, IntakeAssignment):
            event = MaterialArrivalEvent(
                event_id="arrival:invalid", case_id="", case_snapshot_id="",
                submission_id="", received_at="", sender_id="", state=state,
                item_records=(), warnings=diagnostics,
            )
            return IntakeResult("1", "", event, (), diagnostics,
                                {"items_received": 0, "parser_calls": 0,
                                 "interpreter_calls": 0, "index_calls": 0})
        event = MaterialArrivalEvent(
            event_id=f"arrival:{a.submission_id}", case_id=a.case_id,
            case_snapshot_id=a.case_snapshot_id, submission_id=a.submission_id,
            received_at=a.received_at, sender_id=a.sender_id, state=state,
            item_records=(), warnings=diagnostics,
        )
        return IntakeResult("1", a.submission_id, event, (), diagnostics,
                            {"items_received": len(a.items), "parser_calls": 0,
                             "interpreter_calls": 0, "index_calls": 0})

