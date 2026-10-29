"""Pure validation and candidate generation. Never writes an authoritative field."""
from dataclasses import dataclass
from .content import PlannerContext
from .deck import DeckState, DeckOperation, consume_card, discard_hand, draw_cards, shuffle_draw
from .errors import DeckRejected, require
from .wire import FrozenMessage, checked, message


@dataclass(frozen=True, slots=True)
class Decision:
    evidence: FrozenMessage

    @property
    def code(self):
        return self.evidence.value['code']

    @property
    def candidate(self):
        value = self.evidence.value['deck_patch']
        return None if value is None else checked(value, 'DeckPatchCandidate')

    @property
    def action_intent(self):
        value = self.evidence.value['action_intent']
        return None if value is None else FrozenMessage.from_value(value)


def _decision(command, snapshot, context, code, *, patch=None, intent=None, draw_report=None,
              prior_command_sha256=None):
    c = command.value
    return Decision(FrozenMessage.from_value({'format': 'P15-DECISION/0.1.0-isolated',
        'battle_id': c['battle_id'], 'request_id': c['command_id'], 'command_sha256': command.sha256,
        'basis_snapshot_sha256': snapshot.sha256, 'expected_revision': c['expected_revision'],
        'context_sha256': context.sha256, 'status': 'CANDIDATE' if patch is not None else 'REJECTED',
        'code': code, 'deck_patch': None if patch is None else patch.value,
        'candidate_sha256': None if patch is None else patch.sha256,
        'action_intent': intent, 'draw_report': draw_report,
        'prior_command_sha256': prior_command_sha256}))


def _check_basis(s, context):
    require(s['rules_version'] == context.policy.rules_version, 'RULES_VERSION_MISMATCH')
    require(s['content_version'] == context.policy.content_version, 'CONTENT_VERSION_MISMATCH')
    members = {m['unit_id']: m for m in context.party.value['members']}
    players = {u['unit_id']: u for u in s['units'] if u['side'] == 'PLAYER'}
    require(set(members) == set(players), 'PARTY_SNAPSHOT_MISMATCH')
    for uid, m in members.items():
        u = players[uid]
        require((u['definition_id'], u['slot'], u['max_hp']) == (m['character_id'], m['slot'], m['max_hp']), 'PARTY_SNAPSHOT_MISMATCH')
    for inst in s['card_instances']:
        spec = context.catalog.card(inst['card_id'])
        require(spec.playable, 'CONTENT_DISABLED')
        require(inst['owner_unit_id'] in players, 'CARD_OWNER_INVALID')
        if spec.owner_character_id is not None:
            require(players[inst['owner_unit_id']]['definition_id'] == spec.owner_character_id, 'CARD_OWNER_INVALID')
    require(s['energy'] <= context.policy.energy_cap, 'ENERGY_POLICY_BOUNDS')


def _validate_play(c, s, context, deck):
    p = c['payload']
    units = {u['unit_id']: u for u in s['units']}
    actor = units.get(p['actor_id'])
    require(actor is not None and actor['side'] == 'PLAYER' and actor['hp'] > 0, 'ACTOR_INVALID')
    inst = next((i for i in deck.instances if i.instance_id == p['card_instance_id']), None)
    require(inst is not None and p['card_instance_id'] in deck.hand, 'CARD_NOT_IN_HAND')
    require(inst.owner_unit_id == p['actor_id'], 'CARD_OWNER_INVALID')
    spec = context.catalog.card(inst.card_id)
    if spec.owner_character_id is not None:
        require(actor['definition_id'] == spec.owner_character_id, 'CARD_OWNER_INVALID')
    targets = p['target_ids']
    require(len(targets) == spec.target_count and len(set(targets)) == len(targets), 'TARGET_INVALID')
    require(all(t in units and units[t]['hp'] > 0 and units[t]['side'] == spec.target_side for t in targets), 'TARGET_INVALID')
    seen = {(t, status['status_id']) for t in targets for status in units[t]['statuses']}
    for effect in spec.effects.value:
        if effect['effect_code'] == 'STATUS':
            for target in targets:
                require((target, effect['status_id']) not in seen, 'STATUS_REAPPLY_UNDEFINED')
                seen.add((target, effect['status_id']))
    require(s['energy'] >= spec.cost, 'ENERGY_INSUFFICIENT')
    return spec


