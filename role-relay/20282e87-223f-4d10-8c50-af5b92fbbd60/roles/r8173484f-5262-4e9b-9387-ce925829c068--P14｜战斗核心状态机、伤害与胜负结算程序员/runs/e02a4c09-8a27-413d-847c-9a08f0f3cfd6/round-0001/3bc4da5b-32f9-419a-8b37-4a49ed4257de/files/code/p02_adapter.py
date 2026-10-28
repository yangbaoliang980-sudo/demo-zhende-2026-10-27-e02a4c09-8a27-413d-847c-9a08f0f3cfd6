"""Versioned test-only projection: P02 legacy fixture -> P13 frozen wire.

No upstream bytes are rewritten. Four legacy historical receipts are blocked:
their full commands/receipt ranges are absent, so we do not invent SHA migration.
Unsupported P02 event fields are enumerated in the mapping report, not claimed
to have passed byte-for-byte P13 compatibility.
"""
from pathlib import Path
import hashlib,json
from battle_core import BattleCore,Action,BossEdge,Dot,Effect,Reaction,Rules,SourceBinding
from battle_core.wire import message, raw_message
from examples.fixture_ports import ScriptedDeck,ScriptedEnemy,move

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'upstream/P02/spec/battle/resolution/battle_replay_fixtures.json'
SOURCE=json.loads(PATH.read_text(encoding='utf-8'))
SOURCE_SHA=hashlib.sha256(PATH.read_bytes()).hexdigest()
CASES={c['fixture_id']:c for c in SOURCE['cases']}
BLOCKED_HISTORY={'F010','F011','F021','F028'}
CONTENT='fixture:P02-0.1.0'
POLICY='fixture:P15-script-P02-v1'


def command(value):
    kind=value['type']; payload={}
    if kind=='PLAY_CARD': payload={k:value[k] for k in ['actor_id','card_instance_id','target_ids']}
    if kind=='ABORT': payload={'reason_code':value['reason']}
    return message('BattleCommand',battle_id=value['battle_id'],command_id=value['command_id'],
                   expected_revision=value['expected_revision'],kind=kind,payload=payload)


