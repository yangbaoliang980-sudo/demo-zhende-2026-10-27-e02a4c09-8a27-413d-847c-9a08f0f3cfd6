"""Versioned integration requests, NOT approved P12/P13/P17/P21 contracts.

AtomicStore must execute a deterministic, side-effect-free P11 callback against a
serializable ledger + wallet snapshot, and persist both or neither. It owns all
physical I/O, uniqueness, receipt durability and backup continuity fencing.
"""
from typing import Callable, Protocol
from .types import (Admission, CommitReceipt, Event, Lookup, Mutation, PolicyDecision,
                    Resolution, RewardIntent, Snapshot, WalletDelta, WalletHold)

PORT_VERSION = 'P11-PORTS/0.1.0-proposal'


class AtomicStore(Protocol):
    def snapshot(self) -> Snapshot: ...
    def lookup(self, transaction_id: str) -> Lookup: ...
    def execute_once(self, transaction_id: str, request_sha256: str,
                     decide: Callable[[Snapshot], Mutation]) -> CommitReceipt: ...


class EvidencePort(Protocol):
    def assess(self, event: Event, supplemental_ref: str | None) -> Admission: ...
    def resolve(self, evidence_ref: str, input_sha256: str, case_version: int,
                action: str) -> Resolution | None: ...


class PolicyPort(Protocol):
    def decide(self, original_review: Event, resolution_ref: str | None) -> PolicyDecision: ...


class WalletPort(Protocol):
    # Must be a pure calculation. No spending, reservations, DB writes or network side effects.
    def compute(self, intent: RewardIntent, wallet_snapshot: dict) -> WalletDelta | WalletHold: ...


class ClosedEvidence:
    def assess(self, event, supplemental_ref=None):
        return Admission(reason='P10_IDENTITY_UNDO_AND_EPOCH_UNVERIFIED')

    def resolve(self, evidence_ref, input_sha256, case_version, action):
        return None


class ClosedPolicy:
    def decide(self, original_review, resolution_ref=None):
        return PolicyDecision(False, 'P08_APPROVED_POLICY_NOT_RECEIVED')
