#!/usr/bin/env python3
"""P41 preflight only; not content or runtime tests. Python stdlib only."""
from __future__ import annotations
import csv,hashlib,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]

def evaluated_status(inputs):
    if not inputs.get('user_s09_story_explicit_approval') or not inputs.get('p01_approved_task_id'):
        return 'DEFERRED'
    required=['p04_character_baseline_approved','p07_stage_baseline_approved','p22_released_ids_and_localization_key','p23_story_ui_limits_approved','p13_p41_actual_path_mapping_authorized','target_environment_bound']
    if not all(inputs.get(key,False) for key in required):
        return 'BLOCKED'
    return 'ELIGIBLE_FOR_INDEPENDENT_REVIEW_NOT_APPROVED'

class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'P41_activation_gate.json').read_text(encoding='utf-8'))
    def test_original_state_is_deferred(self):
        self.assertEqual(self.data['status'],'DEFERRED')
        self.assertEqual(evaluated_status(self.data['gate_inputs']),'DEFERRED')
    def test_generic_order_cannot_bypass_explicit_approval(self):
        x=dict(self.data['gate_inputs']);x['p01_approved_task_id']='MOCK_TASK_ID'
        self.assertEqual(evaluated_status(x),'DEFERRED')
    def test_user_only_without_P01_stays_deferred(self):
        x=dict(self.data['gate_inputs']);x['user_s09_story_explicit_approval']=True
        self.assertEqual(evaluated_status(x),'DEFERRED')
    def test_missing_content_baseline_blocks_after_approval(self):
        x=dict(self.data['gate_inputs']);x.update(user_s09_story_explicit_approval=True,p01_approved_task_id='MOCK_TASK_ID')
        self.assertEqual(evaluated_status(x),'BLOCKED')
    def test_no_production_write(self):
        self.assertFalse(self.data['github_modified']);self.assertEqual(self.data['production_paths_written'],[])
        self.assertFalse(self.data['story_content_created'])
    def test_story_files_absent(self):
        paths=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()]
        self.assertFalse(any(p.startswith(('content/story/','design/lore/')) or p=='localization/story_strings.tsv' or p=='story_review.md' for p in paths))
    def test_blocker_owners_present(self):
        with (ROOT/'evidence/blocker_register.tsv').open(encoding='utf-8',newline='') as f:
            rs=list(csv.DictReader(f,delimiter='\t'))
        self.assertGreaterEqual(len(rs),8)
        self.assertTrue(all(r['owner'] and r['status'] and r['blocker_id'] for r in rs))
    def test_staged_approval_never_self_marks_pass(self):
        self.assertTrue(all(v=='NOT_RUN' for v in self.data['owner_review_status'].values()))
    def test_source_registry_candidate_ids_not_release(self):
        inspect=json.loads((ROOT/'evidence/input_inspection.json').read_text(encoding='utf-8'))
        self.assertEqual(inspect['p22']['registry_count'],137)
        self.assertEqual(inspect['p22']['lifecycle_counts'],{'CANDIDATE':137})
        self.assertEqual(inspect['p22']['localization_key_registration_count'],0)
    def test_verified_nested_archive_intake(self):
        evidence=json.loads((ROOT/'evidence/relay_archive_checks.json').read_text(encoding='utf-8'))
        self.assertTrue(all(not x.get('outer_manifest_fail') and not x.get('inner_manifest_fail') for x in evidence['manifest_checks']))
        self.assertTrue(all(x['crc_bad_entry'] is None for x in evidence['crc_checks']))

if __name__=='__main__':
    unittest.main(verbosity=2)
