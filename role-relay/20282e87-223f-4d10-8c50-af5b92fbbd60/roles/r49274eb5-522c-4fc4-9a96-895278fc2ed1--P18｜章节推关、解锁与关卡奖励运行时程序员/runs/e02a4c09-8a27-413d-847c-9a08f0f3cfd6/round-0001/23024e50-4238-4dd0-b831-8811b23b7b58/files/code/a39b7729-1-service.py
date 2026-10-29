"""P18 admission and settlement planner. All outputs are uncommitted candidates."""
from __future__ import annotations
from .common import (FrozenMessage, ContractError, StageError, PlanResult,
    COMMAND_VERSION, CANDIDATE_VERSION, need, shape, ident, digest, integer,
    fingerprint, get_row, first_clear_key, first_clear_identity, repeat_identity, validate_dto)
from .content import CatalogSet
from .state import validate_state, check_store_fence
from .projection import eligible, effective_clear
from .ports import ClosedAuthority


def command(snapshot, catalog, request_id, kind, payload):
    s = snapshot.value
    return FrozenMessage.from_value({'schema_version': COMMAND_VERSION,
        'request_id': request_id, 'player_save_scope_id': s['player_save_scope_id'],
        'store_instance': s['store_instance'], 'continuity_ref': s['continuity_ref'],
        'expected_revision': s['revision'], 'catalog_sha256': catalog.sha256,
        'kind': kind, 'payload': payload})


def _binding(kind, reference, proof):
    return {'kind': kind, 'reference': reference, 'sha256': proof.sha256, 'document': proof.value}