def make_case(case_id):
    c=CASES[case_id]; initial=c['initial_state']; policy=c['fixture_policy']
    if initial['processed_commands']:
        raise ValueError('BLOCKED_LEGACY_RECEIPT_REQUIRES_FULL_HISTORY')
    rng=initial['random']
    if rng['draw_count']!=0: raise ValueError('BLOCKED_LEGACY_INITIAL_SEED_MISSING')
    units=[]; bosses=[]
    for u in initial['combatants']:
        statuses=[{'status_instance_id':f'legacy:{u["unit_id"]}:{i}', 'status_id':s['status_id'],
            'source_unit_id':u['unit_id'],'stacks':1,'remaining_triggers':s['remaining_owner_turns'],
            'insert_order':i} for i,s in enumerate(u['statuses'])]
        units.append({'unit_id':u['unit_id'],'definition_id':u['unit_id'],'side':u['side'],
            'slot':u['formation_order'],'hp':u['hp'],'max_hp':u['max_hp'],'shield':u['shield'],'statuses':statuses})
        if u['boss_current_phase'] is not None:
            bosses.append({'unit_id':u['unit_id'],'current_phase_id':u['boss_current_phase'],
                           'proposed_phase_ids':u['proposed_phases']})
    catalog=SOURCE['fixture_card_catalogue']; card_specs=[]
    for iid,a in catalog.items():
        items=a.get('effects',[{'effect_index':0,**a}])
        effects=tuple(Effect(e['effect_index'],e['kind'],e.get('amount',0),
            e.get('status',{}).get('status_id')) for e in items)
        card_specs.append(Action(iid,'PLAYER' if a['kind'] in ('HEAL','SHIELD') else 'ENEMY',1,effects))
    cards=[{'instance_id':iid,'card_id':iid,'owner_unit_id':catalog[iid]['owner']}
           for zone in initial['zones'].values() for iid in zone]
    s=raw_message('BattleSnapshot',battle_id=initial['battle_id'],revision=initial['revision'],
        rules_version=SOURCE['battle_rule_version'],content_version=CONTENT,phase=initial['phase'],
        turn_number=initial['turn_number'],energy=initial['energy'],units=units,card_instances=cards,
        zones={**initial['zones'],'exhaust':[]},rng={'algorithm':'xorshift32-v1',
        'initial_seed':rng['state_u32'],'state':rng['state_u32'],'draw_count':0},
        last_event_seq=initial['event_cursor'],outcome=initial['terminal_outcome'] or 'ONGOING',boss_states=bosses)
    state=message('BattleState',snapshot=s,accepted_commands=[])
    scripts=[];skills=[];enemy=None
    for cmd in c['commands']:
        script={'command_id':cmd['command_id'],'moves':[],'energy_delta':0}
        if cmd['type']=='PLAY_CARD':
            iid=cmd['card_instance_id']
            script.update(energy_delta=-catalog[iid]['cost'],moves=[move(iid,'hand','discard',len(initial['zones']['discard']))])
        elif cmd['type']=='SYSTEM_ENTER_PLAYER_TURN':
            script['energy_delta']=policy['test_only_refill_energy_to']-initial['energy']
            # Manually declared candidate vectors, not an implementation of P15.
            # F014 fixed xorshift outputs 270369,67634689 are independently tested.
            if case_id=='F014':
                script['moves']=[move('C3','discard','draw',0),move('C2','discard','draw',1),
                                 move('C1','discard','draw',2),move('C3','draw','hand',0)]
                script['rng_after']={'algorithm':'xorshift32-v1','initial_seed':1,'state':67634689,'draw_count':2}
            elif case_id=='F022': script['moves']=[move('C1','draw','hand',0)]
        elif cmd['type']=='SYSTEM_ENEMY_ACTION':
            if 'test_only_enemy_intent_damage' in policy or case_id=='F023':
                skill_id=cmd['intent_id']
                skills.append(Action(skill_id,'PLAYER',1,(Effect(0,'DAMAGE',policy.get('test_only_enemy_intent_damage',0)),)))
                enemy=ScriptedEnemy({'intent_id':cmd['intent_id'],'actor_id':cmd['actor_id'],
                    'skill_id':skill_id,'target_ids':cmd['target_ids'],
                    'no_valid_target':policy.get('test_only_enemy_no_target_fallback','REJECT')})
        if cmd['type'] in ('PLAY_CARD','END_TURN','SYSTEM_ENTER_PLAYER_TURN'):
            if not any(p['command_id']==script['command_id'] for p in scripts):scripts.append(script)
    reactions=tuple(Reaction(r['source_id'],r['trigger_id'],r['on'],r['damage']) for r in policy.get('test_only_reactions',[]))
    edges=tuple(BossEdge(b['unit_id'],e['from'],e['to'],e['threshold_hp_lte'],1,False)
                for b in bosses for e in policy.get('test_only_boss_graph',[]))
    rules=Rules(SOURCE['battle_rule_version'],CONTENT,POLICY,
        'ENEMY_EXIT',
        policy.get('test_only_draw_count',0),None,'UNCAPPED_TEST_ONLY',cards=tuple(card_specs),
        skills=tuple(skills),statuses=(Dot('BURN',3,1),),reactions=reactions,boss_edges=edges,
        source_bindings=(SourceBinding('P02-fixtures','P02-BATTLE-REPLAY-FIXTURES-0.1.0',SOURCE_SHA),))
    deck=ScriptedDeck(POLICY,scripts)
    core=BattleCore(state,rules,stage_id='fixture:stage',profile_scope='fixture:profile',
                    deck_planner=deck,enemy_planner=enemy)
    return core,[command(x) for x in c['commands']],deck,enemy


def execute(core,commands):
    replies=[]
    for cmd in commands:
        kind=cmd.value['kind']
        method=core.abort if kind=='ABORT' else (core.submit_system if kind.startswith('SYSTEM_') else core.submit)
        replies.append(method(cmd))
    return replies


