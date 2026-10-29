"""Ordered boss phase proposals at P14 drained checkpoints. No phase commit."""
from .types import FrozenMessage, PhaseCheckpoint, PhasePlan, fingerprint, require, wire
from .inputs import validate_inputs, observed_outcome


def propose_phases(snapshot,behavior,catalog,checkpoint):
    msg,s,actor,enemy,boss=validate_inputs(snapshot,behavior,catalog)
    require(type(checkpoint) is PhaseCheckpoint,'CHECKPOINT_REQUIRED')
    require(checkpoint.before_hp<=actor['max_hp'],'CHECKPOINT_HP_INVALID')
    require(checkpoint.trigger_event_seq<=s['last_event_seq'],'TRIGGER_EVENT_NOT_OBSERVED')
    evidence={'schema_version':'P16-PHASE-EVIDENCE/0.1.0-proposal','battle_id':s['battle_id'],
        'actor_id':behavior.actor_id,'snapshot_sha256':msg.sha256,'expected_revision':s['revision'],
        'root_command_id':checkpoint.root_command_id,'trigger_event_seq':checkpoint.trigger_event_seq,
        'content_sha256':catalog.source_sha256,'graph_sha256':catalog.graph_sha256,
        'before_hp':checkpoint.before_hp,'after_hp':actor['hp'],'max_hp':actor['max_hp'],
        'phase_before':None if boss is None else boss['current_phase_id'],
        'observed_outcome':observed_outcome(s),'proposal_order':[],
        'acceptance_requirements':{'owner':'P14','one_atomic_batch':True,'phase_epoch_increments':0,
            'entry_wait_count_if_accepted':0,'extra_actions':0,'summons':0,'heal':0,'shield':0,'revive':False},
        'approval_status':'PROPOSAL_NOT_COMMITTED'}
    def result(disposition,reason,proposals=()):
        return PhasePlan(disposition,reason,tuple(proposals),FrozenMessage.from_value(evidence))
    if s['phase'] in ('TERMINAL','ABORTED','FAULTED'):
        evidence['observed_outcome']=s['outcome']; return result('NO_OP','ALREADY_CLOSED')
    if behavior.pending_reactions:
        evidence['observed_outcome']='DEFER'; return result('DEFER','REACTIONS_PENDING')
    if observed_outcome(s)!='ONGOING': return result('NO_OP','TERMINAL_PREEMPTS_PHASE')
    if actor['hp']==0: return result('NO_OP','ACTOR_DEAD')
    if boss is None: return result('NO_OP','NOT_A_BOSS')
    if behavior.degraded: return result('NO_OP','DEGRADED_MODE')
    if not behavior.graph_available or catalog.graph is None:
        evidence['degradation_recommendation']={'owner':'P14','keep_current_phase':True,
            'cancel_charge_once':True,'first_skill_id':catalog.special('DEGRADED_WAIT')['skill_id'],
            'then_skill_id':enemy['degraded_basic_skill_id'],'reenter_same_battle':False}
        return result('DEGRADATION_RECOMMENDATION',catalog.graph_error or 'PHASE_GRAPH_MISSING')
    graph=catalog.graph.value
    require(graph['enemy_id']==actor['definition_id'],'GRAPH_ENEMY_MISMATCH')
    edges={x['from_phase_id']:x for x in graph['transitions']}
    phase=boss['current_phase_id']; known=set(boss['proposed_phase_ids'])|set(behavior.phase_committed_ids)
    proposals=[]
    # A validated strictly increasing graph also has this explicit traversal cap.
    for _ in range(len(graph['phases'])):
        edge=edges.get(phase)
        if edge is None: break
        target=edge['to_phase_id']
        if target in known:
            phase=target; continue
        frac=edge['threshold_max_hp_fraction']; threshold=actor['max_hp']*frac['numerator']
        if not checkpoint.before_hp*frac['denominator']>threshold>=actor['hp']*frac['denominator']:
            break
        # Same identity as P14's existing deterministic proposal event, so the
        # two observations cannot create a second independent phase identity.
        pid='phase:'+fingerprint({'battle_id':s['battle_id'],'unit_id':actor['unit_id'],
            'to_phase_id':target,'content_version':s['content_version']})
        proposals.append(wire('PhaseProposal',battle_id=s['battle_id'],expected_revision=s['revision'],
            proposal_id=pid,boss_unit_id=actor['unit_id'],from_phase_id=phase,to_phase_id=target,
            trigger_event_seq=checkpoint.trigger_event_seq,content_version=s['content_version']))
        evidence['proposal_order'].append({'transition_id':edge['transition_id'],'proposal_id':pid,
            'from_phase_id':phase,'to_phase_id':target,
            'once_key':'phase-once:'+fingerprint({'battle_id':s['battle_id'],'actor_id':actor['unit_id'],
                'to_phase_id':target,'content_sha256':catalog.source_sha256})})
        known.add(target); phase=target
    if proposals:
        evidence['acceptance_requirements'].update(phase_epoch_increments=1,entry_wait_count_if_accepted=1)
        evidence['acceptance_requirements']['final_phase_id']=phase
        evidence['acceptance_requirements']['cancel_old_charge_once']=True
        evidence['acceptance_requirements']['heavy_cooldown_if_charge_cancelled']=2
        evidence['acceptance_requirements']['initial_state_id']=enemy['phase_initial_state_ids'][phase]
    return result('PROPOSALS' if proposals else 'NO_OP','NONE',proposals)
