"""Assertions on fixed interpretation integration runs, never a semantic model score."""
import unittest,json,itertools
from pathlib import Path
from revision.v2.kernel import *
ROOT=Path(__file__).resolve().parent
class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results={x['scenario']:x for x in json.loads((ROOT/'results/scenario_summary.json').read_text())['scenarios']}
    def test_base_positive_findings_and_boundaries(self):
        r=self.results['base']
        self.assertEqual(r['partial_offset_account'],'supported');self.assertEqual(r['AB_mapping'],'supported')
        for p in ('incident_leak_measured','complete_trajectory','incident_extra_keeper','complete_redesign'):self.assertEqual(r[p],'unknown')
        self.assertEqual(r['valve_origins'],['VAL-17'])
    def test_timing_changes_only_relevant_path(self):
        r=self.results['shutdown_after'];self.assertEqual(r['this_shutdown_excluded'],'supported')
        self.assertEqual(r['this_shutdown_precedes'],'unknown');self.assertEqual(r['relative_motion'],'supported')
    def test_no_view_cannot_reconstruct_actual_pose(self):
        r=self.results['no_lateral'];self.assertEqual(r['offset_observation'],'unknown');self.assertEqual(r['partial_offset_account'],'unknown')
        self.assertEqual(r['relative_motion'],'supported')
    def test_identity_gap_does_not_leak_base_mapping(self):
        r=self.results['unresolved_mapping'];self.assertEqual(r['AB_mapping'],'unknown');self.assertEqual(r['fall'],'supported')
    def test_camera_correction_reopens_only_relevant_need(self):
        r=self.results['late_correction'];self.assertEqual(r['partial_offset_account'],'unknown');self.assertEqual(r['fall'],'supported')
        self.assertEqual(r['relative_motion'],'supported');self.assertEqual(r['motion_need']['uncovered'],['lateral_observation'])
        self.assertEqual(r['motion_need']['disposition'],'reassessment_needed')
    def test_all_120_permutations_fixed_interpretations(self):
        import sys
        sys.path.insert(0,str(ROOT))
        from test_runtime import setup,srcs
        docs=srcs();reference=None
        for order in itertools.permutations(('E05','E07','E12','E08','E16')):
            k=setup()
            for d in order:k.receive(docs[d])
            view=k.snapshot()['claims']
            if reference is None:reference=view
            self.assertEqual(view,reference)
if __name__=='__main__':unittest.main()
