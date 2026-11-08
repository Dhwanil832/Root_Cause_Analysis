"""Atomically validate that model-extracted observations are scoped and quote-grounded."""
from shared.validation import ProposalError,safe_atom,required_quote,short_id
from revision.v2.kernel import Key

def validate_assertions(runtime,source,extraction):
    proposals=extraction.get('assertions',[])
    if not isinstance(proposals,list) or len(proposals)>24:raise ProposalError('Invalid assertion list')
    seen=set();result=[]
    for item in proposals:
        if not isinstance(item,dict):raise ProposalError('Assertion must be an object')
        semantic=safe_atom(item['semantic_label'])
        subject=safe_atom(item['subject']);predicate=safe_atom(item['predicate'],110)
        scope=safe_atom(item['scope']);conf=safe_atom(item['configuration'])
        basis=item.get('basis','assessed_source_assertion')
        if basis not in {'assessed_source_assertion','documented_measurement','conditional_model','record_availability','action_status'}:
            raise ProposalError('Invalid observation basis')
        quote=required_quote(item['quote'],source['text'])
        key=Key(subject,predicate,scope,conf)
        claim_id=short_id('C_',key.label())
        if claim_id in seen:continue
        seen.add(claim_id)
        result.append({'claim_id':claim_id,'semantic_label':semantic,'subject':subject,
                       'predicate':predicate,'scope':scope,'configuration':conf,
                       'key':key.label(),'quote':quote,'basis':basis,
                       'positive':bool(item.get('polarity',True)),'first_source':source['id']})
    return result

