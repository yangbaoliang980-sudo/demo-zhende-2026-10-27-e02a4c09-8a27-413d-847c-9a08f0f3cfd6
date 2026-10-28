"""Isolated adapter over the unchanged P11 proposal. Never authorizes rewards.

The bridge accepts no wire-supplied receipts, trusted flags, wallet amounts,
commands, or resolution actions. The formal P13/P21 mapping is still BLOCKED.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from threading import RLock
from .ports import Backpressure, BackendUnavailable
from .protocol import (PROTOCOL, VERSION, HEX32, HEX64, ID, ProtocolError,
                       byte_hash, canonical, decode_request, digest, strict_json, validate)

@dataclass(frozen=True)
class Pairing:
    producer_id: str
    source_id: str
    collection_lineage: str
    beneficiary_id: str
    secret: bytes

    def __post_init__(self):
        if type(self.secret) is not bytes or len(self.secret) != 32:
            raise ValueError('PAIRING_REQUIRES_256_BIT_SECRET')
        for value in (self.producer_id, self.source_id, self.collection_lineage, self.beneficiary_id):
            if not isinstance(value, str) or not ID.fullmatch(value):
                raise ValueError('INVALID_PAIRING_REFERENCE')

    @property
    def scope(self):
        return {'source_id':self.source_id, 'collection_lineage':self.collection_lineage,
                'beneficiary_id':self.beneficiary_id}


def result(disposition, *, state=None, code='OK', detail='OK', inbox=None, receipt=None,
           award='UNDETERMINED', terminal=False, delay=None, next_action='NONE'):
    return {'disposition':disposition, 'ledger_state':state, 'error_code':code,
            'detail_code':detail, 'inbox_id':inbox, 'receipt':receipt,
            'evidence_scope':'ISOLATED_P11_P21_SIMULATION', 'award_status':award,
            'delivery_terminal':terminal, 'retry_after_ms':delay, 'next_action':next_action}


def retry(code='E_COMMIT_UNKNOWN', *, inbox=None, detail='AUTHORITATIVE_RESULT_REQUIRED',
          state='UNKNOWN', receipt=None, next_action='QUERY'):
    return result('RETRY_LATER', state=state, code=code, detail=detail, inbox=inbox,
                  receipt=receipt, delay=1000, next_action=next_action)


class P11Bridge:
    def __init__(self, ledger, authority, scope, *, execution_mode='isolated'):
        if execution_mode != 'isolated':
            raise ValueError('PRODUCTION_ADAPTER_NOT_APPROVED')
        validate(scope, 'scope')
        self.ledger, self.authority = ledger, authority
        self.scope = dict(scope)
        self.lock = RLock()

    def _row(self, snapshot, inbox_id):
        row = snapshot.ledger['inbox'].get(inbox_id)
        if row is not None:
            event = row.get('event')
            if not isinstance(event, dict) or any(event.get(k) != v for k, v in self.scope.items()):
                raise ProtocolError('E_SCOPE')
            if digest(event) != inbox_id or row.get('input_sha256') != inbox_id:
                raise RuntimeError('ROW_BINDING_FAILED')
        return row

    def _verified(self, outcome, inbox_id):
        snapshot = self.authority.snapshot()
        if not snapshot.continuity_verified or outcome.receipt is None:
            return None, None
        row = self._row(snapshot, inbox_id)
        if row is None or outcome.inbox_id != inbox_id:
            raise RuntimeError('OUTCOME_BINDING_FAILED')
        current = row
        if row.get('follow_family'):
            current = snapshot.ledger['families'].get(row.get('family_key'))
            if current is None:
                raise RuntimeError('FAMILY_BINDING_FAILED')
        proof = asdict(outcome.receipt)
        ref = current.get('last_commit')
        if (not isinstance(ref, dict) or current['state'] != outcome.state or
            proof.get('transaction_id') != ref.get('transaction_id') or
            proof.get('request_sha256') != ref.get('request_sha256') or
            proof.get('durable') is not True or proof.get('origin') != 'P21_SIMULATOR' or
            proof.get('store_instance') != snapshot.store_instance or
            type(proof.get('sequence')) is not int or
            not 0 < proof['sequence'] <= snapshot.high_watermark <= 2**53-1):
            raise RuntimeError('RECEIPT_BINDING_FAILED')
        for name in ('request_sha256', 'ledger_sha256', 'wallet_sha256'):
            if not isinstance(proof.get(name), str) or not HEX64.fullmatch(proof[name]):
                raise RuntimeError('RECEIPT_DIGEST_FAILED')
        found = self.authority.lookup(proof['transaction_id'])
        if found.status != 'COMMITTED' or found.receipt is None:
            return None, row
        if asdict(found.receipt) != proof:
            raise RuntimeError('AUTHORITATIVE_RECEIPT_MISMATCH')
        # Bind state and receipt again through P11, not a cached transport result.
        fresh = self.ledger.query(inbox_id)
        if fresh.state != outcome.state or fresh.receipt != outcome.receipt or fresh.ack != outcome.ack:
            return None, row
        summary = {'origin':proof['origin'], 'transaction_id':proof['transaction_id'],
                   'sequence':proof['sequence'], 'store_id_sha256':byte_hash(proof['store_instance'].encode()),
                   'receipt_sha256':digest(proof)}
        validate(summary, 'receipt')
        return summary, row

    def _translate(self, outcome, inbox_id):
        proof, row = self._verified(outcome, inbox_id)
        if proof is None:
            return retry(inbox=inbox_id)
        state = str(outcome.state)
        expected = {'APPLIED':'ACK_APPLIED','QUARANTINED':'ACK_QUARANTINED',
                    'REVERTED':'ACK_REVERTED','REJECTED':'ACK_REJECTED',
                    'PENDING_RECONCILIATION':'ACK_PENDING_RECONCILIATION'}
        if outcome.ack != expected.get(state):
            return retry('E_BACKEND_CONTRACT', inbox=inbox_id, detail='UNEXPECTED_P11_OUTCOME')
        detail = outcome.reason
        if not isinstance(detail, str) or not __import__('re').fullmatch(r'[A-Z][A-Z0-9_]{0,95}', detail):
            detail = 'P11_REASON_AVAILABLE_IN_LOCAL_LEDGER'
        args = dict(state=state, detail=detail, inbox=inbox_id, receipt=proof)
        if state == 'APPLIED':
            return result('ACK_APPLIED', award='APPLIED', terminal=True, **args)
        if state == 'QUARANTINED':
            return result('ACK_QUARANTINED', code='E_QUARANTINED', award='NOT_AWARDED',
                          delay=30000, next_action='QUERY', **args)
        if state == 'REVERTED':
            return result('STATUS', award='REVERTED', terminal=True, **args)
        if state == 'REJECTED':
            return result('REJECTED', code='E_LEDGER_REJECTED', award='NOT_AWARDED', terminal=True, **args)
        return retry('E_CAUSAL_PENDING', inbox=inbox_id, detail=detail, state=state,
                     receipt=proof, next_action='QUERY' if row['processed'] else 'SUBMIT')

    def submit(self, event):
        inbox_id = digest(event)
        with self.lock:
            try:
                # Never inspect or replace the P11 Evidence/Policy ports here.
                self.ledger.handle(canonical(event))
                return self._translate(self.ledger.query(inbox_id), inbox_id)
            except ProtocolError:
                raise
            except Backpressure:
                return retry('E_BACKPRESSURE', inbox=inbox_id, detail='BACKEND_ADMISSION_DEFERRED')
            except (OSError, TimeoutError, BackendUnavailable):
                return retry('E_BACKEND_UNAVAILABLE', inbox=inbox_id)
            except Exception:
                # May include a commit that succeeded just before a failure.
                return retry('E_BACKEND_CONTRACT', inbox=inbox_id, detail='P11_P21_QUERY_REQUIRED')

    def query(self, inbox_id):
        with self.lock:
            try:
                snapshot = self.authority.snapshot()
                if not snapshot.continuity_verified:
                    return retry(inbox=inbox_id, detail='RESTORE_CONTINUITY_UNPROVEN')
                row = self._row(snapshot, inbox_id)
                if row is None:
                    return result('STATUS', state='NOT_FOUND', code='E_NOT_FOUND',
                                  detail='ABSENT_IN_CONTINUOUS_SNAPSHOT', inbox=inbox_id,
                                  delay=250, next_action='SUBMIT')
                return self._translate(self.ledger.query(inbox_id), inbox_id)
            except ProtocolError:
                raise
            except Backpressure:
                return retry('E_BACKPRESSURE', inbox=inbox_id, detail='BACKEND_ADMISSION_DEFERRED')
            except (OSError, TimeoutError, BackendUnavailable):
                return retry('E_BACKEND_UNAVAILABLE', inbox=inbox_id)
            except Exception:
                return retry('E_BACKEND_CONTRACT', inbox=inbox_id, detail='P11_P21_QUERY_REQUIRED')


class GameIngress:
    """Authenticated bytes enter here; limits/schema/scope precede ledger calls."""
    def __init__(self, pairing, bridge):
        if pairing.scope != bridge.scope:
            raise ValueError('PAIRING_BRIDGE_SCOPE_MISMATCH')
        self.pairing, self.bridge = pairing, bridge

    def handle(self, raw):
        message_id = None
        try:
            # Recover only a bounded technical ID to correlate a version rejection.
            candidate = strict_json(raw)
            if isinstance(candidate, dict) and isinstance(candidate.get('message_id'), str):
                if HEX32.fullmatch(candidate['message_id']):
                    message_id = candidate['message_id']
            msg = decode_request(raw)
            if msg['producer_id'] != self.pairing.producer_id or msg['scope'] != self.pairing.scope:
                raise ProtocolError('E_SCOPE')
            if msg['message_type'] == 'HELLO':
                body = result('STATUS', award='NOT_APPLICABLE', terminal=True, detail='ISOLATED_CONTRACT_READY')
            elif msg['message_type'] == 'SUBMIT_EVENT':
                event = msg['payload']['event']
                if any(event[k] != v for k, v in self.pairing.scope.items()):
                    raise ProtocolError('E_SCOPE')
                body = self.bridge.submit(event)
            else:
                body = self.bridge.query(msg['payload']['inbox_id'])
        except ProtocolError as exc:
            body = result('REJECTED', code=exc.code, detail=exc.code, terminal=True)
        reply = {'protocol':PROTOCOL, 'protocol_version':VERSION, 'message_type':'RESULT',
                 'message_id':message_id, 'producer_id':self.pairing.producer_id,
                 'scope':self.pairing.scope, 'request_sha256':byte_hash(raw), 'payload':body}
        validate(reply, 'response')
        return canonical(reply)
