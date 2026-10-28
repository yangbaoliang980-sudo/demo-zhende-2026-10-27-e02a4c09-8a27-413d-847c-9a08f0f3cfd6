import copy
from dataclasses import FrozenInstanceError,replace
from concurrent.futures import ThreadPoolExecutor
import unittest

from battle_core import (BattleCore,Action,BossEdge,Dot,Effect,Reaction,Rules,
                         CandidateRejected,DependencyUnavailable)
from battle_core.replay import replay
from battle_core.wire import ContractError,FrozenMessage,MAX_INTEGER,checked,fingerprint,message
from examples.fixture_ports import ScriptedDeck,ScriptedEnemy,move
from .helpers import native,command,authority_bytes,all_events,add_dot


class CoreAcceptanceTests(unittest.TestCase):
    def assertNoMutation(self,core,call,code):
        before=authority_bytes(core)
        reply=call().value
        self.assertEqual(reply['code'],code)
        self.assertEqual(reply['result'],'REJECTED')
        self.assertIsNone(reply['commit'])
        self.assertEqual(authority_bytes(core),before)
        return reply

    def test_damage_cost_card_and_revision_are_one_commit(self):
        core,_,_=native();reply=core.submit(command(core)).value
        self.assertEqual((reply['result'],reply['code']),('COMMITTED','OK'))
        s=core.state().value['snapshot'];enemy=s['units'][-1]
        self.assertEqual((enemy['shield'],enemy['hp'],s['energy'],s['revision']),(0,9,2,1))
        self.assertNotIn('c1',s['zones']['hand']);self.assertIn('c1',s['zones']['discard'])
        self.assertEqual([e['event_type'] for e in reply['commit']['events']],
                         ['COMMAND_ACCEPTED','ENERGY_SPENT','CARD_MOVED','EFFECT_STARTED','DAMAGE_APPLIED','COMMAND_COMMITTED'])

    def test_duplicate_before_stale_revision_and_closed_guard(self):
        def alter(s):s['units'][-1].update(hp=2,shield=0)
        core,deck,enemy=native(alter=alter);cmd=command(core)
        core.submit(cmd);before=authority_bytes(core);calls=deck.calls
        r=core.submit(cmd).value
        self.assertEqual(r['result'],'DUPLICATE_NO_OP');self.assertIsNone(r['commit'])
        self.assertEqual(authority_bytes(core),before);self.assertEqual(deck.calls,calls)
        self.assertNoMutation(core,lambda:core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','late')),'ALREADY_CLOSED')
        self.assertEqual(enemy.calls,0)
        self.assertEqual(sum(e['event_type']=='BATTLE_FINISHED' for e in all_events(core)),1)

    def test_same_id_with_changed_revision_is_collision(self):
        core,_,_=native();cmd=command(core);core.submit(cmd)
        self.assertNoMutation(core,lambda:core.submit(command(core,revision=1)),'COMMAND_ID_COLLISION')

    def test_same_id_different_target_is_collision_before_target_checks(self):
        core,_,_=native();core.submit(command(core))
        self.assertNoMutation(core,lambda:core.submit(command(core,revision=0,targets=['P1'])),'COMMAND_ID_COLLISION')

    def test_old_revision_changes_no_state_or_replay_or_seq(self):
        core,_,_=native();core.submit(command(core))
        self.assertNoMutation(core,lambda:core.submit(command(core,cid='old',revision=0)),'REVISION_CONFLICT')

    def test_new_id_for_discarded_card_is_rejected(self):
        core,_,_=native();core.submit(command(core))
        self.assertNoMutation(core,lambda:core.submit(command(core,cid='second')),'CARD_NOT_IN_HAND')

    def test_rejected_id_is_reusable_with_corrected_payload(self):
        core,deck,_=native()
        self.assertNoMutation(core,lambda:core.submit(command(core,targets=['unknown'])),'TARGET_INVALID')
        self.assertEqual(deck.calls,0)
        self.assertEqual(core.submit(command(core)).value['result'],'COMMITTED')
        self.assertEqual(len(core.state().value['accepted_commands']),1)

    def test_target_side_dead_and_actor_owner_checks_precede_payment(self):
        variants=[({'targets':['P1']},None,'TARGET_INVALID'),
                  ({'targets':['E1']},lambda s:s['units'][0].update(hp=0),'ACTOR_INVALID'),
                  ({'actor':'P2'},None,'CARD_OWNER_INVALID')]
        for args,alter,code in variants:
            with self.subTest(code=code):
                core,deck,_=native(alter=alter)
                self.assertNoMutation(core,lambda:core.submit(command(core,**args)),code)
                self.assertEqual(deck.calls,0)

    def test_user_cannot_send_system_command_or_abort(self):
        core,_,_=native()
        for kind in ['SYSTEM_START','SYSTEM_ENEMY_ACTION','SYSTEM_ENTER_PLAYER_TURN','ABORT']:
            with self.subTest(kind=kind):
                self.assertNoMutation(core,lambda:core.submit(command(core,kind,'unauthorized')),'COMMAND_CHANNEL_FORBIDDEN')

    def test_wrong_battle_scope_cannot_reuse_command(self):
        core,_,_=native();cmd=command(core).value;cmd['battle_id']='fixture:other'
        self.assertNoMutation(core,lambda:core.submit(cmd),'BATTLE_ID_MISMATCH')

    def test_invalid_wire_data_raises_without_state_change(self):
        for mutate in [lambda d:d.update(extra=True),lambda d:d.update(expected_revision=True),
                       lambda d:d.update(expected_revision=0.0),
                       lambda d:d['payload'].update(target_ids=['E1','E1']),
                       lambda d:d.update(contract_version='YLTT-INTERNAL/99')]:
            core,_,_=native();before=authority_bytes(core);d=command(core).value;mutate(d)
            with self.assertRaises(ContractError):core.submit(d)
            self.assertEqual(authority_bytes(core),before)

    def test_unbound_deck_is_blocked_without_partial_accept(self):
        core,_,_=native(deck_factory=lambda r,s:None)
        self.assertNoMutation(core,lambda:core.submit(command(core)),'DEPENDENCY_UNAVAILABLE')

    def test_negative_deck_verdict_preserves_receipts(self):
        def factory(r,s):return ScriptedDeck(r.deck_policy_version,[{'command_id':'play','reject_code':'P15_POLICY_REJECTED'}])
        core,_,_=native(deck_factory=factory)
        self.assertNoMutation(core,lambda:core.submit(command(core)),'P15_POLICY_REJECTED')

    def test_only_p15_candidate_sets_cost_no_second_deduction(self):
        def factory(r,s):
            s[0]['energy_delta']=-2
            return ScriptedDeck(r.deck_policy_version,s)
        core,_,_=native(deck_factory=factory);core.submit(command(core))
        self.assertEqual(core.state().value['snapshot']['energy'],1)
        self.assertEqual([e['data']['amount'] for e in all_events(core) if e['event_type']=='ENERGY_SPENT'],[2])

    def test_insufficient_energy_rolls_back_everything(self):
        core,_,_=native(alter=lambda s:s.update(energy=0))
        self.assertNoMutation(core,lambda:core.submit(command(core)),'ENERGY_INSUFFICIENT')

    def test_candidate_binding_and_rng_rejections(self):
        cases=[('battle_id','fixture:other','DECK_CANDIDATE_BINDING_MISMATCH'),
               ('command_id','other','DECK_CANDIDATE_BINDING_MISMATCH'),
               ('expected_revision',1,'DECK_CANDIDATE_BINDING_MISMATCH'),
               ('command_sha256','a'*64,'DECK_CANDIDATE_BINDING_MISMATCH'),
               ('snapshot_sha256','b'*64,'DECK_CANDIDATE_BINDING_MISMATCH'),
               ('policy_version','fixture:other-policy','DECK_CANDIDATE_BINDING_MISMATCH'),
               ('rng_after',{'algorithm':'xorshift32-v1','initial_seed':1,'state':1,'draw_count':1},'DECK_RNG_INVALID'),
               ('rng_before',{'algorithm':'xorshift32-v1','initial_seed':1,'state':270369,'draw_count':1},'CANDIDATE_SCHEMA_INVALID'),
               ('rng_before',{'algorithm':'xorshift32-v1','initial_seed':1,'state':2,'draw_count':0},'DECK_RNG_INVALID'),
               ('energy_delta',1,'DECK_PAYMENT_SIGN_INVALID')]
        for key,value,code in cases:
            with self.subTest(field=key,value=value):
                class TamperedDeck(ScriptedDeck):
                    def propose(self,cmd,snapshot):
                        p=super().propose(cmd,snapshot).value;p[key]=value
                        return FrozenMessage.from_value(p)
                core,_,_=native(deck_factory=lambda r,s:TamperedDeck(r.deck_policy_version,s))
                self.assertNoMutation(core,lambda:core.submit(command(core)),code)

    def test_bad_deck_move_cannot_leave_a_half_fee(self):
        cases=[([move('missing','hand','discard',0)],'DECK_MOVE_SOURCE_INVALID'),
               ([move('c1','draw','discard',0)],'DECK_MOVE_SOURCE_INVALID'),
               ([move('c1','hand','discard',3)],'DECK_MOVE_INDEX_INVALID'),
               ([], 'PLAYED_CARD_NOT_MOVED'),
               ([move('c1','hand','exhaust',0)],'PLAYED_CARD_NOT_MOVED'),
               ([move('c1','hand','discard',0),move('c1','hand','discard',1)],'DECK_MOVE_SOURCE_INVALID')]
        for moves,code in cases:
            with self.subTest(code=code,moves=moves):
                def factory(r,s):s[0]['moves']=moves;return ScriptedDeck(r.deck_policy_version,s)
                core,_,_=native(deck_factory=factory)
                self.assertNoMutation(core,lambda:core.submit(command(core)),code)

    def test_one_turn_increment_across_a_complete_cycle(self):
        core,_,_=native();core.submit(command(core))
        end=command(core,'END_TURN','end');core.submit(end)
        self.assertEqual(core.state().value['snapshot']['turn_number'],1)
        before=authority_bytes(core)
        self.assertEqual(core.submit(end).value['result'],'DUPLICATE_NO_OP')
        self.assertEqual(authority_bytes(core),before)
        self.assertNoMutation(core,lambda:core.submit(command(core,'END_TURN','another-end')),'PHASE_INVALID')
        core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','enemy'))
        self.assertEqual((core.state().value['snapshot']['turn_number'],core.state().value['snapshot']['phase']),(2,'PLAYER_TURN_PENDING'))
        core.submit_system(command(core,'SYSTEM_ENTER_PLAYER_TURN','enter'))
        self.assertEqual((core.state().value['snapshot']['turn_number'],core.state().value['snapshot']['phase']),(2,'PLAYER_READY'))

    def test_system_start_is_one_commit(self):
        core,_,_=native(alter=lambda s:s.update(phase='CREATED',turn_number=0,energy=0))
        r=core.submit_system(command(core,'SYSTEM_START','start')).value
        self.assertEqual((r['result'],r['code']),('COMMITTED','OK'))
        s=core.state().value['snapshot']
        self.assertEqual((s['phase'],s['turn_number'],s['revision'],s['energy']),('PLAYER_READY',1,1,3))

    def test_start_with_both_sides_dead_is_draw_before_resources(self):
        def alter(s):
            s.update(phase='CREATED',turn_number=0,energy=0)
            for u in s['units']:u['hp']=0
        core,deck,enemy=native(alter=alter)
        core.submit_system(command(core,'SYSTEM_START','start'))
        self.assertEqual(core.result().value['outcome'],'DRAW')
        self.assertEqual((deck.calls,enemy.calls),(0,0))

    def test_heal_clamps_and_cannot_revive(self):
        core,_,_=native(alter=lambda s:s['units'][0].update(hp=8))
        core.submit(command(core,cid='heal',card='c3',targets=['P1']))
        e=next(e for e in all_events(core) if e['event_type']=='HEAL_APPLIED')
        self.assertEqual((e['data']['amount'],e['data']['hp_after']),(2,10))
        core,_,_=native(alter=lambda s:s['units'][1].update(hp=0))
        self.assertNoMutation(core,lambda:core.submit(command(core,cid='heal',card='c3',targets=['P2'])),'TARGET_INVALID')

    def test_explicit_shield_cap_and_overflow_policy(self):
        for policy in ['CLAMP','REJECT']:
            core,_,_=native(alter=lambda s:s['units'][0].update(shield=39),
                            rule_changes={'shield_cap':40,'shield_overflow':policy})
            cmd=command(core,cid='shield',card='c2',targets=['P1'])
            if policy=='REJECT':self.assertNoMutation(core,lambda:core.submit(cmd),'SHIELD_CAP_EXCEEDED')
            else:
                core.submit(cmd)
                self.assertEqual(core.state().value['snapshot']['units'][0]['shield'],40)

    def test_multi_hit_resolves_shield_per_hit(self):
        core,_,_=native();core.submit(command(core,cid='double',card='c5'))
        hits=[e['data'] for e in all_events(core) if e['event_type']=='DAMAGE_APPLIED']
        self.assertEqual([(h['raw'],h['absorbed'],h['hp_loss']) for h in hits],[(3,3,0),(5,2,3)])

    def test_dead_target_receives_no_second_hit(self):
        core,_,_=native(alter=lambda s:s['units'][-1].update(hp=2,shield=0))
        core.submit(command(core,cid='double',card='c5'))
        self.assertEqual(sum(e['event_type']=='DAMAGE_APPLIED' for e in all_events(core)),1)
        self.assertEqual(sum(e['event_type']=='UNIT_DIED' for e in all_events(core)),1)
        self.assertEqual(core.result().value['outcome'],'WIN')

    def test_dot_does_not_damage_immediately(self):
        core,_,_=native();core.submit(command(core,cid='dot',card='c4'))
        self.assertEqual(core.state().value['snapshot']['units'][-1]['hp'],12)
        self.assertFalse(any(e['event_type']=='DAMAGE_APPLIED' for e in all_events(core)))

    def test_dot_reapplication_remains_blocked(self):
        core,_,_=native(alter=lambda s:add_dot(s,'E1'))
        self.assertNoMutation(core,lambda:core.submit(command(core,cid='dot',card='c4')),'STATUS_REAPPLY_UNDEFINED')

    def test_player_dot_terminal_precedes_resources_and_draw(self):
        def alter(s):
            s['phase']='PLAYER_TURN_PENDING';s['turn_number']=2;s['energy']=0
            s['units'][0]['hp']=3;s['units'][1]['hp']=0;s['units'][2]['hp']=0;add_dot(s,'P1')
        core,deck,enemy=native(alter=alter)
        core.submit_system(command(core,'SYSTEM_ENTER_PLAYER_TURN','enter'))
        self.assertEqual(core.result().value['outcome'],'LOSS')
        self.assertEqual((deck.calls,enemy.calls),(0,0));self.assertEqual(core.state().value['snapshot']['energy'],0)

    def test_enemy_dot_terminal_precedes_ai_and_second_action(self):
        def alter(s):
            s['phase']='ENEMY_READY';s['units'][-1].update(hp=3,shield=0);add_dot(s,'E1')
        core,_,enemy=native(alter=alter);cmd=command(core,'SYSTEM_ENEMY_ACTION','enemy')
        core.submit_system(cmd)
        self.assertEqual(core.result().value['outcome'],'WIN');self.assertEqual(enemy.calls,0)
        self.assertNoMutation(core,lambda:core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','second')),'ALREADY_CLOSED')

    def test_dot_expiry_then_resources_uses_post_dot_basis(self):
        bases=[]
        class Observed(ScriptedDeck):
            def propose(self,c,s):bases.append(s.value);return super().propose(c,s)
        def alter(s):s.update(phase='PLAYER_TURN_PENDING',turn_number=2);add_dot(s,'P1')
        core,_,_=native(alter=alter,deck_factory=lambda r,s:Observed(r.deck_policy_version,s))
        core.submit_system(command(core,'SYSTEM_ENTER_PLAYER_TURN','enter'))
        self.assertEqual((bases[0]['units'][0]['hp'],bases[0]['units'][0]['statuses']),(7,[]))
        events=all_events(core)
        self.assertLess(next(e['seq'] for e in events if e['event_type']=='DAMAGE_APPLIED'),
                        next(e['seq'] for e in events if e['event_type']=='STATUS_CHANGED'))

    def test_dot_units_and_statuses_use_slot_and_insert_order(self):
        def alter(s):
            s.update(phase='PLAYER_TURN_PENDING',turn_number=2)
            add_dot(s,'P2',insert_order=5,status_id='burn');add_dot(s,'P1',insert_order=4,status_id='other')
            add_dot(s,'P1',insert_order=2,status_id='burn');s['units'].reverse()
        core,_,_=native(alter=alter,rule_changes={'statuses':(Dot('burn',1,1),Dot('other',2,1))})
        core.submit_system(command(core,'SYSTEM_ENTER_PLAYER_TURN','enter'))
        hits=[e['data'] for e in all_events(core) if e['event_type']=='DAMAGE_APPLIED']
        self.assertEqual([(h['target_unit_id'],h['raw']) for h in hits],[('P1',1),('P1',2),('P2',1)])

    def test_death_retaliation_finishes_as_single_draw(self):
        def alter(s):
            s['units'][0]['hp']=4;s['units'][1]['hp']=0;s['units'][2]['hp']=0
            s['units'][-1].update(hp=8,shield=0)
        core,_,_=native(alter=alter,rule_changes={'reactions':(Reaction('E1','death','ON_DEATH',4),)})
        core.submit(command(core))
        self.assertEqual([e['data']['outcome'] for e in all_events(core) if e['event_type']=='BATTLE_FINISHED'],['DRAW'])

    def test_root_effects_finish_before_reactions(self):
        core,_,_=native(rule_changes={'reactions':(Reaction('E1','retaliate','ON_DAMAGED',1),)})
        core.submit(command(core,cid='double',card='c5'))
        hits=[e['data']['source_unit_id'] for e in all_events(core) if e['event_type']=='DAMAGE_APPLIED']
        self.assertEqual(hits,['P1','P1','E1','E1'])

    def test_reaction_queue_is_breadth_first_and_tier_stable(self):
        reactions=(Reaction('E1','later','ON_DAMAGED',1,2),Reaction('E1','first','ON_DAMAGED',1,1),
                   Reaction('P1','child','ON_DAMAGED',1))
        def alter(s):s['units'][-1].update(hp=9,shield=0)
        core,_,_=native(alter=alter,rule_changes={'reactions':reactions})
        core.submit(command(core))
        started=[x for x in core.resolution_traces()[0].value['steps'] if x['kind']=='REACTION_STARTED']
        self.assertEqual([x['trigger_id'] for x in started[:2]],['first','later'])
        self.assertEqual([x['depth'] for x in started],sorted(x['depth'] for x in started))

    def test_reaction_limit_rolls_back_gameplay_then_commits_only_fault(self):
        def alter(s):
            for u in s['units']:u.update(hp=100000,max_hp=100000,shield=0)
        core,_,_=native(alter=alter,rule_changes={'reactions':(Reaction('P1','reflect-p','ON_DAMAGED',1),Reaction('E1','reflect-e','ON_DAMAGED',1))})
        before=core.state().value['snapshot'];cmd=command(core);r=core.submit(cmd).value
        self.assertEqual((r['result'],r['code']),('COMMITTED','REACTION_LIMIT'))
        after=core.state().value['snapshot']
        for key in ['units','energy','zones','rng','turn_number']:self.assertEqual(after[key],before[key])
        self.assertEqual((after['phase'],after['revision']),('FAULTED',1))
        self.assertEqual([e['event_type'] for e in all_events(core)],['COMMAND_ACCEPTED','BATTLE_FAULTED','COMMAND_COMMITTED'])
        self.assertIsNone(core.result());self.assertEqual(core.submit(cmd).value['result'],'DUPLICATE_NO_OP')
        self.assertEqual(replay(core.export_replay()).state().raw,core.state().raw)

    def test_abort_is_closed_without_battle_result(self):
        core,_,_=native();core.abort(command(core,'ABORT','quit'))
        self.assertEqual(core.state().value['snapshot']['outcome'],'ABORTED');self.assertIsNone(core.result())
        self.assertNoMutation(core,lambda:core.submit(command(core)),'ALREADY_CLOSED')

    def test_interruptions_at_all_precommit_points_leave_no_result_or_event(self):
        class Interrupt(BaseException):pass
        for point in ['after_deck_patch','after_resolution','before_publish']:
            with self.subTest(point=point):
                armed=[True]
                def hook(stage):
                    if armed[0] and stage==point:raise Interrupt()
                core,_,_=native(alter=lambda s:s['units'][-1].update(hp=2,shield=0),interrupt=hook)
                before=authority_bytes(core);cmd=command(core)
                with self.assertRaises(Interrupt):core.submit(cmd)
                self.assertEqual(authority_bytes(core),before)
                armed[0]=False
                self.assertEqual(core.submit(cmd).value['code'],'OK');self.assertEqual(core.result().value['outcome'],'WIN')

    def test_snapshot_and_result_cannot_be_mutated_through_return_values(self):
        core,_,_=native(alter=lambda s:s['units'][-1].update(hp=2,shield=0))
        view=core.snapshot('fixture:native');value=view.value;value['units'][0]['hp']=0
        self.assertEqual(core.snapshot('fixture:native').value['units'][0]['hp'],10)
        core.submit(command(core));result=core.result();value=result.value;value['outcome']='LOSS'
        self.assertEqual(core.result().value['outcome'],'WIN')
        with self.assertRaises((FrozenInstanceError,AttributeError)):result.raw=b'{}'

    def test_concurrent_identical_requests_commit_once(self):
        core,deck,_=native();cmd=command(core)
        with ThreadPoolExecutor(max_workers=8) as pool:replies=list(pool.map(lambda _:core.submit(cmd).value,range(24)))
        self.assertEqual(sum(r['result']=='COMMITTED' for r in replies),1)
        self.assertEqual(sum(r['result']=='DUPLICATE_NO_OP' for r in replies),23)
        self.assertEqual((deck.calls,len(core.committed_batches())),(1,1))

    def test_reentrant_provider_cannot_commit_nested_command(self):
        held={};nested=[]
        class Reentrant(ScriptedDeck):
            def propose(self,c,s):nested.append(held['core'].submit(c).value);return super().propose(c,s)
        core,_,_=native(deck_factory=lambda r,s:Reentrant(r.deck_policy_version,s));held['core']=core
        core.submit(command(core))
        self.assertEqual(nested[0]['code'],'REENTRANT_COMMAND');self.assertEqual(len(core.committed_batches()),1)

    def test_result_hash_binds_final_snapshot_and_replay(self):
        core,_,_=native(alter=lambda s:s['units'][-1].update(hp=2,shield=0));core.submit(command(core))
        result=core.result().value
        self.assertEqual(result['final_snapshot_sha256'],core.snapshot('fixture:native').sha256)
        self.assertEqual(result['replay_input_sha256'],core.export_replay().sha256)
        finish=next(e for e in all_events(core) if e['event_type']=='BATTLE_FINISHED')
        self.assertEqual(result['terminal_event_seq'],finish['seq'])
        self.assertLess(result['terminal_event_seq'],core.state().value['snapshot']['last_event_seq'])

    def test_production_mode_is_unavailable(self):
        core,_,_=native()
        with self.assertRaises(DependencyUnavailable):BattleCore(core.state(),core._rules,stage_id='s',profile_scope='p',mode='production')

    def test_p13_terminal_fixture_does_not_fabricate_a_result(self):
        def alter(s):s.update(phase='TERMINAL',outcome='WIN');s['units'][-1].update(hp=0)
        core,_,_=native(alter=alter)
        self.assertIsNone(core.result())
        self.assertNoMutation(core,lambda:core.submit(command(core)),'ALREADY_CLOSED')

    def test_unbound_multi_enemy_schedule_fails_closed(self):
        def alter(s):
            s['phase']='ENEMY_READY';u=copy.deepcopy(s['units'][-1]);u.update(unit_id='E2',slot=1);s['units'].append(u)
        core,_,enemy=native(alter=alter)
        self.assertNoMutation(core,lambda:core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','enemy')),'ENEMY_BATCH_CONTRACT_UNBOUND')
        self.assertEqual(enemy.calls,0)

    def test_enemy_skip_preserves_locked_target_and_does_not_retarget(self):
        def alter(s):s['phase']='ENEMY_READY';s['units'][0]['hp']=0
        def factory(script):script['no_valid_target']='SKIP';return ScriptedEnemy(script)
        core,_,_=native(alter=alter,enemy_factory=factory);core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','enemy'))
        self.assertFalse(any(e['event_type']=='DAMAGE_APPLIED' for e in all_events(core)))
        self.assertTrue(any(e['event_type']=='ENEMY_ACTION_SKIPPED' for e in all_events(core)))

    def test_unsupported_buff_content_stays_disabled(self):
        disabled=Action('strike','ENEMY',1,(),playable=False)
        core,_,_=native(rule_changes={'cards':(disabled,)})
        self.assertNoMutation(core,lambda:core.submit(command(core)),'CONTENT_DISABLED')
        with self.assertRaises(ValueError):Effect(0,'BUFF',2)

    def test_source_card_owner_character_is_enforced(self):
        action=Action('strike','ENEMY',1,(Effect(0,'DAMAGE',8),),owner_definition_id='hero2')
        core,_,_=native(rule_changes={'cards':(action,)})
        self.assertNoMutation(core,lambda:core.submit(command(core)),'CARD_OWNER_INVALID')


# Define separately, preserving shared assertion helper without inheriting tests.
class BossBoundaryTests(unittest.TestCase):
    assertNoMutation=CoreAcceptanceTests.assertNoMutation

    def boss(self,hp=12,**kwargs):
        def alter(s):
            s['units'][-1].update(hp=hp,shield=0)
            s['boss_states']=[{'unit_id':'E1','current_phase_id':'p1','proposed_phase_ids':[]}]
        changes={'boss_edges':(BossEdge('E1','p1','p2',10,1,False),)}
        changes.update(kwargs.pop('rule_changes',{}))
        return native(alter=alter,rule_changes=changes,**kwargs)

    def test_living_crossing_is_proposed_once_without_phase_commit(self):
        core,_,_=self.boss();core.submit(command(core))
        b=core.state().value['snapshot']['boss_states'][0]
        self.assertEqual((b['current_phase_id'],b['proposed_phase_ids']),('p1',['p2']))
        self.assertEqual(sum(e['event_type']=='BOSS_PHASE_PROPOSED' for e in all_events(core)),1)
        before=authority_bytes(core);core.submit(command(core,revision=0));self.assertEqual(authority_bytes(core),before)

    def test_lethal_crossing_emits_no_phase_and_no_extra_action(self):
        core,_,enemy=self.boss(hp=8);core.submit(command(core))
        self.assertEqual(core.result().value['outcome'],'WIN')
        self.assertFalse(any(e['event_type'].startswith('BOSS_PHASE') for e in all_events(core)))
        self.assertNoMutation(core,lambda:core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','enemy')),'ALREADY_CLOSED')
        self.assertEqual(enemy.calls,0)

    def test_reaction_loss_suppresses_boss_proposal(self):
        core,_,_=self.boss(rule_changes={'reactions':(Reaction('E1','kill','ON_DAMAGED',10),)})
        state=core.state().value
        state['snapshot']['units'][1]['hp']=0;state['snapshot']['units'][2]['hp']=0
        core=BattleCore(state,core._rules,stage_id='s',profile_scope='p',deck_planner=core._deck)
        core.submit(command(core))
        self.assertEqual(core.result().value['outcome'],'LOSS')
        self.assertFalse(any(e['event_type']=='BOSS_PHASE_PROPOSED' for e in all_events(core)))

    def test_multiple_thresholds_preserve_graph_order(self):
        edges=(BossEdge('E1','p2','p3',5,1,False),BossEdge('E1','p1','p2',10,1,False))
        core,_,_=self.boss(rule_changes={'boss_edges':edges});core.submit(command(core))
        self.assertEqual([e['data']['to_phase_id'] for e in all_events(core) if e['event_type']=='BOSS_PHASE_PROPOSED'],['p2','p3'])

    def test_pending_phase_blocks_uncontracted_enemy_transition(self):
        core,_,enemy=self.boss();core.submit(command(core));core.submit(command(core,'END_TURN','end'))
        self.assertNoMutation(core,lambda:core.submit_system(command(core,'SYSTEM_ENEMY_ACTION','enemy')),'PHASE_COMMIT_CONTRACT_UNBOUND')
        self.assertEqual(enemy.calls,0)

    def test_phase_proposal_cannot_write_state_via_self_reported_dto(self):
        core,_,_=self.boss();before=authority_bytes(core)
        proposal=message('PhaseProposal',battle_id='fixture:native',expected_revision=0,proposal_id='p',
            boss_unit_id='E1',from_phase_id='p1',to_phase_id='p2',trigger_event_seq=1,content_version='fixture:native-v1')
        with self.assertRaises(DependencyUnavailable):core.inspect_phase_proposal(proposal)
        self.assertEqual(authority_bytes(core),before)
