from dataclasses import replace
from battle_core import BattleCore,Action,Dot,Effect,Rules
from battle_core.wire import message,raw_message
from examples.fixture_ports import ScriptedDeck,ScriptedEnemy,move


def native(*,alter=None,rule_changes=None,deck_factory=None,enemy_factory=None,interrupt=None):
    ids=[('c1','strike'),('c2','shield'),('c3','heal'),('c4','dot'),('c5','double')]
    units=[{'unit_id':'P'+str(i+1),'definition_id':'hero'+str(i+1),'side':'PLAYER','slot':i,
            'hp':10,'max_hp':10,'shield':0,'statuses':[]} for i in range(3)]
    units.append({'unit_id':'E1','definition_id':'enemy1','side':'ENEMY','slot':0,
                  'hp':12,'max_hp':12,'shield':5,'statuses':[]})
    s=raw_message('BattleSnapshot',battle_id='fixture:native',revision=0,
        rules_version='P02-BATTLE-0.1.0-draft',content_version='fixture:native-v1',phase='PLAYER_READY',
        turn_number=1,energy=3,units=units,
        card_instances=[{'instance_id':iid,'card_id':cid,'owner_unit_id':'P1'} for iid,cid in ids],
        zones={'hand':[x[0] for x in ids],'draw':[],'discard':[],'exhaust':[]},
        rng={'algorithm':'xorshift32-v1','initial_seed':1,'state':1,'draw_count':0},
        last_event_seq=0,outcome='ONGOING',boss_states=[])
    if alter: alter(s)
    rules=Rules('P02-BATTLE-0.1.0-draft','fixture:native-v1','fixture:deck-v1','ENEMY_EXIT',0,None,'UNCAPPED_TEST_ONLY',
        cards=(Action('strike','ENEMY',1,(Effect(0,'DAMAGE',8),)),
               Action('shield','PLAYER',1,(Effect(0,'SHIELD',4),)),
               Action('heal','PLAYER',1,(Effect(0,'HEAL',5),)),
               Action('dot','ENEMY',1,(Effect(0,'STATUS',status_id='burn'),)),
               Action('double','ENEMY',1,(Effect(0,'DAMAGE',3),Effect(1,'DAMAGE',5)))),
        skills=(Action('enemy-strike','PLAYER',1,(Effect(0,'DAMAGE',3),)),),statuses=(Dot('burn',3,1),))
    if rule_changes: rules=replace(rules,**rule_changes)
    scripts=[{'command_id':cid,'energy_delta':-1,'moves':[move(iid,'hand','discard',0)]}
             for cid,iid in [('play','c1'),('shield','c2'),('heal','c3'),('dot','c4'),('double','c5')]]
    scripts.extend([{'command_id':'end','energy_delta':0,'moves':[]},
                    {'command_id':'enter','energy_delta':1,'moves':[]},
                    {'command_id':'start','energy_delta':3,'moves':[]}])
    deck=ScriptedDeck(rules.deck_policy_version,scripts) if deck_factory is None else deck_factory(rules,scripts)
    enemy_script={'intent_id':'fixture:enemy-intent','actor_id':'E1','skill_id':'enemy-strike',
                  'target_ids':['P1'],'no_valid_target':'REJECT'}
    enemy=ScriptedEnemy(enemy_script) if enemy_factory is None else enemy_factory(enemy_script)
    core=BattleCore(message('BattleState',snapshot=s,accepted_commands=[]),rules,
        stage_id='fixture:stage',profile_scope='fixture:profile',deck_planner=deck,enemy_planner=enemy,test_interrupt=interrupt)
    return core,deck,enemy


def command(core,kind='PLAY_CARD',cid='play',revision=None,card='c1',actor='P1',targets=None):
    s=core.state().value['snapshot'];payload={}
    if kind=='PLAY_CARD':payload={'actor_id':actor,'card_instance_id':card,'target_ids':['E1'] if targets is None else targets}
    if kind=='ABORT':payload={'reason_code':'USER_QUIT'}
    return message('BattleCommand',battle_id=s['battle_id'],command_id=cid,
                   expected_revision=s['revision'] if revision is None else revision,kind=kind,payload=payload)


def authority_bytes(core):
    return (core.state().raw,None if core.result() is None else core.result().raw,
            tuple(b.raw for b in core.committed_batches()),tuple(t.raw for t in core.resolution_traces()),
            core.export_replay().sha256)


def all_events(core):
    return [e for b in core.committed_batches() for e in b.value['events']]


def add_dot(s,uid,remaining=1,insert_order=0,status_id='burn'):
    u=next(u for u in s['units'] if u['unit_id']==uid)
    u['statuses'].append({'status_instance_id':'fixture:status:'+str(insert_order),'status_id':status_id,
        'source_unit_id':uid,'stacks':1,'remaining_triggers':remaining,'insert_order':insert_order})
