"""Model-proposed knowledge gaps must be explicitly supported by source quotes."""
from shared.validation import ProposalError,safe_atom,required_quote,bounded_str,short_id

def validate_new_gaps(runtime,source,frontier):
    known_labels={g['semantic_label'] for g in runtime.gaps.values()}
    proposals=[];new=[]
    for item in frontier.get('new_gaps',[]):
        label=safe_atom(item['semantic_label'])
        if label in known_labels:continue
        if item.get('kind') not in {'causal','operational','access'}:
            raise ProposalError('Invalid gap kind')
        quote=required_quote(item['quote'],source['text'])
        question=bounded_str(item['question']);why=bounded_str(item['why'])
        impact=bounded_str(item['expected_change'])
        hints=[]
        for x in item.get('routes_to_consider',[])[:8]:
            if not isinstance(x,dict):continue
            route=safe_atom(x.get('route','unknown'))
            hints.append({'route':route,'topic':bounded_str(x['topic']),
                          'directness':max(0,min(3,int(x.get('directness',1)))),
                          'burden':max(0,min(4,int(x.get('burden',1))))})
        gap_id=short_id('G_',label)
        new.append({'id':gap_id,'semantic_label':label,'kind':item['kind'],
                    'question':question,'why':why,'expected_change':impact,
                    'created_from':source['id'],'source_quote':quote,
                    'routes_to_consider':hints,
                    'related_hypothesis_summaries':item.get('related_hypothesis_summaries',[]),
                    'status':'open','need_id':None})
        proposals.append({'question':question,'purpose':why,'asset':source['id'],
                          'scope':item['kind'],'fields':[gap_id],
                          'targets':[],'citations':[{'document':source['id'],'quote':quote}],
                          'importance':1,'kind':item['kind']})
        known_labels.add(label)
    return new,proposals

