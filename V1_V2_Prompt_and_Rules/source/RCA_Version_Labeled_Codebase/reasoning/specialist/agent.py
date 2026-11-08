"""Specialist: causal frontier and uncertainty, no direct state mutation."""
from __future__ import annotations
from shared.validation import ProposalError, safe_atom, required_quote, bounded_str, short_id
from revision.v2.kernel import Key
from reasoning.specialist.components.frontier_graph import inspect_frontier

from reasoning.specialist.components.frontier_validator import validate_new_gaps

class SpecialistAgentMixin:
    def _validated_new_gaps(self,source, frontier):
        return validate_new_gaps(self ,source, frontier)

    def _validated_inferences(self,source,frontier,new_claims):
        known=dict(self.claims);known.update({x['claim_id']:x for x in new_claims})
        rules=[];mechanisms=[];deferred=[]
        for item in frontier.get('inferences',[]):
            premises=item.get('premise_claim_ids',[])
            if not isinstance(premises,list) or len(set(premises))<2 or any(x not in known for x in premises):
                deferred.append({'reason':'Missing two distinct known premises','proposal':item});continue
            if not any(x in {n['claim_id'] for n in new_claims} for x in premises):
                deferred.append({'reason':'No current-source observed premise','proposal':item});continue
            if not all(known[x]['positive'] for x in premises):
                deferred.append({'reason':'Negative premise requires a different warrant','proposal':item});continue
            try:
                refs=[r for r in item.get('warrant_source_ids',[]) if r in self.session.documents]
                if not refs:raise ProposalError('No actual delivered warrant source')
                quote=required_quote(item['quote'],source['text'])
                target=Key(safe_atom(item['subject']),safe_atom(item['predicate'],110),
                           safe_atom(item['scope']),safe_atom(item.get('configuration','assessed_inference')))
                inf_id=short_id('I_',target.label())
                if any(r.id==inf_id for r in self.session.kernel.rules):continue
                rules.append({'id':inf_id,'premises':[known[x]['key'] for x in premises],
                              'conclusion':target.label(),'warrant':bounded_str(item['warrant'],1500),
                              'evidence_refs':[{'source':x,'version':self.session.kernel.sources[x].version if x in self.session.kernel.sources else 1}
                                               for x in dict.fromkeys(refs)],
                              'grade':'conditional_support'})
                effect_id=item.get('effect_claim_id')
                causes=item.get('cause_claim_ids',[])
                if effect_id in known and causes and all(c in known for c in causes):
                    mechanism_id=short_id('M_',inf_id)
                    if mechanism_id not in self.session.mechanisms:
                        mechanisms.append({'id':mechanism_id,'effect':known[effect_id]['key'],
                                           'causes':[known[c]['key'] for c in causes],
                                           'rationale':bounded_str(item['warrant'],1500),
                                           'grade':'qualified_partial','support_key':target.label(),
                                           'citations':[{'document':source['id'],'quote':quote}]})
            except (KeyError,ValueError,ProposalError) as e:
                deferred.append({'reason':str(e),'proposal':item})
        return rules,mechanisms,deferred


    def propose_frontier(self,source,state,new_claims):
        graph=inspect_frontier(self.session)
        frontier=self.ask_role('specialist','frontier',{
            'document':source,'new_assertions':new_claims,
            'existing_claims':state['existing_claims'],
            'hypotheses':state['hypotheses'],'gaps':state['gaps'],
            'routes':state['routes'],'recent_events':state['recent_events'],
            'graph_frontier':graph})
        if not isinstance(frontier,dict):
            raise ProposalError('Specialist must return an object')
        policy_context={**state,'graph_frontier':graph,'current_source':source,'new_assertions':new_claims}
        return self.registry.transform_frontier(frontier,policy_context)
