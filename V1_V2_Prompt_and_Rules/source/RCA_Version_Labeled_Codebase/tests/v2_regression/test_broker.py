import unittest
from pathlib import Path
from revision.v2.session import Session
from revision.v2.broker import Custodian
ROOT=Path(__file__).resolve().parent/'fixtures'
class BrokerTests(unittest.TestCase):
    def setUp(self):self.s=Session();self.b=Custodian(ROOT);self.b.initial(self.s)
    def test_initial_only_two_docs(self):self.assertEqual(set(self.s.documents),{'E01','E02'})
    def test_motion_does_not_need_hidden_mechanism(self):
        r=self.b.action(self.s,'request',owner='video',question='How did the assembly move before it fell?')
        self.assertEqual({d['id'] for d in r['released']},{'E05','E12'})
    def test_unsolicited_on_third_tick(self):
        for i in range(3):r=self.b.action(self.s,'wait')
        self.assertEqual(r['released'][0]['id'],'E10');self.assertEqual(self.s.documents['E10']['request_ids'],[])
    def test_modification_on_sixth_tick(self):
        for i in range(6):r=self.b.action(self.s,'wait')
        self.assertEqual(r['released'][0]['id'],'E13')
    def test_early_acquisition_scheduled_push_is_duplicate(self):
        self.b.action(self.s,'request',owner='outage',question='What other work was taking place?')
        self.b.action(self.s,'wait');r=self.b.action(self.s,'wait');self.assertEqual(r['released'][0]['result'],'duplicate')
    def test_correction_schedule_relative_to_oblique_delivery(self):
        b=Custodian(ROOT,'late_correction');s=Session();b.initial(s)
        b.action(s,'request',owner='video',question='Please provide the movement records.')
        b.action(s,'wait');r=b.action(s,'wait');self.assertIn('E12_correction',[x['id'] for x in r['released']])
    def test_no_lateral_variant_not_base(self):
        b=Custodian(ROOT,'no_lateral');s=Session();b.initial(s);b.action(s,'request',owner='video',question='Please provide the movement records.')
        self.assertIn('not retained',s.documents['E12']['text']);self.assertNotIn('has moved outward',s.documents['E12']['text'])
    def test_no_hidden_inventory_in_public_view(self):
        import json
        v=json.dumps(self.s.public_view());self.assertNotIn('scenario',v);self.assertNotIn('E07',v);self.assertNotIn('RUBRIC',v)
    def test_unknown_tool_does_not_execute(self):
        with self.assertRaises(ValueError):self.b.action(self.s,'read_path',path='author_only/RUBRIC.md')
    def test_local_search_no_matches_is_not_exhaustive(self):
        r=self.b.action(self.s,'search_local',query='contact geometry');self.assertTrue(r['response']['no_match_does_not_mean_nonexistence'])
    def test_broker_restart_preserves_tick(self):
        self.b.action(self.s,'wait');b=Custodian.restore(self.b.export_admin());b.action(self.s,'wait');r=b.action(self.s,'wait')
        self.assertEqual(r['released'][0]['id'],'E10')
if __name__=='__main__':unittest.main()
