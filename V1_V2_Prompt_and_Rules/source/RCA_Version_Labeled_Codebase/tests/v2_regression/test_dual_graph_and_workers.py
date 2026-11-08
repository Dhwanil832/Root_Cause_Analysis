import unittest,copy,json
from pathlib import Path
from revision.v2.kernel import Key,Source,Observation
from revision.v2.session import Session
ROOT=Path(__file__).resolve().parent
class ExplanationGraphTests(unittest.TestCase):
    def test_drawing_candidate_causal_link_does_not_establish_cause(self):
        s=Session();s.ingest('notice','The beam fell. The cause remains to be investigated.')
        effect=Key('asset','fell').label();cause=Key('asset','support_failed').label()
        s.submit_assessment(dict(document='notice',actor='test',observations=[dict(key=effect,citations=[dict(document='notice',quote='The beam fell.')])],
           mechanisms=[dict(id='m',causes=[cause],effect=effect,grade='hypothesis',rationale='Candidate only',citations=[dict(document='notice',quote='The cause remains to be investigated.')])]))
        self.assertEqual(s.kernel.status(Key.parse(effect)),'supported');self.assertEqual(s.kernel.status(Key.parse(cause)),'unknown')
        self.assertEqual(s.causal_view()['links'][0]['status'],'hypothesis_or_reassessment')
    def test_stale_assessment_is_actually_rejected_at_commit(self):
        s=Session();s.ingest('x','A preliminary document awaits review.')
        k=Key('asset','state');s.kernel.receive(Source('prior',1,'primary',(Observation(k),)))
        job=s.start_job('x',['claim:'+k.label()]);s.kernel.receive(Source('prior',2,'primary',()))
        with self.assertRaises(ValueError):s.submit_assessment(dict(document='x',actor='test',observations=[],job_context=job))
        self.assertIn('x',s.pending_intake)
    def test_unrelated_assessment_can_commit(self):
        s=Session();s.ingest('x','A preliminary document awaits review.');job=s.start_job('x',[])
        s.kernel.receive(Source('unrelated',1,'other',(Observation(Key('other','updated')),)))
        self.assertEqual(s.submit_assessment(dict(document='x',actor='test',observations=[],job_context=job)),'accepted')
    def test_actual_partial_warrant_does_not_bind_specific_camera(self):
        # A model-consistency warrant should cite the engineering model; observed
        # pose support is already a premise and may come from independent sources.
        p=json.loads((ROOT/'walkthrough/actor_responses/E07.json').read_text())
        r=next(r for r in p['rules'] if r['id']=='qualified_offset_account')
        self.assertNotIn('E12',[v['source'] for v in r['evidence_refs']])
if __name__=='__main__':unittest.main()

class WarrantBehaviorTests(unittest.TestCase):
    def test_independent_pose_can_support_same_mechanism_after_original_camera_correction(self):
        from revision.v2.kernel import Ref
        s=Session.load(ROOT/'results/scenarios/base/session.json')
        pose=Key('RB-3','outward_position_observed')
        s.kernel.receive(Source('independent_observer',1,'new_independent_origin',(Observation(pose),)))
        s.kernel.receive(Source('E12',2,'E12',()))
        self.assertEqual(s.kernel.status(Key('RB-3','partial_offset_release_account')),'supported')
