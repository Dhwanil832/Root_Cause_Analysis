from reasoning.assessor.components.scope_guard import inspect_scope_risks


def test_post_incident_scope_not_misread_as_incident_time():
    source={'id':'shop','text':'A later bench test showed oil loss of 8 mL.'}
    later={'semantic_label':'post_result','scope':'post_incident','configuration':'later_test',
           'basis':'documented_measurement','predicate':'later_bench_loss_8ml','quote':source['text']}
    assert inspect_scope_risks(source,[later],{})['quarantine_assertion_labels']==[]
    event={**later,'semantic_label':'event_result','configuration':'incident','scope':'incident_time'}
    assert inspect_scope_risks(source,[event],{})['quarantine_assertion_labels']==['event_result']
