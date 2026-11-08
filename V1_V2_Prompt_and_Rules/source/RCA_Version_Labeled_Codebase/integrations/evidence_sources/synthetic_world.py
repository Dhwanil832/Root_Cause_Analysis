"""An isolated, read-only synthetic evidence environment.

All six records are in the world, but the investigator sees only the report
and documents actually delivered through a discovered route or human upload.
The route directory describes department responsibilities, not hidden file IDs.
"""
from __future__ import annotations
from pathlib import Path
import json, re

class EvidenceWorld:
    CAPABILITIES={
        'security':{'description':'Security can provide archived camera-review worksheets and footage access information.',
                    'keywords':('camera','video','footage','recording','security','mopping','cleaning','activity','movement')},
        'maintenance':{'description':'Maintenance handles machinery fault reports, dated work orders and service tickets.',
                       'keywords':('maintenance','repair','ticket','fault','service','leak','coupling','equipment report')},
        'engineering':{'description':'Engineering has technical operating notes, drawings and machine function descriptions.',
                       'keywords':('engineering','equipment','function','operation','hose','drain','manual','drawing','process')},
        'shift_supervisor':{'description':'Shift supervisors can help locate eyewitness statements and first-hand observations.',
                            'keywords':('witness','worker','supervisor','people','firsthand','saw','observe','slip','walkway')},
    }
    DOCUMENT_BY_ROUTE={'security':'CAM-17','maintenance':'MNT-81','engineering':'OPS-02','shift_supervisor':'WIT-06'}
    def __init__(self,fixture_path):
        self.__inventory=json.loads(Path(fixture_path).read_text())
        self.discovered={}
        self.received=set()
        self.request_history=[]
        self.discovery_history=[]
        self.unsolicited_sent=False

    def initial_packet(self):
        doc_id='IR-01';self.received.add(doc_id)
        return self._public(doc_id)

    def _public(self,doc_id):
        d=self.__inventory[doc_id]
        return {'id':doc_id,'title':d['name'],'text':d['text'],'origin':d['release']}

    def discover(self,information_description, suggested_route=None):
        """Keyword directory search. It does not reveal hidden document existence.

        Route-name requests are permitted guesses, not evidence that a document exists.
        """
        if not isinstance(information_description,str) or not information_description.strip():
            raise ValueError('Give a nonempty description of information sought')
        query=information_description.lower()
        matches=[]
        for route,info in self.CAPABILITIES.items():
            if suggested_route==route or any(term in query for term in info['keywords']):
                matches.append({'id':route,'description':info['description']})
                self.discovered[route]=info['description']
        matches.sort(key=lambda x:x['id'])
        self.discovery_history.append({'query':information_description,'suggested_route':suggested_route,
                                       'routes':[m['id'] for m in matches]})
        return matches

    def request(self,route,question):
        if route not in self.discovered:raise ValueError('Discover a route before using it')
        if not isinstance(question,str) or len(question.strip())<12:
            raise ValueError('Request must explain the sought information')
        # The initial pilot has exactly one authored record per authorized route.
        doc_id=self.DOCUMENT_BY_ROUTE.get(route)
        if not doc_id:raise ValueError('No record returned for that route')
        if doc_id in self.received:
            result={'route':route,'question':question,'status':'already_supplied','document':None}
        else:
            self.received.add(doc_id)
            result={'route':route,'question':question,'status':'delivered','document':self._public(doc_id)}
        self.request_history.append({'route':route,'question':question,'status':result['status']})
        return result

    def maybe_unsolicited(self):
        """Independent push after the camera record enters the case.

        This is a controlled scenario timing rule, not an action chosen by the agent.
        It is not leaked through route discovery or the model prompts.
        """
        if self.unsolicited_sent or 'CAM-17' not in self.received:return None
        self.unsolicited_sent=True
        self.received.add('COR-17')
        return self._public('COR-17')

    def public_routes(self):
        return [{'id':k,'description':v} for k,v in sorted(self.discovered.items())]

    def audit(self):
        """Designer-side debug data; never send to a model."""
        return {'requests':self.request_history,'discovery':self.discovery_history,
                'received':sorted(self.received),'unsolicited_delivered':self.unsolicited_sent}
