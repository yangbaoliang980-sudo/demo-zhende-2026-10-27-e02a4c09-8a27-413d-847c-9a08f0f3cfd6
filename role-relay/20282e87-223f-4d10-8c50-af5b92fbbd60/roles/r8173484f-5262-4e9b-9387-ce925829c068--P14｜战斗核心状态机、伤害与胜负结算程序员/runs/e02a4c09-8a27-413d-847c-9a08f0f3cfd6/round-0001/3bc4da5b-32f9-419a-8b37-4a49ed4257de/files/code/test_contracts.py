import copy
import json
import unittest
from pathlib import Path
from runtime.framework.yltt_framework.codec import ContractError, FrozenMessage, canonical, loads, fingerprint, MAX_INTEGER
from runtime.framework.yltt_framework.contracts import validate, decode, validate_shape

ROOT=Path(__file__).resolve().parents[3]
def sample(name):return json.loads((ROOT/'contracts/internal/examples'/f'{name}.json').read_text())


class CodecTests(unittest.TestCase):
    def test_canonical_key_order_and_unicode(self):
        self.assertEqual(canonical({'b':2,'a':'言灵'}),b'{"a":"\xe8\xa8\x80\xe7\x81\xb5","b":2}')
        self.assertEqual(fingerprint({'b':2,'a':1}),fingerprint({'a':1,'b':2}))

    def test_reject_duplicate_nested_keys(self):
        with self.assertRaises(ContractError):loads(b'{"a":{"b":1,"b":2}}')

    def test_reject_float_nonfinite_bad_utf8_bom_surrogate(self):
        for raw in [b'1.0',b'1e3',b'NaN',b'Infinity',b'"\xff"',b'\xef\xbb\xbf{}',b'"\\ud800"']:
            with self.subTest(raw=raw),self.assertRaises(ContractError):loads(raw)

    def test_safe_integer_boundaries(self):
        self.assertEqual(loads(str(MAX_INTEGER).encode()),MAX_INTEGER)
        for n in [MAX_INTEGER+1,-MAX_INTEGER-1]:
            with self.subTest(n=n),self.assertRaises(ContractError):loads(str(n).encode())

    def test_size_and_depth_limits(self):
        for raw in [b' '*1_048_577,b'['*34+b'0'+b']'*34]:
            with self.subTest(size=len(raw)),self.assertRaises(ContractError):loads(raw)

    def test_frozen_message_has_no_shared_mutable_state(self):
        source={'a':[1,2]};message=FrozenMessage.from_value(source)
        source['a'][0]=9;returned=message.value;returned['a'].append(3)
        self.assertEqual(message.value,{'a':[1,2]})

    def test_no_non_ascii_keys_or_control_values(self):
        for value in [{'人':1},{'a':'line\nbreak'},{'a':object()}]:
            with self.subTest(value=value),self.assertRaises(ContractError):canonical(value)


