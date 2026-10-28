"""Private immutable resolution inputs. These are NOT P13/P22 content schemas.

Every policy is supplied explicitly for isolated tests. No production defaults,
cost formula, draw policy, AI selector, buff or debuff rule is invented here.
"""
from dataclasses import asdict, dataclass
import re
from .wire import MAX_INTEGER, FrozenMessage


def integer(x, low=0, high=MAX_INTEGER):
    if type(x) is not int or not low <= x <= high:
        raise ValueError('CONFIG_INTEGER_RANGE')


def identifier(s):
    if type(s) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}', s) is None:
        raise ValueError('CONFIG_ID')


@dataclass(frozen=True, slots=True)
class SourceBinding:
    label: str
    version: str
    sha256: str

    def __post_init__(self):
        identifier(self.label); identifier(self.version)
        if not re.fullmatch('[0-9a-f]{64}', self.sha256):
            raise ValueError('CONFIG_SOURCE_HASH')


@dataclass(frozen=True, slots=True)
class Effect:
    effect_index: int
    kind: str
    amount: int = 0
    status_id: str | None = None

    def __post_init__(self):
        integer(self.effect_index); integer(self.amount)
        if self.kind not in ('DAMAGE', 'SHIELD', 'HEAL', 'STATUS'):
            raise ValueError('UNSUPPORTED_EFFECT_RULE')
        if self.kind == 'STATUS':
            identifier(self.status_id)
            if self.amount != 0:
                raise ValueError('STATUS_AMOUNT_LIVES_IN_DEFINITION')
        elif self.status_id is not None:
            raise ValueError('UNEXPECTED_STATUS_ID')


@dataclass(frozen=True, slots=True)
class Action:
    action_id: str
    target_side: str
    target_count: int
    effects: tuple[Effect, ...]
    playable: bool = True
    owner_definition_id: str | None = None
    after_play_zone: str = 'discard'

    def __post_init__(self):
        identifier(self.action_id); integer(self.target_count, 0, 4096)
        if self.target_side not in ('PLAYER', 'ENEMY') or type(self.playable) is not bool:
            raise ValueError('CONFIG_ACTION')
        if type(self.effects) is not tuple or not all(isinstance(e, Effect) for e in self.effects):
            raise ValueError('IMMUTABLE_EFFECTS_REQUIRED')
        if len({e.effect_index for e in self.effects}) != len(self.effects):
            raise ValueError('DUPLICATE_EFFECT_INDEX')
        if self.effects and self.target_count == 0:
            raise ValueError('EFFECT_WITHOUT_TARGET')
        if self.owner_definition_id is not None:
            identifier(self.owner_definition_id)
        if self.after_play_zone not in ('discard', 'exhaust'):
            raise ValueError('CONFIG_AFTER_PLAY_ZONE')


@dataclass(frozen=True, slots=True)
class Dot:
    status_id: str
    amount: int
    duration: int

    def __post_init__(self):
        identifier(self.status_id); integer(self.amount); integer(self.duration, 1)


@dataclass(frozen=True, slots=True)
class Reaction:
    source_unit_id: str
    trigger_id: str
    on: str
    damage: int
    tier: int = 0
    effect_index: int = 0

    def __post_init__(self):
        identifier(self.source_unit_id); identifier(self.trigger_id)
        integer(self.damage); integer(self.tier); integer(self.effect_index)
        if self.on not in ('ON_DEATH', 'ON_DAMAGED'):
            raise ValueError('UNSUPPORTED_TRIGGER')


@dataclass(frozen=True, slots=True)
class BossEdge:
    unit_id: str
    from_phase_id: str
    to_phase_id: str
    numerator: int
    denominator: int
    relative_to_max_hp: bool

    def __post_init__(self):
        for s in (self.unit_id, self.from_phase_id, self.to_phase_id): identifier(s)
        integer(self.numerator, 1); integer(self.denominator, 1)
        if type(self.relative_to_max_hp) is not bool or self.from_phase_id == self.to_phase_id:
            raise ValueError('INVALID_BOSS_EDGE')
        if self.relative_to_max_hp and self.numerator >= self.denominator:
            raise ValueError('INVALID_BOSS_FRACTION')


