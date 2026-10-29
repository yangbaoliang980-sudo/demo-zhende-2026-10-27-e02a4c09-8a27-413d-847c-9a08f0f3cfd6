"""Prepare and revalidate a joint P18/P17 proposal; P21 alone may persist it.

The composite envelope is an RFC proposal. The P13 projection is validated
against the unchanged original schema. No durable success proof is minted.
"""
from .common import (FrozenMessage, PlanResult, INTERNAL_VERSION, need, shape,
                     fingerprint, validate_dto)


def _check_wallet_candidate(grant, candidate, snapshot, stage_state, wallet_port):
    need(type(candidate) is FrozenMessage and type(snapshot) is FrozenMessage, 'E_WALLET_CANDIDATE_TYPE')
    c, m = candidate.value, snapshot.value
    # P17's own validator owns its complete state and arithmetic.
    wallet_port.validate(grant, candidate, snapshot)
    need(c['schema_version'] == 'P17-CANDIDATE/0.1.0-isolated', 'E_WALLET_CANDIDATE_VERSION')
    need(c['required_counterpart_owner'] == 'P18', 'E_COUNTERPART_OWNER')
    need(c['before_sha256'] == snapshot.sha256, 'E_META_BEFORE_HASH')
    need(c['evidence_binding'] == {'reference': grant.value['grant_ref'], 'sha256': grant.sha256}, 'E_GRANT_BINDING')
    need(c['request']['kind'] == 'APPLY_GRANT' and c['request']['payload'] == {'grant_ref': grant.value['grant_ref']}, 'E_META_OPERATION_BINDING')
    need((m['profile_id'], m['store_instance'], m['continuity_ref']) ==
         (stage_state['player_save_scope_id'], stage_state['store_instance'], stage_state['continuity_ref']), 'E_META_SCOPE_FENCE')
    delta = validate_dto(c['wallet_delta'], 'WalletDeltaCandidate')
    need(delta.value['beneficiary_id'] == stage_state['player_save_scope_id'] and
         delta.value['expected_wallet_revision'] == m['wallet_revision'], 'E_WALLET_REVISION_FENCE')
    return delta


def prepare_atomic(planner, stage_candidate, stage_snapshot, meta_snapshot=None, wallet_port=None):
    result = planner.validate_for_commit(stage_candidate, stage_snapshot)
    if result.status == 'DUPLICATE_NO_OP': return result
    c = stage_candidate.value; state = stage_snapshot.value
    wallet_candidate = None; delta = None
    if c['grant'] is not None:
        need(wallet_port is not None and meta_snapshot is not None, 'E_P17_PORT_UNBOUND')
        grant = FrozenMessage.from_value(c['grant'])
        wallet_candidate = wallet_port.propose(grant, meta_snapshot)
        delta = _check_wallet_candidate(grant, wallet_candidate, meta_snapshot, state, wallet_port)
    body = FrozenMessage.from_value({'schema_version': 'P18-JOINT-BODY/0.1.0-proposal',
        'stage_candidate': c,
        'wallet_character_candidate': None if wallet_candidate is None else wallet_candidate.value,
        'expected_meta_sha256': None if wallet_candidate is None else meta_snapshot.sha256,
        'receipt_publication': 'ONLY_AFTER_P21_DURABLE_ATOMIC_COMMIT',
        'required_atomic_owners': ['P18', 'P17'] if wallet_candidate is not None else ['P18']})
    projection = validate_dto({'contract_version': INTERNAL_VERSION, 'dto_type': 'AtomicCommitProposal',
        'transaction_id': 'p18.tx.' + fingerprint([state['player_save_scope_id'], c['request']['request_id']]),
        'request_sha256': c['request_sha256'], 'transaction_kind': 'STAGE_PROGRESS_WALLET',
        'domain_candidate_sha256': body.sha256, 'wallet_candidate': None if delta is None else delta.value,
        'expected_domain_revision': state['revision'], 'expected_store_instance': state['store_instance']}, 'AtomicCommitProposal')
    return FrozenMessage.from_value({'schema_version': 'P18-ATOMIC-BUNDLE/0.1.0-proposal',
        'body': body.value, 'body_sha256': body.sha256, 'p13_projection': projection.value,
        'contract_acceptance': 'PREPARED_NOT_ACCEPTED', 'durable': False})


def validate_atomic(bundle, planner, stage_snapshot, meta_snapshot=None, wallet_port=None):
    need(type(bundle) is FrozenMessage, 'E_BUNDLE_TYPE')
    b = bundle.value
    shape(b, 'schema_version body body_sha256 p13_projection contract_acceptance durable')
    need(b['schema_version'] == 'P18-ATOMIC-BUNDLE/0.1.0-proposal', 'E_BUNDLE_VERSION')
    need(b['durable'] is False and b['contract_acceptance'] == 'PREPARED_NOT_ACCEPTED', 'E_FALSE_DURABLE_CLAIM')
    need(fingerprint(b['body']) == b['body_sha256'], 'E_BUNDLE_BODY_HASH')
    p = validate_dto(b['p13_projection'], 'AtomicCommitProposal')
    need(p.value['domain_candidate_sha256'] == b['body_sha256'], 'E_PROJECTION_BODY_HASH')
    shape(b['body'], 'schema_version stage_candidate wallet_character_candidate expected_meta_sha256 receipt_publication required_atomic_owners')
    proposed = prepare_atomic(planner, FrozenMessage.from_value(b['body']['stage_candidate']),
                              stage_snapshot, meta_snapshot, wallet_port)
    if isinstance(proposed, PlanResult): return proposed
    need(proposed.raw == bundle.raw, 'E_JOINT_RECOMPUTE_MISMATCH')
    return PlanResult('CANDIDATE', 'VALIDATED_NOT_COMMITTED', candidate=bundle)

