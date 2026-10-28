"""Single-authority BattleState/BattleResult commit with copy-before-swap."""
from dataclasses import dataclass
import hashlib
import threading
from .model import Rules, identifier
from .ports import CandidateRejected, DependencyUnavailable, SafetyFault
from .resolver import Transaction
from .rng import advance
from .wire import (ContractError, FrozenMessage, MAX_INTEGER, checked, fingerprint,
                   message, raw_message)


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    header: FrozenMessage
    entries: tuple[FrozenMessage, ...]

    @property
    def sha256(self):
        h=hashlib.sha256(b'P14-REPLAY/0.1.0-isolated\x00')
        for part in (self.header,) + self.entries:
            h.update(len(part.raw).to_bytes(8,'big')); h.update(part.raw)
        return h.hexdigest()

    def value(self):
        return {'format':'P14-REPLAY/0.1.0-isolated','header':self.header.value,
                'entries':[e.value for e in self.entries],'sha256':self.sha256}


@dataclass(frozen=True, slots=True)
class Committed:
    state: FrozenMessage
    result: FrozenMessage | None
    batches: tuple[FrozenMessage, ...]
    traces: tuple[FrozenMessage, ...]
    entries: tuple[FrozenMessage, ...]


class BattleCore:
    """One battle per instance. Only this owner changes the committed record.

    submit() is the P13 BattlePort user input surface (PLAY_CARD/END_TURN).
    submit_system() is for a trusted host scheduler; never route network/UI JSON
    directly to it. abort() is an explicit host capability authorized by that
    host's quit flow. Same-process Python is not a security sandbox.
    """
    def __init__(self, initial_state, rules: Rules, *, stage_id, profile_scope,
                 deck_planner=None, enemy_planner=None, mode='isolated',
                 test_interrupt=None):
        if mode != 'isolated':
            raise DependencyUnavailable('PRODUCTION_MAPPING_AND_CONTRACTS_BLOCKED')
        if not isinstance(rules, Rules): raise TypeError('IMMUTABLE_RULES_REQUIRED')
        identifier(stage_id); identifier(profile_scope)
        state=checked(initial_state,'BattleState')
        self._rules=rules; self._deck=deck_planner; self._enemy=enemy_planner
        self._stage_id=stage_id; self._profile_scope=profile_scope
        self._interrupt=test_interrupt
        self._lock=threading.RLock(); self._resolving=False
        self._validate_domain(state.value)
        self._header=FrozenMessage.from_value({'version':'P14-REPLAY-HEADER/0.1.0-isolated',
            'initial_state':state.value,'rules':rules.frozen().value,
            'stage_id':stage_id,'profile_scope':profile_scope})
        self._committed=Committed(state,None,(),(),())

    def _validate_domain(self,state):
        s=state['snapshot']
        if (s['rules_version'],s['content_version']) != (self._rules.rules_version,self._rules.content_version):
            raise ContractError('BATTLE_CONTENT_VERSION_MISMATCH')
        sides={u['side'] for u in s['units']}
        if sides != {'PLAYER','ENEMY'}: raise ContractError('BOTH_SIDES_REQUIRED')
        units={u['unit_id']:u for u in s['units']}
        dots={d.status_id:d for d in self._rules.statuses}
        for u in s['units']:
            ids=set()
            for status in u['statuses']:
                if status['status_id'] not in dots: raise ContractError('UNKNOWN_STATUS_DEFINITION')
                if status['status_id'] in ids or status['stacks'] != 1:
                    raise ContractError('STATUS_STACK_RULE_UNDEFINED')
                ids.add(status['status_id'])
                if status['source_unit_id'] is not None and status['source_unit_id'] not in units:
                    raise ContractError('UNKNOWN_STATUS_SOURCE')
                if status['remaining_triggers'] == 0: raise ContractError('EXPIRED_STATUS_IN_SNAPSHOT')
            if self._rules.shield_cap is not None and u['shield']>self._rules.shield_cap:
                raise ContractError('INITIAL_SHIELD_ABOVE_CAP')
        for r in self._rules.reactions:
            if r.source_unit_id not in units: raise ContractError('UNKNOWN_REACTION_SOURCE')
        boss_ids={b['unit_id'] for b in s['boss_states']}
        for b in s['boss_states']:
            if units[b['unit_id']]['side']!='ENEMY': raise ContractError('BOSS_SIDE_INVALID')
        for e in self._rules.boss_edges:
            if e.unit_id not in boss_ids: raise ContractError('BOSS_EDGE_WITHOUT_BOSS')
        r=s['rng']
        if advance(r['initial_seed'],r['draw_count'])!=r['state']:
            raise ContractError('INITIAL_RNG_HISTORY_INVALID')
        player=any(u['hp']>0 and u['side']=='PLAYER' for u in units.values())
        enemy=any(u['hp']>0 and u['side']=='ENEMY' for u in units.values())
        expected='ONGOING' if player and enemy else ('WIN' if player else ('LOSS' if enemy else 'DRAW'))
        if s['phase']=='TERMINAL' and expected!=s['outcome']:
            raise ContractError('TERMINAL_LIVE_COUNTS_MISMATCH')
        if s['phase'] not in ('CREATED','TERMINAL','FAULTED','ABORTED') and expected!='ONGOING':
            raise ContractError('UNRESOLVED_TERMINAL_SNAPSHOT')
        if s['phase']=='CREATED':
            if s['turn_number']!=0: raise ContractError('CREATED_TURN_NUMBER')
        elif s['turn_number']==0 and s['phase'] not in ('TERMINAL','ABORTED','FAULTED'):
            raise ContractError('ACTIVE_TURN_NUMBER')
        prior_rev=0;prior_seq=0
        for rec in state['accepted_commands']:
            if rec['committed_revision']<=prior_rev or rec['first_event_seq']<=prior_seq:
                raise ContractError('RECEIPT_ORDER_INVALID')
            prior_rev=rec['committed_revision']; prior_seq=rec['last_event_seq']

    def snapshot(self,battle_id):
        with self._lock:
            s=self._committed.state.value['snapshot']
            if battle_id!=s['battle_id']: raise KeyError('BATTLE_NOT_FOUND')
            return checked(s,'BattleSnapshot')

    def state(self):
        with self._lock: return self._committed.state

    def result(self):
        with self._lock: return self._committed.result

    def committed_batches(self):
        with self._lock: return self._committed.batches

    def resolution_traces(self):
        """Private P14 audit records; not additional BattleEvents/sequence numbers."""
        with self._lock: return self._committed.traces

    def export_replay(self):
        with self._lock: return ReplayBundle(self._header,self._committed.entries)

    def submit(self,command):
        return self._submit(command,'USER')

    def submit_system(self,command):
        return self._submit(command,'SYSTEM')

    def abort(self,command):
        return self._submit(command,'ABORT_CAPABILITY')

    def _reply(self,c,result,code,commit=None,revision=None):
        return message('BattleReply',battle_id=c['battle_id'],command_id=c['command_id'],
            result=result,code=code,observed_revision=(self._committed.state.value['snapshot']['revision']
            if revision is None else revision),commit=commit)

    def _submit(self,command,channel):
        # Invalid wire shape cannot create a plausible ACK identity; it raises
        # P13 ContractError before touching any committed object.
        command=checked(command,'BattleCommand'); c=command.value
        with self._lock:
            if self._resolving:
                return self._reply(c,'REJECTED','REENTRANT_COMMAND')
            allowed={'USER':{'PLAY_CARD','END_TURN'},
                     'SYSTEM':{'SYSTEM_START','SYSTEM_ENTER_PLAYER_TURN','SYSTEM_ENEMY_ACTION'},
                     'ABORT_CAPABILITY':{'ABORT'}}
            if c['kind'] not in allowed[channel]:
                return self._reply(c,'REJECTED','COMMAND_CHANNEL_FORBIDDEN')
            old=self._committed; s=old.state.value['snapshot']
            if c['battle_id']!=s['battle_id']:
                return self._reply(c,'REJECTED','BATTLE_ID_MISMATCH')
            for receipt in old.state.value['accepted_commands']:
                if receipt['command_id']==c['command_id']:
                    if receipt['command_sha256']==command.sha256:
                        return self._reply(c,'DUPLICATE_NO_OP','DUPLICATE_NO_OP')
                    return self._reply(c,'REJECTED','COMMAND_ID_COLLISION')
            if s['phase'] in ('TERMINAL','ABORTED','FAULTED'):
                return self._reply(c,'REJECTED','ALREADY_CLOSED')
            phases={'PLAY_CARD':'PLAYER_READY','END_TURN':'PLAYER_READY','SYSTEM_START':'CREATED',
                    'SYSTEM_ENEMY_ACTION':'ENEMY_READY','SYSTEM_ENTER_PLAYER_TURN':'PLAYER_TURN_PENDING'}
            if c['kind']!='ABORT' and s['phase']!=phases[c['kind']]:
                return self._reply(c,'REJECTED','PHASE_INVALID')
            if c['expected_revision']!=s['revision']:
                return self._reply(c,'REJECTED','REVISION_CONFLICT')
            if (len(old.state.value['accepted_commands'])>=4096 or s['revision']==MAX_INTEGER
                    or s['last_event_seq']>MAX_INTEGER-16384):
                return self._reply(c,'REJECTED','STATE_CAPACITY_REACHED')
            self._resolving=True
            tx=None
            try:
                tx=Transaction(old.state,command,self._rules,self._deck,self._enemy,self._interrupt)
                try:
                    tx.run()
                except CandidateRejected as exc:
                    return self._reply(c,'REJECTED',exc.code)
                except DependencyUnavailable:
                    return self._reply(c,'REJECTED','DEPENDENCY_UNAVAILABLE')
                except ContractError:
                    return self._reply(c,'REJECTED','CANDIDATE_SCHEMA_INVALID')
                record,reply=self._prepare_commit(old,tx,channel,'OK')
                tx.checkpoint_hook('before_publish')
                self._committed=record  # The sole, exception-free commit point.
                return reply
            except SafetyFault as exc:
                return self._commit_safety_fault(old,command,channel,tx,exc.code)
            except Exception:
                return self._commit_safety_fault(old,command,channel,tx,'INTERNAL_RESOLUTION_ERROR')
            finally:
                # KeyboardInterrupt/SystemExit/test BaseException also arrive
                # here with old state intact: no candidate or partial event leaked.
                self._resolving=False

    def _prepare_commit(self,old,tx,channel,code):
        tx.emit('COMMAND_COMMITTED',revision=tx.revision)
        tx.s['revision']=tx.revision; tx.s['last_event_seq']=tx.events[-1]['seq']
        tx.state['accepted_commands'].append({'command_id':tx.c['command_id'],
            'command_sha256':tx.command.sha256,'committed_revision':tx.revision,
            'first_event_seq':tx.events[0]['seq'],'last_event_seq':tx.events[-1]['seq']})
        state=checked(tx.state,'BattleState'); self._validate_domain(state.value)
        batch=message('BattleCommitBatch',battle_id=tx.s['battle_id'],command_id=tx.c['command_id'],
                      previous_revision=tx.revision-1,snapshot=tx.s,events=tx.events)
        entry=FrozenMessage.from_value({'command':tx.c,'channel':channel,
            'inputs':tx.inputs,'fault_code':None if code=='OK' else code})
        entries=old.entries+(entry,)
        result=old.result
        if tx.s['phase']=='TERMINAL':
            if result is not None: raise SafetyFault('SECOND_BATTLE_RESULT')
            snapshot=checked(tx.s,'BattleSnapshot')
            result_id='result:'+fingerprint({'battle_id':tx.s['battle_id'],'stage_id':self._stage_id,
                'profile_scope':self._profile_scope,'snapshot_sha256':snapshot.sha256})
            result=message('BattleResult',result_id=result_id,battle_id=tx.s['battle_id'],
                terminal_revision=tx.revision,terminal_event_seq=next(e['seq'] for e in tx.events if e['event_type']=='BATTLE_FINISHED'),
                outcome=tx.s['outcome'],stage_id=self._stage_id,profile_scope=self._profile_scope,
                rules_version=self._rules.rules_version,content_version=self._rules.content_version,
                final_snapshot_sha256=snapshot.sha256,
                replay_input_sha256=ReplayBundle(self._header,entries).sha256)
        trace=FrozenMessage.from_value({'version':'P14-RESOLUTION-TRACE/0.1.0-isolated',
            'command_id':tx.c['command_id'],'revision':tx.revision,'batch_sha256':batch.sha256,
            'steps':tx.trace,'fault_code':None if code=='OK' else code})
        reply=self._reply(tx.c,'COMMITTED',code,batch.value,tx.revision)
        return Committed(state,result,old.batches+(batch,),old.traces+(trace,),entries),reply

    def _commit_safety_fault(self,old,command,channel,failed,code):
        # The failed gameplay transaction is discarded. Build a fresh record
        # solely from OLD state: only fault phase/outcome/revision/receipt change.
        tx=Transaction(old.state,command,self._rules,None,None,None)
        tx.inputs=[] if failed is None else failed.inputs
        tx.emit('COMMAND_ACCEPTED',command_sha256=command.sha256)
        tx.s['phase']='FAULTED'; tx.s['outcome']='FAULTED'
        tx.emit('BATTLE_FAULTED',reason_code=code)
        tx.note('GAMEPLAY_TRANSACTION_ROLLED_BACK',reason_code=code,
                discarded_events=0 if failed is None else len(failed.events))
        record,reply=self._prepare_commit(old,tx,channel,code)
        # If even the safety record cannot be encoded, an exception propagates
        # with OLD state intact; never fall back to partial or unverifiable writes.
        self._committed=record
        return reply

    def inspect_phase_proposal(self,proposal):
        """Validate shape, explicitly refuse the unbound S07 commit operation.

        P13 v0.1 has no command kind/phase epoch/action-slot fields for accepting
        PhaseProposal. This method never changes the phase or invents a command.
        """
        checked(proposal,'PhaseProposal')
        raise DependencyUnavailable('PHASE_COMMIT_CONTRACT_UNBOUND')
