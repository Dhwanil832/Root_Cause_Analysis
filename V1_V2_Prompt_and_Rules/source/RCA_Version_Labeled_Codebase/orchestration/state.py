"""Shared case state and snapshots; it does NOT house investigation algorithms."""
from __future__ import annotations
import copy, json
from dataclasses import asdict
from pathlib import Path
from revision.v2.kernel import Key
from revision.v2.session import Session

class CaseState:
    def __init__(self, world, case_id='WET-FLOOR-01', max_steps=18):
        self.world=world
        self.session=Session(case_id)
        self.session.metadata.update(run_kind='not_started', blind=False,
            independent_reviewer=False, document_entailment_verified_by_runtime=False)
        self.focal_event='Incident report not yet received.'
        self.claims={}
        self.inference_ids=set()
        self.hypotheses={}
        self.gaps={}
        self.attempts=[]
        self.assessment_history=[]
        self.intake_history=[]
        self.routing_history=[]
        self.discoveries=[]
        self.events=[]
        self.max_steps=max_steps
        self.blockers=[]
        self.stop_reason='not_started'
        self._step_index=0
        self.model_calls=[]
        self.model_input_history=[]
        self.contract_rejections=[]
        self.config_snapshot={}
        self.last_model_name='unknown'

    def _claim_projection(self):
        views=self.session.kernel.claim_views()
        result=[]
        for x in self.claims.values():
            v=views.get(x['key'],{'status':'unknown','origins':[],'positive_supports':[]})
            result.append(dict(**x,status=v['status'],origins=v.get('origins',[]),
                               supporting_source_versions=v.get('positive_supports',[])))
        return sorted(result,key=lambda x:(x['first_source'],x['claim_id']))


    def _gap_projection(self):
        projected=[]
        for g in self.gaps.values():
            copy_g=copy.deepcopy(g)
            need=g.get('need_id')
            if need and need in self.session.kernel.needs:
                v=self.session.kernel.need_view(need)
                copy_g['kernel_disposition']=v['disposition']
                copy_g['status']='resolved' if v['disposition']=='covered' else 'open'
                copy_g['coverage_invalidated']=v['coverage_invalidated']
            projected.append(copy_g)
        return projected


    def public_state(self):
        from reasoning.specialist.components.frontier_graph import inspect_frontier
        return {'graph_frontier':inspect_frontier(self.session),
                'case':self.session.case_id,
                'focal_event':self.focal_event,
                'existing_claims':self._claim_projection(),
                'hypotheses':list(self.hypotheses.values()),
                'gaps':self._gap_projection(),
                'routes':self.world.public_routes(),
                'attempts':list(self.attempts),
                'recent_events':[{k:v for k,v in e.items() if k in {'event','source','route','reason','step'}}
                                 for e in self.events[-7:]],
                'received_source_ids':sorted(self.session.documents)}


    def record(self,event,**kwargs):
        self._step_index+=1
        data={'step':self._step_index,'event':event,**kwargs,
              'claims':self._claim_projection(),
              'hypotheses':copy.deepcopy(list(self.hypotheses.values())),
              'gaps':self._gap_projection(),
              'routes':self.world.public_routes(),
              'kernel_revision':self.session.kernel.revision,
              'causal_view':self.session.causal_view(),
              'received_source_ids':sorted(self.session.documents)}
        self.events.append(data)
        return data


    def _refresh_gaps(self):
        for g in self.gaps.values():
            nid=g.get('need_id')
            if not nid:continue
            state=self.session.kernel.need_view(nid)['disposition']
            g['status']='resolved' if state=='covered' else 'open'


    def output(self,path):
        root=Path(path);root.mkdir(parents=True,exist_ok=True)
        self.session.save(root/'session.json')
        (root/'trace.json').write_text(json.dumps(self.events,indent=2))
        (root/'custodian_audit_DESIGNER_ONLY.json').write_text(json.dumps(self.world.audit(),indent=2))
        (root/'model_calls.json').write_text(json.dumps([asdict(x) for x in self.model_calls],indent=2))
        (root/'model_inputs_MODEL_VISIBLE.json').write_text(json.dumps(self.model_input_history,indent=2))
        (root/'component_manifest.json').write_text(json.dumps({'components':{r:self.registry.selected_name(r) for r in self.registry.components},'prompt_hashes':self.registry.prompt_hashes,'prompt_variants':self.registry.prompt_variants,'provider':self.config_snapshot.get('llm',{}).get('provider'),'mode':self.mode},indent=2))
        models={id(m):m for m in getattr(self,'_models',{}).values()}
        http_attempts=sum(getattr(m,'http_attempts',0) for m in models.values())
        summary={'case':self.session.case_id,'stop_reason':self.stop_reason,
                 'provider_http_attempts':http_attempts,
                 'calls_total':len(self.model_calls),'provider_http_calls':sum(x.actual_call_performed for x in self.model_calls),
                 'verified_real_llm_calls':None, # HTTP transport cannot independently certify endpoint implementation
                 'sources_assessed':sorted(self.session.documents),
                 'claims':self._claim_projection(),
                 'hypotheses':list(self.hypotheses.values()),'gaps':self._gap_projection(),
                 'intake_audits':list(self.intake_history),
                 'contract_rejections':list(self.contract_rejections),
                 'assessor_reviews':list(self.assessment_history),
                 'route_plans':list(self.routing_history),
                 'corrections':[x for x in self.session.transcript if x.get('event')=='source_interpretation_corrected'],
                 'causal_view':self.session.causal_view(),
                 'signed_off':self.session.kernel.phase=='signed_off',
                 'notes':['HTTP responses alone do not authenticate whether the endpoint is a real language model.',
                          'Sourced report does not necessarily establish physical truth.',
                          'LLM semantic entailment is not independently verified.',
                          'Fixture model calls are not live model calls.']}
        summary['component_config']={r:v.get('implementation') for r,v in self.config_snapshot.get('agents',{}).items()}
        summary['prompt_hashes']=getattr(self.registry,'prompt_hashes',{})
        summary['prompt_variants']=getattr(self.registry,'prompt_variants',{})
        summary['llm_provider']=self.config_snapshot.get('llm',{}).get('provider')
        summary['mode']=getattr(self,'mode','unknown')
        (root/'summary.json').write_text(json.dumps(summary,indent=2))
        return summary

