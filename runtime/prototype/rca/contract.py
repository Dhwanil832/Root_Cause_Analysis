"""Shared mechanical contract. This describes admissibility, never causal truth."""
VERSION = '2026-10-04-dependency-repair-2'
ID_PATTERN = r'[A-Za-z][A-Za-z0-9_-]{0,79}'
STATUSES = {
    'node': ['reported', 'candidate', 'supported', 'refuted', 'unresolved', 'conflicting', 'withdrawn'],
    'edge': ['candidate', 'supported', 'refuted', 'unresolved', 'conflicting', 'withdrawn'],
    'request': ['proposed', 'searching', 'awaiting_user', 'partial', 'answered', 'blocked', 'terminated'],
}
SOURCE_REQUIRED = ['supported', 'refuted', 'conflicting', 'answered', 'blocked']
UNIQUE_LISTS = ['sources', 'depends_on', 'from_ids', 'fields']

def instructions():
    return f'''MECHANICAL UPDATE CONTRACT {VERSION}
Return only the JSON object described by the schema. Schema validation is followed by state/role validation; a valid JSON shape is not a valid causal judgment.
create: record.id must never have existed in the ledger; expected_version=0; replaces=null. A committed new record starts at version 1.
revise: existing active record.id, expected_version=current ledger version, replaces=null. Preserve kind, claim and scope_key exactly. For edges preserve endpoint membership and mode. For requests preserve asset exactly; window and requested fields may be refined with a concrete reason.
replace: a fresh record.id; replaces=old ledger record ID; expected_version=old current version; SAME kind as the old record. Retire the old record and update all live dependents in the same operations batch. Use separate records, not replacement, to represent different kinds.
Operations execute in listed order on a tentative ledger; final dependency checks are atomic. Nothing commits when a batch fails. Consult feedback.errors, correct the cited field, and resubmit justified operations against CURRENT versions. Do not invent evidence to satisfy a gate.
Record IDs must match {ID_PATTERN}. claim, scope_key and operation.reason must be nonblank. These lists contain unique strings: {', '.join(UNIQUE_LISTS)}.
Status by kind: {STATUSES}. Nonempty sources are required for {SOURCE_REQUIRED}; mere citation does not establish truth.
node: from_ids=[], to_id=null, mode=null, asset=null, window=null, fields=[].
edge: nonempty from_ids of ledger NODE IDs, to_id a different ledger NODE ID, mode=all (joint premises) or any (alternative premises), asset=null, window=null, fields=[]. All dependencies and endpoints must be active and present after the batch; no self-dependency.
request: nonempty asset, window, fields; from_ids=[], to_id=null, mode=null. Link target hypotheses through depends_on. fields names acquisition targets: on partial coverage narrow to uncovered fields; on answered/blocked retain the last target fields to document scope. In reason, explicitly explain each answered, remaining, conflicting or unavailable field with source/locator and reopening conditions. Removed fields are not automatically treated as proved answers.
Dependency types are derived from record kinds, exposed in dependency_relations. A request's depends_on links investigation targets; a physical record's links to requests track acquisition only. Neither direction is physical evidence and neither propagates staleness. Physical-to-physical depends_on links and edge endpoints are proof dependencies. Cite actual source documents in sources; a request's answered status never establishes a physical fact.
Changing request status, fields, scope coverage or reaffirming a request does not invalidate physical findings. A changed physical judgment or source version does invalidate its actual proof dependents. An unchanged reaffirmation does not start another invalidation wave. Source corrections still require reassessment of direct source consumers and their physical proof dependents, including explicit uncertainty or withdrawal when warranted.
Read reassessment_required and stale_causes. The runtime schedules stale records for assessor review before upstream closure; only justified lead operations clear them. You may explicitly reaffirm unchanged dependent content with fresh reasoning in the same batch as changed premises. When otherwise valid updates leave a cited stopping link stale, updates can commit but the stopping decision is deferred: it is NOT accepted as explained. Reassessment and a fresh upstream review must follow. No-progress reassessment is an explicit incomplete state, never successful completion.
sources contains ONLY top-level supplied document IDs: e.g. ["DOC_A"]. Put a section/page locator such as DOC_A.S02/page 3 in operation.reason, tied to DOC_A; never put it in sources. depends_on, from_ids, to_id, replaces and target_ids refer to ledger IDs, not document IDs. Job IDs have a separate namespace.
Duplicate scope_key is rejected within the same record kind after Unicode/whitespace/case normalization. Duplicate normalized node claims and identical edge endpoint sets/modes are rejected. For open requests, same normalized asset/window plus ANY overlapping field conflicts with an active request, including answered or blocked requests. Reuse that record if the same acquisition is still justified, or ask only distinct uncovered fields; do not reopen an answered/blocked route merely to avoid a duplicate error.
Reopening blocked to searching/partial/awaiting_user requires a newly cited source OR a newer version of a previously cited source plus an explanation of the real new route. Unchanged evidence is insufficient.
Evidence workers revise only the assigned request, and may set awaiting_user, partial, answered or blocked. All other proposed work goes to lead review. Only the lead dispatches jobs. One evidence job targets exactly one searching/partial request. Unknown targets are errors; matching queued/completed work is identified in dispatch feedback.
The ledger includes durable justification and request coverage history. Coverage entries preserve what the model said and which fields changed; they are not independent evidence. human_review records the human note and reviewed version. Read source_changes for corrected versions and reassess stale dependents. Only review=human_approved at the current fresh version denotes approval; no prior approval transfers automatically.
Examples (illustrative syntax, not incident evidence): create uses action=create, expected_version=0, replaces=null; revise record N_A at v3 uses action=revise, expected_version=3, replaces=null; replace N_A at v3 with N_B uses action=replace, expected_version=3, replaces=N_A, record.id=N_B and the same record.kind.
'''

class ContractError(ValueError):
    def __init__(self, code, **detail):
        super().__init__(code)
        self.detail = dict(code=code, **detail)

def reject(code, **detail):
    raise ContractError(code, **detail)
