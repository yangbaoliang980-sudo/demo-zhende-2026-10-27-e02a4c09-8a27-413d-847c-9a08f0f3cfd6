from pathlib import Path
import ast,copy,json,os,subprocess,sys,unittest
from battle_core import BattleCore,DependencyUnavailable
from battle_core.core import ReplayBundle
from battle_core.replay import replay
from battle_core.rng import next_u32,advance,verify_transition
from battle_core.wire import ContractError,FrozenMessage,checked,message
from examples.demo import build_demo,run_demo
from examples.fixture_ports import ScriptedDeck,move
from .helpers import native,command,all_events,authority_bytes

ROOT=Path(__file__).resolve().parents[1]


class ReplayAndBoundaryTests(unittest.TestCase):
    def test_full_demo_replays_state_events_result_exactly(self):
        core,out=run_demo();again=replay(out['replay'])
        self.assertEqual(authority_bytes(core),authority_bytes(again))
        self.assertEqual((out['snapshot']['revision'],out['snapshot']['outcome'],out['p16_calls']),(10,'WIN',1))

    def test_three_process_hash_seeds_produce_identical_bytes(self):
        outputs=[]
        for seed in ('0','1','2026'):
            env=dict(os.environ);env['PYTHONHASHSEED']=seed;env['PYTHONDONTWRITEBYTECODE']='1'
            p=subprocess.run([sys.executable,'-B','-m','battle_core','--digest'],cwd=ROOT,env=env,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr.decode())
            outputs.append(p.stdout)
        self.assertEqual(len(set(outputs)),1)

    def test_replay_rejects_modified_bytes(self):
        _,out=run_demo();value=out['replay'];value['entries'][0]['inputs'][0]['candidate']['energy_delta']=9
        with self.assertRaisesRegex(ValueError,'REPLAY_DIGEST_MISMATCH'):replay(value)

    def test_replay_rejects_wrong_candidate_basis_even_with_new_outer_hash(self):
        core,_=run_demo();b=core.export_replay();entries=list(b.entries)
        value=entries[0].value;value['inputs'][0]['basis_sha256']='0'*64;entries[0]=FrozenMessage.from_value(value)
        with self.assertRaises(ValueError):replay(ReplayBundle(b.header,tuple(entries)))

    def test_p02_xorshift_known_vector_and_nonzero_seed_guard(self):
        s=1;outputs=[]
        for i in range(5):s=next_u32(s);outputs.append(s)
        self.assertEqual(outputs,[270369,67634689,2647435461,307599695,2398689233])
        for invalid in (0,-1,2**32,True,1.0):
            with self.assertRaises(ValueError):next_u32(invalid)

    def test_rng_jump_matches_sequential_generator_and_composes(self):
        for seed in (1,17,0xffffffff):
            s=seed
            for count in range(201):
                self.assertEqual(advance(seed,count),s);s=next_u32(s)
            a=2**40+3;b=2**32+19
            self.assertEqual(advance(advance(seed,a),b),advance(seed,a+b))

    def test_rng_jump_full_period_preserves_state_without_losing_count(self):
        self.assertEqual(advance(1,2**32-1),1)
        before={'algorithm':'xorshift32-v1','initial_seed':1,'state':1,'draw_count':0}
        after={**before,'draw_count':2**32-1}
        self.assertTrue(verify_transition(before,after))
        self.assertFalse(verify_transition(after,before))

    def test_invalid_initial_rng_seed_state_relation_is_rejected(self):
        with self.assertRaisesRegex(ContractError,'INITIAL_RNG_HISTORY_INVALID'):
            native(alter=lambda s:s['rng'].update(state=2))

    def test_config_and_initial_state_are_copied(self):
        base,_,_=native();initial=base.state().value
        core=BattleCore(initial,base._rules,stage_id='s',profile_scope='p')
        initial['snapshot']['units'][0]['hp']=0
        self.assertEqual(core.state().value['snapshot']['units'][0]['hp'],10)
        with self.assertRaises((AttributeError,TypeError)):base._rules.cards += ()

    def test_p13_duplicate_json_keys_rejected(self):
        from battle_core.wire import FrozenMessage
        with self.assertRaises(ContractError):FrozenMessage(b'{"x":1,"x":2}')

    def test_kernel_has_no_renderer_clock_storage_or_expectation_dependency(self):
        forbidden={'time','datetime','random','pygame','godot','unity','sqlite3','pickle','resolution_replay_tests','examples'}
        for f in (ROOT/'battle_core').glob('*.py'):
            if f.name=='__main__.py':continue
            tree=ast.parse(f.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):names=[a.name.split('.')[0] for a in node.names]
                elif isinstance(node,ast.ImportFrom):names=[(node.module or '').split('.')[0]]
                else:continue
                self.assertFalse(forbidden.intersection(names),(f.name,names))
            self.assertNotIn('expected.final_state',f.read_text())
        # No cost/amount rule is stored in the private Action model.
        from battle_core.model import Action
        self.assertNotIn('cost',Action.__dataclass_fields__)

    def test_each_committed_dto_uses_original_p13_validator(self):
        core,out=run_demo()
        checked(core.state(),'BattleState');checked(core.result(),'BattleResult')
        for b in core.committed_batches():
            checked(b,'BattleCommitBatch')
            for e in b.value['events']:checked(e,'BattleEvent')
        for r in out['replies']:checked(r,'BattleReply')

    def test_skip_cancel_and_reorder_consumer_reads_cannot_change_logic(self):
        expected,out=run_demo();core,cmds,_,_=build_demo()
        for index,cmd in enumerate(cmds):
            method=core.submit_system if cmd.value['kind'].startswith('SYSTEM_') else core.submit
            method(cmd)
            # Consumer simulation: dropping batches, reading old snapshots, and
            # mutating detached presentation copies never calls a write port.
            if index%2:
                for b in reversed(core.committed_batches()):
                    view=b.value;view['snapshot']['units'][0]['hp']=999
            if index%3==0:core.snapshot('fixture:demo')
        self.assertEqual(authority_bytes(core),authority_bytes(expected))


