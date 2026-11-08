"""Raw-document intake, citation-checked proposals, durable JSON state, and agenda.

No model is hidden in this module. submit_assessment() consumes an actual actor's
structured response. A quote existing in a document is NOT an entailment check.
This separation is intentional and is recorded in every run's metadata.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import copy, json, hashlib, os, re
from .kernel import Kernel, Key, Source, Observation, Ref, Rule, JobToken


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


class Session:
    def __init__(self,case_id='FCB-01'):
        self.case_id=case_id
        self.kernel=Kernel()
        self.documents={}
        self.pending_intake=[]
        self.transcript=[]
        self.snapshots=[]
        self.episodes=[]
        self.mechanisms={}
        self.assessments=[]
        self.metadata=dict(run_kind='unassigned',blind=False,independent_reviewer=False,
                           document_entailment_verified_by_runtime=False)

    def ingest(self,doc_id: str,text: str,origin='human_upload',request_ids=()):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}',doc_id):raise ValueError('Invalid document ID')
        if not isinstance(text,str) or not text.strip():raise ValueError('Empty text')
        if len(text)>5_000_000:raise ValueError('Text exceeds bounded intake size')
        content_hash=sha(text)
        for old_id,doc in self.documents.items():
            if doc['sha256']==content_hash:
                self.transcript.append(dict(event='duplicate_document',id=doc_id,canonical=old_id))
                return 'duplicate'
        if doc_id in self.documents:raise ValueError('Use a new document ID for revised raw content; never overwrite originals')
        valid=[q for q in request_ids if q in self.kernel.needs]
        invalid=[q for q in request_ids if q not in self.kernel.needs]
        self.documents[doc_id]=dict(text=text,sha256=content_hash,origin=origin,request_ids=valid)
        self.pending_intake.append(doc_id)
        prior=self.kernel.phase
        if prior in {'waiting','signed_off','partial_boundary'}:self.kernel.phase='reassessment_pending'
        self.transcript.append(dict(event='raw_source_arrived',id=doc_id,sha256=content_hash,origin=origin,
                                    request_ids=valid,invalid_optional_links=invalid,prior_phase=prior))
        return 'accepted'

    def _citations(self,citations):
        if not citations:raise ValueError('A sourced finding requires citations')
        checked=[]
        for c in citations:
            if set(c)-{'document','quote'}:raise ValueError('Unexpected citation field')
            did=c['document'];quote=c['quote']
            if did not in self.documents:raise ValueError('Citation to an unseen document: '+did)
            if not isinstance(quote,str) or len(quote.strip())<8:raise ValueError('Quote is too short')
            if quote not in self.documents[did]['text']:raise ValueError('Quote not present in '+did)
            checked.append(dict(document=did,quote=quote,sha256=self.documents[did]['sha256']))
        return checked

    def submit_assessment(self,proposal: dict):
        """Atomic commit of already-reviewed actor interpretations; not automated truth validation."""
        original=copy.deepcopy(self.__dict__)
        try:return self._submit_assessment(proposal)
        except Exception as exc:
            self.__dict__=original
            self.transcript.append(dict(event='assessment_rejected',error=str(exc),proposal=proposal))
            raise

    def _submit_assessment(self,p):
        permitted={'document','actor','origin_group','observations','rules','new_episodes','corrections','coverage','parent_refs','review_note','mechanisms','job_context'}
        if set(p)-permitted:raise ValueError('Unexpected assessment fields')
        did=p['document']
        if did not in self.pending_intake:raise ValueError('Document is not awaiting assessment')
        job=p.get('job_context')
        if job:
            token=JobToken(tuple(tuple(x) for x in job['fingerprints']),job.get('case_revision'))
            if job.get('document_hash')!=self.documents[did]['sha256'] or not self.kernel.commit_allowed(token):
                raise ValueError('Stale worker assessment; reassess changed read-set resources')
        actor=p.get('actor','')
        if not actor:raise ValueError('Assessor identity required')
        observations=[];attached=[]
        for item in p.get('observations',[]):
            cites=self._citations(item.get('citations',[]))
            if not any(x['document']==did for x in cites):raise ValueError('Observation must cite the assessed source')
            key=Key.parse(item['key']);basis=item.get('basis','assessed_source_assertion')
            if basis not in {'assessed_source_assertion','documented_measurement','conditional_model','hypothesis','record_availability','action_status'}:
                raise ValueError('Invalid epistemic basis')
            if basis=='hypothesis':raise ValueError('Put hypotheses in a rule/episode, not asserted observations')
            refs=tuple(Ref(**x) for x in item.get('requires',[]))
            observations.append(Observation(key,item.get('positive',True),basis,refs,cites[0]['quote']))
            attached.append(dict(key=key.label(),citations=cites,basis=basis))
        parents=tuple(Ref(**r) for r in p.get('parent_refs',[]))
        self.kernel.receive(Source(did,1,p.get('origin_group',did),tuple(observations),parents,self.documents[did]['sha256']),
                            self.documents[did]['request_ids'])
        for corr in p.get('corrections',[]):
            target=corr['target'];self._citations(corr['citations'])
            if not any(c['document']==did for c in corr['citations']):raise ValueError('Correction must cite new source')
            if target not in self.kernel.sources:raise ValueError('Unknown corrected source')
            old=self.kernel.sources[target]
            keys=set(corr['withdraw_keys'])
            if not keys<=set(o.key.label() for o in old.observations):raise ValueError('Correction references absent interpretation')
            if not corr.get('reason','').strip():raise ValueError('Correction rationale required')
            revised=tuple(o for o in old.observations if o.key.label() not in keys)
            self.kernel.receive(Source(old.id,old.version+1,old.origin,revised,(Ref(did,1),),old.content_hash))
            self.transcript.append(dict(event='source_interpretation_corrected',target=target,original_raw_preserved=True,reason=corr['reason']))
        for r in p.get('rules',[]):
            # Rules must carry source references. Their semantic warrant is reviewed, not proven here.
            refs=tuple(Ref(**x) for x in r.get('evidence_refs',[]))
            if not refs or not all(self.kernel.ref_current(x) for x in refs):raise ValueError('Rule needs current source references')
            self.kernel.add_rule(Rule(r['id'],tuple(Key.parse(k) for k in r['premises']),Key.parse(r['conclusion']),
                                      r['warrant'],refs,r.get('grade','conditional_support'),
                                      tuple(r['cause_interval']) if r.get('cause_interval') else None,
                                      tuple(r['effect_interval']) if r.get('effect_interval') else None))
        for m in p.get('mechanisms',[]):
            if not m.get('id') or m['id'] in self.mechanisms:raise ValueError('New mechanism ID required')
            if m.get('grade') not in {'hypothesis','qualified_partial'}:raise ValueError('Only assessed partial or candidate links supported here')
            if not m.get('causes') or not m.get('rationale'):raise ValueError('Mechanism needs conditions and rationale')
            effect=Key.parse(m['effect']);causes=[Key.parse(c) for c in m['causes']]
            if effect in causes:raise ValueError('Self-causal mechanism')
            self._citations(m['citations'])
            self.kernel.known_keys.add(effect);self.kernel.known_keys.update(causes)
            self.mechanisms[m['id']]=copy.deepcopy(m)
        for e in p.get('new_episodes',[]):
            if not e.get('question','').strip() or not e.get('purpose','').strip():raise ValueError('Episode needs question and purpose')
            if not e.get('asset') or not e.get('scope') or not e.get('fields'):raise ValueError('Episode needs bounded information need')
            self._citations(e['citations'])
            q=self.kernel.request(e['asset'],e['scope'],set(e['fields']),e.get('targets',[]))
            for owner in e.get('routes',[]):self.kernel.route(q,owner,'ready')
            self.episodes.append(dict(id=f'EP{len(self.episodes)+1:03d}',need=q,question=e['question'],purpose=e['purpose'],
                                     created_by_source=did,kind=e.get('kind','factual'),importance=e.get('importance',1),
                                     alternatives=e.get('outcomes',{}),status='open'))
        for cov in p.get('coverage',[]):
            self.kernel.respond(cov['need'],set(cov.get('fields',[])),cov.get('unavailable',False),
                                tuple(Ref(**x) for x in cov.get('refs',[])),cov['route'])
        self.pending_intake.remove(did)
        self.assessments.append(dict(document=did,actor=actor,source_hash=self.documents[did]['sha256'],
                                      findings=attached,review_note=p.get('review_note',''),full_proposal=p))
        self.transcript.append(dict(event='assessment_committed',document=did,actor=actor,
                                    semantic_verification='actor_review_not_runtime_entailment'))
        self.capture('assessed_'+did)
        return 'accepted'

    def start_job(self,document,reads=None):
        token=self.kernel.job_snapshot(reads)
        return dict(fingerprints=list(token.fingerprints),case_revision=token.case_revision,document_hash=self.documents[document]['sha256'])

    def causal_view(self):
        links=[]
        for m in self.mechanisms.values():
            item=copy.deepcopy(m)
            exclusion=m.get('excluded_by')
            support=m.get('support_key')
            if exclusion and self.kernel.status(Key.parse(exclusion))=='supported':state='excluded_for_this_mechanism'
            elif support and self.kernel.status(Key.parse(support))=='supported':state='qualified_partial_support'
            else:state='hypothesis_or_reassessment'
            item['status']=state
            item['unresolved_conditions']=[c for c in m['causes'] if self.kernel.status(Key.parse(c))!='supported']
            links.append(item)
        return dict(links=links,note='Causal explanation links are separate from evidentiary inference rules. Drawing a link never establishes its effect or causal correctness.')

    def agenda(self):
        tasks=[dict(kind='assess_new_source',document=d,priority=1000) for d in self.pending_intake]
        # Ranking is deliberately transparent. No invented entropy or calibrated probabilities.
        for e in self.episodes:
            n=self.kernel.need_view(e['need'])
            if n['disposition'] in {'covered','evidence_boundary','awaiting_evidence'}:continue
            tasks.append(dict(kind='investigate',episode=e['id'],question=e['question'],need=e['need'],
                              fields=n['uncovered'],routes=n['routes'],priority=10*e['importance']+len(n['targets']),
                              warning='heuristic ranking; semantic value not independently validated'))
        return sorted(tasks,key=lambda x:-x['priority'])

    def close(self,reason,scope_approved=False):
        self.kernel.close(reason,bool(self.pending_intake),scope_approved)
        self.capture('signed_off')

    def capture(self,label):
        self.snapshots.append(dict(label=label,**copy.deepcopy(self.kernel.snapshot()),
                                   pending_intake=list(self.pending_intake),seen_documents=sorted(self.documents),causal_graph=copy.deepcopy(self.causal_view())))

    def public_view(self):
        # No hidden fixture manifest, gold labels, future events, or counterfactual arm.
        return dict(case=self.case_id,metadata=self.metadata,sources={k:v for k,v in self.documents.items()},
                    graph=self.kernel.snapshot(),causal_graph=self.causal_view(),agenda=self.agenda(),episodes=self.episodes)

    def save(self,path):
        """JSON checkpoint, not executable pickle; atomic replace."""
        payload=dict(case_id=self.case_id,documents=self.documents,pending_intake=self.pending_intake,
                     transcript=self.transcript,snapshots=self.snapshots,episodes=self.episodes,mechanisms=self.mechanisms,
                     assessments=self.assessments,metadata=self.metadata,kernel=dict(
                     sources=[asdict(s) for s in self.kernel.sources.values()],
                     archived_sources=[asdict(s) for s in self.kernel.archived_sources.values()],
                     rules=[asdict(r) for r in self.kernel.rules],retired_rules=[asdict(r) for r in self.kernel.retired_rules],
                     known_keys=[asdict(k) for k in sorted(self.kernel.known_keys)],
                     needs=[asdict(n) for n in self.kernel.needs.values()],aliases=self.kernel.aliases,
                     history=self.kernel.history,revision=self.kernel.revision,phase=self.kernel.phase,signoffs=self.kernel.signoffs))
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(payload,indent=2,default=lambda x: sorted(x) if isinstance(x,set) else str(x)));os.replace(temp,path)

    @classmethod
    def load(cls,path):
        from .kernel import Need,Coverage
        p=json.loads(Path(path).read_text());s=cls(p['case_id'])
        for name in ('documents','pending_intake','transcript','snapshots','episodes','assessments','metadata'):setattr(s,name,p[name])
        s.mechanisms=p.get('mechanisms',{})
        k=p['kernel']
        def source(x):
            return Source(x['id'],x['version'],x['origin'],tuple(Observation(Key(**o['key']),o['positive'],o['basis'],
                          tuple(Ref(**r) for r in o['requires']),o['quote']) for o in x['observations']),
                          tuple(Ref(**r) for r in x['parents']),x['content_hash'])
        def rule(x):
            return Rule(x['id'],tuple(Key(**a) for a in x['premises']),Key(**x['conclusion']),x['warrant'],
                        tuple(Ref(**a) for a in x['evidence_refs']),x['grade'],
                        tuple(x['cause_interval']) if x['cause_interval'] else None,
                        tuple(x['effect_interval']) if x['effect_interval'] else None)
        s.kernel.sources={x['id']:source(x) for x in k['sources']}
        s.kernel.archived_sources={Ref(x['id'],x['version']):source(x) for x in k['archived_sources']}
        s.kernel.rules=[rule(x) for x in k['rules']];s.kernel.retired_rules=[rule(x) for x in k['retired_rules']]
        s.kernel.known_keys={Key(**x) for x in k['known_keys']}
        for n in k['needs']:
            s.kernel.needs[n['id']]=Need(n['id'],n['asset'],n['scope'],set(n['fields']),
                [Coverage(set(c['fields']),tuple(Ref(**r) for r in c['refs']),c['route']) for c in n['coverage']],
                n['routes'],set(n['targets']),n['version'],n['history'])
        for name in ('aliases','history','revision','phase','signoffs'):setattr(s.kernel,name,k[name])
        return s
