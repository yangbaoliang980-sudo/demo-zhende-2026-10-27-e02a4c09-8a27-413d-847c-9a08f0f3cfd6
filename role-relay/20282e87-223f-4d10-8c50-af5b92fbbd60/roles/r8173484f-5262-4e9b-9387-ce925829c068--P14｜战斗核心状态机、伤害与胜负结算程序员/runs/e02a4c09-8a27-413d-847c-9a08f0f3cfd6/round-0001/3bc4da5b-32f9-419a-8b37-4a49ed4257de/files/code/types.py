"""Local DTO proposal. P13/P12 must approve their own production mappings."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

LOCAL_EVENT_VERSION = 'P11-LOCAL-EVENT/0.1.0-proposal'
MAX_INPUT_BYTES = 65536
HASH_ZERO = '0' * 64


class LedgerStatus(StrEnum):
    APPLIED = 'APPLIED'
    REVERTED = 'REVERTED'
    QUARANTINED = 'QUARANTINED'
    PENDING_RECONCILIATION = 'PENDING_RECONCILIATION'
    REJECTED = 'REJECTED'


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def byte_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def strict_json(raw: bytes) -> Any:
    def reject_constant(value):
        raise ValueError('NONFINITE_JSON_NUMBER')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                      parse_constant=reject_constant)


@dataclass(frozen=True)
class Event:
    schema_version: str
    source_id: str
    collection_lineage: str
    collection_epoch: str
    beneficiary_id: str
    event_id: str | None
    family_id: str | None
    kind: str
    revision: int
    predecessor_event_id: str | None
    rating: str | None
    card_reference: str | None
    source_evidence_sha256: str | None

    @classmethod
    def parse(cls, raw: bytes) -> 'Event':
        data = strict_json(raw)
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            raise ValueError('INVALID_DTO_KEYS')
        if data['schema_version'] != LOCAL_EVENT_VERSION:
            raise ValueError('UNSUPPORTED_LOCAL_SCHEMA')
        for key in ('source_id', 'collection_lineage', 'collection_epoch', 'beneficiary_id'):
            _identifier(data[key])
        for key in ('event_id', 'family_id', 'predecessor_event_id', 'card_reference'):
            if data[key] is not None:
                _identifier(data[key])
        if type(data['revision']) is not int or not 0 <= data['revision'] <= 2**53-1:
            raise ValueError('INVALID_REVISION')
        if data['kind'] not in ('REVIEW', 'UNDO', 'RESTORE'):
            raise ValueError('UNSUPPORTED_EVENT_KIND')
        if data['kind'] == 'REVIEW':
            if data['revision'] != 0 or data['predecessor_event_id'] is not None:
                raise ValueError('INVALID_REVIEW_CAUSAL_SHAPE')
            if data['rating'] not in ('Again', 'Hard', 'Good', 'Easy'):
                raise ValueError('UNKNOWN_RATING_SEMANTICS')
        elif data['revision'] == 0 or data['predecessor_event_id'] is None or data['rating'] is not None:
            raise ValueError('INVALID_CONTROL_CAUSAL_SHAPE')
        evidence = data['source_evidence_sha256']
        if evidence is not None and (not isinstance(evidence, str) or len(evidence) != 64 or
                                      any(c not in '0123456789abcdef' for c in evidence)):
            raise ValueError('INVALID_EVIDENCE_HASH')
        return cls(**data)

    @property
    def scope(self) -> tuple[str, str, str]:
        # Neither save slot, policy, category, day, rating nor delivery id can reset uniqueness.
        return (self.source_id, self.collection_lineage, self.beneficiary_id)

    @property
    def operation_key(self) -> str:
        return digest(['P11-operation-v1', *self.scope, self.event_id])

    @property
    def family_key(self) -> str:
        return digest(['P11-family-v1', *self.scope, self.family_id])

    @property
    def fingerprint(self) -> str:
        return digest(asdict(self))


def _identifier(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 256 or
            value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('INVALID_IDENTIFIER')


@dataclass(frozen=True)
class Admission:
    authenticated: bool = False
    identity_proven: bool = False
    undo_capability_proven: bool = False
    causal_link_proven: bool = False
    epoch_proven: bool = False
    evidence_ref: str | None = None
    reason: str = 'UPSTREAM_EVIDENCE_MISSING'

    @property
    def sufficient(self):
        return all((self.authenticated, self.identity_proven, self.undo_capability_proven,
                    self.causal_link_proven, self.epoch_proven, bool(self.evidence_ref)))


@dataclass(frozen=True)
class Resolution:
    evidence_ref: str
    input_sha256: str
    case_version: int
    action: str
    issuer: str
    proof_sha256: str
    target_inbox_id: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    eligible: bool
    reason: str
    snapshot: dict | None = None


@dataclass(frozen=True)
class RewardIntent:
    transaction_id: str
    operation_key: str
    family_key: str
    kind: str
    desired_active: bool
    policy_snapshot: dict
    source_evidence_ref: str
    resolution_ref: str | None

    @property
    def fingerprint(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class WalletDelta:
    intent_sha256: str
    family_key: str
    expected_wallet_version: int
    wallet_before_sha256: str
    changes: dict[str, int]
    source_after: dict
    unresolved: bool
    reason: str
    policy_sha256: str


@dataclass(frozen=True)
class WalletHold:
    reason: str


@dataclass(frozen=True)
class Snapshot:
    ledger: dict
    wallet: dict
    continuity_verified: bool
    continuity_ref: str | None
    store_instance: str
    high_watermark: int


@dataclass(frozen=True)
class Mutation:
    ledger: dict
    wallet_delta: WalletDelta | None = None


@dataclass(frozen=True)
class CommitReceipt:
    transaction_id: str
    request_sha256: str
    store_instance: str
    sequence: int
    ledger_sha256: str
    wallet_sha256: str
    origin: str
    durable: bool


@dataclass(frozen=True)
class Lookup:
    status: str  # COMMITTED, ABSENT (authoritative), UNKNOWN
    receipt: CommitReceipt | None = None


@dataclass(frozen=True)
class Outcome:
    inbox_id: str | None
    state: str
    reason: str
    ack: str | None
    receipt: CommitReceipt | None
    family_key: str | None = None
    duplicate: bool = False
    evidence_scope: str = 'UNBOUND'


class CommitUnknown(Exception):
    """The commit may have happened. Only authoritative lookup may resolve it."""


class PortViolation(Exception):
    """A candidate or receipt failed P11's boundary invariants."""


def new_ledger():
    return {'schema_version': 'P11-LEDGER/0.1.0', 'inbox': {}, 'claims': {}, 'families': {},
            'operations': {}, 'case_index': {s.value: [] for s in LedgerStatus}, 'audit': []}


def encoded_raw(raw):
    return base64.b64encode(raw).decode('ascii')
