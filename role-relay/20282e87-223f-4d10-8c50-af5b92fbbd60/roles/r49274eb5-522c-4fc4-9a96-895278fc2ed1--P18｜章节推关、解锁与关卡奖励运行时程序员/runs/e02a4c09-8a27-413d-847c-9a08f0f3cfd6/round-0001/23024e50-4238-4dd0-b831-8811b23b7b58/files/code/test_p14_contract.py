import unittest,copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from enemy_ai import bundled_catalog,publish_intent,resolve_intent,propose_phases,PhaseCheckpoint,Charge,P14SingleSlotAdapter,AiError
from enemy_ai.types import FrozenMessage,wire
from examples.fixture_inputs import snapshot,context,changed,ELITE,BOSS,P1,P2,P3
from examples.p14_fixture import (make_core,make_rules,command,authority_bytes,CountProvider,
                                  DeclaredDeckFixture,boss_edges)
from upstream.P14.battle_core import Action,Effect,Dot
from upstream.P14.battle_core.ports import CandidateRejected,DependencyUnavailable


class P14ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cat=bundled_catalog()

    def test_real_p14_damage_from_p06_skill(self):
        s=snapshot();c=context(s);core,p,_=make_core(s,c)
        result=core.submit_system(command(core)).value
        self.assertEqual('COMMITTED',result['result']);self.assertEqual('OK',result['code'])
        damage=[e for e in result['commit']['events'] if e['event_type']=='DAMAGE_APPLIED']
        self.assertEqual(1,len(damage));self.assertEqual((8,0,8,42),(damage[0]['data']['raw'],damage[0]['data']['absorbed'],damage[0]['data']['hp_loss'],damage[0]['data']['hp_after']))
        self.assertEqual(50,s.value['units'][0]['hp'])

    def test_shield_changes_actual_loss_not_preview(self):
        s=snapshot();c=context(s);s,c=changed(s,c,lambda v:v['units'][0].update(shield=8))
        core,p,_=make_core(s,c);r=core.submit_system(command(core)).value
        d=next(e['data'] for e in r['commit']['events'] if e['event_type']=='DAMAGE_APPLIED')
        self.assertEqual((8,8,0),(d['raw'],d['absorbed'],d['hp_loss']))
        self.assertEqual(8,p.action.base_amount_per_hit)

    def test_p06_elite_release_damage_projection(self):
        s=snapshot(ELITE);c=context(s,state_id='E_RELEASE',enemy_slot=7,
            charge=Charge('MOCK_P06_SKILL_E_RELEASE',('H1',),0,7,'fixture:charge'))
        s,c=changed(s,c,lambda v:v['units'][0].update(shield=4))
        core,p,_=make_core(s,c);r=core.submit_system(command(core)).value
        d=next(e['data'] for e in r['commit']['events'] if e['event_type']=='DAMAGE_APPLIED')
        self.assertEqual((24,4,20),(d['raw'],d['absorbed'],d['hp_loss']))
        self.assertNotIn('heavy_cooldown',core.state().value['snapshot'])

    def test_p06_boss_release_damage_projection(self):
        s=snapshot(BOSS);c=context(s,state_id=P1+':2',enemy_slot=7,
            charge=Charge('MOCK_P06_SKILL_B_RELEASE',('H1',),0,7,'fixture:charge'))
        s,c=changed(s,c,lambda v:v['units'][0].update(shield=4))
        core,p,_=make_core(s,c);r=core.submit_system(command(core)).value
        d=next(e['data'] for e in r['commit']['events'] if e['event_type']=='DAMAGE_APPLIED')
        self.assertEqual((36,4,32),(d['raw'],d['absorbed'],d['hp_loss']))

    def test_overkill_from_p14(self):
        s=snapshot();c=context(s);s,c=changed(s,c,lambda v:v['units'][0].update(hp=3))
        core,_,_=make_core(s,c);r=core.submit_system(command(core)).value
        d=next(e['data'] for e in r['commit']['events'] if e['event_type']=='DAMAGE_APPLIED')
        self.assertEqual((8,3,5),(d['raw'],d['hp_loss'],d['overkill']))

    def test_invalid_locked_target_skips_without_hidden_retarget(self):
        s=snapshot();c=context(s);p=publish_intent(s,c,self.cat)
        s,c=changed(s,c,lambda v:v['units'][0].update(hp=0))
        core,_,_=make_core(s,c,announcement=p.announcement);r=core.submit_system(command(core)).value
        self.assertEqual('COMMITTED',r['result']);self.assertFalse(any(e['event_type']=='DAMAGE_APPLIED' for e in r['commit']['events']))
        self.assertEqual([0,50,50],[u['hp'] for u in r['commit']['snapshot']['units'][:3]])

    def test_duplicate_request_calls_ai_once(self):
        providers=[]
        def wrap(a):providers.append(CountProvider(a));return providers[-1]
        s=snapshot();c=context(s);core,_,_=make_core(s,c,provider_wrapper=wrap);cmd=command(core)
        self.assertEqual('COMMITTED',core.submit_system(cmd).value['result']);old=authority_bytes(core)
        self.assertEqual('DUPLICATE_NO_OP',core.submit_system(cmd).value['result'])
        self.assertEqual(old,authority_bytes(core));self.assertEqual(1,providers[0].calls)

    def test_concurrent_twentyfour_retries_one_damage(self):
        providers=[]
        def wrap(a):providers.append(CountProvider(a));return providers[-1]
        s=snapshot();core,_,_=make_core(s,context(s),provider_wrapper=wrap);cmd=command(core)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:core.submit_system(cmd).value['result'],range(24)))
        self.assertEqual(1,results.count('COMMITTED'));self.assertEqual(23,results.count('DUPLICATE_NO_OP'))
        self.assertEqual(1,providers[0].calls);self.assertEqual(42,core.state().value['snapshot']['units'][0]['hp'])

    def test_stale_command_rejects_before_ai(self):
        providers=[]
        def wrap(a):providers.append(CountProvider(a));return providers[-1]
        s=snapshot();core,_,_=make_core(s,context(s),provider_wrapper=wrap);old=authority_bytes(core)
        r=core.submit_system(command(core,revision=99)).value
        self.assertEqual('REVISION_CONFLICT',r['code']);self.assertEqual(old,authority_bytes(core));self.assertEqual(0,providers[0].calls)

    def test_same_id_changed_payload_collision(self):
        s=snapshot();core,_,_=make_core(s,context(s));cmd=command(core);core.submit_system(cmd);old=authority_bytes(core)
        r=core.submit_system(command(core,revision=1)).value
        self.assertEqual('COMMAND_ID_COLLISION',r['code']);self.assertEqual(old,authority_bytes(core))

    def test_interruption_rolls_back_then_retry_matches_clean(self):
        class Cut(BaseException):pass
        for point in ('after_resolution','before_publish'):
            with self.subTest(point=point):
                fired=[]
                def interrupt(stage):
                    if stage==point and not fired:fired.append(True);raise Cut()
                s=snapshot();c=context(s);core,_,_=make_core(s,c,interrupt=interrupt);cmd=command(core);old=authority_bytes(core)
                with self.assertRaises(Cut):core.submit_system(cmd)
                self.assertEqual(old,authority_bytes(core));retry=core.submit_system(cmd)
                clean,_,_=make_core(s,c);expected=clean.submit_system(command(clean))
                self.assertEqual(expected.raw,retry.raw);self.assertEqual(authority_bytes(clean),authority_bytes(core))

    def test_rejection_uses_real_exception_class_no_fault(self):
        s=snapshot();c=context(s);p=publish_intent(s,c,self.cat)
        v=p.announcement.value;v['source_revision']=99
        from enemy_ai.planner import _seal
        core,_,_=make_core(s,c,announcement=_seal(v));old=authority_bytes(core)
        r=core.submit_system(command(core)).value
        self.assertEqual(('REJECTED','STALE_OR_FUTURE_ANNOUNCEMENT'),(r['result'],r['code']))
        self.assertEqual(old,authority_bytes(core));self.assertNotEqual('FAULTED',core.state().value['snapshot']['phase'])

    def test_lethal_dot_preempts_ai_and_phase(self):
        s=snapshot(BOSS,phase_id=P3,hp=2);c=context(s,state_id=P3+':3',enemy_slot=7,
            charge=Charge('MOCK_P06_SKILL_B_RELEASE',('H1',),1,7,'fixture:charge'))
        def mut(v):v['units'][-1]['statuses']=[{'status_instance_id':'fixture:dot','status_id':'MOCK_P03_STATUS_BURN','source_unit_id':'H1','stacks':1,'remaining_triggers':1,'insert_order':0}]
        s,c=changed(s,c,mut);providers=[]
        def wrap(a):providers.append(CountProvider(a));return providers[-1]
        rules=make_rules(self.cat,statuses=(Dot('MOCK_P03_STATUS_BURN',2,1),),boss_edges=boss_edges(self.cat,'E1'))
        core,_,_=make_core(s,c,rules=rules,provider_wrapper=wrap);r=core.submit_system(command(core)).value
        self.assertEqual('WIN',r['commit']['snapshot']['outcome']);self.assertEqual(0,providers[0].calls)
        self.assertEqual(50,r['commit']['snapshot']['units'][0]['hp'])
        self.assertFalse(any(e['event_type']=='BOSS_PHASE_PROPOSED' for e in r['commit']['events']))

    def test_nonlethal_dot_does_not_interrupt_release(self):
        s=snapshot(BOSS,hp=100);c=context(s,state_id=P1+':2',enemy_slot=7,
            charge=Charge('MOCK_P06_SKILL_B_RELEASE',('H1',),0,7,'fixture:charge'))
        def mut(v):v['units'][-1]['statuses']=[{'status_instance_id':'fixture:dot','status_id':'MOCK_P03_STATUS_BURN','source_unit_id':'H1','stacks':1,'remaining_triggers':1,'insert_order':0}]
        s,c=changed(s,c,mut);rules=make_rules(self.cat,statuses=(Dot('MOCK_P03_STATUS_BURN',2,1),),boss_edges=boss_edges(self.cat,'E1'))
        core,_,_=make_core(s,c,rules=rules);r=core.submit_system(command(core)).value
        self.assertEqual('COMMITTED',r['result']);self.assertEqual(98,r['commit']['snapshot']['units'][-1]['hp'])
        self.assertEqual(14,r['commit']['snapshot']['units'][0]['hp'])

    def test_phase_proposal_real_p14_identity_and_commit_block(self):
        s=snapshot(BOSS,battle_phase='PLAYER_READY',hp=80);c=context(s)
        def add_card(v):
            v['card_instances']=[{'instance_id':'fixture:card','card_id':'fixture:damage50','owner_unit_id':'H1'}]
            v['zones']['hand']=['fixture:card']
        s,c=changed(s,c,add_card)
        rules=make_rules(self.cat,cards=(Action('fixture:damage50','ENEMY',1,(Effect(0,'DAMAGE',50),)),),boss_edges=boss_edges(self.cat,'E1'))
        deck=DeclaredDeckFixture(({'instance_id':'fixture:card','from_zone':'hand','to_zone':'discard','to_index':0},),-1)
        core,_,_=make_core(s,c,rules=rules,deck=deck)
        r=core.submit(command(core,'PLAY_CARD','fixture:damage',payload={'actor_id':'H1','card_instance_id':'fixture:card','target_ids':['E1']})).value
        events=[e for e in r['commit']['events'] if e['event_type']=='BOSS_PHASE_PROPOSED']
        self.assertEqual([P2,P3],[e['data']['to_phase_id'] for e in events])
        after=core.snapshot('fixture:p16');v=after.value;v['boss_states'][0]['proposed_phase_ids']=[]
        # P16 checkpoint observation BEFORE P14 records its pending IDs, at the
        # same observed post-damage HP. This is an explicit checkpoint fixture.
        checkpoint_snapshot=FrozenMessage.from_value(v);bc=context(checkpoint_snapshot)
        plan=propose_phases(checkpoint_snapshot,bc,self.cat,PhaseCheckpoint('fixture:damage',80,events[0]['seq']))
        self.assertEqual([e['data']['proposal_id'] for e in events],[p.value['proposal_id'] for p in plan.proposals])
        old=authority_bytes(core)
        with self.assertRaisesRegex(DependencyUnavailable,'PHASE_COMMIT_CONTRACT_UNBOUND'):
            core.inspect_phase_proposal(plan.proposals[0])
        self.assertEqual(old,authority_bytes(core));self.assertEqual(P1,after.value['boss_states'][0]['current_phase_id'])

    def test_existing_p14_cannot_execute_partial_sweep(self):
        s=snapshot(BOSS,phase_id=P2);c=context(s);p=publish_intent(s,c,self.cat)
        s,c=changed(s,c,lambda v:v['units'][1].update(hp=0))
        decision=resolve_intent(s,c,self.cat,p.announcement)
        self.assertEqual(('H1','H3'),decision.action.target_ids)
        core,_,_=make_core(s,c,announcement=p.announcement);r=core.submit_system(command(core)).value
        # P14's fixed target_count=3 causes an explicit skip. This test documents
        # an integration blocker; it is not a passing partial-sweep integration.
        self.assertTrue(any(e['event_type']=='ENEMY_ACTION_SKIPPED' for e in r['commit']['events']))
        self.assertEqual([50,0,50],[u['hp'] for u in r['commit']['snapshot']['units'][:3]])

    def test_production_adapter_scope_is_rejected(self):
        s=snapshot();c=context(s);p=publish_intent(s,c,self.cat)
        with self.assertRaisesRegex(AiError,'P14_BEHAVIOR_COMMIT_CONTRACT_UNBOUND'):
            P14SingleSlotAdapter(self.cat,c,p.announcement,rejection_type=CandidateRejected,scope='production')

    def test_multienemy_p14_port_remains_blocked(self):
        s=snapshot();c=context(s)
        def mut(v):
            other=copy.deepcopy(v['units'][-1]);other.update(unit_id='E2',slot=1);v['units'].append(other)
        s,c=changed(s,c,mut);core,_,_=make_core(s,c);old=authority_bytes(core)
        r=core.submit_system(command(core)).value
        self.assertEqual('ENEMY_BATCH_CONTRACT_UNBOUND',r['code']);self.assertEqual(old,authority_bytes(core))
