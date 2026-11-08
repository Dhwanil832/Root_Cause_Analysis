"""Evidence-aware state kernel.

Input interpretations and inference warrants require a model/expert. This module
checks bookkeeping, explicit constraints and provenance, not semantic truth.
Python 3.10+, standard library only. No case-specific conclusion labels here.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Iterable
from itertools import product
import copy
import hashlib
import json


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


@dataclass(frozen=True, order=True)
class Key:
    subject: str
    proposition: str
    event_scope: str = 'day0'
    configuration: str = 'original'
    def label(self) -> str:
        return '|'.join((self.subject,self.proposition,self.event_scope,self.configuration))
    @classmethod
    def parse(cls, value: str) -> Key:
        parts=value.split('|')
        if len(parts)!=4 or not all(parts): raise ValueError('Expected four scoped claim fields')
        return cls(*parts)


@dataclass(frozen=True, order=True)
class Ref:
    source: str
    version: int


@dataclass(frozen=True)
class Observation:
    key: Key
    positive: bool = True
    # A substantive source assertion, not independent proof of an incident cause.
    basis: str = 'assessed_source_assertion'
    # Explicit claim-level derivative provenance; ALL listed refs are required.
    requires: tuple[Ref,...] = ()
    quote: str = ''


@dataclass(frozen=True)
class Source:
    id: str
    version: int
    origin: str
    observations: tuple[Observation,...]
    # Empty for primary interpretations. Used for wholly derivative documents.
    parents: tuple[Ref,...] = ()
    # Hash binds the submitted interpretation to its original raw record(s).
    content_hash: str = ''


@dataclass(frozen=True)
class Rule:
    id: str
    premises: tuple[Key,...]
    conclusion: Key
    warrant: str = ''
    evidence_refs: tuple[Ref,...] = ()
    grade: str = 'conditional_support'
    # Optional bounds supplied by an interpreter or numerical tool, not guessed.
    cause_interval: tuple[float,float] | None = None
    effect_interval: tuple[float,float] | None = None


@dataclass
class Coverage:
    fields: set[str]
    refs: tuple[Ref,...]
    route: str


@dataclass
class Need:
    id: str
    asset: str
    scope: str
    fields: set[str]
    coverage: list[Coverage] = field(default_factory=list)
    routes: dict[str,str] = field(default_factory=dict)
    targets: set[str] = field(default_factory=set)
    version: int = 1
    history: list[dict] = field(default_factory=list)
    # Dynamic properties are computed by Kernel.need_view().


@dataclass(frozen=True)
class JobToken:
    fingerprints: tuple[tuple[str,str],...]
    case_revision: int | None = None


class Kernel:
    def __init__(self, max_support_sets: int = 2048) -> None:
        self.sources: dict[str,Source] = {}
        self.archived_sources: dict[Ref,Source] = {}
        self.rules: list[Rule] = []
        self.retired_rules: list[Rule] = []
        self.needs: dict[str,Need] = {}
        self.aliases: dict[str,str] = {}
        self.history: list[dict] = []
        self.revision=0
        self.phase='active'
        self.max_support_sets=max_support_sets
        self.known_keys: set[Key]=set()
        self.signoffs: list[dict]=[]

    def ref_current(self, ref: Ref, seen=None) -> bool:
        sid=self.aliases.get(ref.source,ref.source)
        src=self.sources.get(sid)
        if src is None or src.version!=ref.version:return False
        seen=set() if seen is None else set(seen)
        if sid in seen:return False
        seen.add(sid)
        return all(self.ref_current(p,seen) for p in src.parents)

    def _validate_lineage(self, source: Source) -> None:
        refs=list(source.parents)+[r for o in source.observations for r in o.requires]
        if any(r.source==source.id for r in refs):raise ValueError('Self-dependent source')
        if any(r.version<1 or not r.source for r in refs):raise ValueError('Invalid lineage reference')
        # Protect against cycles, including forward references eventually resolving.
        graph={s.id:set(p.source for p in s.parents) | {r.source for o in s.observations for r in o.requires} for s in self.sources.values()}
        graph[source.id]={r.source for r in refs}
        self._acyclic(graph)

    @staticmethod
    def _acyclic(graph) -> None:
        visiting,done=set(),set()
        def walk(v):
            if v in visiting:raise ValueError('Cyclic dependencies')
            if v in done:return
            visiting.add(v)
            for w in graph.get(v,()):walk(w)
            visiting.remove(v);done.add(v)
        for v in graph:walk(v)

    def _record(self,event,before,**details):
        self.revision+=1
        after=self.claim_views()
        changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
        self.history.append(dict(sequence=len(self.history)+1,revision=self.revision,event=event,
                                 changed_claims=changed,**details))
        if self.phase in {'waiting','signed_off','partial_boundary'}:
            self.phase='reassessment_pending'

    def _source_fingerprint(self,s: Source):
        payload=asdict(s);payload.pop('id');payload.pop('version')
        return digest(payload)

    def receive(self,source: Source,request_ids: Iterable[str]=()) -> str:
        if not source.id or not source.origin or type(source.version) is not int or source.version<1:
            raise ValueError('Source id, origin and positive integer version required')
        if any(type(o.positive) is not bool for o in source.observations):raise ValueError('Boolean polarity required')
        self._validate_lineage(source)
        old=self.sources.get(source.id)
        if old and source.version<old.version:
            # Keep the rejected old payload for audit but never activate it.
            self.history.append(dict(sequence=len(self.history)+1,revision=self.revision,event='stale_source_ignored',source=source.id,version=source.version))
            return 'stale_version_retained_outside_active_state'
        if old and source.version==old.version:
            if source==old:return 'duplicate'
            raise ValueError('Same source version has changed interpretation/content')
        if source.id in self.aliases:
            target=self.sources[self.aliases[source.id]]
            if self._source_fingerprint(source)==self._source_fingerprint(target):return 'duplicate'
            raise ValueError('Duplicate alias cannot be revised as an independent source')
        if old is None:
            for existing in self.sources.values():
                if self._source_fingerprint(existing)==self._source_fingerprint(source):
                    self.aliases[source.id]=existing.id
                    return 'duplicate'
        before=self.claim_views()
        links=tuple(request_ids)
        bad=[q for q in links if q not in self.needs]
        if old:self.archived_sources[Ref(old.id,old.version)]=old
        self.sources[source.id]=source
        self.known_keys.update(o.key for o in source.observations)
        self._record('source_received',before,source=source.id,version=source.version,
                     request_ids=[q for q in links if q in self.needs],invalid_optional_links=bad)
        return 'accepted'

    def add_rule(self,rule: Rule) -> None:
        if rule in self.rules:return
        if any(r.id==rule.id for r in self.rules):raise ValueError('Replace a changed rule explicitly')
        if not rule.id or not rule.premises:raise ValueError('Nonempty rule and premises required')
        if not rule.warrant.strip():raise ValueError('Inference requires an explicit assessed warrant')
        if rule.grade not in {'conditional_support','deduction','hypothesis'}:raise ValueError('Invalid warrant grade')
        if rule.cause_interval and rule.effect_interval:
            if rule.cause_interval[0]>rule.effect_interval[1]:raise ValueError('Cause interval lies after effect')
        graph={}
        for r in self.rules+[rule]:
            for p in r.premises:graph.setdefault(p,set()).add(r.conclusion)
        self._acyclic(graph)
        before=self.claim_views(); self.rules.append(rule)
        self.known_keys.update(rule.premises); self.known_keys.add(rule.conclusion)
        self._record('rule_added',before,rule=asdict(rule))

    def replace_rule(self,old_id: str,new: Rule,reason: str) -> None:
        if not reason.strip():raise ValueError('Replacement reason required')
        backup=copy.deepcopy(self.__dict__)
        try:
            old=next(r for r in self.rules if r.id==old_id)
            if new.id==old.id:raise ValueError('New structure requires a new identity')
            before=self.claim_views();self.rules.remove(old);self.retired_rules.append(old)
            self.add_rule(new)
            self._record('rule_replaced',before,old_id=old_id,new_id=new.id,reason=reason)
        except Exception:
            self.__dict__=backup;raise

    def _expand_refs(self,refs) -> frozenset[Ref]:
        result=set(refs)
        def visit(ref):
            src=self.sources.get(self.aliases.get(ref.source,ref.source))
            if src is not None and src.version==ref.version:
                for parent in src.parents:
                    if parent not in result:result.add(parent);visit(parent)
        for r in list(result):visit(r)
        return frozenset(result)

    def _evaluate(self,key: Key,memo: dict):
        if key in memo:return memo[key]
        pos=[];neg=[]
        for s in self.sources.values():
            for o in s.observations:
                if o.key!=key:continue
                refs=(Ref(s.id,s.version),)+o.requires
                if all(self.ref_current(r) for r in refs):
                    (pos if o.positive else neg).append(self._expand_refs(refs))
        # Alternatives are disjunctive support sets; each rule has conjunctive premises.
        for rule in self.rules:
            if rule.conclusion!=key or rule.grade=='hypothesis':continue
            if not all(self.ref_current(r) for r in rule.evidence_refs):continue
            parent_results=[self._evaluate(p,memo) for p in rule.premises]
            if not all(x['status']=='supported' for x in parent_results):continue
            for combination in product(*(x['positive'] for x in parent_results)):
                union=frozenset().union(*combination,self._expand_refs(rule.evidence_refs))
                pos.append(union)
                if len(pos)>self.max_support_sets:raise RuntimeError('Support-set limit reached; simplify/review, never silently truncate')
        pos=list(dict.fromkeys(pos));neg=list(dict.fromkeys(neg))
        status='conflicting' if pos and neg else 'supported' if pos else 'refuted' if neg else 'unknown'
        memo[key]=dict(status=status,positive=pos,negative=neg)
        return memo[key]

    def status(self,key: Key,memo=None) -> str:
        return self._evaluate(key,{} if memo is None else memo)['status']

    def all_keys(self):return set(self.known_keys)

    def source_origins(self,key: Key,positive=True) -> set[str]:
        supports=self._evaluate(key,{})['positive' if positive else 'negative']
        return {self.sources[r.source].origin for group in supports for r in group if r.source in self.sources
                and not self.sources[r.source].parents
                and not (self.sources[r.source].observations and all(o.requires for o in self.sources[r.source].observations))}

    def claim_views(self):
        memo={};out={}
        for key in sorted(self.known_keys):
            ev=self._evaluate(key,memo)
            def encode(groups):return sorted([sorted(f'{r.source}@{r.version}' for r in g) for g in groups])
            out[key.label()]=dict(status=ev['status'],positive_supports=encode(ev['positive']),negative_supports=encode(ev['negative']),
                                 origins=sorted(self.source_origins(key)),
                                 rule_ids=sorted(r.id for r in self.rules if r.conclusion==key))
        return out

    def request(self,asset: str,scope: str,fields: set[str],targets: Iterable[str]=()) -> str:
        if not asset or not scope or not fields or not all(isinstance(f,str) and f.strip() for f in fields):raise ValueError('Bounded fields required')
        # The actor canonicalises meanings. These are exact set relationships, not semantic NLP.
        for n in self.needs.values():
            if n.asset==asset and n.scope==scope and fields<=n.fields:
                if not set(targets)<=n.targets:
                    before=self.claim_views();n.targets.update(targets);n.version+=1
                    self._record('need_targets_added',before,need=n.id)
                return n.id
        # Merge overlapping unsent/planning needs; do not silently change a sent request.
        for n in self.needs.values():
            if n.asset==asset and n.scope==scope and fields & n.fields and not any(v=='pending' for v in n.routes.values()):
                before=self.claim_views();n.fields|=fields;n.targets.update(targets);n.version+=1
                self._record('need_extended',before,need=n.id,fields=sorted(n.fields));return n.id
        nid=f'Q{len(self.needs)+1:03d}'
        before=self.claim_views();self.needs[nid]=Need(nid,asset,scope,set(fields),targets=set(targets))
        self._record('need_created',before,need=nid,fields=sorted(fields));return nid

    def route(self,nid: str,owner: str,state='ready') -> None:
        if state not in {'ready','pending','partial','answered','unavailable','denied'}:raise ValueError('Invalid route status')
        before=self.claim_views();n=self.needs[nid];n.routes[owner]=state;n.version+=1
        self._record('route_changed',before,need=nid,owner=owner,state=state)

    def respond(self,nid: str,covered=None,unavailable=False,refs: tuple[Ref,...]=(),route='unspecified') -> None:
        n=self.needs[nid];covered=set(covered or ())
        if not covered<=n.fields:raise ValueError('Unknown coverage field')
        if covered and not refs:raise ValueError('Coverage requires versioned evidence references')
        if any(not self.ref_current(r) for r in refs):raise ValueError('Coverage references inactive evidence')
        before=self.claim_views()
        if covered:n.coverage.append(Coverage(covered,tuple(refs),route))
        current_coverage=set()
        for item in n.coverage:
            if all(self.ref_current(r) for r in item.refs):current_coverage |= item.fields
        n.routes[route]='unavailable' if unavailable else ('answered' if current_coverage>=n.fields else 'partial')
        n.version+=1;n.history.append(dict(covered=sorted(covered),refs=[asdict(r) for r in refs],route=route,unavailable=unavailable))
        self._record('need_response',before,need=nid,route=route)

    def need_view(self,nid):
        n=self.needs[nid];covered=set();invalidated=False
        for c in n.coverage:
            if all(self.ref_current(r) for r in c.refs):covered |= c.fields
            else:invalidated=True
        uncovered=n.fields-covered
        if not uncovered:state='covered'
        elif invalidated:state='reassessment_needed'
        elif any(x=='pending' for x in n.routes.values()):state='awaiting_evidence'
        elif any(x in {'ready','partial'} for x in n.routes.values()):state='actionable'
        elif n.routes and all(x in {'unavailable','denied'} for x in n.routes.values()):state='evidence_boundary'
        else:state='partial' if covered else 'open'
        return dict(asset=n.asset,scope=n.scope,fields=sorted(n.fields),covered=sorted(covered),uncovered=sorted(uncovered),
                    disposition=state,routes=dict(n.routes),targets=sorted(n.targets),version=n.version,coverage_invalidated=invalidated)

    def _resource(self,name):
        kind,_,value=name.partition(':')
        if kind=='source':
            s=self.sources.get(value);return asdict(s) if s else None
        if kind=='claim':return self.claim_views().get(value,dict(status='unknown'))
        if kind=='need':return self.need_view(value) if value in self.needs else None
        if kind=='rule':return [asdict(r) for r in self.rules if r.id==value]
        if name=='phase':return self.phase
        raise ValueError('Unknown read-set resource: '+name)

    def job_snapshot(self,reads: Iterable[str] | None=None) -> JobToken:
        if reads is None:return JobToken((),self.revision)
        return JobToken(tuple(sorted((r,digest(self._resource(r))) for r in set(reads))))

    def commit_allowed(self,token: JobToken) -> bool:
        if token.case_revision is not None:return token.case_revision==self.revision
        return all(digest(self._resource(r))==fp for r,fp in token.fingerprints)

    def stale_resources(self,token):
        return [r for r,fp in token.fingerprints if digest(self._resource(r))!=fp]

    def close(self,reason: str,pending_intake=False,scope_approved=False) -> None:
        if pending_intake:raise ValueError('Unprocessed sources prevent closure')
        if any(self.need_view(q)['disposition'] in {'actionable','awaiting_evidence','open','partial','reassessment_needed'} for q in self.needs):
            if not scope_approved:raise ValueError('Open investigative work requires waiting or scoped human disposition')
        if not reason.strip():raise ValueError('Closure reason required')
        self.signoffs.append(dict(reason=reason,snapshot=copy.deepcopy(self.snapshot())))
        self.phase='signed_off';self.revision+=1
        self.history.append(dict(sequence=len(self.history)+1,revision=self.revision,event='signoff',reason=reason))

    def snapshot(self):
        views=self.claim_views()
        return dict(revision=self.revision,phase=self.phase,claims={k:v['status'] for k,v in views.items()},
                    justifications=views,rules=[asdict(r) for r in self.rules],
                    sources={k:dict(version=s.version,origin=s.origin,parents=[asdict(r) for r in s.parents]) for k,s in self.sources.items()},
                    requests={q:self.need_view(q) for q in self.needs})