class ContractTests(unittest.TestCase):
    def test_all_public_examples_are_valid(self):
        files=sorted((ROOT/'contracts/internal/examples').glob('*.json'))
        self.assertEqual(len(files),21)
        for p in files:
            with self.subTest(dto=p.stem):validate(json.loads(p.read_text()),p.stem)

    def test_exact_version_unknown_type_and_owner_claim(self):
        for field,value in [('contract_version','YLTT-INTERNAL/1.0.0'),('dto_type','P14Trusted'),('owner','P14')]:
            data=sample('BattleCommand');data[field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):validate(data)

    def test_bool_is_not_revision(self):
        data=sample('BattleCommand');data['expected_revision']=True
        with self.assertRaises(ContractError):validate(data)

    def test_malformed_type_tag_is_rejected_without_typeerror(self):
        for tag in [[],{},0,None]:
            data=sample('BattleCommand');data['dto_type']=tag
            with self.subTest(tag=tag),self.assertRaises(ContractError):validate(data)

    def test_kind_payload_binding_and_duplicate_targets(self):
        data=sample('BattleCommand');data['kind']='PLAY_CARD'
        with self.assertRaises(ContractError):validate(data)
        data['payload']={'actor_id':'hero1','card_instance_id':'cardinst1','target_ids':['enemy1','enemy1']}
        with self.assertRaises(ContractError):validate(data)

    def test_snapshot_hp_reference_and_zone_partition(self):
        for case in ['hp','owner','duplicate','missing','unknown']:
            s=sample('BattleSnapshot')
            if case=='hp':s['units'][0]['hp']=11
            elif case=='owner':s['card_instances'][0]['owner_unit_id']='missing'
            elif case=='duplicate':s['zones']['discard']=['cardinst1']
            elif case=='missing':s['zones']['hand']=[]
            else:s['zones']['hand']=['unknown']
            with self.subTest(case=case),self.assertRaises(ContractError):validate(s)

    def test_snapshot_terminal_is_not_ongoing(self):
        s=sample('BattleSnapshot');s['phase']='TERMINAL'
        with self.assertRaises(ContractError):validate(s)
        s['outcome']='WIN';validate(s)

    def test_duplicate_unit_and_slot(self):
        for kind in ['id','slot']:
            s=sample('BattleSnapshot')
            if kind=='id':s['units'][1]['unit_id']='hero1'
            else:s['units'][1]['slot']=0
            with self.subTest(kind=kind),self.assertRaises(ContractError):validate(s)

    def test_batch_cross_scope_gap_and_last_commit(self):
        for case in ['scope','gap','end','revision','highwater']:
            b=sample('BattleCommitBatch')
            if case=='scope':b['events'][1]['battle_id']='other'
            elif case=='gap':b['events'][1]['seq']=4
            elif case=='end':b['events']=b['events'][:-1]
            elif case=='revision':b['snapshot']['revision']=4
            else:b['snapshot']['last_event_seq']=4
            with self.subTest(case=case),self.assertRaises(ContractError):validate(b)

    def test_event_payload_bound_to_type(self):
        e=sample('BattleEvent');e['event_type']='DAMAGE_APPLIED'
        with self.assertRaises(ContractError):validate(e)

    def test_duplicate_reply_cannot_republish_commit(self):
        r=sample('BattleReply');r['result']='DUPLICATE_NO_OP'
        with self.assertRaises(ContractError):validate(r)
        r['commit']=None;validate(r)

    def test_battle_state_receipt_bounds(self):
        s=sample('BattleState');s['accepted_commands']=[{'command_id':'x','command_sha256':'a'*64,'committed_revision':1,'first_event_seq':1,'last_event_seq':2}]
        with self.assertRaises(ContractError):validate(s)

    def test_deck_patch_cannot_contain_state_write(self):
        d=sample('DeckPatchCandidate');d['set_hp']=0
        with self.assertRaises(ContractError):validate(d)
        d=sample('DeckPatchCandidate');d['rng_after']['initial_seed']=2
        with self.assertRaises(ContractError):validate(d)

    def test_party_has_three_distinct_slots(self):
        s=sample('PartySnapshot');s['members'][2]['slot']=1
        with self.assertRaises(ContractError):validate(s)

    def test_wallet_no_negative_balance_or_duplicate_resource(self):
        for case in ['negative','duplicate']:
            w=sample('WalletSnapshot')
            if case=='negative':w['balances'][0]['available']=-1
            else:w['balances'].append(dict(w['balances'][0]))
            with self.subTest(case=case),self.assertRaises(ContractError):validate(w)

    def test_wallet_delta_requires_source_attribution(self):
        w=sample('WalletDeltaCandidate');w['changes']=[{'resource_id':'fixture:coin','available_delta':1,'reserved_delta':0}]
        with self.assertRaises(ContractError):validate(w)

    def test_study_applied_needs_proof_and_matching_scope(self):
        s=sample('StudyStatusView');s['state']='APPLIED'
        with self.assertRaises(ContractError):validate(s)
        p=sample('CommitProofView');s.update(commit_proof=p,observed_store_instance=p['store_instance'],observed_high_watermark=p['high_watermark'],continuity_ref=p['continuity_ref'])
        validate(s);s['observed_store_instance']='other'
        with self.assertRaises(ContractError):validate(s)

    def test_study_absence_needs_continuity(self):
        s=sample('StudyStatusView');s['state']='NOT_FOUND'
        with self.assertRaises(ContractError):validate(s)
        s.update(observed_store_instance='fixture:store',observed_high_watermark=0,continuity_ref='fixture:continuity');validate(s)

    def test_lookup_unknown_is_not_a_commit(self):
        s=sample('CommitLookupView');s['proof']=sample('CommitProofView')
        with self.assertRaises(ContractError):validate(s)

    def test_lookup_absence_requires_restore_continuity(self):
        s=sample('CommitLookupView');s['status']='ABSENT'
        with self.assertRaises(ContractError):validate(s)
        s.update(observed_store_instance='fixture:store',observed_high_watermark=0,continuity_ref='fixture:continuity');validate(s)

    def test_ready_store_has_identity_version_and_watermark(self):
        s=sample('SaveStatusView');s['state']='READY'
        with self.assertRaises(ContractError):validate(s)

    def test_schema_evaluator_rejects_unknown_keywords_and_remote_refs(self):
        for shape in [{'type':'integer','multipleOf':2},{'$ref':'https://invalid.local/schema'}]:
            with self.subTest(shape=shape),self.assertRaises(ContractError):validate_shape(2,shape)


if __name__=='__main__':unittest.main()
