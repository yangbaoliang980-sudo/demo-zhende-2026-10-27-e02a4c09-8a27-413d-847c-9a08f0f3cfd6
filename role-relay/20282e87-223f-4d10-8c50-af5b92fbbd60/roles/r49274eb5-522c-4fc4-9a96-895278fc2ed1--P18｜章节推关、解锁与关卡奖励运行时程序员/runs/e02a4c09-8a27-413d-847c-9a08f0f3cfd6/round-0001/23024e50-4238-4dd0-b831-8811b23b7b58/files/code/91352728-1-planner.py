"""Deterministic intent selection and execution revalidation. No state writes.

The output may describe a behavior change, but P14 must own its atomic commit.
Preview reads, rejected transactions and retries never advance any cursor.
"""
from .types import (API_VERSION, AiError, Announcement, Decision, EnemyAction,
                    FrozenMessage, MAX_INTEGER, fingerprint, require, wire,
                    integer, identifier, sha256)
from .inputs import validate_inputs, observed_outcome

ANNOUNCEMENT_VERSION='P16-ANNOUNCEMENT/0.1.0-proposal'


def _action(skill,targets=()):
    return EnemyAction(skill['skill_id'],skill['intent_id'],skill['action_kind'],tuple(targets),
        skill['base_amount_per_hit'],skill['hit_count'],skill['future_release_base_amount'])


def _boss_phase(boss):
    return 'NONE' if boss is None else boss['current_phase_id']


def _guard(s,c,actor,boss):
    if s['phase'] in ('TERMINAL','ABORTED','FAULTED'):
        return 'CLOSED','ALREADY_CLOSED'
    if c.pending_reactions:
        return 'DEFER','REACTIONS_PENDING'
    if observed_outcome(s)!='ONGOING':
        return 'TERMINAL','TERMINAL_PREEMPTS_ACTION'
    if actor['hp']==0:
        return 'NO_OP','ACTOR_DEAD'
    if boss is not None and any(p not in c.phase_committed_ids for p in boss['proposed_phase_ids']):
        return 'DEFER','PHASE_COMMIT_PENDING'
    return None


def _empty(msg,s,c,catalog,disposition,reason):
    action=_action(catalog.special('SKIP')) if reason=='ACTOR_DEAD' else None
    view={'version':'P16-INTENT-VIEW/0.1.0-proposal','battle_id':s['battle_id'],
        'actor_id':c.actor_id,'expected_revision':s['revision'],'reason':reason,
        'observed_outcome':s['outcome'] if disposition=='CLOSED' else observed_outcome(s),
        'action':None if action is None else action.message().value,
        'slot_consumed':False,'phase_changed':False,'summon_proposals':[],
        'damage_label':'BASE_DAMAGE_NOT_HP_LOSS','presentation_affects_logic':False}
    return Decision(disposition,reason,action,None,FrozenMessage.from_value(view),None,None,FrozenMessage.from_value(s['rng']))


def _declared(c,catalog,enemy,boss):
    if enemy['tier']=='BOSS':
        if c.degraded:
            return catalog.skill(enemy['degraded_basic_skill_id']),'NONE','DEGRADED_STRIKE'
        if not c.graph_available or catalog.graph is None:
            return catalog.special('DEGRADED_WAIT'),catalog.graph_error or 'PHASE_GRAPH_MISSING','DEGRADED_STRIKE'
        if c.entry_wait_pending:
            return catalog.special('ENTRY_WAIT'),'NONE',enemy['phase_initial_state_ids'][boss['current_phase_id']]
    state=next(x for x in enemy['states'] if x['state_id']==c.state_id)
    return catalog.skill(state['skill_id']),'NONE',state['next_state_id']


def _valid_targets(s,c):
    return sorted((u for u in s['units'] if u['side']=='PLAYER' and u['hp']>0 and u['unit_id'] in c.targetable_ids),
                  key=lambda u:(u['slot'],u['unit_id'].encode('utf-8')))


