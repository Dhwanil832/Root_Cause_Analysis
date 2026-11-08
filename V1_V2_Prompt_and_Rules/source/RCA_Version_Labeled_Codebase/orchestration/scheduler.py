"""Event loop: unsolicited sources can preempt the normal next-action decision."""
from __future__ import annotations

def run_steps(runtime):
    initial=runtime.world.initial_packet()
    runtime.focal_event=initial['text'][:2400]  # Only what the initial report actually states.
    runtime.assess(initial,via='initial_incident_packet')
    for _ in range(runtime.max_steps):
        incoming=runtime.world.maybe_unsolicited()
        if incoming:runtime.assess(incoming,via='unsolicited_human_upload')
        action=runtime.choose()
        if action['mode']=='wait':
            runtime.stop_reason='no_admissible_action'
            break
        runtime.execute(action)
    else:
        runtime.stop_reason='action_budget_exhausted'
    runtime._refresh_gaps()
    runtime.session.metadata.update(
        run_kind='provider_http_invoked' if any(c.actual_call_performed for c in runtime.model_calls) else 'fixture_model_only',
        provider_http_calls=sum(c.actual_call_performed for c in runtime.model_calls),
        calls_total=len(runtime.model_calls),
        prompt_hashes=runtime.registry.prompt_hashes,
        model_config=runtime.config_snapshot.get('llm',{}),
        components={r:runtime.registry.selected_name(r) for r in runtime.registry.components},
        case_still_open=True,
    )
    runtime.record('provisional_report',reason=runtime.stop_reason,
        note='No engineering review; reported claims not independently certified.')
    return runtime
