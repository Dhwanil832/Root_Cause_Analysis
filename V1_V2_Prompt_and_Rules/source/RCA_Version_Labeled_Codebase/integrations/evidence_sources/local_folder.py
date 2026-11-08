"""Optional real-file evidence environment; only requested sources are released.

Usage: --incident /case/initial.md --evidence-dir /case/evidence
The host may see all local documents. Only delivered documents appear in LLM prompts.
Folders inside evidence-dir are custodian routes. The folder `unsolicited/` is
an independent incoming queue and is not exposed by route discovery.
"""
from __future__ import annotations
from pathlib import Path
import re
from integrations.utilities.file_reader import read_document

WORDS=re.compile(r'[a-z0-9]{4,}')
class LocalEvidenceWorld:
    def __init__(self,incident,evidence_dir):
        self.incident=Path(incident)
        self.root=Path(evidence_dir)
        if not self.incident.is_file():raise FileNotFoundError(self.incident)
        if not self.root.is_dir():raise NotADirectoryError(self.root)
        # Every released source must have an unambiguous identity.
        stems={self.incident.stem}
        for candidate in self.root.rglob('*'):
            if not candidate.is_file() or candidate.name=='route_description.md':continue
            if candidate.suffix.lower() not in {'.md','.txt','.json','.csv'}:continue
            if candidate.stem in stems:
                raise ValueError(f'Duplicate source ID across custodians: {candidate.stem}')
            stems.add(candidate.stem)
        self.discovered={}
        self.received=set()
        self.request_history=[]
        self.discovery_history=[]
        self._unsolicited=iter(sorted((self.root/'unsolicited').glob('*.md')) if (self.root/'unsolicited').exists() else [])
    def _doc(self,path,origin):
        path=Path(path)
        doc_id=path.stem
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}',doc_id):raise ValueError('Invalid source filename stem')
        return {'id':doc_id,'title':path.name,'text':read_document(path),'origin':origin}
    def initial_packet(self):
        doc=self._doc(self.incident,'initial_incident_report')
        self.received.add(doc['id'])
        return doc
    def _routes(self):
        return {p.name:p for p in self.root.iterdir() if p.is_dir() and p.name!='unsolicited' and not p.name.startswith('.')}
    def discover(self,information_description,suggested_route=None):
        known=self._routes()
        matching=[]
        query=information_description.lower()
        for name,folder in known.items():
            route_terms=set(name.replace('_',' ').split())
            if name==suggested_route or any(word in query for word in route_terms):
                description=(folder/'route_description.md').read_text() if (folder/'route_description.md').exists() else f'{name} can review requests for available local records.'
                self.discovered[name]=description
                matching.append({'id':name,'description':description})
        self.discovery_history.append({'query':information_description,'suggested_route':suggested_route,'routes':[m['id'] for m in matching]})
        return matching
    def request(self,route,question):
        if route not in self.discovered:raise ValueError('Route must be discovered first')
        if not isinstance(question,str) or len(question.strip())<12:raise ValueError('Request must specify the information needed')
        folder=self._routes()[route]
        files=[p for p in folder.iterdir() if p.is_file() and p.name!='route_description.md' and p.suffix.lower() in {'.md','.txt','.json','.csv'}]
        unseen=[p for p in files if p.stem not in self.received]
        # Lexical matching is explicitly weak; custodians never return internal future filenames.
        words=set(WORDS.findall(question.lower()))
        ranked=[]
        for file in unseen:
            text=read_document(file)
            score=len(words & set(WORDS.findall(text.lower())))
            ranked.append((score,file.name,file))
        ranked.sort(key=lambda e:(-e[0],e[1]))
        best=ranked[0][-1] if ranked and ranked[0][0]>0 else None
        doc=self._doc(best,f'request_from_{route}') if best else None
        if doc:self.received.add(doc['id'])
        result={'route':route,'question':question,'status':'delivered' if doc else 'not_found','document':doc}
        self.request_history.append({'route':route,'question':question,'status':result['status']})
        return result
    def maybe_unsolicited(self):
        for next_source in self._unsolicited:
            doc=self._doc(next_source,'unsolicited_human_upload')
            if doc['id'] not in self.received:
                self.received.add(doc['id'])
                return doc
        return None
    def public_routes(self):
        return [{'id':k,'description':v} for k,v in sorted(self.discovered.items())]
    def audit(self):
        return {'received':sorted(self.received),'requests':self.request_history,'discovery':self.discovery_history}