def projected_state(core):
    s=core.state().value['snapshot'];bosses={b['unit_id']:b for b in s['boss_states']}
    dots={d.status_id:d for d in core._rules.statuses}
    units=[]
    for u in s['units']:
        b=bosses.get(u['unit_id']); statuses=[]
        for status in u['statuses']:
            spec=dots[status['status_id']]
            statuses.append({'status_id':spec.status_id,'kind':'DOT','amount':spec.amount,
                             'remaining_owner_turns':status['remaining_triggers']})
        units.append({'unit_id':u['unit_id'],'side':u['side'],'formation_order':u['slot'],
            'hp':u['hp'],'max_hp':u['max_hp'],'shield':u['shield'],'alive':u['hp']>0,'statuses':statuses,
            'boss_current_phase':None if b is None else b['current_phase_id'],
            'proposed_phases':[] if b is None else b['proposed_phase_ids']})
    return {'battle_id':s['battle_id'],'revision':s['revision'],'phase':s['phase'],
        'turn_number':s['turn_number'],'energy':s['energy'],'combatants':units,
        'zones':{k:s['zones'][k] for k in ('hand','draw','discard')},
        'random':{'algorithm':s['rng']['algorithm'],'state_u32':s['rng']['state'],'draw_count':s['rng']['draw_count']},
        'terminal_outcome':s['outcome'] if s['outcome'] in ('WIN','LOSS','DRAW') else None}


def projected_expected_state(case):
    return {k:v for k,v in case['expected']['final_state'].items() if k not in ('event_cursor','processed_commands')}


def expected_event_projection(case):
    out=[]
    for e in case['expected']['logic_events']:
        t=e['type']; d=None
        if t in ('TRIGGER_QUEUED','TRIGGER_STARTED','STATUS_TICKED','ENERGY_REFRESHED',
                 'ENEMY_ACTION_STARTED','ROUND_ADVANCED','DECK_RECYCLED'):continue
        if t=='DECK_SHUFFLED':
            out.extend(('CARD_MOVED',{'instance_id':iid,'from_zone':'discard','to_zone':'draw'}) for iid in e['resulting_order'])
            continue
        if t=='COMMAND_ACCEPTED':d={}
        elif t=='ENERGY_SPENT':d={'amount':e['amount'],'energy_after':e['after']}
        elif t=='CARD_MOVED':d={'instance_id':e['card_instance_id'],'from_zone':e['from_zone'].lower(),'to_zone':e['to_zone'].lower()}
        elif t=='CARD_DRAWN':t='CARD_MOVED';d={'instance_id':e['card_instance_id'],'from_zone':'draw','to_zone':'hand'}
        elif t=='EFFECT_STARTED':d={'effect_index':e['effect_index'],'target_unit_ids':[e['target_id']]}
        elif t=='DAMAGE_APPLIED':d={'source_unit_id':e['source_id'],'target_unit_id':e['target_id'],
            'raw':e['raw_amount'],'absorbed':e['shield_absorbed'],'hp_loss':e['hp_loss'],'overkill':e['overkill']}
        elif t=='SHIELD_GRANTED':t='SHIELD_CHANGED';d={'target_unit_id':e['target_id'],'delta':e['amount'],'shield_after':e['after']}
        elif t=='HEAL_APPLIED':d={'target_unit_id':e['target_id'],'amount':e['applied'],'hp_after':e['after']}
        elif t=='STATUS_APPLIED':t='STATUS_CHANGED';d={'target_unit_id':e['target_id'],'status_id':e['status_id'],'operation':'ADDED'}
        elif t=='STATUS_DURATION_UPDATED':t='STATUS_CHANGED';d={'target_unit_id':e['target_id'],'status_id':e['status_id'],'operation':'REMOVED' if e['removed'] else 'UPDATED'}
        elif t=='BOSS_PHASE_PROPOSED':d={'unit_id':e['boss_id'],'to_phase_id':e['phase_id']}
        elif t=='ENEMY_ACTION_SKIPPED':d={'unit_id':e['actor_id'],'reason_code':e['reason']}
        elif t=='BATTLE_ABORTED':d={'reason_code':e['reason']}
        else:d={k:v for k,v in e.items() if k not in ('type','seq')}
        out.append((t,d))
    return out
