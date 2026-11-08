import unittest
from revision.v2.kernel import Kernel,Source,Key,Observation,Ref
class PartialResponseRegressionTests(unittest.TestCase):
    def test_partial_response_must_not_close_route(self):
        k=Kernel();k.receive(Source('answer',1,'answer',(Observation(Key('asset','reported_value')),)))
        q=k.request('asset','day0',{'configuration','execution'})
        k.respond(q,{'configuration'},refs=(Ref('answer',1),),route='maintenance')
        self.assertNotEqual(k.need_view(q)['disposition'],'evidence_boundary')
        self.assertIn(k.need_view(q)['disposition'],{'actionable','partial','open'})
    def test_partial_response_cannot_allow_unqualified_signoff(self):
        k=Kernel();k.receive(Source('answer',1,'answer',()))
        q=k.request('asset','day0',{'a','b'});k.respond(q,{'a'},refs=(Ref('answer',1),),route='owner')
        with self.assertRaises(ValueError):k.close('Everything complete')
    def test_withdrawn_coverage_is_reassessment_not_unavailability(self):
        k=Kernel();k.receive(Source('answer',1,'answer',()))
        q=k.request('asset','day0',{'a'});k.respond(q,{'a'},refs=(Ref('answer',1),),route='owner')
        k.receive(Source('answer',2,'answer',()))
        self.assertEqual(k.need_view(q)['disposition'],'reassessment_needed')
if __name__=='__main__':unittest.main()
