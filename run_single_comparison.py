"""One clean pass per model; reuse scored connected attempts, run missing ones.

The frozen harness is imported unchanged. Semantic grades are never invented
from execution completion. Model calls are preserved and not silently retried.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import traceback

from common import ROOT, PACKAGE, engine, provider, read, save, digest, now, verify
from rca import prompts
import adapter
import codex_adapter

OUT = ROOT / 'experiments/single-run-2026-10-05'
ENDPOINT = 'http://127.0.0.1:11434/api/chat'


def progress(lane, **fields):
    value = dict(at=now(), pid=os.getpid(), lane=lane, **fields)
    save(OUT / (lane + '-status.json'), value)
    print(json.dumps(value), flush=True)


def clean(key, model, lane, client):
    folder = OUT / 'results' / key / 'clean'
    outcomes = []
    for item in read(OUT / 'clean-inputs/index.json'):
        target = folder / 'packets' / item['id']
        if (target / 'execution.json').exists():
            outcomes.append(read(target / 'execution.json'))
            continue
        packet = read(OUT / 'clean-inputs/packets' / (item['id'] + '.json'))
        progress(lane, model=model, mode='clean', task=item['id'], phase='generating',
                 saved_packets=len(outcomes), target_packets=17)
        result = dict(task=item['id'], stage=item['stage'], score=None)
        try:
            if target.exists():
                completed = read(target / 'result.json') if (target / 'result.json').exists() else {}
                if completed.get('status') != 'completed':
                    result.update(status='incomplete_preserved', reason='No silent resampling of an existing attempt.')
                    save(target / 'execution.json', result)
                    outcomes.append(result)
                    continue
                answer = (target / 'answer.txt').read_text()
                assert digest(answer) == completed['answer_hash']
                data = json.loads(answer)
            else:
                data = client(prompts.prompt(item['role']), packet, target)
            state = read(OUT / 'clean-inputs/states' / (item['id'] + '.json'))
            job = packet['assignment']
            try:
                after, validation = engine.apply_result(state, job, data,
                    str(target.relative_to(folder)), engine.signature(state, job))
                save(target / 'validation.json', validation)
                save(target / 'state_after.json', after)
                result.update(status='answer_saved', accepted=validation.get('accepted'),
                              rejection_reason=validation.get('reason'))
            except Exception as exc:
                # A controller failure must never be labelled a reasoning error.
                result.update(status='harness_validation_error', detail=str(exc),
                              answer_preserved=True)
        except Exception as exc:
            result.update(status='execution_failure', category=getattr(exc, 'category', type(exc).__name__),
                          detail=provider.sanitize(str(exc)))
        save(target / 'execution.json', result)
        outcomes.append(result)
        save(folder / 'execution-summary.json', dict(mode='clean', packets=outcomes,
             completed_answers=sum(x['status'] == 'answer_saved' for x in outcomes),
             processed_tasks=len(outcomes), target_tasks=17, score=None,
             scoring_status='manual_semantic_review_required'))
        print(json.dumps(dict(model=model, **result)), flush=True)
        if lane == 'gpt' and result.get('category') in ['codex_execution', 'evaluation_isolation']:
            progress(lane, model=model, phase='transport_requires_attention', detail=result)
            return False
    return True


def connected(key, config, lane, client, plan):
    folder = OUT / 'results' / key / 'connected'
    if key in plan['existing_connected']:
        original = ROOT / plan['existing_connected'][key]
        statepath = original / ('repaired/case/state.json' if key == 'gpt' else 'case/state.json')
        state = read(statepath)
        assert state['runtime_fingerprint'] == plan['runtime_fingerprint']
        save(folder / 'existing-result.json', dict(source=str(original),
             reused_once=True, new_model_calls=0, runtime_fingerprint=state['runtime_fingerprint'],
             score=read(original / 'score-summary.json'), phase=state['phase']))
        return
    case = folder / 'case'
    if (folder / 'execution-summary.json').exists():
        return
    if engine.statepath(case).exists():
        save(folder / 'execution-summary.json', dict(phase='existing_attempt_requires_review',
             score=None, reason='No implicit continuation/resampling.'))
        return
    start = read(PACKAGE / 'public/start.json')
    state = engine.create(case, start['description'],
        [PACKAGE / 'public/records' / (sid + '.json') for sid in start['initial_source_ids']], 'qwen')
    state['execution_profile'] = config
    state['execution_profile_hash'] = digest(config)
    save(engine.statepath(case), state)
    failure = None
    def call(prompt, packet, target):
        progress(lane, model=config['model'], mode='connected', role=packet['assignment']['kind'],
                 phase='generating', call=str(target))
        return client(prompt, packet, target)
    try:
        state = engine.run(case, max_calls=None, client=call)
    except Exception as exc:
        failure = provider.diagnostic(exc, config)
        state = read(engine.statepath(case))
    requests = [dict(id=k, version=v['version'], record=v['record'])
                for k,v in state['ledger'].items()
                if not v.get('superseded_by') and v['record']['kind']=='request'
                and v['record']['status'] in ['awaiting_user','partial']]
    save(folder / 'execution-summary.json', dict(phase=state['phase'], calls=len(state['calls']),
        records=len(state['ledger']), failure=failure, requests_for_custodian=requests,
        queue=state['queue'], feedback=state.get('feedback'), score=None,
        scoring_status='manual_semantic_review_required',
        custodian_status='review_needed' if requests and not state['queue'] else 'not_ready'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lane', choices=['local', 'gpt'])
    args = ap.parse_args()
    verify()
    plan = read(OUT / 'PLAN.json')
    assert plan['repetitions'] == 1 and plan['runtime_fingerprint'] == engine.fingerprint()
    with engine.lock(OUT / (args.lane + '-lock')):
        if args.lane == 'gpt':
            if not codex_adapter.CLI:
                raise RuntimeError('Codex CLI unavailable; no model attempt made.')
            save(OUT/'results/gpt/profile.json', codex_adapter.PROFILE)
            connected('gpt', codex_adapter.PROFILE, args.lane, codex_adapter.call, plan)
            done = clean('gpt', 'gpt-5.5', args.lane, codex_adapter.call)
            progress(args.lane, phase='answers_saved_pending_review' if done else 'needs_attention')
            return
        profiles = read(OUT / 'profiles.json')
        for key in plan['local_order']:
            config = profiles[key]
            model = config['model']
            folder = OUT / 'results' / key
            progress(args.lane, model=model, phase='loading')
            try:
                save(folder / 'profile.json', config)
                save(folder / 'loaded-models.json', adapter.preload(ENDPOINT, config))
                client = lambda prompt, packet, target: adapter.call(prompt, packet, target, config, ENDPOINT)
                connected(key, config, args.lane, client, plan)
                clean(key, model, args.lane, client)
                save(folder / 'model-status.json', dict(phase='attempts_saved_pending_review', model=model))
            except Exception as exc:
                save(folder / 'model-status.json', dict(phase='setup_or_execution_error',
                     model=model, diagnostic=provider.diagnostic(exc, config), score=None))
                traceback.print_exc()
            finally:
                try:
                    adapter.unload(ENDPOINT, model)
                except Exception as exc:
                    print('Unload diagnostic:', str(exc), flush=True)
        progress(args.lane, phase='attempts_saved_pending_review')


if __name__ == '__main__':
    main()
