import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'design/linguistic/reference'))
from pos_mapper import (load_rules,classify,binding_for,validate_record,replay_overrides,make_override,digest,OverrideError)

class OverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=load_rules(ROOT/'content/linguistic/pos_mapping_rules.json')
        cls.profile=json.loads((ROOT/'content/linguistic/field_profile.synthetic.json').read_text())
        cases=[json.loads(s) for s in (ROOT/'content/linguistic/classification_cases.jsonl').read_text().splitlines()]
        cls.record=cases[19]['input']
        cls.events=[json.loads(s) for s in (ROOT/'content/linguistic/override_log.synthetic.jsonl').read_text().splitlines()]

    def test_set_correction_rollback_clear_unknown_history(self):
        expected=['NOUN','VERB','NOUN','UNKNOWN','UNKNOWN']
        reasons=['MANUAL_OVERRIDE','MANUAL_OVERRIDE','MANUAL_OVERRIDE','AMBIGUOUS_LABEL','MANUAL_OVERRIDE']
        for i,(cat,why) in enumerate(zip(expected,reasons),1):
            r=classify(self.record,self.rules,self.profile,self.events[:i])
            self.assertEqual((r['category'],r['reason_code']),(cat,why))

    def test_hash_tamper_fails_closed(self):
        events=copy.deepcopy(self.events);events[0]['after_category']='VERB'
        self.assertEqual(classify(self.record,self.rules,self.profile,events)['reason_code'],'OVERRIDE_LOG_INVALID')

    def test_concurrent_head_rejected_even_rehashed(self):
        events=copy.deepcopy(self.events[:2]);events[1]['expected_head']=None
        events[1]['event_sha256']=digest({k:v for k,v in events[1].items() if k!='event_sha256'})
        with self.assertRaisesRegex(OverrideError,'CONCURRENT_EDIT'):replay_overrides(events)

    def test_before_value_conflict_rejected(self):
        events=copy.deepcopy(self.events[:2]);events[1]['before_category']='ADVERB'
        events[1]['event_sha256']=digest({k:v for k,v in events[1].items() if k!='event_sha256'})
        with self.assertRaises(OverrideError):replay_overrides(events)

    def test_duplicate_event_rejected(self):
        with self.assertRaises(OverrideError):replay_overrides(self.events[:1]*2)

    def test_missing_audit_actor_rejected(self):
        events=copy.deepcopy(self.events[:1]);events[0]['actor_ref']=''
        events[0]['event_sha256']=digest({k:v for k,v in events[0].items() if k!='event_sha256'})
        with self.assertRaises(OverrideError):replay_overrides(events)

    def test_stale_field_snapshot_does_not_inherit_override(self):
        record=copy.deepcopy(self.record);record['fields']['Expression']['value']='別の語'
        r=classify(record,self.rules,self.profile,self.events[:1])
        self.assertEqual(r['category'],'UNKNOWN');self.assertIn('STALE_OVERRIDE_NOT_APPLIED',r['warnings'])

    def test_invalid_or_unzoned_timestamp_rejected(self):
        for timestamp in ('not-a-time','2026-10-28T00:00:00'):
            events=copy.deepcopy(self.events[:1]);events[0]['recorded_at']=timestamp
            events[0]['event_sha256']=digest({k:v for k,v in events[0].items() if k!='event_sha256'})
            with self.assertRaisesRegex(OverrideError,'TIMESTAMP_INVALID'):replay_overrides(events)

    def test_another_template_does_not_inherit_override(self):
        record=copy.deepcopy(self.record);profile=copy.deepcopy(self.profile)
        record['scope_ref']=profile['scope_ref']='syn:collection-a:note-type-a:template-1'
        self.assertEqual(classify(record,self.rules,profile,self.events[:1])['reason_code'],'AMBIGUOUS_LABEL')

    def test_changed_profile_hash_requires_new_override(self):
        p=copy.deepcopy(self.profile);p['allowed_fields'].reverse()
        r=classify(self.record,self.rules,p,self.events[:1])
        self.assertEqual(r['category'],'UNKNOWN');self.assertIn('STALE_OVERRIDE_NOT_APPLIED',r['warnings'])

    def test_changed_mapping_cannot_reuse_current_override(self):
        old=load_rules(ROOT/'content/linguistic/fixtures/rollback_rules.synthetic.json')
        r=classify(self.record,old,self.profile,self.events[:1])
        self.assertEqual(r['category'],'UNKNOWN');self.assertIn('STALE_OVERRIDE_NOT_APPLIED',r['warnings'])

    def test_rollback_cannot_target_another_subject(self):
        record=copy.deepcopy(self.record);record['subject_ref']='syn:different'
        b=binding_for(record,self.profile,self.rules,validate_record(record,self.profile))
        with self.assertRaisesRegex(OverrideError,'ROLLBACK_TARGET'):make_override(self.events[:1],b,'ROLLBACK',target_event_id='syn:override-0001')

    def test_rollback_cannot_target_future_event(self):
        b=self.events[0]['binding']
        with self.assertRaises(OverrideError):make_override(self.events[:1],b,'ROLLBACK',target_event_id='syn:future')

    def test_override_cannot_bypass_no_field_authorization(self):
        p=copy.deepcopy(self.profile);p['authorization_ref']=None
        self.assertEqual(classify(self.record,self.rules,p,self.events[:1])['reason_code'],'PROFILE_NOT_AUTHORIZED')

    def test_override_never_emits_wallet_delta(self):
        for i in range(1,len(self.events)+1):
            result=classify(self.record,self.rules,self.profile,self.events[:i])
            self.assertEqual(result['reward_effect'],'NONE_PREVIEW_ONLY');self.assertFalse(result['production_award_authorized'])
            self.assertNotIn('wallet_delta',result);self.assertNotIn('review_event_id',result)

if __name__=='__main__':unittest.main()
