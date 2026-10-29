"""P16 immutable local candidates. Only EnemyIntent/PhaseProposal are P13 DTOs.

BehaviorSnapshot is an explicit, unapproved extension from the trusted P14
composition boundary. It is not inferred from a UI, clock or mutable AI cache.
"""
from dataclasses import asdict, dataclass
import re
from upstream.P13.runtime.framework.yltt_framework.codec import (
    FrozenMessage, ContractError, MAX_INTEGER, fingerprint,
)
from upstream.P13.runtime.framework.yltt_framework.contracts import validate

API_VERSION = 'P16-ENEMY-AI/0.1.0-isolated'
BEHAVIOR_VERSION = 'P16-BEHAVIOR/0.1.0-proposal'
CONTRACT_VERSION = 'YLTT-INTERNAL/0.1.0-isolated'
CONTENT_VERSION = 'P06-ENEMY-0.1.0-proposal'
RULES_VERSION = 'P02-BATTLE-0.1.0-draft'


class AiError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(ok, code):
    if not ok:
        raise AiError(code)


def integer(value, low=0, high=MAX_INTEGER, code='INTEGER_RANGE'):
    require(type(value) is int and low <= value <= high, code)


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', value) is not None, 'INVALID_ID')


def sha256(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'INVALID_SHA256')


def plain(value):
    if isinstance(value, tuple):
        return [plain(x) for x in value]
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    return value


def frozen_dataclass(value):
    return FrozenMessage.from_value(plain(asdict(value)))


def checked(value, name):
    try:
        return validate(value.value if isinstance(value, FrozenMessage) else value, name)
    except ContractError as exc:
        raise AiError('SNAPSHOT_OR_DTO_INVALID') from exc


def wire(name, **fields):
    return checked({'contract_version': CONTRACT_VERSION, 'dto_type': name, **fields}, name)


@dataclass(frozen=True, slots=True)
class Charge:
    release_skill_id: str
    locked_target_ids: tuple[str, ...]
    phase_epoch: int
    ready_slot: int
    created_intent_token: str

    def __post_init__(self):
        identifier(self.release_skill_id); identifier(self.created_intent_token)
        require(type(self.locked_target_ids) is tuple and len(self.locked_target_ids) == 1, 'CHARGE_TARGET_SHAPE')
        for uid in self.locked_target_ids: identifier(uid)
        integer(self.phase_epoch); integer(self.ready_slot, 1)

    @classmethod
    def from_value(cls, value):
        v = dict(value); v['locked_target_ids'] = tuple(v['locked_target_ids'])
        return cls(**v)


@dataclass(frozen=True, slots=True)
class BehaviorSnapshot:
    schema_version: str
    battle_id: str
    actor_id: str
    revision: int
    snapshot_sha256: str
    enemy_slot: int
    state_id: str
    phase_epoch: int
    heavy_cooldown: int
    last_successful_single_target_slot: int
    charge: Charge | None
    entry_wait_pending: bool
    degraded: bool
    phase_committed_ids: tuple[str, ...]
    targetable_ids: tuple[str, ...]
    pending_reactions: int
    graph_available: bool

    def __post_init__(self):
        require(self.schema_version == BEHAVIOR_VERSION, 'BEHAVIOR_VERSION_UNSUPPORTED')
        for s in (self.battle_id, self.actor_id, self.state_id): identifier(s)
        sha256(self.snapshot_sha256)
        for n in (self.revision, self.phase_epoch, self.heavy_cooldown, self.pending_reactions): integer(n)
        integer(self.enemy_slot, 1); integer(self.last_successful_single_target_slot, -1, 4095)
        require(self.charge is None or type(self.charge) is Charge, 'CHARGE_TYPE')
        for b in (self.entry_wait_pending, self.degraded, self.graph_available):
            require(type(b) is bool, 'BOOLEAN_REQUIRED')
        for seq in (self.phase_committed_ids, self.targetable_ids):
            require(type(seq) is tuple and len(seq) <= 4096 and all(type(s) is str for s in seq)
                    and len(seq) == len(set(seq)), 'DUPLICATE_OR_MUTABLE_IDS')
            for s in seq: identifier(s)

    @classmethod
    def from_value(cls, value):
        v = dict(value)
        for k in ('phase_committed_ids', 'targetable_ids'): v[k] = tuple(v[k])
        if v['charge'] is not None: v['charge'] = Charge.from_value(v['charge'])
        return cls(**v)

    def message(self):
        return frozen_dataclass(self)

    def semantic_sha256(self):
        """Fields frozen across a player window; targetability is revalidated."""
        data = self.message().value
        for k in ('revision', 'snapshot_sha256', 'targetable_ids', 'pending_reactions', 'graph_available'):
            data.pop(k)
        return fingerprint(data)


@dataclass(frozen=True, slots=True)
class EnemyAction:
    skill_id: str
    intent_dictionary_id: str
    kind: str
    target_ids: tuple[str, ...]
    base_amount_per_hit: int
    hit_count: int
    future_release_base_amount: int

    def message(self): return frozen_dataclass(self)


@dataclass(frozen=True, slots=True)
class Announcement:
    """Frozen pre-player-window plan; token binds fields, not an auth credential."""
    data: FrozenMessage

    @property
    def value(self): return self.data.value

    @property
    def token(self): return self.value['intent_token']


@dataclass(frozen=True, slots=True)
class Decision:
    disposition: str
    reason: str
    action: EnemyAction | None
    intent: FrozenMessage | None
    view: FrozenMessage
    behavior_candidate: FrozenMessage | None
    announcement: Announcement | None
    rng: FrozenMessage

    def message(self):
        return FrozenMessage.from_value({'api_version': API_VERSION,
            'disposition': self.disposition, 'reason': self.reason,
            'action': None if self.action is None else self.action.message().value,
            'intent': None if self.intent is None else self.intent.value,
            'view': self.view.value,
            'behavior_candidate': None if self.behavior_candidate is None else self.behavior_candidate.value,
            'announcement': None if self.announcement is None else self.announcement.value,
            'rng': self.rng.value, 'rng_draws_delta': 0, 'authoritative_state_changed': False})


@dataclass(frozen=True, slots=True)
class PhaseCheckpoint:
    root_command_id: str
    before_hp: int
    trigger_event_seq: int

    def __post_init__(self):
        identifier(self.root_command_id); integer(self.before_hp)
        integer(self.trigger_event_seq, 1)


@dataclass(frozen=True, slots=True)
class PhasePlan:
    disposition: str
    reason: str
    proposals: tuple[FrozenMessage, ...]
    evidence: FrozenMessage

    def message(self):
        return FrozenMessage.from_value({'api_version': API_VERSION,
            'disposition': self.disposition, 'reason': self.reason,
            'proposals': [p.value for p in self.proposals], 'evidence': self.evidence.value,
            'authoritative_state_changed': False, 'extra_actions': 0, 'summon_proposals': []})
