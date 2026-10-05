"""Typed dependency freshness. Acquisition links never stand in for evidence."""
import copy

def active(item):
    return item['record']['status'] not in ['withdrawn', 'terminated'] and not item.get('superseded_by')

def references(record):
    return set(record['depends_on'] + record['from_ids'] + ([record['to_id']] if record['to_id'] else []))

def proof_dependencies(ledger, record):
    if record['kind'] == 'request':
        return set()
    return {rid for rid in references(record)
            if rid in ledger and ledger[rid]['record']['kind'] != 'request'}

def relations(ledger, record):
    """Expose the interpretation without adding model-written schema fields."""
    return dict(
        source_evidence=list(record['sources']),
        proof_records=sorted(proof_dependencies(ledger, record)),
        acquisition_requests=sorted(rid for rid in record['depends_on']
                                    if record['kind'] != 'request' and ledger[rid]['record']['kind'] == 'request'),
        investigation_targets=sorted(record['depends_on']) if record['kind'] == 'request' else [],
    )

def meaning(ledger, item):
    """Material proof changes, excluding task bookkeeping and record versions."""
    r = item['record']
    if r['kind'] == 'request':
        return None
    return dict(kind=r['kind'], claim=r['claim'], scope_key=r['scope_key'], status=r['status'],
                sources={sid: item['source_versions'].get(sid) for sid in r['sources']},
                proof_records=sorted(proof_dependencies(ledger, r)),
                from_ids=sorted(r['from_ids']), to_id=r['to_id'], mode=r['mode'],
                superseded_by=item.get('superseded_by'))

def invalidate(state, seeds, reason, protected=()):
    """Invalidate true proof dependents; direct source consumers may be requests.

    Protected records were explicitly assessed in this atomic batch. They stop
    propagation: changing a premise cannot silently change a reassessed result.
    """
    ledger = state['ledger']
    protected = set(protected)
    impacted = set(seeds)
    changed = set()
    while True:
        added = {rid for rid, item in ledger.items()
                 if rid not in impacted and rid not in protected and active(item)
                 and proof_dependencies(ledger, item['record']) & impacted}
        if not added:
            break
        impacted |= added
    for rid in impacted - protected:
        item = ledger.get(rid)
        if not item or not active(item):
            continue
        item['stale'] = True
        item['review'] = 'pending_human' if item['record']['kind'] != 'request' else 'not_applicable'
        causes = item.setdefault('stale_causes', [])
        if reason not in causes:
            causes.append(copy.deepcopy(reason))
        changed.add(rid)
    return sorted(changed)

def outstanding(state):
    return sorted(rid for rid, item in state['ledger'].items() if active(item) and item.get('stale'))
