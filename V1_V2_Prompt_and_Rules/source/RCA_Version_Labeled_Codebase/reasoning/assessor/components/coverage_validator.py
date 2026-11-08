"""Only an observed, newly received claim can cover an earlier information need."""
from shared.validation import ProposalError

def validate_resolutions(runtime,source,frontier,new_claims):
    current={c['claim_id']:c for c in new_claims}
    by_label={c['semantic_label']:c for c in new_claims}
    result=[]
    for item in frontier.get('resolved_gaps',[]):
        gid=item.get('gap_id')
        if gid not in runtime.gaps:raise ProposalError('A resolution referred to a nonexistent gap')
        linked=[]
        for label in item.get('supporting_assertion_labels',[]):
            if label not in by_label:raise ProposalError('Gap resolution lacks a new sourced assertion')
            linked.append(by_label[label])
        if not linked:raise ProposalError('A gap resolution cannot rely only on language-model opinion')
        gap=runtime.gaps[gid]
        if not gap.get('need_id') or gap['status']!='open':continue
        route=runtime._source_route(source['id']) or 'unsolicited'
        result.append({'need':gap['need_id'],'fields':[gid], 'route':route,
                       'refs':[{'source':source['id'],'version':1}]})
    return result

