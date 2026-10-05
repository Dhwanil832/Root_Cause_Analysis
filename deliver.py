"""Deliver an explicitly reviewed custodian batch without changing the harness."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / 'benchmark/R3-investigation-v1'
parser = argparse.ArgumentParser()
parser.add_argument('arm', choices=['gpt','qwen','gptoss','granite','hermes','mistral'])
parser.add_argument('batch', type=Path)
args = parser.parse_args()
arm = ROOT / 'runs' / args.arm
sys.path.insert(0, str(ROOT / 'runtime/prototype'))
from rca import engine
from rca.storage import read, save, now

batch = read(args.batch)
case = arm / 'case'
state = read(case / 'state.json')
assert not state.get('pending_call'), 'Cannot deliver during a model call'
if state['phase'] == 'needs_attention':
    assert not state['queue'], 'Do not bypass pending repair/review work with evidence'
    assert state.get('feedback', {}).get('accepted') is True, 'Do not bypass rejected output with evidence'
    assert batch.get('pause_reason') == 'accepted_noop_search_queue_exhausted', 'Record why this evidence pause is not an output rejection'
assert not state['queue'], 'Wait for scheduled local work before delivery'
assert not args.batch.with_suffix('.receipt.json').exists(), 'Batch already delivered'
lock = read(ROOT / 'runtime/runtime-lock.json')
assert all(hashlib.sha256((ROOT/'runtime'/f).read_bytes()).hexdigest()==h for f,h in lock['files'].items())
freeze = read(PACKAGE / 'FREEZE.json')
assert all(hashlib.sha256((PACKAGE/f).read_bytes()).hexdigest()==h for f,h in freeze['files'].items())
entries = []
policy = read(PACKAGE / 'custodian-policy.json')
for route in batch['requests']:
    rid = route['request_id']
    item = state['ledger'][rid]
    assert item['version'] == route['request_version'], 'Request version changed'
    assert item['record']['status'] in ['awaiting_user', 'partial']
    for doc in route['documents']:
        entries.append(dict(path=PACKAGE/'public/records'/(doc+'.json'), request_id=rid))
    if route.get('unmatched_fields'):
        text = policy['unmatched_answer'].format(verbatim_unmatched_fields='; '.join(route['unmatched_fields']))
        entries.append(dict(answer=text, request_id=rid))
for doc in batch.get('unsolicited_documents', []):
    assert doc == policy['unsolicited']['document']
    assert doc not in state['sources'], 'Unsolicited document already supplied'
    entries.append(dict(path=PACKAGE/'public/records'/(doc+'.json')))
if hasattr(engine, 'submit_bundle'):
    result = engine.submit_bundle(case, entries)
else:
    # The frozen baseline exposes only single-entry submission. Preserve its
    # native enqueue/coalescing behavior and finish delivery before resuming.
    result = []
    for entry in entries:
        sid, changed = engine.submit(case, **entry)
        result.append(dict(source_id=sid, changed=changed))
        save(args.batch.with_suffix('.progress.json'), dict(at=now(), outcomes=result))
save(args.batch.with_suffix('.receipt.json'), dict(at=now(), outcomes=result))
print(json.dumps(result))
