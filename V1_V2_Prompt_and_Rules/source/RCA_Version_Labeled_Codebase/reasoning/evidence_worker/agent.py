"""Evidence Worker: restricted tool API; no privileged fixture inventory access."""
from __future__ import annotations
from shared.validation import ProposalError
from reasoning.evidence_worker.components.source_discovery import discover
from reasoning.evidence_worker.components.request_builder import validate_request

class EvidenceWorkerAgentMixin:
    def execute(self,action):
        return self.registry.execute_evidence_action(self,action)

    def _execute_baseline(self,action):
        mode=action['mode']
        if mode=='wait':return False
        gid=action['gap_id'];route=action['route']
        if mode=='discover':
            matches=discover(self.world,action['information_needed'],route)
            self.discoveries.append({'gap_id':gid,'route':route,'description':action['information_needed'],'found':[m['id'] for m in matches]})
            self.record('route_discovery',gap_id=gid,route=route,discovered=matches,
                        reason=action['possible_effect'])
            return True
        if mode=='request':
            nid=self.gaps[gid]['need_id']
            if nid:self.session.kernel.route(nid,route,'pending')
            answer=self.world.request(route,validate_request(action.get('question','')))
            self.attempts.append({'mode':mode,'gap_id':gid,'route':route,
                                  'question':action.get('question',''),
                                  'returned_document':answer['document']['id'] if answer['document'] else None,
                                  'status':answer['status']})
            self.record('evidence_requested',gap_id=gid,route=route,returned=answer['status'],
                        reason=action['possible_effect'])
            if answer['document']:
                self.assess(answer['document'],via='request_from_'+route)
                if nid and self.session.kernel.need_view(nid)['disposition']!='covered':
                    self.session.kernel.route(nid,route,'partial')
                return True
            if nid:self.session.kernel.route(nid,route,'partial')
            return True
        raise ProposalError('Unsupported action mode')

