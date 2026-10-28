"""Auditable chains and economic conservation checks; never computes an award."""
from .types import HASH_ZERO, PortViolation, WalletDelta, digest


def append_audit(ledger, transaction_id, action, input_id, details):
    previous = ledger['audit'][-1]['sha256'] if ledger['audit'] else HASH_ZERO
    entry = {'sequence': len(ledger['audit']) + 1, 'previous_sha256': previous,
             'transaction_id': transaction_id, 'action': action, 'inbox_id': input_id,
             'details': details}
    entry['sha256'] = digest(entry)
    ledger['audit'].append(entry)


def verify_audit(ledger):
    previous = HASH_ZERO
    for i, original in enumerate(ledger['audit'], 1):
        entry = dict(original)
        claimed = entry.pop('sha256')
        if entry['sequence'] != i or entry['previous_sha256'] != previous or digest(entry) != claimed:
            raise PortViolation('AUDIT_CHAIN_INVALID')
        previous = claimed
    return previous


def check_accounting(values):
    if set(values) != {'G', 'R', 'S', 'A', 'T', 'U', 'K', 'M'}:
        raise PortViolation('ACCOUNTING_FIELDS_INVALID')
    if any(type(v) is not int or v < 0 for v in values.values()):
        raise PortViolation('ACCOUNTING_NONNEGATIVE_INTEGER_REQUIRED')
    g, r, s, a, t, u, k, m = (values[x] for x in ('G','R','S','A','T','U','K','M'))
    if a + s != g - r or g - r + m != t + u + k or (u > 0 and m > 0):
        raise PortViolation('ACCOUNTING_CONSERVATION_FAILED')


def validate_delta(delta: WalletDelta, intent, wallet):
    if (delta.intent_sha256 != intent.fingerprint or delta.family_key != intent.family_key or
            delta.expected_wallet_version != wallet['version'] or
            delta.wallet_before_sha256 != digest(wallet) or
            delta.policy_sha256 != digest(intent.policy_snapshot)):
        raise PortViolation('WALLET_DELTA_BINDING_MISMATCH')
    if type(delta.unresolved) is not bool:
        raise PortViolation('WALLET_DELTA_OUTCOME_INVALID')
    before = wallet['sources'].get(intent.family_key, {})
    if before and before.get('attribution_known') is not True:
        raise PortViolation('PRIOR_SOURCE_ATTRIBUTION_REQUIRES_P17_RECONCILIATION')
    if delta.source_after.get('attribution_known') is not True:
        raise PortViolation('SOURCE_ATTRIBUTION_REQUIRED_FOR_DELTA')
    if delta.source_after.get('policy_sha256') != digest(intent.policy_snapshot):
        raise PortViolation('SOURCE_POLICY_BINDING_MISMATCH')
    old_units = before.get('units', {})
    new_units = delta.source_after.get('units', {})
    allowed = intent.policy_snapshot['entitlement']
    if set(new_units) != set(allowed) or set(delta.changes) - set(allowed):
        raise PortViolation('UNAPPROVED_RESOURCE_CHANGE')
    exposure = False
    for unit, new in new_units.items():
        check_accounting(new)
        old = old_units.get(unit, {k: 0 for k in ('G','R','S','A','T','U','K','M')})
        amount = delta.changes.get(unit, 0)
        if type(amount) is not int or wallet['balances'].get(unit, 0) + amount < 0:
            raise PortViolation('NEGATIVE_WALLET_OR_NONINTEGER_DELTA')
        if new['S'] != old['S'] or new['K'] != old['K']:
            raise PortViolation('SPEND_OR_WAIVER_CANNOT_BE_INTRODUCED_BY_P11_OPERATION')
        if new['G'] < old['G'] or new['R'] < old['R']:
            raise PortViolation('AUDIT_COUNTER_CANNOT_DECREASE')
        if amount != (new['G'] - old['G']) - (new['R'] - old['R']):
            raise PortViolation('DELTA_COUNTER_MISMATCH')
        if new['G'] - old['G'] != max(amount, 0) or new['R'] - old['R'] != max(-amount, 0):
            raise PortViolation('HIDDEN_OFFSETTING_CREDIT_AND_RECLAIM')
        if amount != new['A'] - old['A']:
            raise PortViolation('SOURCE_DELTA_MISMATCH')
        if new['T'] != (allowed[unit] if intent.desired_active else 0):
            raise PortViolation('TARGET_ENTITLEMENT_MISMATCH')
        if amount > 0 and (not intent.desired_active or new['G'] - new['R'] > allowed[unit]):
            raise PortViolation('EXCESS_ENTITLEMENT')
        if amount < 0 and (intent.desired_active or -amount > old['A'] or
                           intent.policy_snapshot.get('reclaim_unspent') is not True):
            raise PortViolation('UNAUTHORIZED_RECLAIM')
        exposure |= bool(new['U'] or new['M'])
    if delta.unresolved != exposure:
        raise PortViolation('UNRESOLVED_FLAG_MISMATCH')


def validate_policy(snapshot):
    required = {'version','approval_ref','source_sha256','mapping_version','mapping_sha256',
                'category','reward_day','reward_day_rule','entitlement','budget_ref',
                'reclaim_unspent','restore_allowed','scope','evidence_scope'}
    if not isinstance(snapshot, dict) or set(snapshot) != required:
        raise PortViolation('POLICY_SNAPSHOT_INCOMPLETE')
    for field in required - {'entitlement','reclaim_unspent','restore_allowed','scope'}:
        if not isinstance(snapshot[field], str) or not snapshot[field]:
            raise PortViolation('POLICY_SNAPSHOT_MISSING_BINDING')
    if type(snapshot['reclaim_unspent']) is not bool or type(snapshot['restore_allowed']) is not bool:
        raise PortViolation('POLICY_CAPABILITY_MISSING')
    for field in ('source_sha256', 'mapping_sha256'):
        if len(snapshot[field]) != 64 or any(c not in '0123456789abcdef' for c in snapshot[field]):
            raise PortViolation('POLICY_HASH_BINDING_INVALID')
    if not isinstance(snapshot['entitlement'], dict) or any(
            not isinstance(k, str) or not k or type(v) is not int or v < 0
            for k, v in snapshot['entitlement'].items()):
        raise PortViolation('APPROVED_ENTITLEMENT_REQUIRED')