class P03EffectExamplesTests(unittest.TestCase):
    def test_eight_enabled_p03_examples_execute_real_core(self):
        catalog=json.loads((ROOT/'upstream/P03/content/cards/card_catalog.json').read_text())
        examples=json.loads((ROOT/'upstream/P03/content/cards/card_effect_examples.json').read_text())['examples']
        template,_,_,_=build_demo();rules=template._rules
        definitions={c['card_id']:c for c in catalog['cards']}
        for example in examples[:8]:
            with self.subTest(example=example['example_id']):
                inp=example['input_context'];want=example['static_expected'];card=definitions[example['card_id']]
                base,_,_=native();state=base.state().value;s=state['snapshot'];s['content_version']=rules.content_version
                s['units'][0].update(hp=inp.get('ally_hp',10),max_hp=inp.get('ally_max_hp',10),shield=inp.get('ally_shield',0))
                if card['owner_character_id'] is not None:s['units'][0]['definition_id']=card['owner_character_id']
                s['units'][-1].update(hp=inp.get('enemy_hp',12),max_hp=inp.get('enemy_hp',12),shield=inp.get('enemy_shield',0))
                s['card_instances']=[{'instance_id':'source-card','card_id':example['card_id'],'owner_unit_id':'P1'}]
                s['zones']={'hand':['source-card'],'draw':[],'discard':[],'exhaust':[]}
                deck=ScriptedDeck(rules.deck_policy_version,[{'command_id':'example','energy_delta':-card['cost']['amount'],
                                                           'moves':[move('source-card','hand','discard',0)]}])
                core=BattleCore(state,rules,stage_id='fixture:stage',profile_scope='fixture:profile',deck_planner=deck)
                target='E1' if card['target_rule']['side']=='ENEMY' else 'P1'
                reply=core.submit(command(core,cid='example',card='source-card',targets=[target])).value
                self.assertEqual((reply['result'],reply['code']),('COMMITTED','OK'))
                final=core.state().value['snapshot'];hero=final['units'][0];enemy=final['units'][-1]
                if 'enemy_hp_after' in want:self.assertEqual(enemy['hp'],want['enemy_hp_after'])
                if 'enemy_shield_after' in want:self.assertEqual(enemy['shield'],want['enemy_shield_after'])
                if 'ally_shield_after' in want:self.assertEqual(hero['shield'],want['ally_shield_after'])
                if 'ally_hp_after' in want:self.assertEqual(hero['hp'],want['ally_hp_after'])
                if 'shield_absorbed' in want:
                    hit=next(e['data'] for e in all_events(core) if e['event_type']=='DAMAGE_APPLIED')
                    self.assertEqual((hit['absorbed'],hit['hp_loss']),(want['shield_absorbed'],want['hp_loss']))
                if 'status_added' in want:
                    self.assertEqual(enemy['hp'],want['enemy_hp_immediately_after'])
                    self.assertEqual(enemy['statuses'][0]['status_id'],want['status_added'])
                    self.assertEqual(enemy['statuses'][0]['remaining_triggers'],want['owner_turns'])

    def test_two_unapproved_p03_modifiers_are_not_executable_content(self):
        core,_,_,_=build_demo()
        ids={a.action_id for a in core._rules.cards}
        self.assertNotIn('MOCK_P03_CARD_FOCUS_DRAFT',ids)
        self.assertNotIn('MOCK_P03_CARD_FEEBLE_DRAFT',ids)
