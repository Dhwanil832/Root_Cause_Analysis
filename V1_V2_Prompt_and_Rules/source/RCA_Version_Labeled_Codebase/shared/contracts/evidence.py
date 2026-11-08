"""Source DTO with explicit provenance and unchanged raw content."""
from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceDocument:
    id:str
    title:str
    text:str
    origin:str
    def public(self):return {'id':self.id,'title':self.title,'text':self.text,'origin':self.origin}