def _charge_guard(c,skill):
    if skill['action_kind']=='CHARGE' and c.heavy_cooldown:
        return 'COOLDOWN'
    if skill['action_kind']=='RELEASE':
        if c.charge is None: return 'CHARGE_MISSING'
        if c.charge.ready_slot>c.enemy_slot: return 'CHARGE_EARLY'
        if c.charge.ready_slot<c.enemy_slot: return 'CHARGE_EXPIRED'
    return None


def _seal(data):
    data=dict(data); data.pop('intent_token',None)
    data['intent_token']='intent:'+fingerprint(data)
    return Announcement(FrozenMessage.from_value(data))


def announcement_record(msg,s,c,catalog,action,reason):
    """Build the replayable record; inputs must originate at a trusted owner."""
    return _seal({'schema_version':ANNOUNCEMENT_VERSION,'battle_id':s['battle_id'],
        'actor_id':c.actor_id,'source_revision':s['revision'],'source_snapshot_sha256':msg.sha256,
        'source_event_seq':s['last_event_seq'],'turn_number':s['turn_number'],'enemy_slot':c.enemy_slot,
        'state_id':c.state_id,'phase_epoch':c.phase_epoch,'content_version':s['content_version'],
        'content_sha256':catalog.source_sha256,'graph_sha256':catalog.graph_sha256,
        'behavior_semantic_sha256':c.semantic_sha256(),'action':action.message().value,'guard_reason':reason})


def restore_announcement(data):
    require(type(data) is dict,'ANNOUNCEMENT_OBJECT_REQUIRED')
    fields={'schema_version','battle_id','actor_id','source_revision','source_snapshot_sha256','source_event_seq',
            'turn_number','enemy_slot','state_id','phase_epoch','content_version','content_sha256','graph_sha256',
            'behavior_semantic_sha256','action','guard_reason','intent_token'}
    require(set(data)==fields and data['schema_version']==ANNOUNCEMENT_VERSION,'ANNOUNCEMENT_SHAPE_OR_VERSION')
    for k in ('source_revision','source_event_seq','phase_epoch'):
        integer(data[k],code='ANNOUNCEMENT_INTEGER_INVALID')
    for k in ('turn_number','enemy_slot'):
        integer(data[k],1,code='ANNOUNCEMENT_INTEGER_INVALID')
    for k in ('battle_id','actor_id','state_id','content_version','guard_reason','intent_token'):
        identifier(data[k])
    for k in ('source_snapshot_sha256','content_sha256','behavior_semantic_sha256'):
        sha256(data[k])
    if data['graph_sha256'] is not None: sha256(data['graph_sha256'])
    expected=_seal(data)
    require(data['intent_token']==expected.token,'ANNOUNCEMENT_DIGEST_MISMATCH')
    # Canonical codec rejects floats, nonfinite values and out-of-range integers.
    return expected


