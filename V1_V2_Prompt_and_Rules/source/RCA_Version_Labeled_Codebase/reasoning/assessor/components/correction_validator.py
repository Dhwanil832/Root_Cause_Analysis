"""A source correction needs an active source and exact earlier assertion IDs."""
from shared.validation import ProposalError,required_quote,bounded_str

def validate_corrections(runtime,source,extraction):
    corrections=[]
    for item in extraction.get('corrections',[]):
        target=item.get('target_source')
        ids=item.get('target_claim_ids',[])
        if not isinstance(ids,list) or not ids or target not in runtime.session.kernel.sources:
            raise ProposalError('Correction needs existing source and specific earlier claim IDs')
        keys=[]
        for cid in ids:
            old=runtime.claims.get(cid)
            if not old or old['first_source']!=target:
                raise ProposalError('Correction target is not attached to the named earlier source')
            key=old['key']
            if key not in [ob.key.label() for ob in runtime.session.kernel.sources[target].observations]:
                raise ProposalError('Corrected claim is not an active assertion in source')
            keys.append(key)
        quote=required_quote(item['quote'],source['text'])
        corrections.append({'target':target,'withdraw_keys':list(dict.fromkeys(keys)),
                            'reason':bounded_str(item['reason']),
                            'citations':[{'document':source['id'],'quote':quote}]})
    return corrections

