"""StudyLedger business owner. All durable writes are delegated to AtomicStore.

Delivery, fact admission, reward authorization, wallet calculation and atomic
commit are separate steps. None of the ports in this package is a production
adapter. Receipt lookups, including duplicates, never re-run economic policy.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .audit import append_audit, validate_delta, validate_policy, verify_audit
from .ports import ClosedEvidence, ClosedPolicy
from .types import (MAX_INPUT_BYTES, CommitUnknown, Event, LedgerStatus as S, Mutation,
                    Outcome, PortViolation, RewardIntent, WalletDelta, WalletHold, byte_digest,
                    canonical, digest, encoded_raw)


class StudyLedger:
    def __init__(self, store, wallet, evidence=None, policy=None):
        self.store = store
        self.wallet = wallet
        self.evidence = evidence or ClosedEvidence()
        self.policy = policy or ClosedPolicy()

    def _verify_receipt(self, receipt, tx, request_hash):
        if (receipt is None or not receipt.durable or receipt.transaction_id != tx or
                receipt.request_sha256 != request_hash or type(receipt.sequence) is not int or
                receipt.sequence <= 0 or receipt.store_instance != self.store.snapshot().store_instance or
                receipt.origin not in ('P21_PRODUCTION', 'P21_SIMULATOR')):
            raise PortViolation('INVALID_COMMIT_RECEIPT')
        return receipt

    def _commit(self, tx, request_hash, decide):
        found = self.store.lookup(tx)
        if found.status == 'UNKNOWN':
            raise CommitUnknown('AUTHORITATIVE_LOOKUP_UNAVAILABLE')
        if found.status == 'COMMITTED':
            return self._verify_receipt(found.receipt, tx, request_hash)
        if found.status != 'ABSENT':
            raise PortViolation('INVALID_LOOKUP_STATUS')
        try:
            receipt = self.store.execute_once(tx, request_hash, decide)
            self._verify_receipt(receipt, tx, request_hash)
        except CommitUnknown:
            pass
        # No success ACK solely from an RPC return; resolve the authoritative durable receipt.
        found = self.store.lookup(tx)
        if found.status != 'COMMITTED':
            raise CommitUnknown('COMMIT_RESULT_NOT_CONFIRMED')
        return self._verify_receipt(found.receipt, tx, request_hash)

    @staticmethod
    def _uncertain(inbox_id, reason):
        return Outcome(inbox_id, S.PENDING_RECONCILIATION, reason, None, None)

    def receive(self, raw: bytes):
        if not isinstance(raw, bytes):
            raise TypeError('receive requires bytes')
        if len(raw) > MAX_INPUT_BYTES:
            return Outcome(None, S.REJECTED, 'INPUT_LIMIT_NO_DURABLE_RECEIPT', None, None)
        try:
            event = Event.parse(raw)
            inbox_id = event.fingerprint
            parse_error = None
        except (ValueError, UnicodeError, RecursionError) as exc:
            event, inbox_id, parse_error = None, byte_digest(raw), type(exc).__name__
        tx = 'receive:' + inbox_id
        request_hash = digest(['receive-v1', inbox_id])

        def decide(snapshot):
            ledger = deepcopy(snapshot.ledger)
            if inbox_id not in ledger['inbox']:
                state = S.REJECTED if event is None else S.PENDING_RECONCILIATION
                reason = 'MALFORMED_OR_UNSUPPORTED_LOCAL_DTO' if event is None else 'DURABLE_RECEIVED_NOT_AWARDED'
                row = {'input_sha256': inbox_id, 'raw_sha256': byte_digest(raw),
                       'first_raw_base64': encoded_raw(raw), 'event': asdict(event) if event else None,
                       'state': state.value, 'reason': reason, 'case_version': 0, 'history': [],
                       'processed': event is None, 'follow_family': False, 'family_key': None,
                       'last_commit': {'transaction_id': tx, 'request_sha256': request_hash},
                       'parse_error_type': parse_error}
                ledger['inbox'][inbox_id] = row
                ledger['case_index'][state.value].append(inbox_id)
                append_audit(ledger, tx, 'DURABLE_RECEIVE', inbox_id,
                             {'raw_sha256': row['raw_sha256'], 'state': state.value, 'reason': reason})
            return Mutation(ledger)

        try:
            self._commit(tx, request_hash, decide)
            return self.query(inbox_id, received_only=True)
        except (CommitUnknown, PortViolation) as exc:
            return self._uncertain(inbox_id, str(exc))

    def handle(self, raw: bytes):
        received = self.receive(raw)
        if received.receipt is None or received.inbox_id is None:
            return received
        return self.process(received.inbox_id)

    def process(self, inbox_id):
        row = self.store.snapshot().ledger['inbox'].get(inbox_id)
        if row is None:
            return self._uncertain(inbox_id, 'INBOX_NOT_DURABLY_RECEIVED')
        if row['processed']:
            return self.query(inbox_id, duplicate=True)
        tx = 'process:' + inbox_id
        req = digest(['process-v1', inbox_id])
        try:
            self._commit(tx, req, lambda snap: self._decide(snap, inbox_id, tx, req))
            return self.query(inbox_id)
        except (CommitUnknown, PortViolation) as exc:
            return self._uncertain(inbox_id, str(exc))

    def resolve(self, inbox_id, evidence_ref, action='REPROCESS'):
        if action not in ('REPROCESS', 'LINK_DUPLICATE', 'REJECT'):
            return self._uncertain(inbox_id, 'UNSUPPORTED_RESOLUTION_ACTION')
        tx = 'resolve:' + digest([inbox_id, evidence_ref, action])
        req = digest(['resolve-v1', inbox_id, evidence_ref, action])
        found = self.store.lookup(tx)
        if found.status == 'COMMITTED':
            try:
                self._verify_receipt(found.receipt, tx, req)
                return self.query(inbox_id, duplicate=True)
            except PortViolation as exc:
                return self._uncertain(inbox_id, str(exc))
        if found.status == 'UNKNOWN':
            return self._uncertain(inbox_id, 'RESOLUTION_RESULT_UNKNOWN')
        initial = self.store.snapshot().ledger['inbox'].get(inbox_id)
        if initial is None:
            return self._uncertain(inbox_id, 'UNKNOWN_CASE')
        grant = self.evidence.resolve(evidence_ref, inbox_id, initial['case_version'], action)
        if grant is None:
            return self._uncertain(inbox_id, 'NEW_BOUND_RESOLUTION_EVIDENCE_REQUIRED')

        def decide(snapshot):
            row = snapshot.ledger['inbox'][inbox_id]
            if (grant.input_sha256 != inbox_id or grant.case_version != row['case_version'] or
                    grant.action != action or grant.evidence_ref != evidence_ref or
                    not grant.proof_sha256 or not grant.issuer):
                raise PortViolation('RESOLUTION_BINDING_OR_VERSION_MISMATCH')
            if row['state'] not in (S.QUARANTINED, S.PENDING_RECONCILIATION, S.REJECTED):
                raise PortViolation('SETTLED_CASE_CANNOT_BE_ADMIN_REWRITTEN')
            if any(x.get('evidence_ref') == evidence_ref for x in row['history']):
                raise PortViolation('RESOLUTION_REQUIRES_NEW_EVIDENCE')
            ledger = deepcopy(snapshot.ledger)
            append_audit(ledger, tx, 'RESOLUTION_EVIDENCE_ATTACHED', inbox_id, asdict(grant))
            if action == 'REJECT':
                # Reject the case only. Never delete/reject already granted economic rights.
                if any(op['inbox_id'] == inbox_id for op in ledger['operations'].values()):
                    raise PortViolation('ECONOMIC_OPERATION_CANNOT_BE_ADMIN_REJECTED')
                family = ledger['families'].get(row.get('family_key')) if row.get('follow_family') else None
                if family is not None:
                    if any(op['family_key'] == family['family_key'] for op in ledger['operations'].values()):
                        raise PortViolation('ACTIVE_FAMILY_CANNOT_BE_ADMIN_REJECTED')
                    family['rejected_by_case'] = inbox_id
                return self._finish(ledger, inbox_id, tx, req, S.REJECTED,
                                    'REJECTED_BY_BOUND_EVIDENCE', family=family, resolution=grant)
            if action == 'LINK_DUPLICATE':
                target = ledger['inbox'].get(grant.target_inbox_id)
                if target is None or not target.get('follow_family'):
                    raise PortViolation('PROVEN_DUPLICATE_TARGET_REQUIRED')
                family = ledger['families'].get(target['family_key'])
                if family is None:
                    raise PortViolation('DUPLICATE_TARGET_NOT_RESOLVED')
                if (row['event'] is None or target['event'] is None or
                        Event(**row['event']).scope != Event(**target['event']).scope):
                    raise PortViolation('DUPLICATE_LINK_SCOPE_MISMATCH')
                # EvidencePort must prove the cross-epoch alias. No new wallet intent.
                ledger['inbox'][inbox_id]['linked_to'] = grant.target_inbox_id
                return self._finish(ledger, inbox_id, tx, req, S(family['state']),
                                    'PROVEN_DUPLICATE_LINKED_WITHOUT_AWARD', family=family,
                                    resolution=grant)
            revised = type(snapshot)(ledger, snapshot.wallet, snapshot.continuity_verified,
                                     snapshot.continuity_ref, snapshot.store_instance, snapshot.high_watermark)
            return self._decide(revised, inbox_id, tx, req, resolution=grant)

        try:
            self._commit(tx, req, decide)
            return self.query(inbox_id)
        except (CommitUnknown, PortViolation) as exc:
            return self._uncertain(inbox_id, str(exc))

    def _finish(self, ledger, inbox_id, tx, req, state, reason, family=None,
                wallet_delta=None, resolution=None, terminal_event=None, details=None):
        row = ledger['inbox'][inbox_id]
        old = row['state']
        ledger['case_index'][old] = [x for x in ledger['case_index'][old] if x != inbox_id]
        if inbox_id not in ledger['case_index'][state.value]:
            ledger['case_index'][state.value].append(inbox_id)
        ref = {'transaction_id': tx, 'request_sha256': req}
        row.update(state=state.value, reason=reason, processed=True,
                   case_version=row['case_version']+1, last_commit=ref)
        row['follow_family'] = False
        row['history'].append({'version': row['case_version'], 'from': old, 'to': state.value,
                               'reason': reason, 'transaction_id': tx,
                               'evidence_ref': resolution.evidence_ref if resolution else None})
        if family is not None:
            family['state'] = state.value
            family['last_commit'] = ref
            ledger['families'][family['family_key']] = family
            row['family_key'] = family['family_key']
            row['follow_family'] = True
        if terminal_event is not None:
            ledger['operations'][terminal_event.operation_key] = {
                'inbox_id': inbox_id, 'fingerprint': terminal_event.fingerprint,
                'family_key': terminal_event.family_key, 'kind': terminal_event.kind,
                'revision': terminal_event.revision, 'atomic_commit': ref,
                'reward_transaction_id': 'reward:' + terminal_event.operation_key,
                'wallet_changed': wallet_delta is not None}
        append_audit(ledger, tx, 'LEDGER_DECISION', inbox_id,
                     {'from': old, 'to': state.value, 'reason': reason,
                      'family_key': row['family_key'],
                      'wallet_delta': asdict(wallet_delta) if wallet_delta else None,
                      **(details or {})})
        return Mutation(ledger, wallet_delta)

    @staticmethod
    def _new_family(event, base_event_id, original=None):
        return {'family_key': event.family_key, 'scope': list(event.scope),
                'epoch': event.collection_epoch, 'base_event_id': base_event_id,
                'original_review': asdict(original) if original else None,
                'head_event_id': event.event_id, 'head_revision': event.revision,
                'desired_active': event.kind != 'UNDO', 'policy_snapshot': None,
                'authorization_key': 'entitlement:' + event.family_key,
                'state': S.PENDING_RECONCILIATION.value, 'last_commit': None}

    def _decide(self, snapshot, inbox_id, tx, req, resolution=None):
        ledger = deepcopy(snapshot.ledger)
        row = ledger['inbox'][inbox_id]
        finish = lambda state, reason, **kw: self._finish(
            ledger, inbox_id, tx, req, state, reason, resolution=resolution, **kw)
        if row['event'] is None:
            return finish(S.REJECTED, 'MALFORMED_INPUT_CANNOT_BE_PROMOTED')
        event = Event(**row['event'])
        admission = self.evidence.assess(event, resolution.evidence_ref if resolution else None)
        if not event.event_id or not event.family_id:
            return finish(S.QUARANTINED, 'MISSING_PROVEN_IDENTITY_FIELDS')
        if not admission.sufficient:
            return finish(S.QUARANTINED, admission.reason)
        existing_claim = ledger['claims'].get(event.operation_key)
        if existing_claim and existing_claim['fingerprint'] != event.fingerprint:
            row['conflict_with'] = existing_claim['inbox_id']
            row['follow_family'] = False
            return finish(S.QUARANTINED, 'SAME_IDENTITY_DIFFERENT_PAYLOAD',
                          details={'original_input_sha256': existing_claim['fingerprint'],
                                   'incoming_input_sha256': event.fingerprint})
        ledger['claims'].setdefault(event.operation_key,
                                   {'fingerprint': event.fingerprint, 'inbox_id': inbox_id})
        family = ledger['families'].get(event.family_key)
        if not snapshot.continuity_verified:
            return finish(S.PENDING_RECONCILIATION, 'P21_RESTORE_CONTINUITY_NOT_PROVEN')
        if event.operation_key in ledger['operations']:
            if family is None:
                return finish(S.PENDING_RECONCILIATION, 'OPERATION_WITHOUT_FAMILY_RECONCILE')
            # Already committed operation: never recompute it, even after policy changes.
            return finish(S(family['state']), 'EXISTING_OPERATION_NO_NEW_WALLET_DELTA', family=family)
        if family is not None and family['epoch'] != event.collection_epoch:
            row['follow_family'] = False
            return finish(S.QUARANTINED, 'CROSS_COLLECTION_EPOCH_REQUIRES_RECONCILIATION')
        if family is not None and family.get('rejected_by_case'):
            if resolution and family['rejected_by_case'] == inbox_id:
                del family['rejected_by_case']
            else:
                return finish(S.QUARANTINED, 'REJECTED_ORIGINAL_REQUIRES_BOUND_REVIEW')

        if event.kind == 'REVIEW':
            if family is None:
                family = self._new_family(event, event.event_id, event)
            elif family['base_event_id'] != event.event_id:
                row['follow_family'] = False
                return finish(S.QUARANTINED, 'DIFFERENT_REVIEW_CANNOT_REUSE_FAMILY')
            else:
                family['original_review'] = family['original_review'] or asdict(event)
                if family['head_revision'] > 0:
                    if not family['desired_active']:
                        return finish(S(family['state']), 'LATE_ORIGINAL_SUPPRESSED_BY_UNDO',
                                      family=family, terminal_event=event)
                    return finish(S(family['state']), 'ORIGINAL_ATTACHED_RETRY_PENDING_RESTORE', family=family)
        else:
            if family is None:
                if event.kind == 'UNDO' and event.revision == 1:
                    family = self._new_family(event, event.predecessor_event_id)
                    return finish(S.REVERTED, 'UNDO_TOMBSTONE_NO_ECONOMIC_EFFECT',
                                  family=family, terminal_event=event)
                return finish(S.PENDING_RECONCILIATION, 'MISSING_CAUSAL_PREDECESSOR')
            if family['head_event_id'] != event.event_id:
                if event.revision > family['head_revision']+1:
                    return finish(S.PENDING_RECONCILIATION, 'MISSING_CAUSAL_PREDECESSOR')
                if (event.revision != family['head_revision']+1 or
                        event.predecessor_event_id != family['head_event_id']):
                    return finish(S.QUARANTINED, 'STALE_OR_CONFLICTING_CAUSAL_LINK')
                if (event.kind == 'UNDO' and not family['desired_active']) or (
                        event.kind == 'RESTORE' and family['desired_active']):
                    return finish(S.QUARANTINED, 'INVALID_FACT_TRANSITION')
                family.update(head_event_id=event.event_id, head_revision=event.revision,
                              desired_active=event.kind == 'RESTORE')
            if family['original_review'] is None:
                return finish(S.PENDING_RECONCILIATION, 'ORIGINAL_REVIEW_EVIDENCE_REQUIRED', family=family)

        policy = family['policy_snapshot']
        if policy is None:
            if not family['desired_active']:
                return finish(S.REVERTED, 'UNAWARDED_FACT_REVERTED_WITHOUT_DEBIT',
                              family=family, terminal_event=event)
            decision = self.policy.decide(Event(**family['original_review']),
                                          resolution.evidence_ref if resolution else None)
            if not decision.eligible:
                return finish(S.QUARANTINED, decision.reason, family=family)
            try:
                validate_policy(decision.snapshot)
                if decision.snapshot['scope'] != list(event.scope):
                    raise PortViolation('POLICY_SCOPE_MISMATCH')
            except PortViolation as exc:
                return finish(S.QUARANTINED, str(exc), family=family)
            family['policy_snapshot'] = policy = deepcopy(decision.snapshot)
        if event.kind == 'RESTORE' and policy['restore_allowed'] is not True:
            return finish(S.PENDING_RECONCILIATION, 'RESTORE_POLICY_NOT_AUTHORIZED', family=family)
        intent = RewardIntent('reward:' + event.operation_key, event.operation_key, event.family_key,
                              event.kind, family['desired_active'], policy, admission.evidence_ref,
                              resolution.evidence_ref if resolution else None)
        # A frozen dataclass does not freeze nested dictionaries. Give the
        # collaborator an isolated copy and validate against our retained intent.
        candidate = self.wallet.compute(deepcopy(intent), deepcopy(snapshot.wallet))
        if isinstance(candidate, WalletHold):
            return finish(S.PENDING_RECONCILIATION, candidate.reason, family=family,
                          details={'reward_intent': asdict(intent), 'compensation_pending': True})
        if not isinstance(candidate, WalletDelta):
            return finish(S.PENDING_RECONCILIATION, 'INVALID_WALLET_CANDIDATE_TYPE', family=family)
        try:
            validate_delta(candidate, intent, snapshot.wallet)
        except PortViolation as exc:
            return finish(S.PENDING_RECONCILIATION, str(exc), family=family,
                          details={'reward_intent': asdict(intent), 'invalid_candidate_rejected': True})
        state = (S.PENDING_RECONCILIATION if candidate.unresolved else
                 S.APPLIED if family['desired_active'] else S.REVERTED)
        return finish(state, candidate.reason, family=family, wallet_delta=candidate,
                      terminal_event=event, details={'reward_intent': asdict(intent),
                                                    'compensation_pending': candidate.unresolved})

    def query(self, inbox_id, *, duplicate=False, received_only=False):
        snapshot = self.store.snapshot()
        row = snapshot.ledger['inbox'].get(inbox_id)
        if row is None:
            return self._uncertain(inbox_id, 'UNKNOWN_INBOX')
        state, ref, reason = row['state'], row['last_commit'], row['reason']
        family_key = row.get('family_key')
        if row.get('follow_family') and family_key in snapshot.ledger['families']:
            family = snapshot.ledger['families'][family_key]
            state, ref = family['state'], family['last_commit']
        if not snapshot.continuity_verified:
            return self._uncertain(inbox_id, 'P21_RESTORE_CONTINUITY_NOT_PROVEN')
        found = self.store.lookup(ref['transaction_id'])
        if found.status != 'COMMITTED':
            return self._uncertain(inbox_id, 'NO_AUTHORITATIVE_COMMIT_RECEIPT')
        try:
            receipt = self._verify_receipt(found.receipt, ref['transaction_id'], ref['request_sha256'])
        except PortViolation as exc:
            return self._uncertain(inbox_id, str(exc))
        ack = 'ACK_RECEIVED' if received_only and not row['processed'] else {
            S.APPLIED: 'ACK_APPLIED', S.REVERTED: 'ACK_REVERTED',
            S.QUARANTINED: 'ACK_QUARANTINED', S.REJECTED: 'ACK_REJECTED',
            S.PENDING_RECONCILIATION: 'ACK_PENDING_RECONCILIATION'}[state]
        return Outcome(inbox_id, state, reason, ack, receipt, family_key, duplicate, receipt.origin)

    def pending_cases(self):
        ledger = self.store.snapshot().ledger
        result = []
        for state in (S.QUARANTINED, S.PENDING_RECONCILIATION):
            for key in sorted(ledger['case_index'][state.value]):
                row = ledger['inbox'][key]
                result.append({'inbox_id': key, 'state': row['state'], 'reason': row['reason'],
                               'case_version': row['case_version'], 'input_sha256': row['input_sha256']})
        return result

    def reconcile(self, checkpoint):
        """Read-only comparison with an independently retained P21 checkpoint.

        Never replays money or lifts P21's restore fence. Missing authority stays blocked.
        """
        snapshot = self.store.snapshot()
        issues = []
        try:
            head = verify_audit(snapshot.ledger)
        except PortViolation as exc:
            head = None
            issues.append(str(exc))
        if checkpoint is None:
            issues.append('INDEPENDENT_CHECKPOINT_REQUIRED')
        else:
            if checkpoint.get('store_instance') != snapshot.store_instance:
                issues.append('CHECKPOINT_STORE_MISMATCH')
            if checkpoint.get('high_watermark') != snapshot.high_watermark:
                issues.append('CHECKPOINT_WATERMARK_MISMATCH')
            if checkpoint.get('ledger_sha256') != digest(snapshot.ledger):
                issues.append('CHECKPOINT_LEDGER_MISMATCH')
            if checkpoint.get('wallet_sha256') != digest(snapshot.wallet):
                issues.append('CHECKPOINT_WALLET_MISMATCH')
        if not snapshot.continuity_verified:
            issues.append('P21_RESTORE_CONTINUITY_NOT_PROVEN')
        for op in snapshot.ledger['operations'].values():
            ref = op['atomic_commit']
            found = self.store.lookup(ref['transaction_id'])
            if found.status != 'COMMITTED':
                issues.append('MISSING_OPERATION_RECEIPT:' + ref['transaction_id'])
            elif found.receipt.request_sha256 != ref['request_sha256']:
                issues.append('OPERATION_RECEIPT_BINDING_MISMATCH:' + ref['transaction_id'])
        return {'schema_version': 'P11-RECONCILIATION/0.1.0',
                'state': S.PENDING_RECONCILIATION.value if issues else 'CONSISTENT_SNAPSHOT',
                'issues': issues, 'audit_head_sha256': head,
                'high_watermark': snapshot.high_watermark, 'wallet_mutations': 0,
                'continuity_ref': snapshot.continuity_ref,
                'authority_note': 'Caller must establish checkpoint provenance through P21; hash agreement is not authorization.'}
