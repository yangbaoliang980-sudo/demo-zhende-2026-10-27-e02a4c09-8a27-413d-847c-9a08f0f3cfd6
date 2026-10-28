"""Real P14 core, upstream P03 TEST_ONLY content, scripted P15/P16 inputs."""
import hashlib,json
from pathlib import Path
from battle_core import BattleCore,Action,Dot,Effect,Rules,SourceBinding
from battle_core.wire import message,raw_message
from .fixture_ports import ScriptedDeck,ScriptedEnemy,move

ROOT=Path(__file__).resolve().parents[1]


def build_demo():
    path=ROOT/'upstream/P03/content/cards/card_catalog.json'
    catalog=json.loads(path.read_text(encoding='utf-8'))
    specs={e['effect_id']:e for e in catalog['effects']}
    cards=[];dots={}
    for c in catalog['cards']:
        if not c['mock_playable']:continue
        effects=[]
        for index,eid in enumerate(c['effect_ids']):
            e=specs[eid]
            if e['effect_code']=='STATUS':
                dots[e['status_id']]=Dot(e['status_id'],e['amount'],e['remaining_owner_turns'])
                effects.append(Effect(index,'STATUS',status_id=e['status_id']))
            else:effects.append(Effect(index,e['effect_code'],e['amount']))
        cards.append(Action(c['card_id'],c['target_rule']['side'],c['target_rule']['target_count'],
                            tuple(effects),owner_definition_id=c['owner_character_id']))
    policy='fixture:demo-deck-script-v1'
    rules=Rules('P02-BATTLE-0.1.0-draft','fixture:P03-demo-v1',policy,'ENEMY_EXIT',3,
        None,'UNCAPPED_TEST_ONLY',cards=tuple(cards),skills=(Action('fixture:enemy-strike','PLAYER',1,(Effect(0,'DAMAGE',3),)),),
        statuses=tuple(dots.values()),source_bindings=(SourceBinding('P03-catalog',catalog['format_version'],hashlib.sha256(path.read_bytes()).hexdigest()),))
    mapping=[('strike1','MOCK_P03_CARD_STRIKE'),('barrier1','MOCK_P03_CARD_BARRIER'),
             ('heal1','MOCK_P03_CARD_RECOVER'),('ember1','MOCK_P03_CARD_EMBER'),('strike2','MOCK_P03_CARD_STRIKE')]
    units=[{'unit_id':f'hero{i+1}','definition_id':f'fixture:hero{i+1}','side':'PLAYER','slot':i,
            'hp':8 if i==0 else 10,'max_hp':10,'shield':0,'statuses':[]} for i in range(3)]
    units.append({'unit_id':'enemy1','definition_id':'fixture:enemy','side':'ENEMY','slot':0,
                  'hp':4,'max_hp':4,'shield':2,'statuses':[]})
    snapshot=raw_message('BattleSnapshot',battle_id='fixture:demo',revision=0,rules_version=rules.rules_version,
        content_version=rules.content_version,phase='CREATED',turn_number=0,energy=0,units=units,
        card_instances=[{'instance_id':iid,'card_id':cid,'owner_unit_id':'hero1'} for iid,cid in mapping],
        zones={'draw':[i for i,c in mapping],'hand':[],'discard':[],'exhaust':[]},
        rng={'algorithm':'xorshift32-v1','initial_seed':1,'state':1,'draw_count':0},last_event_seq=0,outcome='ONGOING',boss_states=[])
    scripts=[{'command_id':'demo:start','energy_delta':3,'moves':[move(i,'draw','hand',n) for n,i in enumerate(['strike1','barrier1','heal1'])]},
        {'command_id':'demo:enter','energy_delta':3,'moves':[move('ember1','draw','hand',0),move('strike2','draw','hand',1)]}]
    for cid,iid,index in [('strike','strike1',0),('shield','barrier1',1),('heal','heal1',2),('dot','ember1',3)]:
        scripts.append({'command_id':'demo:'+cid,'energy_delta':-1,'moves':[move(iid,'hand','discard',index)]})
    for cid in ['end1','end2']:scripts.append({'command_id':'demo:'+cid,'energy_delta':0,'moves':[]})
    deck=ScriptedDeck(policy,scripts)
    enemy=ScriptedEnemy({'intent_id':'fixture:shown-intent','actor_id':'enemy1','skill_id':'fixture:enemy-strike',
                        'target_ids':['hero1'],'no_valid_target':'REJECT'})
    core=BattleCore(message('BattleState',snapshot=snapshot,accepted_commands=[]),rules,
        stage_id='fixture:stage1',profile_scope='fixture:profile',deck_planner=deck,enemy_planner=enemy)
    command_specs=[('SYSTEM_START','start',{}),
        ('PLAY_CARD','strike',{'actor_id':'hero1','card_instance_id':'strike1','target_ids':['enemy1']}),
        ('PLAY_CARD','shield',{'actor_id':'hero1','card_instance_id':'barrier1','target_ids':['hero1']}),
        ('PLAY_CARD','heal',{'actor_id':'hero1','card_instance_id':'heal1','target_ids':['hero1']}),
        ('END_TURN','end1',{}),('SYSTEM_ENEMY_ACTION','enemy1',{}),('SYSTEM_ENTER_PLAYER_TURN','enter',{}),
        ('PLAY_CARD','dot',{'actor_id':'hero1','card_instance_id':'ember1','target_ids':['enemy1']}),
        ('END_TURN','end2',{}),('SYSTEM_ENEMY_ACTION','enemy2',{})]
    commands=[message('BattleCommand',battle_id='fixture:demo',command_id='demo:'+cid,
                      expected_revision=index,kind=kind,payload=payload)
              for index,(kind,cid,payload) in enumerate(command_specs)]
    return core,commands,deck,enemy


def run_demo():
    core,commands,deck,enemy=build_demo();replies=[]
    for cmd in commands:
        call=core.submit_system if cmd.value['kind'].startswith('SYSTEM_') else core.submit
        reply=call(cmd);replies.append(reply.value)
        if reply.value['result']!='COMMITTED' or reply.value['code']!='OK':
            raise RuntimeError(reply.value['code'])
    return core,{'scope':'ISOLATED_REAL_P14_CORE_WITH_SCRIPTED_P15_P16_TEST_INPUTS',
        'commands':[c.value for c in commands],'replies':replies,'snapshot':core.state().value['snapshot'],
        'result':core.result().value,'p15_calls':deck.calls,'p16_calls':enemy.calls,
        'batches':[b.value for b in core.committed_batches()],'replay':core.export_replay().value()}