class StagePlanner:
    def __init__(self, catalog, authority=None, *, historical=(), mode='isolated'):
        need(mode == 'isolated', 'E_PRODUCTION_BOOTSTRAP_BLOCKED')
        self.catalogs = CatalogSet(catalog, tuple(historical))
        self.authority = authority if authority is not None else ClosedAuthority()

    @property
    def catalog(self): return self.catalogs.current

    def plan(self, request, snapshot):
        try:
            return self._plan(request, snapshot)
        except StageError as exc:
            blocked = {'E_STORE_AUTHORITY_UNBOUND', 'E_ENTRY_AUTHORITY_UNBOUND', 'E_RESULT_AUTHORITY_UNBOUND',
                'E_CONTROL_AUTHORITY_UNBOUND', 'E_COMMIT_UNKNOWN', 'E_RESTORE_RECONCILIATION_REQUIRED',
                'E_STORE_HEAD_MISMATCH', 'E_CONTINUITY_FENCE', 'E_PENDING_RECONCILIATION',
                'E_WAIT_FINAL_TERMINAL', 'E_PREREQUISITE_UNDER_REVIEW', 'E_STAGE_UNDER_REVIEW'}
            return PlanResult('BLOCKED' if exc.code in blocked else 'REJECTED', exc.code)
        except ContractError as exc:
            return PlanResult('REJECTED', 'E_CONTRACT:' + str(exc))

    def _plan(self, request, snapshot):
        before = validate_state(snapshot, self.catalog)
        need(type(request) is FrozenMessage, 'E_COMMAND_TYPE')
        r = request.value
        shape(r, 'schema_version request_id player_save_scope_id store_instance continuity_ref expected_revision catalog_sha256 kind payload')
        need(r['schema_version'] == COMMAND_VERSION, 'E_COMMAND_VERSION')
        for k in ('request_id', 'player_save_scope_id', 'store_instance', 'continuity_ref', 'kind'): ident(r[k])
        integer(r['expected_revision']); digest(r['catalog_sha256']); need(type(r['payload']) is dict, 'E_PAYLOAD')
        need(r['player_save_scope_id'] == before['player_save_scope_id'], 'E_SAVE_SCOPE_MISMATCH')
        need(r['store_instance'] == before['store_instance'] and r['continuity_ref'] == before['continuity_ref'], 'E_CONTINUITY_FENCE')
        fence = check_store_fence(snapshot, self.authority)
        old = get_row(before['operations'], 'request_id', r['request_id'])
        if old:
            need(old['request_sha256'] == request.sha256, 'E_REQUEST_ID_COLLISION')
            return PlanResult('DUPLICATE_NO_OP', 'REUSE_REQUEST_RECEIPT', receipt=FrozenMessage.from_value(old))
        need(r['expected_revision'] == before['revision'], 'E_REVISION_CONFLICT')
        need(r['catalog_sha256'] == self.catalog.sha256, 'E_CATALOG_CONFLICT')
        after = snapshot.value
        evidence = [_binding('STORE_FENCE', before['player_save_scope_id'], fence)]
        if r['kind'] == 'ENTER':
            decision, grant, parameters = self._enter(r['payload'], after, evidence)
        elif r['kind'] == 'SETTLE':
            outcome = self._settle(r['payload'], after, evidence)
            if isinstance(outcome, PlanResult): return outcome
            decision, grant = outcome; parameters = None
        elif r['kind'] == 'CLOSE':
            outcome = self._close(r['payload'], after, evidence)
            if isinstance(outcome, PlanResult): return outcome
            decision, grant, parameters = outcome, None, None
        elif r['kind'] == 'REVOKE':
            outcome = self._revoke(r['payload'], after, evidence)
            if isinstance(outcome, PlanResult): return outcome
            decision, grant, parameters = outcome, None, None
        else:
            raise StageError('E_COMMAND_KIND')
        after['revision'] = integer(before['revision'] + 1)
        after['operations'].append({'request_id': r['request_id'], 'request_sha256': request.sha256,
                                    'committed_revision': after['revision']})
        after_message = FrozenMessage.from_value(after)
        validate_state(after_message, self.catalog)
        claims = [fc['key'] for fc in after['first_clears'] if all(fc['key'] != x['key'] for x in before['first_clears'])]
        candidate = FrozenMessage.from_value({'schema_version': CANDIDATE_VERSION,
            'request': r, 'request_sha256': request.sha256, 'before_sha256': snapshot.sha256,
            'after_sha256': after_message.sha256, 'after_state': after, 'decision': decision,
            'grant': None if grant is None else grant.value, 'new_first_clear_keys': claims,
            'battle_parameters': parameters, 'evidence_bindings': evidence,
            'commit_scope': 'ISOLATED_CANDIDATE_NOT_COMMITTED'})
        return PlanResult('CANDIDATE', decision, candidate)

    def _enter(self, payload, state, evidence):
        shape(payload, 'stage_id battle_id entry_ref seed')
        for k in ('stage_id', 'battle_id', 'entry_ref'): ident(payload[k])
        integer(payload['seed'], 1, 2**32 - 1)
        stage = eligible(state, self.catalog, payload['stage_id'])
        active = get_row(state['attempts'], 'battle_id', state['active_battle_id'])
        need(active is None, 'E_PENDING_RECONCILIATION' if active and active['status'] == 'QUARANTINED' else 'E_ACTIVE_ATTEMPT_EXISTS')
        need(get_row(state['attempts'], 'battle_id', payload['battle_id']) is None, 'E_BATTLE_ID_REUSED')
        proof = self.authority.resolve_entry(payload['entry_ref'])
        need(type(proof) is FrozenMessage, 'E_ENTRY_AUTHORITY_UNBOUND')
        e = proof.value
        shape(e, 'schema_version entry_ref player_save_scope_id store_instance continuity_ref stage_id battle_id catalog_sha256 party_snapshot party_source_sha256 battle_rules_version battle_content_version battle_content_sha256')
        need(e['schema_version'] == 'P18-ENTRY-EVIDENCE/0.1.0-proposal', 'E_ENTRY_VERSION')
        for k in ('entry_ref', 'player_save_scope_id', 'store_instance', 'continuity_ref', 'stage_id', 'battle_id', 'battle_rules_version', 'battle_content_version'): ident(e[k])
        for k in ('catalog_sha256', 'party_source_sha256', 'battle_content_sha256'): digest(e[k])
        need((e['entry_ref'], e['player_save_scope_id'], e['store_instance'], e['continuity_ref'], e['stage_id'], e['battle_id'], e['catalog_sha256']) ==
             (payload['entry_ref'], state['player_save_scope_id'], state['store_instance'], state['continuity_ref'], payload['stage_id'], payload['battle_id'], self.catalog.sha256), 'E_ENTRY_BINDING')
        party = validate_dto(e['party_snapshot'], 'PartySnapshot')
        need(len({m['character_id'] for m in party.value['members']}) == 3, 'E_PARTY_DUPLICATE')
        prerequisites = []
        for sid in stage['prerequisites']:
            fc = get_row(state['first_clears'], 'stage_id', sid)
            need(fc is not None, 'E_PREREQUISITE_RECEIPT_MISSING')
            prerequisites.append({'stage_id': sid, 'clear_receipt_ref': fc['receipt_ref'], 'first_clear_key': fc['key']})
        a = {'player_save_scope_id': state['player_save_scope_id'], 'battle_id': payload['battle_id'],
            'stage_id': stage['canonical_stage_id'], 'chapter_id': stage['chapter_id'],
            'catalog_sha256': self.catalog.sha256, 'entry_ref': payload['entry_ref'], 'entry_sha256': proof.sha256,
            'party_snapshot': party.value, 'party_sha256': party.sha256,
            'battle_rules_version': e['battle_rules_version'], 'battle_content_version': e['battle_content_version'],
            'battle_content_sha256': e['battle_content_sha256'], 'seed': payload['seed'],
            'stage_config_sha256': self.catalog.source_hash('P07_GRAPH'),
            'reward_config_sha256': self.catalog.source_hash('P07_REWARDS'),
            'enemy_content_sha256': self.catalog.source_hash('P06_ENEMIES'),
            'boss_graph_sha256': self.catalog.source_hash('P06_BOSS'), 'prerequisites': prerequisites}
        state['attempts'].append({'battle_id': a['battle_id'], 'admission': a,
            'admission_sha256': fingerprint(a), 'status': 'ACTIVE', 'high_revision': 0,
            'terminal': None, 'closure': None})
        state['active_battle_id'] = a['battle_id']
        evidence.append(_binding('ENTRY', payload['entry_ref'], proof))
        params = {'schema_version': 'P18-BATTLE-PARAMETERS/0.1.0-proposal',
            'admission': a, 'admission_sha256': fingerprint(a),
            'enemy_refs': stage['enemy_refs'], 'boss_graph_id': stage['boss_graph_id'],
            'scope': 'ISOLATED_START_REQUEST_NOT_BATTLE_RESULT'}
        return 'ADMITTED', None, params

    def _battle_evidence(self, attempt):
        proof = self.authority.resolve_battle(attempt['battle_id'])
        need(type(proof) is FrozenMessage, 'E_RESULT_AUTHORITY_UNBOUND')
        p = proof.value
        shape(p, 'schema_version battle_id admission_sha256 snapshot result')
        need(p['schema_version'] == 'P18-BATTLE-EVIDENCE/0.1.0-proposal', 'E_BATTLE_EVIDENCE_VERSION')
        ident(p['battle_id']); digest(p['admission_sha256'])
        need(p['battle_id'] == attempt['battle_id'] and p['admission_sha256'] == attempt['admission_sha256'], 'E_BATTLE_EVIDENCE_BINDING')
        snap = validate_dto(p['snapshot'], 'BattleSnapshot')
        s = snap.value; a = attempt['admission']
        need((s['battle_id'], s['rules_version'], s['content_version']) ==
             (attempt['battle_id'], a['battle_rules_version'], a['battle_content_version']), 'E_BATTLE_EVIDENCE_BINDING')
        need({m['unit_id'] for m in a['party_snapshot']['members']} ==
             {u['unit_id'] for u in s['units'] if u['side'] == 'PLAYER'}, 'E_BATTLE_PARTY_BINDING')
        need(s['rng']['initial_seed'] == a['seed'], 'E_BATTLE_SEED_BINDING')
        if p['result'] is not None:
            result = validate_dto(p['result'], 'BattleResult'); r = result.value
            need((r['battle_id'], r['stage_id'], r['profile_scope'], r['rules_version'], r['content_version']) ==
                 (a['battle_id'], a['stage_id'], a['player_save_scope_id'], a['battle_rules_version'], a['battle_content_version']), 'E_RESULT_ADMISSION_BINDING')
            need(s['phase'] == 'TERMINAL' and s['outcome'] == r['outcome'], 'E_NOT_FINAL_RESULT')
            need(r['terminal_revision'] == s['revision'] and r['terminal_event_seq'] <= s['last_event_seq'], 'E_TERMINAL_REVISION_BINDING')
            need(r['final_snapshot_sha256'] == snap.sha256, 'E_FINAL_SNAPSHOT_HASH')
            live_player = any(u['hp'] > 0 for u in s['units'] if u['side'] == 'PLAYER')
            live_enemy = any(u['hp'] > 0 for u in s['units'] if u['side'] == 'ENEMY')
            need({'WIN': (True, False), 'LOSS': (False, True), 'DRAW': (False, False)}[r['outcome']] == (live_player, live_enemy), 'E_TERMINAL_LIVE_COUNTS')
        return proof

    def _quarantine(self, state, attempt, proof, reason, *, review=False):
        prior = next((q for q in state['quarantines'] if q['battle_id'] == attempt['battle_id'] and q['evidence_sha256'] == proof.sha256 and q['reason'] == reason), None)
        if prior:
            return PlanResult('DUPLICATE_NO_OP', 'REUSE_QUARANTINE_RECORD', receipt=FrozenMessage.from_value(prior))
        state['quarantines'].append({'battle_id': attempt['battle_id'], 'reason': reason,
                                    'evidence_sha256': proof.sha256, 'evidence': proof.value})
        if review:
            attempt['status'] = 'REVIEW_REQUIRED'
            get_row(state['stages'], 'stage_id', attempt['admission']['stage_id'])['review_required'] = True
        else:
            attempt['status'] = 'QUARANTINED'
        return reason, None

    def _settle(self, payload, state, evidence):
        shape(payload, 'result')
        message = validate_dto(payload['result'], 'BattleResult'); r = message.value
        need(r['profile_scope'] == state['player_save_scope_id'], 'E_SAVE_SCOPE_MISMATCH')
        attempt = get_row(state['attempts'], 'battle_id', r['battle_id'])
        need(attempt is not None, 'E_MISSING_ADMISSION')
        a = attempt['admission']
        need((r['stage_id'], r['rules_version'], r['content_version']) ==
             (a['stage_id'], a['battle_rules_version'], a['battle_content_version']), 'E_RESULT_ADMISSION_BINDING')
        need(attempt['status'] not in ('ABORTED', 'FAULTED'), 'E_ABORT_OR_FAULT_TOMBSTONE')
        need(r['terminal_revision'] >= attempt['high_revision'], 'E_STALE_TERMINAL')
        need(attempt['status'] != 'REVOKED', 'E_REVOKED_TOMBSTONE')
        old = attempt['terminal']
        if old and r['terminal_revision'] == old['result']['terminal_revision']:
            need(message.sha256 == old['result_sha256'], 'E_TERMINAL_IDENTITY_COLLISION')
            return PlanResult('DUPLICATE_NO_OP', 'REUSE_COMMITTED_RECEIPT', receipt=FrozenMessage.from_value(old))
        proof = self._battle_evidence(attempt); p = proof.value
        need(p['result'] is not None, 'E_WAIT_FINAL_TERMINAL')
        current = validate_dto(p['result'], 'BattleResult')
        need(r['terminal_revision'] >= current.value['terminal_revision'], 'E_STALE_TERMINAL')
        need(r['terminal_revision'] == current.value['terminal_revision'], 'E_FUTURE_TERMINAL')
        need(current.sha256 == message.sha256, 'E_UNTRUSTED_RESULT')
        evidence.append(_binding('BATTLE', r['battle_id'], proof))
        if old:
            attempt['high_revision'] = r['terminal_revision']
            return self._quarantine(state, attempt, proof, 'RECONCILE_REVISION_NO_NEW_AWARD', review=True)
        need(state['active_battle_id'] == r['battle_id'], 'E_INACTIVE_ATTEMPT')
        pinned = self.catalogs.resolve(a['catalog_sha256'])
        if pinned is None:
            return self._quarantine(state, attempt, proof, 'QUARANTINE_MISSING_PINNED_CONTENT')
        stage = pinned.stage(a['stage_id'])
        if r['outcome'] == 'WIN':
            own = get_row(state['stages'], 'stage_id', a['stage_id'])
            if own['review_required'] or any(not effective_clear(state, pinned, sid) for sid in stage['prerequisites']):
                return self._quarantine(state, attempt, proof, 'QUARANTINE_PREREQUISITE_REVOKED')
            need([(p['stage_id'], p['first_clear_key']) for p in a['prerequisites']] ==
                 [(sid, first_clear_key(state['player_save_scope_id'], sid)) for sid in stage['prerequisites']], 'E_PREREQUISITE_BINDING')
            for ppre in a['prerequisites']:
                fc = get_row(state['first_clears'], 'stage_id', ppre['stage_id'])
                need(fc is not None and fc['receipt_ref'] == ppre['clear_receipt_ref'], 'E_PREREQUISITE_RECEIPT_BINDING')
            enemy_counts = {}
            for u in p['snapshot']['units']:
                if u['side'] == 'ENEMY': enemy_counts[u['definition_id']] = enemy_counts.get(u['definition_id'], 0) + 1
            need(enemy_counts == {e['enemy_id']: e['count'] for e in stage['enemy_refs']}, 'E_BATTLE_ENEMY_BINDING')
        first = r['outcome'] == 'WIN' and get_row(state['first_clears'], 'stage_id', a['stage_id']) is None
        decision = 'NO_CLEAR'
        if r['outcome'] == 'WIN':
            decision = 'FIRST_CLEAR' if first else ('REPEAT_CLEAR' if stage['repeat_enabled'] else 'REPEAT_DISABLED')
        receipt_ref = 'p18.receipt.' + fingerprint([state['player_save_scope_id'], r['battle_id']])
        grant = self._grant(state, a, r, stage, pinned, decision, receipt_ref)
        attempt['terminal'] = {'result': r, 'result_sha256': message.sha256, 'decision': decision,
            'receipt_ref': receipt_ref, 'grant_ref': None if grant is None else grant.value['grant_ref'],
            'reward_identity': (None if decision == 'NO_CLEAR' else
                first_clear_identity(state['player_save_scope_id'], a['stage_id']) if first else
                repeat_identity(state['player_save_scope_id'], a['stage_id'], r['battle_id'], r['terminal_revision']))}
        attempt['high_revision'] = r['terminal_revision']; attempt['status'] = 'SETTLED'
        state['active_battle_id'] = None
        if r['outcome'] == 'WIN':
            get_row(state['stages'], 'stage_id', a['stage_id'])['confirmed_win_battles'].append(r['battle_id'])
        if first:
            state['first_clears'].append({'key': first_clear_key(state['player_save_scope_id'], a['stage_id']),
                'stage_id': a['stage_id'], 'battle_id': r['battle_id'], 'result_sha256': message.sha256, 'receipt_ref': receipt_ref})
            state['first_clears'].sort(key=lambda x: x['stage_id'])
        return decision, grant

    def _grant(self, state, admission, result, stage, pinned, decision, receipt_ref):
        if decision not in ('FIRST_CLEAR', 'REPEAT_CLEAR'): return None
        reward = stage['first' if decision == 'FIRST_CLEAR' else 'repeat']
        if reward['tokens'] == reward['xp_each'] == 0: return None
        # Fixed namespace, never chapter, content version or battle for first-clear.
        identity = {'campaign_id': 'YLTT_STAGE_SCOPE', 'stage_id': stage['canonical_stage_id']}
        if decision == 'REPEAT_CLEAR': identity['battle_id'] = result['battle_id']
        return FrozenMessage.from_value({'schema_version': 'P17-GRANT-INPUT/0.1.0-proposal',
            'grant_ref': 'p18.grant.' + fingerprint([receipt_ref, decision]), 'issuer': 'P18',
            'profile_id': state['player_save_scope_id'],
            'source_kind': 'STAGE_FIRST_CLEAR' if decision == 'FIRST_CLEAR' else 'STAGE_REPEAT',
            'identity': identity, 'eligibility_ref': receipt_ref,
            'policy_version': pinned.value['content_version'], 'policy_sha256': admission['reward_config_sha256'],
            'resources': [{'resource_id': reward['resource_id'], 'amount': reward['tokens']}] if reward['tokens'] else [],
            'characters': [], 'xp': [{'character_id': m['character_id'], 'amount': reward['xp_each']}
                for m in admission['party_snapshot']['members']] if reward['xp_each'] else [], 'equipment': []})

    def _close(self, payload, state, evidence):
        shape(payload, 'battle_id'); ident(payload['battle_id'])
        at = get_row(state['attempts'], 'battle_id', payload['battle_id'])
        need(at is not None, 'E_MISSING_ADMISSION')
        if at['status'] in ('ABORTED', 'FAULTED'):
            return PlanResult('DUPLICATE_NO_OP', 'REUSE_CLOSURE_RECEIPT', receipt=FrozenMessage.from_value(at['closure']))
        need(at['terminal'] is None and at['status'] == 'ACTIVE', 'E_CANNOT_CLOSE_TERMINAL')
        proof = self._battle_evidence(at); p = proof.value; s = p['snapshot']
        need(p['result'] is None and s['phase'] in ('ABORTED', 'FAULTED'), 'E_AUTHORITATIVE_CLOSURE_REQUIRED')
        integer(s['revision'], 1)
        at['status'] = s['phase']; at['high_revision'] = s['revision']
        at['closure'] = {'kind': s['phase'], 'evidence_sha256': proof.sha256,
                         'revision': s['revision'], 'evidence': p}
        state['active_battle_id'] = None
        evidence.append(_binding('BATTLE_CLOSE', payload['battle_id'], proof))
        return s['phase'] + '_NO_CLEAR'

    def _revoke(self, payload, state, evidence):
        shape(payload, 'control_ref'); ident(payload['control_ref'])
        proof = self.authority.resolve_control(payload['control_ref'])
        need(type(proof) is FrozenMessage, 'E_CONTROL_AUTHORITY_UNBOUND')
        p = proof.value
        shape(p, 'schema_version control_ref player_save_scope_id battle_id admission_sha256 superseded_result new_revision')
        need(p['schema_version'] == 'P18-REVOCATION-EVIDENCE/0.1.0-proposal', 'E_CONTROL_VERSION')
        for k in ('control_ref', 'player_save_scope_id', 'battle_id'): ident(p[k])
        digest(p['admission_sha256']); integer(p['new_revision'], 1)
        need(p['control_ref'] == payload['control_ref'] and p['player_save_scope_id'] == state['player_save_scope_id'], 'E_CONTROL_BINDING')
        old = get_row(state['controls'], 'control_ref', p['control_ref'])
        if old:
            need(old['evidence_sha256'] == proof.sha256, 'E_CONTROL_ID_COLLISION')
            return PlanResult('DUPLICATE_NO_OP', 'REUSE_REVIEW_RECEIPT', receipt=FrozenMessage.from_value(old))
        at = get_row(state['attempts'], 'battle_id', p['battle_id'])
        need(at is not None, 'E_MISSING_ADMISSION'); a = at['admission']
        need(at['admission_sha256'] == p['admission_sha256'], 'E_CONTROL_BINDING')
        original = validate_dto(p['superseded_result'], 'BattleResult'); r = original.value
        need((r['battle_id'], r['stage_id'], r['profile_scope'], r['outcome'], r['rules_version'], r['content_version']) ==
             (a['battle_id'], a['stage_id'], a['player_save_scope_id'], 'WIN', a['battle_rules_version'], a['battle_content_version']), 'E_CONTROL_RESULT_BINDING')
        need(p['new_revision'] > max(at['high_revision'], r['terminal_revision']), 'E_STALE_CONTROL')
        need(at['status'] not in ('ABORTED', 'FAULTED', 'REVOKED'), 'E_CLOSED_ATTEMPT')
        if at['terminal']:
            need(at['terminal']['result_sha256'] == original.sha256, 'E_CONTROL_RESULT_BINDING')
            at['status'] = 'REVIEW_REQUIRED'
            get_row(state['stages'], 'stage_id', a['stage_id'])['review_required'] = True
            decision = 'REVIEW_HOLD'
        else:
            at['status'] = 'REVOKED'; decision = 'REVOKED_PENDING'
        at['high_revision'] = p['new_revision']
        at['closure'] = {'kind': 'REVOKED', 'evidence_sha256': proof.sha256,
                         'revision': p['new_revision'], 'evidence': p}
        if state['active_battle_id'] == at['battle_id']: state['active_battle_id'] = None
        state['controls'].append({'control_ref': p['control_ref'], 'evidence_sha256': proof.sha256,
                                  'evidence': p, 'decision': decision})
        evidence.append(_binding('REVOCATION', p['control_ref'], proof))
        return decision

    def validate_for_commit(self, candidate, current_snapshot):
        need(type(candidate) is FrozenMessage, 'E_CANDIDATE_TYPE')
        c = candidate.value
        shape(c, 'schema_version request request_sha256 before_sha256 after_sha256 after_state decision grant new_first_clear_keys battle_parameters evidence_bindings commit_scope')
        need(c['schema_version'] == CANDIDATE_VERSION, 'E_CANDIDATE_VERSION')
        req = FrozenMessage.from_value(c['request'])
        need(req.sha256 == c['request_sha256'], 'E_CANDIDATE_REQUEST_HASH')
        result = self.plan(req, current_snapshot)
        if result.status == 'DUPLICATE_NO_OP': return result
        need(result.status == 'CANDIDATE', result.reason)
        need(result.candidate.raw == candidate.raw, 'E_CANDIDATE_RECOMPUTE_MISMATCH')
        return result

    def resume(self, snapshot, battle_id):
        state = validate_state(snapshot, self.catalog); check_store_fence(snapshot, self.authority)
        ident(battle_id); at = get_row(state['attempts'], 'battle_id', battle_id)
        need(at is not None and state['active_battle_id'] == battle_id, 'E_NO_ACTIVE_BATTLE')
        need(at['status'] == 'ACTIVE', 'E_PENDING_RECONCILIATION')
        need(self.catalogs.resolve(at['admission']['catalog_sha256']) is not None, 'E_PINNED_CONTENT_MISSING')
        proof = self._battle_evidence(at)
        need(proof.value['result'] is None and proof.value['snapshot']['phase'] not in ('ABORTED', 'FAULTED', 'TERMINAL'), 'E_TERMINAL_REQUIRES_SETTLEMENT')
        return FrozenMessage.from_value({'schema_version': 'P18-RESUME/0.1.0-proposal',
            'admission': at['admission'], 'admission_sha256': at['admission_sha256'],
            'battle_snapshot': proof.value['snapshot'], 'scope': 'READ_ONLY_NO_NEW_ATTEMPT'})

    def lookup_terminal(self, snapshot, battle_id):
        state = validate_state(snapshot, self.catalog); check_store_fence(snapshot, self.authority)
        ident(battle_id); at = get_row(state['attempts'], 'battle_id', battle_id)
        return None if at is None or at['terminal'] is None else FrozenMessage.from_value(at['terminal'])
