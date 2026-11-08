from types import SimpleNamespace
import pytest
from shared.validation import ProposalError
from reasoning.evidence_worker.components.route_decision import apply_route_plan


def actor():
    return SimpleNamespace(gaps={'g':{'id':'g','kind':'causal','status':'open',
                   'routes_to_consider':[{'route':'security'},{'route':'maintenance'}]}},
                   attempts=[],discoveries=[])


def action():
    return {'gap_id':'g','mode':'discover','route':'security',
            'question':'What observations cover the incident aisle?',
            'information_needed':'Camera and machine observations at the aisle',
            'possible_effect':'Distinguish proposed causes','directness':2,'burden':1}


def test_redirect_to_previously_discovered_alternative_is_authorized():
    p={'routes':[{'id':'maintenance'}]}
    revised,audit=apply_route_plan(actor(),action(),{'decision':'redirect','route':'maintenance',
          'question':'Provide dated maintenance records near the incident',
          'information_needed':'Maintenance activity affecting water paths',
          'reason':'Newly discovered maintenance route has appropriate scope'},p)
    assert revised['mode']=='request'
    assert revised['route']=='maintenance'
    assert audit['changed_route']


def test_unknown_unhinted_route_is_rejected_and_not_executed():
    with pytest.raises(ProposalError,match='public authorization'):
        apply_route_plan(actor(),action(),{'decision':'redirect','route':'private_answer_store',
         'reason':'I want to see hidden evidence'}, {'routes':[]})


def test_execute_cannot_silently_change_the_lead_route():
    with pytest.raises(ProposalError,match='explicit redirect'):
        apply_route_plan(actor(),action(),{'decision':'execute','route':'maintenance',
         'reason':'I will silently switch'}, {'routes':[]})


def test_hold_is_an_explicit_auditable_non_action():
    result,audit=apply_route_plan(actor(),action(),{'decision':'hold','reason':'No suitable source appears accessible'}, {'routes':[]})
    assert result is None and audit['decision']=='hold'