def plan(command, snapshot, context: PlannerContext, *, prior: Decision | None = None):
    """Same immutable inputs -> identical bytes. Prior is optional local evidence.

    request_id is the local name for P13 command_id, not an extra wire field.
    A prior identical request returns its original evidence, including its basis.
    Only P14's accepted_commands is authoritative about successful execution.
    """
    require(isinstance(context, PlannerContext), 'IMMUTABLE_CONTEXT_REQUIRED')
    command = checked(command, 'BattleCommand')
    snapshot = checked(snapshot, 'BattleSnapshot')
    c, s = command.value, snapshot.value
    if prior is not None:
        require(isinstance(prior, Decision), 'PRIOR_EVIDENCE_REQUIRED')
        old = prior.evidence.value
        require(old['context_sha256'] == context.sha256, 'PRIOR_CONTEXT_MISMATCH')
        require((old['battle_id'], old['request_id']) == (c['battle_id'], c['command_id']), 'PRIOR_REQUEST_MISMATCH')
        if old['command_sha256'] == command.sha256:
            return prior
        # Use the original evidence basis so a collision retry is stable too.
        value = old.copy()
        value.update(command_sha256=command.sha256, expected_revision=c['expected_revision'],
                     status='REJECTED', code='COMMAND_ID_COLLISION', deck_patch=None, candidate_sha256=None,
                     action_intent=None, draw_report=None, prior_command_sha256=old['command_sha256'])
        return Decision(FrozenMessage.from_value(value))
    try:
        require(c['battle_id'] == s['battle_id'] == context.battle_id, 'BATTLE_ID_MISMATCH')
        require(s['phase'] not in ('TERMINAL', 'ABORTED', 'FAULTED'), 'ALREADY_CLOSED')
        phases = {'PLAY_CARD': 'PLAYER_READY', 'END_TURN': 'PLAYER_READY',
                  'SYSTEM_START': 'CREATED', 'SYSTEM_ENTER_PLAYER_TURN': 'PLAYER_TURN_PENDING'}
        require(c['kind'] in phases, 'COMMAND_NOT_OWNED_BY_P15')
        require(s['phase'] == phases[c['kind']], 'PHASE_INVALID')
        require(c['expected_revision'] == s['revision'], 'REVISION_CONFLICT')
        _check_basis(s, context)
        deck = DeckState.from_snapshot(snapshot)
        policy = context.policy
        require(len(deck.hand) <= policy.hand_limit, 'HAND_LIMIT_ALREADY_EXCEEDED')
        moves = ()
        intent = report = None
        energy_delta = 0
        if c['kind'] == 'PLAY_CARD':
            spec = _validate_play(c, s, context, deck)
            op = consume_card(deck, c['payload']['card_instance_id'], spec.after_play_zone)
            energy_delta = -spec.cost
            # Reference-only effect intent. P14 reads its own frozen Action/Effect
            # definitions and performs all effect, HP, death and outcome logic.
            intent = {'format': 'P15-ACTION-INTENT/0.1.0-isolated', 'wire_submission': False,
                'battle_id': c['battle_id'], 'command_id': c['command_id'], 'command_sha256': command.sha256,
                'snapshot_sha256': snapshot.sha256, 'content_version': context.catalog.content_version,
                'card_id': spec.card_id, 'actor_id': c['payload']['actor_id'],
                'card_instance_id': c['payload']['card_instance_id'], 'target_ids': c['payload']['target_ids'],
                'effect_ids': list(spec.effect_ids), 'effect_definitions_sha256': spec.effects.sha256,
                'catalog_source_sha256': context.catalog.source_sha256}
        elif c['kind'] == 'END_TURN':
            op = discard_hand(deck) if policy.end_turn == 'DISCARD_ALL' else DeckOperation(deck, ())
        else:
            if c['kind'] == 'SYSTEM_START' and policy.shuffle_initial:
                shuffled = shuffle_draw(deck)
                deck, moves = shuffled.after, shuffled.moves
            count = policy.initial_draw if c['kind'] == 'SYSTEM_START' else policy.turn_draw
            op = draw_cards(deck, count, hand_limit=policy.hand_limit, recycle_discard=policy.recycle_discard)
            report = {'requested': count, 'drawn': op.drawn, 'shortfall': op.shortfall,
                      'recycled': op.recycled, 'stopped_by': op.stopped_by}
            if policy.entry_energy_mode == 'SET':
                energy_delta = policy.entry_energy - s['energy']
            elif policy.entry_energy_mode == 'ADD_CAPPED':
                energy_delta = min(policy.energy_cap, s['energy'] + policy.entry_energy) - s['energy']
        moves += op.moves
        require(len(moves) <= 4096, 'PATCH_CAPACITY_EXCEEDED')
        patch = message('DeckPatchCandidate', battle_id=c['battle_id'], command_id=c['command_id'],
            expected_revision=s['revision'], command_sha256=command.sha256, snapshot_sha256=snapshot.sha256,
            policy_version=policy.version, moves=[m.value() for m in moves], energy_delta=energy_delta,
            rng_before=s['rng'], rng_after=op.after.rng.value())
        if intent is not None:
            intent['deck_candidate_sha256'] = patch.sha256
        return _decision(command, snapshot, context, 'OK', patch=patch, intent=intent, draw_report=report)
    except DeckRejected as exc:
        return _decision(command, snapshot, context, exc.code)
