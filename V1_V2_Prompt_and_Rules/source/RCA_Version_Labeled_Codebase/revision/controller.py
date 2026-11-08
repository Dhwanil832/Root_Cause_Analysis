"""Only controller can admit source interpretations and modify persistent v2 state."""
from __future__ import annotations
from revision.v2.session import Session

class Controller:
    def ingest(self,session:Session,source:dict,origin:str):
        return session.ingest(source['id'],source['text'],origin)

    def commit(self,session:Session,proposal:dict):
        return session.submit_assessment(proposal)

    def snapshot(self,session:Session):
        return session.public_view()

    def close(self,session:Session,reason:str,scope_approved=False):
        return session.close(reason,scope_approved)