def _candidate(msg,s,c,catalog,enemy,boss,declared,action,reason,next_state,ann):
    require(c.enemy_slot<MAX_INTEGER,'ACTION_SLOT_CAPACITY_REACHED')
    charge=c.charge
    after_charge=None if charge is None else {
        'release_skill_id':charge.release_skill_id,'locked_target_ids':list(charge.locked_target_ids),
        'phase_epoch':charge.phase_epoch,'ready_slot':charge.ready_slot,'created_intent_token':charge.created_intent_token}
    cooldown=max(0,c.heavy_cooldown-1)
    cursor=c.last_successful_single_target_slot
    entry_wait=False if action.kind=='ENTRY_WAIT' else c.entry_wait_pending
    degraded=c.degraded
    if action.kind=='CHARGE':
        release=next(st for st in enemy['states'] if st['state_id']==next_state)
        after_charge={'release_skill_id':release['skill_id'],'locked_target_ids':list(action.target_ids),
                      'phase_epoch':c.phase_epoch,'ready_slot':c.enemy_slot+1,'created_intent_token':ann.token}
    if declared['action_kind']=='RELEASE':
        after_charge=None
        if charge is not None: cooldown=2
    if action.kind=='DEGRADED_WAIT':
        after_charge=None; degraded=True; entry_wait=False
        if charge is not None: cooldown=2
    if action.kind in ('STRIKE','RELEASE') and len(action.target_ids)==1:
        cursor=next(u['slot'] for u in s['units'] if u['unit_id']==action.target_ids[0])
    candidate={'schema_version':'P16-BEHAVIOR-CANDIDATE/0.1.0-proposal',
        'battle_id':s['battle_id'],'actor_id':c.actor_id,'expected_revision':s['revision'],
        'snapshot_sha256':msg.sha256,'intent_token':ann.token,'content_sha256':catalog.source_sha256,
        'slot_key':'slot:'+fingerprint({'battle_id':s['battle_id'],'actor_id':c.actor_id,'enemy_slot':c.enemy_slot}),
        'source_behavior_sha256':c.message().sha256,'consume_slot':True,'extra_actions':0,
        'commit_owner':'P14','approval_status':'PROPOSAL_NOT_COMMITTED',
        'commit_condition':'ONLY_IF_ACTION_RESOLVED_ACTOR_ALIVE_AND_BATTLE_ONGOING_AT_SLOT_END',
        'proposed_fields':{'enemy_slot':c.enemy_slot+1,'state_id':next_state,'heavy_cooldown':cooldown,
            'last_successful_single_target_slot':cursor,'charge':after_charge,
            'entry_wait_pending':entry_wait,'degraded':degraded},
        'forbidden_writes':['hp','shield','phase','current_phase_id','phase_epoch','revision','wallet']}
    candidate['candidate_id']='behavior:'+fingerprint(candidate)
    return FrozenMessage.from_value(candidate)


def _decision(msg,s,c,catalog,enemy,boss,declared,action,reason,next_state,ann,*,resolving,removed=(),deviation='NONE'):
    degraded=action.kind=='DEGRADED_WAIT'
    candidate=None
    if resolving:
        candidate=_candidate(msg,s,c,catalog,enemy,boss,declared,action,reason,next_state,ann)
    intent=wire('EnemyIntent',battle_id=s['battle_id'],expected_revision=s['revision'],intent_id=ann.token,
        actor_id=c.actor_id,skill_id=action.skill_id,target_ids=list(action.target_ids),content_version=s['content_version'],no_valid_target='SKIP')
    next_skill=None
    if next_state=='DEGRADED_STRIKE':
        next_skill=catalog.skill(enemy['degraded_basic_skill_id'])['skill_id']
    else:
        nxt=next((x for x in enemy['states'] if x['state_id']==next_state),None)
        if nxt is not None: next_skill=nxt['skill_id']
    view={'version':'P16-INTENT-VIEW/0.1.0-proposal','battle_id':s['battle_id'],'actor_id':c.actor_id,
        'expected_revision':s['revision'],'intent_token':ann.token,'enemy_slot':c.enemy_slot,
        'phase_id':_boss_phase(boss),'phase_epoch':c.phase_epoch,'action':action.message().value,
        'reason':reason,'deviation_reason':deviation,'removed_target_ids':list(removed),
        'damage_label':'BASE_DAMAGE_NOT_HP_LOSS','observed_outcome':observed_outcome(s),
        'slot_consumed':False,'slot_consumption_proposed':resolving,
        'preview_only':not resolving,'phase_changed':False,'summon_proposals':[],
        'next_forecast':{'state_id':next_state,'skill_id':next_skill,'target_ids':None,
            'certainty':'CONDITIONAL_AFTER_P14_COMMIT_REQUIRES_NEW_SNAPSHOT'},
        'presentation_affects_logic':False,'requires_owner_commit':True}
    disposition='DEGRADATION_RECOMMENDATION' if degraded else ('ACTION_CANDIDATE' if resolving else 'PREVIEW_CANDIDATE')
    return Decision(disposition,reason,action,intent,FrozenMessage.from_value(view),candidate,ann,FrozenMessage.from_value(s['rng']))


