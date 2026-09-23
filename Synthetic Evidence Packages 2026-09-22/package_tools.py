#!/usr/bin/env python3
"""Operator-only integrity checks and allowlisted exports. Never calls an RCA app."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ('R3-16515', 'IA-16036')
STAGES = ('B0', 'B1', 'B2')
REQUIRED_PRIVATE = (
    'normalized_row.json', 'source_and_synthesis_ledger.md', 'fixed_scenario.md',
    'entity_register.md', 'timeline.md', 'causal_reference.md', 'evidence_design.md',
    'release_expectations.md', 'answer_bank.json', 'answer_agent_instructions.md',
    'evaluation_targets.json', 'run_protocol.md', 'validation_report.md',
)


def key(ref):
    return (ref['document_id'], ref['revision'])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(case):
    base = ROOT / f'{case}_evidence_package_v1'
    manifest = json.loads((base / 'package_manifest.json').read_text())
    checks = []

    def check(name, valid, detail):
        checks.append({'check': name, 'status': 'pass' if valid else 'fail', 'detail': detail})

    records = manifest['documents']
    index = {key(d): d for d in records}
    check('unique_document_revisions', len(index) == len(records), len(records))
    texts = {}
    for doc in records:
        path = base / doc['path']
        safe = path.resolve().is_relative_to((base / 'payloads').resolve()) and not path.is_symlink()
        check('payload_path:' + doc['path'], safe and path.is_file(), 'Must be an existing payload file, not operator material.')
        if not path.is_file() or not safe:
            continue
        text = path.read_text()
        texts[key(doc)] = text
        check('hash:' + doc['path'], digest(path) == doc['sha256'], digest(path))
        check('metadata:' + doc['path'], f'Document ID: {doc["document_id"]}\n' in text and f'Revision: {doc["revision"]}\n' in text, 'Header identity and revision')
        check('complete_body:' + doc['path'], len(text.split()) > 65 and not re.search(r'\bTODO\b|write a report here|<placeholder>', text, re.I), 'Basic completeness and placeholder scan; not semantic adequacy')
        check('no_private_markers:' + doc['path'], not re.search(r'evaluation_targets|fixed_scenario|answer_bank|\b[RA][NT]\d{2}\b|synthetic reconstruction|\bB[012]\b', text), 'Known private-file, target/need-ID and standalone stage-marker scan; B17 is an asset, not release B1')

    actual = {str(p.relative_to(base)) for p in (base / 'payloads').rglob('*.md')}
    check('all_payloads_in_manifest', actual == {d['path'] for d in records}, len(actual))
    active = set()
    active_by_stage = {}
    all_released = set()
    for i, release in enumerate(manifest['releases']):
        stage = STAGES[i]
        add = {key(x) for x in release['additions']}
        remove = {key(x) for x in release['withdrawals']}
        check('lineage:' + stage, release['release_id'] == stage and release['resulting_version'] == i + 1 and release['expected_parent_version'] == (None if i == 0 else i), 'Declared stage order and parent')
        check('eligible_additions:' + stage, all(x in index and index[x]['eligible_from_release'] == stage for x in add), 'Only newly eligible revisions')
        check('withdrawals_exist:' + stage, remove <= active, 'Cannot withdraw an unreleased revision')
        for pair in release['supersessions']:
            old, new = key(pair['old_source']), key(pair['new_source'])
            check('supersession:' + stage, old in remove and new in add and old[0] == new[0] and new[1] > old[1], [old, new])
        active = (active - remove) | add
        all_released |= add
        active_by_stage[stage] = set(active)
        check('cumulative_set:' + stage, active == {key(x) for x in release['cumulative_active_sources']}, len(active))
        check('no_future_active:' + stage, all(STAGES.index(index[x]['eligible_from_release']) <= i for x in active), 'Release-time isolation in manifest, not live runtime access control')
    check('all_documents_scheduled', all_released == set(index), len(all_released))

    bank = json.loads((base / 'private/answer_bank.json').read_text())
    seen = set()
    for entry in bank['entries']:
        eid = entry['need_id']
        check('unique_need:' + eid, eid not in seen, eid)
        seen.add(eid)
        check('subpart_coverage:' + eid, {s['subpart_id'] for s in entry['subparts']} == {s['subpart_id'] for s in entry['coverage']}, 'Every subpart has explicit coverage')
        for source in entry['sources']:
            source_key = key(source)
            check('answer_source_available:' + eid, source_key in active_by_stage[entry['eligible_from_release']], source_key)
            check('exact_quote:' + eid + ':' + source['document_id'], source['exact_excerpt'] in texts.get(source_key, ''), source['locator'])
            section = source['locator'].split('/')[0].split('–')[0]
            check('answer_section:' + eid + ':' + source['document_id'], bool(re.search(r'^## ' + re.escape(section) + r'\b', texts.get(source_key, ''), re.M)), source['locator'])

    evaluation = json.loads((base / 'private/evaluation_targets.json').read_text())
    seen = set()
    fields = {'target_id', 'stage', 'dimension', 'expected_meaning', 'required_evidence_bundles', 'required_scope', 'acceptable_variants', 'insufficient_responses', 'overclaims', 'expected_delta', 'remaining_unknowns', 'assessment_method', 'historical_or_synthetic_basis'}
    for target in evaluation['targets']:
        tid = target['target_id']
        check('target_contract:' + tid, fields <= set(target) and tid not in seen, 'Required fields and uniqueness')
        seen.add(tid)
        for bundle in target['required_evidence_bundles']:
            check('target_bundle_available:' + tid, bool(bundle) and all(key(ref) in active_by_stage[target['stage']] for ref in bundle), bundle)
            for ref in bundle:
                section = ref['locator'].split('/')[0].split('–')[0]
                check('target_section:' + tid, bool(re.search(r'^## ' + re.escape(section) + r'\b', texts.get(key(ref), ''), re.M)), ref)

    for filename in REQUIRED_PRIVATE:
        check('required_private:' + filename, (base / 'private' / filename).is_file(), filename)
    for path in base.rglob('*.json'):
        json.loads(path.read_text())
    never = manifest['never_upload']
    def prohibited(relative):
        return any(relative == value or (value.endswith('/') and relative.startswith(value)) for value in never)
    operator_files = [str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() and not p.is_relative_to(base / 'payloads')]
    check('all_operator_files_excluded', all(prohibited(p) for p in operator_files), operator_files)

    normalized = json.loads((base / 'private/normalized_row.json').read_text())
    original = ROOT.parent / normalized['source']['path']
    check('historical_workbook_unchanged', digest(original) == normalized['source']['sha256'], normalized['source']['sha256'])
    sizes = []
    for release in manifest['releases']:
        additions = [index[key(x)] for x in release['additions']]
        cumulative = [index[key(x)] for x in release['cumulative_active_sources']]
        sizes.append({'release': release['release_id'], 'added_documents': len(additions), 'added_words': sum(len(texts[key(d)].split()) for d in additions), 'added_bytes': sum((base / d['path']).stat().st_size for d in additions), 'active_documents': len(cumulative), 'active_words': sum(len(texts[key(d)].split()) for d in cumulative)})
    return {'case_id': case, 'status': 'pass' if all(c['status'] == 'pass' for c in checks) else 'fail', 'check_count': len(checks), 'failed_checks': [c for c in checks if c['status'] == 'fail'], 'checks': checks, 'sizes': sizes, 'document_revisions': len(records), 'answer_needs': len(bank['entries']), 'semantic_targets': len(evaluation['targets']), 'scope': 'Structural integrity only; no model run, entailment judgment or independent engineering approval.'}


def export(case, stage, destination):
    base = ROOT / f'{case}_evidence_package_v1'
    dest = Path(destination).expanduser().resolve()
    if dest.exists():
        raise ValueError('Export destination must not already exist; nothing will be overwritten.')
    if dest.is_relative_to(ROOT):
        raise ValueError('Export outside the authoring package root to keep operator/private material separate.')
    result = inspect(case)
    if result['status'] != 'pass':
        raise ValueError('Package integrity failed; do not export.')
    manifest = json.loads((base / 'package_manifest.json').read_text())
    index = {key(d): d for d in manifest['documents']}
    release = next(r for r in manifest['releases'] if r['release_id'] == stage)
    copied = []
    dest.mkdir(parents=True, exist_ok=False)
    for ref in release['cumulative_active_sources']:
        doc = index[key(ref)]
        source = base / doc['path']
        target = dest / doc['scope'] / source.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        if digest(source) != digest(target):
            raise ValueError('Export hash mismatch: ' + str(target))
        copied.append(str(target))
    return {'case_id': case, 'release': stage, 'files': copied, 'operator_notice': 'Synthetic evaluation payload only. Keep the parent operator provenance notice with external sharing, not inside investigator input. No app import or runtime access isolation was performed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--export', choices=STAGES)
    parser.add_argument('--destination')
    args = parser.parse_args()
    if args.export:
        if not args.case or not args.destination:
            parser.error('--export requires --case and --destination')
        output = export(args.case, args.export, args.destination)
        ok = True
    else:
        output = [inspect(case) for case in ([args.case] if args.case else CASES)]
        ok = all(r['status'] == 'pass' for r in output)
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
