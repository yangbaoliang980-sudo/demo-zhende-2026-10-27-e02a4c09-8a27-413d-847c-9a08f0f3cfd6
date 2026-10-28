"""Private disposable transaction. No object here is externally published.

The only authoritative write happens in BattleCore after state, events, receipt,
replay entry and (when terminal) result have all been constructed and validated.
"""
import heapq
from .model import Effect
from .ports import CandidateRejected, DependencyUnavailable, SafetyFault
from .rng import verify_transition
from .wire import MAX_INTEGER, checked, fingerprint, raw_message


def order(unit):
    return (0 if unit['side'] == 'PLAYER' else 1, unit['slot'], unit['unit_id'].encode('utf-8'))


def bounded(n):
    if type(n) is not int or not 0 <= n <= MAX_INTEGER:
        raise SafetyFault('INTEGER_OVERFLOW')
    return n


class Transaction:
    def __init__(self, state, command, rules, deck, enemy, interrupt):
        self.state = state.value
        self.s = self.state['snapshot']
        self.command = command
        self.c = command.value
        self.rules = rules
        self.deck = deck
        self.enemy = enemy
        self.interrupt = interrupt
        self.units = {u['unit_id']:u for u in self.s['units']}
        self.cards = {c['instance_id']:c for c in self.s['card_instances']}
        self.card_specs = {a.action_id:a for a in rules.cards}
        self.skills = {a.action_id:a for a in rules.skills}
        self.status_specs = {d.status_id:d for d in rules.statuses}
        self.events = []
        self.trace = []
        self.inputs = []
        self.queue = []
        self.seen_triggers = set()
        self.reactions_processed = 0
        self.queue_serial = 0
        self.revision = bounded(self.s['revision'] + 1)
        self.start_seq = self.s['last_event_seq']

    def emit(self, name, **data):
        seq = bounded(self.start_seq + len(self.events) + 1)
        if len(self.events) >= 16383:
            raise SafetyFault('EVENT_CAPACITY')
        self.events.append(raw_message('BattleEvent', battle_id=self.s['battle_id'],
            command_id=self.c['command_id'], revision=self.revision, seq=seq,
            event_type=name, data=data))
        return seq

    def note(self, kind, **data):
        self.trace.append({'step':len(self.trace) + 1, 'kind':kind, **data})

    def checkpoint_hook(self, stage):
        if self.interrupt is not None:
            # Test-only hook has no state/candidate argument and cannot mutate a
            # working copy through a callback. Injected BaseException rolls back.
            self.interrupt(stage)

    def before_hp(self):
        return {uid:u['hp'] for uid,u in self.units.items()}

    def targets(self, action, actor, targets):
        if not action.playable:
            raise CandidateRejected('CONTENT_DISABLED')
        if len(targets) != action.target_count or len(set(targets)) != len(targets):
            raise CandidateRejected('TARGET_INVALID')
        if any(uid not in self.units or self.units[uid]['hp'] == 0 or
               self.units[uid]['side'] != action.target_side for uid in targets):
            raise CandidateRejected('TARGET_INVALID')
        if action.owner_definition_id is not None and actor['definition_id'] != action.owner_definition_id:
            raise CandidateRejected('CARD_OWNER_INVALID')
        # Current upstream explicitly leaves repeat DOT stacking undefined.
        # Reject before paying, including duplicate applications in one root.
        seen = {(uid,s['status_id']) for uid in targets for s in self.units[uid]['statuses']}
        for effect in sorted(action.effects, key=lambda e:e.effect_index):
            if effect.kind == 'STATUS':
                for uid in targets:
                    if (uid,effect.status_id) in seen:
                        raise CandidateRejected('STATUS_REAPPLY_UNDEFINED')
                    seen.add((uid,effect.status_id))

    def play_inputs(self):
        p = self.c['payload']; actor = self.units.get(p['actor_id'])
        if actor is None or actor['side'] != 'PLAYER' or actor['hp'] == 0:
            raise CandidateRejected('ACTOR_INVALID')
        instance = self.cards.get(p['card_instance_id'])
        if instance is None or instance['instance_id'] not in self.s['zones']['hand']:
            raise CandidateRejected('CARD_NOT_IN_HAND')
        if instance['owner_unit_id'] != actor['unit_id']:
            raise CandidateRejected('CARD_OWNER_INVALID')
        action = self.card_specs.get(instance['card_id'])
        if action is None:
            raise CandidateRejected('CONTENT_UNAVAILABLE')
        self.targets(action, actor, p['target_ids'])
        return actor, instance, action

    def deck_patch(self, action=None, instance=None):
        if self.deck is None:
            raise DependencyUnavailable('P15_DECK_PORT_UNBOUND')
        basis = checked(self.s, 'BattleSnapshot')
        candidate = checked(self.deck.propose(self.command, basis), 'DeckPatchCandidate')
        p = candidate.value
        if (p['battle_id'], p['command_id'], p['expected_revision'], p['command_sha256'],
            p['snapshot_sha256'], p['policy_version']) != (
            self.s['battle_id'], self.c['command_id'], self.s['revision'], self.command.sha256,
            basis.sha256, self.rules.deck_policy_version):
            raise CandidateRejected('DECK_CANDIDATE_BINDING_MISMATCH')
        if p['rng_before'] != self.s['rng'] or not verify_transition(p['rng_before'],p['rng_after']):
            raise CandidateRejected('DECK_RNG_INVALID')
        energy = self.s['energy'] + p['energy_delta']
        if energy < 0:
            raise CandidateRejected('ENERGY_INSUFFICIENT')
        if energy > MAX_INTEGER:
            raise CandidateRejected('DECK_ENERGY_OVERFLOW')
        if self.c['kind'] == 'PLAY_CARD' and p['energy_delta'] > 0:
            raise CandidateRejected('DECK_PAYMENT_SIGN_INVALID')
        self.inputs.append({'port':'P15', 'basis_sha256':basis.sha256, 'candidate':p})
        before = self.s['energy']; self.s['energy'] = energy
        if self.c['kind'] == 'PLAY_CARD':
            self.emit('ENERGY_SPENT', amount=-p['energy_delta'], energy_after=energy)
        elif p['energy_delta'] != 0:
            self.note('ENERGY_REFRESHED', before=before, after=energy,
                      source='P15_CANDIDATE', schema_gap='P14-RFC-002')
        drawn = 0
        for move in p['moves']:
            src = self.s['zones'][move['from_zone']]
            dst = self.s['zones'][move['to_zone']]
            iid = move['instance_id']
            if iid not in self.cards or iid not in src:
                raise CandidateRejected('DECK_MOVE_SOURCE_INVALID')
            src.remove(iid)
            if move['to_index'] > len(dst):
                raise CandidateRejected('DECK_MOVE_INDEX_INVALID')
            dst.insert(move['to_index'], iid)
            self.emit('CARD_MOVED', **move)
            if move['from_zone'] == 'draw' and move['to_zone'] == 'hand': drawn += 1
        if instance is not None and instance['instance_id'] not in self.s['zones'][action.after_play_zone]:
            raise CandidateRejected('PLAYED_CARD_NOT_MOVED')
        # Structural conservation, not a second implementation of P15 rules.
        all_ids = [i for z in self.s['zones'].values() for i in z]
        if len(all_ids) != len(set(all_ids)) or set(all_ids) != set(self.cards):
            raise CandidateRejected('DECK_CARD_CONSERVATION')
        self.s['rng'] = p['rng_after']
        if self.c['kind'] in ('SYSTEM_START', 'SYSTEM_ENTER_PLAYER_TURN'):
            requested = self.rules.entry_draw_requested
            if drawn > requested:
                raise CandidateRejected('DRAW_REPORT_CONFLICT')
            if drawn < requested:
                self.emit('DRAW_SHORTFALL', requested=requested, drawn=drawn)
        self.checkpoint_hook('after_deck_patch')

    def damage(self, source, target, amount, depth=0):
        u = self.units[target]
        if u['hp'] == 0:
            self.note('DEAD_TARGET_SKIPPED', target_unit_id=target)
            return
        absorbed = min(u['shield'], amount)
        hp_loss = min(u['hp'], amount - absorbed)
        u['shield'] -= absorbed; u['hp'] -= hp_loss
        seq = self.emit('DAMAGE_APPLIED', source_unit_id=source, target_unit_id=target,
            raw=amount, absorbed=absorbed, hp_loss=hp_loss,
            overkill=amount-absorbed-hp_loss, hp_after=u['hp'], shield_after=u['shield'])
        death_seq = None
        if u['hp'] == 0:
            death_seq = self.emit('UNIT_DIED', unit_id=target)
        if amount > 0:
            self.enqueue('ON_DAMAGED', target, source, seq, depth + 1)
        if death_seq is not None:
            self.enqueue('ON_DEATH', target, source, death_seq, depth + 1)

    def enqueue(self, on, source, target, parent_seq, depth):
        if target is None or target not in self.units:
            return
        for r in self.rules.reactions:
            key = (r.source_unit_id, r.trigger_id, parent_seq)
            if r.source_unit_id != source or r.on != on or key in self.seen_triggers:
                continue
            self.seen_triggers.add(key); self.queue_serial += 1
            heapq.heappush(self.queue, (depth,r.tier,parent_seq,*order(self.units[source]),
                r.effect_index,r.trigger_id.encode('utf-8'),self.queue_serial,r,target))
            self.note('REACTION_QUEUED', trigger_id=r.trigger_id, source_unit_id=source,
                      target_unit_id=target, parent_event_seq=parent_seq, depth=depth, tier=r.tier)

    def effect(self, source, target, effect, depth=0):
        u = self.units[target]
        if u['hp'] == 0:
            self.note('DEAD_TARGET_SKIPPED', target_unit_id=target, effect_index=effect.effect_index)
            return
        self.emit('EFFECT_STARTED', source_unit_id=source, effect_index=effect.effect_index,
                  target_unit_ids=[target])
        if effect.kind == 'DAMAGE':
            self.damage(source,target,effect.amount,depth)
        elif effect.kind == 'HEAL':
            applied = min(effect.amount, u['max_hp'] - u['hp']); u['hp'] += applied
            self.emit('HEAL_APPLIED', source_unit_id=source, target_unit_id=target,
                      amount=applied, hp_after=u['hp'])
        elif effect.kind == 'SHIELD':
            after = u['shield'] + effect.amount
            if self.rules.shield_cap is not None and after > self.rules.shield_cap:
                if self.rules.shield_overflow == 'REJECT':
                    raise CandidateRejected('SHIELD_CAP_EXCEEDED')
                after = self.rules.shield_cap
            bounded(after); delta = after-u['shield']; u['shield'] = after
            self.emit('SHIELD_CHANGED', target_unit_id=target, delta=delta, shield_after=after)
        elif effect.kind == 'STATUS':
            if any(s['status_id'] == effect.status_id for s in u['statuses']):
                raise CandidateRejected('STATUS_REAPPLY_UNDEFINED')
            spec = self.status_specs[effect.status_id]
            ins = bounded(1 + max((s['insert_order'] for s in u['statuses']), default=-1))
            sid = 'status:' + fingerprint({'battle_id':self.s['battle_id'],
                'command_id':self.c['command_id'],'source':source,'target':target,
                'effect_index':effect.effect_index,'status_id':spec.status_id})
            u['statuses'].append({'status_instance_id':sid,'status_id':spec.status_id,
                'source_unit_id':source,'stacks':1,'remaining_triggers':spec.duration,'insert_order':ins})
            self.emit('STATUS_CHANGED',target_unit_id=target,status_instance_id=sid,
                      status_id=spec.status_id,operation='ADDED')

    def root_effects(self, source, action, targets):
        for effect in sorted(action.effects, key=lambda e:e.effect_index):
            for target in targets:
                self.effect(source,target,effect)
        self.drain()

    def drain(self):
        while self.queue:
            if self.reactions_processed >= 1024:
                raise SafetyFault('REACTION_LIMIT')
            item = heapq.heappop(self.queue)
            depth, r, target = item[0], item[-2], item[-1]
            self.reactions_processed += 1
            self.note('REACTION_STARTED', trigger_id=r.trigger_id,
                      source_unit_id=r.source_unit_id, depth=depth, parent_event_seq=item[2])
            # A dead source retains already eligible death/on-hit reactions.
            self.effect(r.source_unit_id,target,Effect(r.effect_index,'DAMAGE',r.damage),depth)

    def checkpoint(self, before):
        if self.queue:
            raise SafetyFault('UNDRAINED_CHECKPOINT')
        player = any(u['side'] == 'PLAYER' and u['hp'] > 0 for u in self.units.values())
        enemy = any(u['side'] == 'ENEMY' and u['hp'] > 0 for u in self.units.values())
        if not (player and enemy):
            outcome = 'WIN' if player else ('LOSS' if enemy else 'DRAW')
            self.s['phase'] = 'TERMINAL'; self.s['outcome'] = outcome
            self.emit('BATTLE_FINISHED', outcome=outcome)
            return True
        by_edge = {(e.unit_id,e.from_phase_id):e for e in self.rules.boss_edges}
        for boss in sorted(self.s['boss_states'], key=lambda b:order(self.units[b['unit_id']])):
            uid=boss['unit_id']; u=self.units[uid]
            if u['hp'] == 0: continue
            phase = boss['current_phase_id']
            while (uid,phase) in by_edge:
                e=by_edge[uid,phase]
                if e.to_phase_id in boss['proposed_phase_ids']:
                    phase=e.to_phase_id; continue
                threshold=e.numerator*(u['max_hp'] if e.relative_to_max_hp else 1)
                if not (before[uid]*e.denominator > threshold >= u['hp']*e.denominator): break
                pid='phase:' + fingerprint({'battle_id':self.s['battle_id'],
                    'unit_id':uid,'to_phase_id':e.to_phase_id,'content_version':self.rules.content_version})
                boss['proposed_phase_ids'].append(e.to_phase_id)
                self.emit('BOSS_PHASE_PROPOSED',unit_id=uid,proposal_id=pid,
                          from_phase_id=e.from_phase_id,to_phase_id=e.to_phase_id)
                phase=e.to_phase_id
        return False

    def owner_entry(self, side):
        before=self.before_hp(); ticked=[]
        for u in sorted(self.s['units'],key=order):
            if u['side'] != side or u['hp'] == 0: continue
            for status in sorted(list(u['statuses']),key=lambda s:s['insert_order']):
                if u['hp'] == 0: break
                if status['remaining_triggers'] == 0: continue
                spec=self.status_specs[status['status_id']]
                self.note('STATUS_TICKED',target_unit_id=u['unit_id'],
                          status_id=spec.status_id,status_instance_id=status['status_instance_id'],amount=spec.amount)
                source=status['source_unit_id'] if status['source_unit_id'] is not None else u['unit_id']
                self.damage(source,u['unit_id'],spec.amount)
                ticked.append((u,status))
        self.drain()
        if self.checkpoint(before): return True
        for u,status in ticked:
            if u['hp'] == 0: continue
            status['remaining_triggers'] -= 1
            op='UPDATED'
            if status['remaining_triggers'] == 0:
                u['statuses'].remove(status); op='REMOVED'
            self.emit('STATUS_CHANGED',target_unit_id=u['unit_id'],
                status_instance_id=status['status_instance_id'],status_id=status['status_id'],operation=op)
        return False

    def player_entry(self, starting=False):
        if self.owner_entry('PLAYER'): return
        self.deck_patch()
        if starting:
            self.s['turn_number']=1
        self.s['phase']='PLAYER_READY'
        self.emit('PLAYER_TURN_STARTED',turn_number=self.s['turn_number'])

    def enemy_turn(self):
        if self.owner_entry('ENEMY'): return
        if any(b['proposed_phase_ids'] for b in self.s['boss_states']):
            raise CandidateRejected('PHASE_COMMIT_CONTRACT_UNBOUND')
        living=[u for u in self.s['units'] if u['side']=='ENEMY' and u['hp']>0]
        # P13 v0.1 has a single-intent port but no ordered multi-actor batch or
        # per-slot continuation. Fail closed instead of silently omitting foes.
        if len(living) != 1:
            raise CandidateRejected('ENEMY_BATCH_CONTRACT_UNBOUND')
        if self.enemy is None:
            raise DependencyUnavailable('P16_ENEMY_PORT_UNBOUND')
        basis=checked(self.s,'BattleSnapshot')
        intent=checked(self.enemy.propose(basis),'EnemyIntent'); p=intent.value
        if (p['battle_id'],p['expected_revision'],p['content_version'],p['actor_id']) != (
                self.s['battle_id'],self.s['revision'],self.rules.content_version,living[0]['unit_id']):
            raise CandidateRejected('ENEMY_INTENT_BINDING_MISMATCH')
        action=self.skills.get(p['skill_id'])
        if action is None: raise CandidateRejected('CONTENT_UNAVAILABLE')
        self.inputs.append({'port':'P16','basis_sha256':basis.sha256,'candidate':p})
        self.note('ENEMY_ACTION_STARTED',actor_id=p['actor_id'],intent_id=p['intent_id'],skill_id=p['skill_id'])
        before=self.before_hp()
        try:
            self.targets(action,living[0],p['target_ids'])
        except CandidateRejected as exc:
            if exc.code != 'TARGET_INVALID' or p['no_valid_target'] != 'SKIP': raise
            self.emit('ENEMY_ACTION_SKIPPED',unit_id=p['actor_id'],reason_code='NO_VALID_TARGET')
        else:
            self.root_effects(p['actor_id'],action,p['target_ids'])
        if self.checkpoint(before): return
        self.emit('TURN_ENDED',side='ENEMY',turn_number=self.s['turn_number'])
        self.s['turn_number']=bounded(self.s['turn_number']+1)
        self.s['phase']='PLAYER_TURN_PENDING'

    def run(self):
        kind=self.c['kind']; play=None
        if kind == 'PLAY_CARD': play=self.play_inputs()
        self.emit('COMMAND_ACCEPTED',command_sha256=self.command.sha256)
        if kind == 'PLAY_CARD':
            actor,instance,action=play; before=self.before_hp()
            self.deck_patch(action,instance)
            self.root_effects(actor['unit_id'],action,self.c['payload']['target_ids'])
            self.checkpoint(before)
        elif kind == 'END_TURN':
            self.deck_patch()
            self.emit('TURN_ENDED',side='PLAYER',turn_number=self.s['turn_number'])
            self.s['phase']='ENEMY_READY'
        elif kind == 'SYSTEM_START':
            for u in sorted(self.s['units'],key=order):
                if u['hp'] == 0: self.emit('UNIT_DIED',unit_id=u['unit_id'])
            if not self.checkpoint(self.before_hp()): self.player_entry(starting=True)
        elif kind == 'SYSTEM_ENTER_PLAYER_TURN':
            self.player_entry()
        elif kind == 'SYSTEM_ENEMY_ACTION':
            self.enemy_turn()
        elif kind == 'ABORT':
            self.s['phase']='ABORTED'; self.s['outcome']='ABORTED'
            self.emit('BATTLE_ABORTED',reason_code=self.c['payload']['reason_code'])
        else:
            raise SafetyFault('UNREACHABLE_COMMAND')
        self.checkpoint_hook('after_resolution')