def publish_intent(snapshot,behavior,catalog):
    """Called before the player window, for the owner's next enemy action slot."""
    msg,s,actor,enemy,boss=validate_inputs(snapshot,behavior,catalog); c=behavior
    guard=_guard(s,c,actor,boss)
    if guard: return _empty(msg,s,c,catalog,*guard)
    require(s['phase'] in ('PLAYER_READY','ENEMY_READY'),'PREVIEW_PHASE_INVALID')
    declared,reason,next_state=_declared(c,catalog,enemy,boss)
    valid=_valid_targets(s,c); targets=[]; skill=declared
    blocked=_charge_guard(c,declared)
    if blocked:
        skill=catalog.special('SKIP'); reason=blocked
    elif declared['target_policy']=='ROTATE_ALIVE_SINGLE':
        after=[u for u in valid if u['slot']>c.last_successful_single_target_slot]
        if valid: targets=[(after or valid)[0]['unit_id']]
    elif declared['target_policy']=='LOCK_ALL_ALIVE':
        targets=[u['unit_id'] for u in valid]
    elif declared['target_policy']=='LOCKED_CHARGE_SINGLE':
        targets=list(c.charge.locked_target_ids)
        if any(t not in {u['unit_id'] for u in valid} for t in targets):
            targets=[]; skill=catalog.special('SKIP'); reason='LOCKED_TARGET_INVALID' if valid else 'NO_VALID_TARGET'
    if skill is declared and declared['target_policy']!='NONE' and not targets:
        skill=catalog.special('SKIP'); reason='NO_VALID_TARGET'
    action=_action(skill,targets)
    ann=announcement_record(msg,s,c,catalog,action,reason)
    return _decision(msg,s,c,catalog,enemy,boss,declared,action,reason,next_state,ann,resolving=False)