@dataclass(frozen=True, slots=True)
class Rules:
    rules_version: str
    content_version: str
    deck_policy_version: str
    turn_increment_at: str
    entry_draw_requested: int
    shield_cap: int | None
    shield_overflow: str
    cards: tuple[Action, ...] = ()
    skills: tuple[Action, ...] = ()
    statuses: tuple[Dot, ...] = ()
    reactions: tuple[Reaction, ...] = ()
    boss_edges: tuple[BossEdge, ...] = ()
    source_bindings: tuple[SourceBinding, ...] = ()

    def __post_init__(self):
        if self.rules_version != 'P02-BATTLE-0.1.0-draft':
            raise ValueError('UNSUPPORTED_RULES_VERSION')
        identifier(self.content_version); identifier(self.deck_policy_version)
        if self.turn_increment_at != 'ENEMY_EXIT':
            raise ValueError('P02_TURN_INCREMENT_AT_ENEMY_EXIT_REQUIRED')
        integer(self.entry_draw_requested, 0, 4096)
        if self.shield_cap is None:
            if self.shield_overflow != 'UNCAPPED_TEST_ONLY':
                raise ValueError('EXPLICIT_TEST_SHIELD_POLICY_REQUIRED')
        else:
            integer(self.shield_cap)
            if self.shield_overflow not in ('CLAMP', 'REJECT'):
                raise ValueError('EXPLICIT_SHIELD_OVERFLOW_POLICY_REQUIRED')
        for name, cls, key in [('cards', Action, 'action_id'), ('skills', Action, 'action_id'),
                              ('statuses', Dot, 'status_id'), ('reactions', Reaction, None),
                              ('boss_edges', BossEdge, None), ('source_bindings', SourceBinding, 'label')]:
            items = getattr(self, name)
            if type(items) is not tuple or not all(isinstance(x, cls) for x in items):
                raise ValueError('IMMUTABLE_CONFIG_REQUIRED:' + name)
            if len(items) > 4096:
                raise ValueError('CONFIG_CAPACITY')
            if key and len({getattr(x, key) for x in items}) != len(items):
                raise ValueError('DUPLICATE_CONFIG_ID')
        status_ids = {s.status_id for s in self.statuses}
        for a in self.cards + self.skills:
            if any(e.kind == 'STATUS' and e.status_id not in status_ids for e in a.effects):
                raise ValueError('UNKNOWN_STATUS_DEFINITION')
        if len({(r.source_unit_id, r.trigger_id) for r in self.reactions}) != len(self.reactions):
            raise ValueError('DUPLICATE_TRIGGER_ID')
        edges = {}
        for e in self.boss_edges:
            key = (e.unit_id, e.from_phase_id)
            if key in edges:
                raise ValueError('AMBIGUOUS_BOSS_GRAPH')
            edges[key] = e.to_phase_id
        for (unit, start) in edges:
            visited = set(); phase = start
            while (unit, phase) in edges:
                if phase in visited: raise ValueError('BOSS_GRAPH_CYCLE')
                visited.add(phase); phase = edges[unit, phase]

    def frozen(self):
        def plain(v):
            if isinstance(v, tuple): return [plain(x) for x in v]
            if isinstance(v, dict): return {k:plain(x) for k,x in v.items()}
            return v
        return FrozenMessage.from_value(plain(asdict(self)))

    @classmethod
    def from_value(cls, data):
        data = dict(data)
        for key in ('cards', 'skills'):
            data[key] = tuple(Action(**{**a, 'effects':tuple(Effect(**e) for e in a['effects'])}) for a in data[key])
        for key, typ in [('statuses', Dot), ('reactions', Reaction), ('boss_edges', BossEdge), ('source_bindings', SourceBinding)]:
            data[key] = tuple(typ(**x) for x in data[key])
        return cls(**data)
