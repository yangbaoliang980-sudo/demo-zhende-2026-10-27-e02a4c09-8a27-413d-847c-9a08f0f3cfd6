"""P11-SIMULATORS/0.1.0: pure synthetic P08/P10/P17 collaborators.

The single test unit and Q=10 come from P08-MATH-A01..A08, not four-button
award values. This file has no production role and accepts only fixture scopes.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from ledger_runtime.audit import check_accounting
from ledger_runtime.types import (Admission, Event, LOCAL_EVENT_VERSION, PolicyDecision,
                                  Resolution, WalletDelta, WalletHold, canonical, digest,
                                  strict_json, byte_digest)

UNIT = 'SYNTHETIC_SINGLE_UNIT'
Q = 10  # P08's supplied arithmetic fixture, never a rating policy.


def event(event_id='review-1', *, family_id='family-1', kind='REVIEW', revision=0,
          predecessor=None, rating='Good', epoch='fixture:epoch-1', card='fixture:card-1',
          source='fixture:source', beneficiary='fixture:player'):
    return {'schema_version': LOCAL_EVENT_VERSION, 'source_id': source,
            'collection_lineage': 'fixture:lineage', 'collection_epoch': epoch,
            'beneficiary_id': beneficiary, 'event_id': event_id, 'family_id': family_id,
            'kind': kind, 'revision': revision, 'predecessor_event_id': predecessor,
            'rating': rating if kind == 'REVIEW' else None,
            'card_reference': card, 'source_evidence_sha256': digest(['synthetic-proof', event_id])}


def control(kind, event_id, predecessor, revision, family_id='family-1', **kw):
    return event(event_id, family_id=family_id, kind=kind, predecessor=predecessor,
                 revision=revision, **kw)


class FixtureEvidence:
    def __init__(self):
        self.blocked = set()
        self.unverified_epochs = set()
        self.resolutions = {}

    def assess(self, value, supplemental_ref=None):
        if (not value.source_id.startswith('fixture:') or not value.collection_lineage.startswith('fixture:') or
                not value.beneficiary_id.startswith('fixture:') or
                value.source_evidence_sha256 != digest(['synthetic-proof', value.event_id])):
            return Admission(reason='NOT_REGISTERED_SYNTHETIC_EVIDENCE')
        if value.event_id in self.blocked:
            return Admission(reason='SYNTHETIC_CAPABILITY_WITHHELD')
        if value.collection_epoch in self.unverified_epochs:
            return Admission(reason='SYNTHETIC_EPOCH_UNVERIFIED')
        return Admission(True, True, True, True, True, 'fixture:admission:' + value.fingerprint,
                         'SYNTHETIC_EVIDENCE_ONLY')

    def grant(self, row, ref, action='REPROCESS', target=None):
        value = Resolution(ref, row['input_sha256'], row['case_version'], action,
                           'SYNTHETIC_TEST_AUTHORITY', digest([ref, row['input_sha256'], action]), target)
        self.resolutions[ref] = value
        return value

    def resolve(self, evidence_ref, input_sha256, case_version, action):
        value = self.resolutions.get(evidence_ref)
        if value and (value.input_sha256, value.case_version, value.action) == (input_sha256, case_version, action):
            return value
        return None


class FixturePolicy:
    def __init__(self):
        self.available = True
        self.mapping_available = True
        self.category = 'UNKNOWN'
        self.reclaim = True
        self.restore = True
        self.version = 'P11-SYNTHETIC-MATH-POLICY/0.1.0'
        self.reward_day = 'fixture:original-reward-day'
        self.entitlement = {UNIT: Q}
        self.calls = 0
        path = Path(__file__).resolve().parents[2] / 'sources/P08/compensation_arithmetic_cases.json'
        source = path.read_bytes()
        self.source_sha = byte_digest(source)
        data = strict_json(source)
        first = next(x for x in data['cases'] if x['case_id'] == 'P08-MATH-A01')
        if first['values']['G'] != Q or first['resource_unit'] != UNIT:
            raise ValueError('P08_MATH_FIXTURE_BINDING_CHANGED')

    def decide(self, original_review, resolution_ref=None):
        self.calls += 1
        if not self.available:
            return PolicyDecision(False, 'SYNTHETIC_POLICY_WITHHELD')
        if not self.mapping_available:
            return PolicyDecision(False, 'MISSING_MAPPING_IS_NOT_UNKNOWN')
        if not original_review.source_id.startswith('fixture:'):
            return PolicyDecision(False, 'SIMULATION_POLICY_REJECTS_REAL_INPUT')
        return PolicyDecision(True, 'HYPOTHETICAL_MATH_AUTHORIZATION_ONLY', {
            'version': self.version, 'approval_ref': 'fixture:NOT_USER_APPROVAL',
            'source_sha256': self.source_sha, 'mapping_version': 'fixture:mapping-v1',
            'mapping_sha256': digest('fixture:mapping-v1'), 'category': self.category,
            'reward_day': self.reward_day, 'reward_day_rule': 'fixture:supplied-original-day',
            'entitlement': deepcopy(self.entitlement), 'budget_ref': 'fixture:budget',
            'reclaim_unspent': self.reclaim, 'restore_allowed': self.restore,
            'scope': list(original_review.scope), 'evidence_scope': 'ISOLATED_SYNTHETIC_ARITHMETIC'})


class FixtureWallet:
    def __init__(self):
        self.calls = 0
        self.forced_hold = None

    def compute(self, intent, wallet):
        self.calls += 1
        if self.forced_hold:
            return WalletHold(self.forced_hold)
        if intent.policy_snapshot['evidence_scope'] != 'ISOLATED_SYNTHETIC_ARITHMETIC':
            return WalletHold('SIMULATOR_REJECTS_NON_SYNTHETIC_POLICY')
        before = wallet['sources'].get(intent.family_key)
        if before and not before.get('attribution_known'):
            return WalletHold('SOURCE_SPEND_ATTRIBUTION_UNKNOWN')
        after = deepcopy(before) if before else {'attribution_known': True, 'units': {},
                                                 'policy_sha256': digest(intent.policy_snapshot)}
        if before and before['policy_sha256'] != digest(intent.policy_snapshot):
            return WalletHold('HISTORICAL_POLICY_MISMATCH')
        changes = {}
        unresolved = False
        for unit, q in intent.policy_snapshot['entitlement'].items():
            old = after['units'].get(unit, {k: 0 for k in ('G','R','S','A','T','U','K','M')})
            if old['K']:
                return WalletHold('WAIVER_RECLASSIFICATION_REQUIRES_APPROVED_RFC')
            values = dict(old)
            net = old['G'] - old['R']
            if intent.desired_active:
                if net > q:
                    return WalletHold('TARGET_LOWER_THAN_RETAINED_REQUIRES_REVIEW')
                amount = q - net
                values['G'] += amount
                values['A'] += amount
                values['T'], values['U'], values['M'] = q, 0, 0
            else:
                amount = -old['A'] if intent.policy_snapshot['reclaim_unspent'] else 0
                values['R'] -= amount
                values['A'] += amount
                values['T'], values['M'] = 0, 0
                values['U'] = values['G'] - values['R']
            changes[unit] = amount
            after['units'][unit] = values
            check_accounting(values)
            unresolved |= bool(values['U'] or values['M'])
        return WalletDelta(intent.fingerprint, intent.family_key, wallet['version'], digest(wallet),
                           changes, after, unresolved,
                           'UNRESOLVED_EXPOSURE_IS_NOT_DEBT' if unresolved else 'SIMULATED_NET_TARGET_COMMITTED',
                           digest(intent.policy_snapshot))
