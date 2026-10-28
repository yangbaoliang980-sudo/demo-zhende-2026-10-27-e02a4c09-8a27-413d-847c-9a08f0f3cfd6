import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'design/linguistic/reference'))
from pos_mapper import (load_rules,classify,normalize_label,strict_json,validate_rules,ContractError,ROLES,CATEGORIES)

class MapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules=load_rules(ROOT/'content/linguistic/pos_mapping_rules.json')
        cls.profile=json.loads((ROOT/'content/linguistic/field_profile.synthetic.json').read_text())
        cls.cases=[json.loads(s) for s in (ROOT/'content/linguistic/classification_cases.jsonl').read_text().splitlines()]

    def test_72_authored_cases(self):
        for c in self.cases:
            with self.subTest(case_id=c['case_id']):
                p=copy.deepcopy(self.profile);p.update(c.get('profile_patch',{}))
                result=classify(c['input'],None if c.get('missing_rules') else self.rules,p)
                for k,v in c['expected'].items():self.assertEqual(result[k],v,k)

    def test_all_eight_categories_present(self):
        self.assertEqual({c['expected']['category'] for c in self.cases if c['expected']['category']},set(CATEGORIES))

    def test_label_list_order_does_not_break_ties(self):
        for label in ('名詞/動詞','動詞/名詞','verb;NOUN','名詞・動詞'):
            r=copy.deepcopy(self.cases[0]['input']);r['fields']['品詞']['value']=label
            result=classify(r,self.rules,self.profile)
            self.assertEqual(result['category'],'UNKNOWN');self.assertEqual(result['candidates'],['NOUN','VERB'])

    def test_unknown_never_creates_award(self):
        for c in self.cases:
            result=classify(c['input'],self.rules,self.profile)
            self.assertFalse(result['production_award_authorized']);self.assertIsNone(result['quantity']);self.assertIsNone(result['formal_resource_id'])

    def test_missing_contract_does_not_use_general_branch(self):
        r=classify(self.cases[0]['input'],None,self.profile)
        self.assertEqual(r['mapping_status'],'BLOCKED');self.assertIsNone(r['category']);self.assertIsNone(r['resource_role_proposal'])

    def test_no_unapproved_value_in_output(self):
        r=copy.deepcopy(self.cases[0]['input']);r['fields']['PrivateNotes']={'state':'READABLE','value':'SECRET_SENTINEL'}
        out=classify(r,self.rules,self.profile)
        self.assertEqual(out['reason_code'],'UNAPPROVED_FIELD_PRESENT');self.assertNotIn('SECRET_SENTINEL',json.dumps(out))
        self.assertIsNone(out['observation_sha256'])

    def test_same_input_same_full_output(self):
        for c in self.cases:
            p=copy.deepcopy(self.profile);p.update(c.get('profile_patch',{}))
            self.assertEqual(classify(c['input'],self.rules,p),classify(copy.deepcopy(c['input']),self.rules,copy.deepcopy(p)))

    def test_reordered_object_keys_same_snapshot(self):
        a=self.cases[0]['input'];b=dict(reversed(list(a.items())))
        self.assertEqual(classify(a,self.rules,self.profile),classify(b,self.rules,self.profile))

    def test_mutated_rules_refused(self):
        r=copy.deepcopy(self.rules);r.data['category_aliases']['noun']='VERB'
        self.assertEqual(classify(self.cases[0]['input'],r,self.profile)['mapping_status'],'BLOCKED')

    def test_changed_reward_route_refused(self):
        d=copy.deepcopy(self.rules.data);d['categories'][0]['resource_role_proposal']='ATTACK_MATERIAL'
        with self.assertRaises(ContractError):validate_rules(d)

    def test_production_boolean_cannot_approve(self):
        d=copy.deepcopy(self.rules.data);d['production_authorized']=True
        with self.assertRaises(ContractError):validate_rules(d)

    def test_alias_compound_collision_refused(self):
        d=copy.deepcopy(self.rules.data);d['compound_pos_labels']['noun']=['VERB']
        with self.assertRaises(ContractError):validate_rules(d)

    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(ContractError):strict_json('{"x":1,"x":2}')

    def test_nonfinite_json_refused(self):
        with self.assertRaises(ContractError):strict_json('{"x":NaN}')

    def test_exact_version_and_hash_pins(self):
        path=ROOT/'content/linguistic/pos_mapping_rules.json'
        with self.assertRaises(ContractError):load_rules(path,'0'*64)
        with self.assertRaises(ContractError):load_rules(path,self.rules.sha256,'missing-version')
        self.assertEqual(load_rules(path,self.rules.sha256,self.rules.version),self.rules)

    def test_normalization_cannot_infer_word_pos(self):
        self.assertEqual(normalize_label('　ＮＯＵＮ　'),'noun')
        for value in ('きれい','かわいい','食べる','猫','今日は雨です。'):
            r=copy.deepcopy(self.cases[0]['input']);r['fields']['品詞']['value']=value
            self.assertEqual(classify(r,self.rules,self.profile)['category'],'UNKNOWN')

    def test_invalid_unicode_returns_unknown(self):
        r=copy.deepcopy(self.cases[0]['input']);r['fields']['品詞']['value']='\ud800'
        self.assertEqual(classify(r,self.rules,self.profile)['reason_code'],'INVALID_UNICODE')

    def test_invalid_record_container_returns_unknown(self):
        for value in (None,[],123,'名詞',True):
            self.assertEqual(classify(value,self.rules,self.profile)['category'],'UNKNOWN')

    def test_synthetic_rules_rollback_preserves_exact_old_output(self):
        old=load_rules(ROOT/'content/linguistic/fixtures/rollback_rules.synthetic.json')
        record=copy.deepcopy(self.cases[25]['input'])
        before=classify(record,old,self.profile);updated=classify(record,self.rules,self.profile);rolled_back=classify(record,old,self.profile)
        self.assertEqual(before['category'],'UNKNOWN');self.assertEqual(updated['category'],'NA_ADJECTIVE')
        self.assertEqual(before,rolled_back);self.assertNotEqual(old.sha256,self.rules.sha256)

if __name__=='__main__':unittest.main()