def resolve_intent(snapshot,behavior,catalog,announcement):
    """Revalidate a frozen announcement after DOT/reactions. Never reselect."""
    msg,s,actor,enemy,boss=validate_inputs(snapshot,behavior,catalog); c=behavior
    guard=_guard(s,c,actor,boss)
    if guard: return _empty(msg,s,c,catalog,*guard)
    require(s['phase']=='ENEMY_READY','EXECUTION_PHASE_INVALID')
    declared,reason,next_state=_declared(c,catalog,enemy,boss)
    require(isinstance(announcement,Announcement),'FROZEN_ANNOUNCEMENT_REQUIRED')
    ann=restore_announcement(announcement.value); a=ann.value
    require(a['battle_id']==s['battle_id'] and a['actor_id']==c.actor_id,'INTENT_ACTOR_OR_BATTLE_MISMATCH')
    require(a['content_version']==s['content_version'],'INTENT_CONTENT_VERSION_MISMATCH')
    require(a['content_sha256']==catalog.source_sha256,'INTENT_CONTENT_HASH_MISMATCH')
    require(type(a['source_revision']) is int and 0<=a['source_revision']<=s['revision'] and type(a['source_event_seq']) is int and 0<=a['source_event_seq']<=s['last_event_seq'],'STALE_OR_FUTURE_ANNOUNCEMENT')
    require(a['turn_number']==s['turn_number'] and a['enemy_slot']==c.enemy_slot,'INTENT_SLOT_EXPIRED')
    if declared['action_kind']=='DEGRADED_WAIT':
        replacement=announcement_record(msg,s,c,catalog,_action(declared),reason)
        return _decision(msg,s,c,catalog,enemy,boss,declared,_action(declared),reason,next_state,replacement,resolving=True,deviation='GRAPH_DEGRADED_REQUIRES_P14_ACCEPTANCE')
    if c.phase_epoch>a['phase_epoch'] and c.entry_wait_pending:
        replacement=announcement_record(msg,s,c,catalog,_action(declared),'PHASE_REPLACED')
        return _decision(msg,s,c,catalog,enemy,boss,declared,_action(declared),'PHASE_REPLACED',next_state,replacement,resolving=True,deviation='PHASE_REPLACED')
    require(a['phase_epoch']==c.phase_epoch,'INTENT_PHASE_EPOCH_MISMATCH')
    require(a['graph_sha256']==catalog.graph_sha256 or c.degraded,'INTENT_GRAPH_VERSION_MISMATCH')
    require(a['state_id']==c.state_id and a['behavior_semantic_sha256']==c.semantic_sha256(),'BEHAVIOR_CHANGED_WITHIN_SLOT')
    value=a['action']; require(type(value) is dict,'INTENT_ACTION_SHAPE')
    require(set(value)=={'skill_id','intent_dictionary_id','kind','target_ids','base_amount_per_hit','hit_count','future_release_base_amount'},'INTENT_ACTION_SHAPE')
    for k in ('base_amount_per_hit','hit_count','future_release_base_amount'):
        integer(value[k],code='INTENT_AMOUNT_TYPE_INVALID')
    skill=catalog.skill(value['skill_id'])
    targets=value['target_ids']
    require(type(targets) is list and len(targets)<=3 and all(type(t) is str for t in targets)
            and len(targets)==len(set(targets)),'INTENT_TARGET_SHAPE')
    for target in targets: identifier(target)
    require(value==_action(skill,targets).message().value,'INTENT_CONTENT_MISMATCH')
    require(skill['skill_id']==declared['skill_id'] or skill['action_kind']=='SKIP','INTENT_STATE_MISMATCH')
    require(not (skill['target_policy']=='NONE' and targets),'INTENT_TARGET_SHAPE')
    require(not (skill['target_policy'] in ('ROTATE_ALIVE_SINGLE','LOCKED_CHARGE_SINGLE') and len(targets)!=1),'INTENT_TARGET_SHAPE')
    units={u['unit_id']:u for u in s['units']}
    require(all(t not in units or units[t]['side']=='PLAYER' for t in targets),'INTENT_TARGET_SIDE_MISMATCH')
    valid=_valid_targets(s,c); valid_ids={u['unit_id'] for u in valid}
    removed=[t for t in targets if t not in valid_ids]
    reason=a['guard_reason']; actual=skill; actual_targets=list(targets); deviation='NONE'
    if skill['action_kind']=='SKIP':
        require(reason in ('NO_VALID_TARGET','LOCKED_TARGET_INVALID','COOLDOWN','CHARGE_MISSING','CHARGE_EARLY','CHARGE_EXPIRED'),'SKIP_REASON_INVALID')
        actual_targets=[]
    else:
        require(reason in ('NONE','PHASE_REPLACED'),'INTENT_REASON_INVALID')
        blocked=_charge_guard(c,declared)
        if blocked:
            actual=catalog.special('SKIP'); actual_targets=[]; reason=blocked; deviation=blocked
        else:
            if declared['action_kind']=='RELEASE':
                require(tuple(targets)==c.charge.locked_target_ids,'CHARGE_TARGET_MISMATCH')
            if declared['target_policy']!='NONE':
                actual_targets=[t for t in targets if t in valid_ids]
                if not actual_targets or (declared['target_policy']!='LOCK_ALL_ALIVE' and removed):
                    actual=catalog.special('SKIP'); actual_targets=[]
                    reason='LOCKED_TARGET_INVALID' if valid else 'NO_VALID_TARGET'; deviation=reason
                elif removed:
                    deviation='LOCKED_TARGETS_FILTERED'
    action=_action(actual,actual_targets)
    return _decision(msg,s,c,catalog,enemy,boss,declared,action,reason,next_state,ann,
                     resolving=True,removed=removed,deviation=deviation)
