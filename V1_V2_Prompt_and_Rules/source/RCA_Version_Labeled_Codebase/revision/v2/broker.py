"""Deterministic fixture custodian, not an enterprise connector or semantic oracle.

Case-specific routing is test-environment configuration, NEVER a causal engine.
No filenames, rubric, scheduled future arrivals or variant name appear in the
public agent response. Calls use ordinary questions plus a known owner/route.
"""
from pathlib import Path
import json,re

ROUTES={
 'maintenance':('E03','E04','E15'),
 'video':('E05','E12'),
 'mechanical_examination':('E06',),
 'engineering_geometry':('E07',),
 'hydraulic_maintenance':('E08',),
 'controls':('E09',),
 'outage':('E10',),
 'engineering_identity':('E11',),
 'field_modifications':('E13',),
 'project_office':('E14',),
}

class Custodian:
    def __init__(self,root,scenario='base'):
        if scenario not in {'base','shutdown_after','no_lateral','unresolved_mapping','late_correction'}:raise ValueError('Unknown fixture scenario')
        self.root=Path(root);self.scenario=scenario;self.tick=0;self.requests=0
        self.delivered=set();self.log=[];self.oblique_tick=None;self.corrected=False
    def _text(self,did):
        mapping={('shutdown_after','E10'):'ALT_E10_after',('no_lateral','E12'):'ALT_E12_no_view',('unresolved_mapping','E11'):'ALT_E11_unresolved'}
        alt=mapping.get((self.scenario,did))
        file=self.root/('variants' if alt else 'evidence')/((alt or did)+'.md')
        return file.read_text()
    def initial(self,session):
        for did in ('E01','E02'):self._deliver(did,session,'initial')
    def _deliver(self,did,session,origin,request_ids=()):
        text=self._text(did)
        result=session.ingest(did,text,origin,request_ids)
        self.delivered.add(did)
        if did=='E12' and self.oblique_tick is None:self.oblique_tick=self.tick
        return dict(id=did,origin=origin,result=result,text=text if result!='duplicate' else None)
    def action(self,session,action,**args):
        if action not in {'search_local','request','wait'}:raise ValueError('Unknown tool action')
        self.tick+=1;released=[];response={}
        if action=='request':
            self.requests+=1
            if self.requests>15:response={'error':'request_budget_exhausted'}
            else:
                owner=args.get('owner');question=args.get('question','')
                if owner not in ROUTES:response={'clarification':'Choose a listed custodian category.', 'available_routes':sorted(ROUTES)}
                elif len(question.strip())<12:response={'clarification':'Describe the incident-scoped information needed.'}
                else:
                    # Owner request is the bounded topic. Return all holdings in that category.
                    # No hidden mechanism keyword required. A production matcher needs validation.
                    response={'owner':owner,'question':question,'matching':'explicit owner/category routing; not learned semantic retrieval'}
                    for d in ROUTES[owner]:released.append(self._deliver(d,session,'requested',args.get('request_ids',())))
        elif action=='search_local':
            q=args.get('query','').lower()
            if not q.strip():response={'clarification':'Provide a search query'}
            else:
                ids=[]
                if re.search(r'work|instruction|procedure|pack|isolation|checklist',q):ids.append('E03')
                if re.search(r'brief|recap|valve|seep|workshop',q):ids.append('E16')
                for d in ids:released.append(self._deliver(d,session,'local_search'))
                response={'query':q,'search_method':'small fixture keyword index', 'no_match_does_not_mean_nonexistence':True}
        # Scheduled events are independent of the model's chosen hypothesis.
        if self.tick==3:released.append(self._deliver('E10',session,'unsolicited_outage_upload'))
        if self.tick==6:released.append(self._deliver('E13',session,'unsolicited_modification_upload'))
        if self.scenario=='late_correction' and self.oblique_tick is not None and self.tick>=self.oblique_tick+2 and not self.corrected:
            text=(self.root/'variants'/'ALT_E12_reid.md').read_text();result=session.ingest('E12_correction',text,'unsolicited_index_correction')
            released.append(dict(id='E12_correction',origin='unsolicited_index_correction',result=result,text=text))
            self.corrected=True
        result=dict(tick=self.tick,response=response,released=released)
        self.log.append(dict(action=action,arguments=args,result=result))
        session.transcript.append(dict(event='environment_action',**self.log[-1]))
        return result
    def export_admin(self):return dict(root=str(self.root),scenario=self.scenario,tick=self.tick,requests=self.requests,delivered=sorted(self.delivered),log=self.log,oblique_tick=self.oblique_tick,corrected=self.corrected)
    @classmethod
    def restore(cls,data):
        b=cls(data['root'],data['scenario'])
        for k in ('tick','requests','log','oblique_tick','corrected'):setattr(b,k,data[k])
        b.delivered=set(data['delivered']);return b
