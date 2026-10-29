"""Immutable deck projections and pure pile operations; no BattleState writer."""
from dataclasses import asdict, dataclass, replace
from .errors import identifier, integer, require
from .rng import RngState, shuffle
from .wire import checked

ZONES = ('draw', 'hand', 'discard', 'exhaust')


@dataclass(frozen=True, slots=True)
class CardInstance:
    instance_id: str
    card_id: str
    owner_unit_id: str

    def __post_init__(self):
        for item in (self.instance_id, self.card_id, self.owner_unit_id):
            identifier(item)


@dataclass(frozen=True, slots=True)
class DeckState:
    """Read-only projection, or a proposed projection. Never committed state."""
    instances: tuple[CardInstance, ...]
    draw: tuple[str, ...]
    hand: tuple[str, ...]
    discard: tuple[str, ...]
    exhaust: tuple[str, ...]
    rng: RngState

    def __post_init__(self):
        require(type(self.instances) is tuple and all(isinstance(c, CardInstance) for c in self.instances), 'IMMUTABLE_CARDS_REQUIRED')
        integer(len(self.instances), 0, 4096)
        ids = tuple(c.instance_id for c in self.instances)
        require(len(set(ids)) == len(ids), 'DUPLICATE_CARD_INSTANCE')
        all_ids = []
        for zone in ZONES:
            values = getattr(self, zone)
            require(type(values) is tuple, 'IMMUTABLE_ZONE_REQUIRED')
            for iid in values:
                identifier(iid)
            all_ids.extend(values)
        require(len(all_ids) == len(set(all_ids)), 'CARD_IN_MULTIPLE_ZONES')
        require(set(all_ids) == set(ids), 'ZONES_CARD_SET_MISMATCH')
        require(isinstance(self.rng, RngState), 'IMMUTABLE_RNG_REQUIRED')
        RngState.from_value(self.rng.value())

    @classmethod
    def from_snapshot(cls, snapshot):
        s = checked(snapshot, 'BattleSnapshot').value
        return cls(tuple(CardInstance(**c) for c in s['card_instances']),
                   **{z: tuple(s['zones'][z]) for z in ZONES}, rng=RngState.from_value(s['rng']))

    def value(self):
        return {'card_instances': [asdict(c) for c in self.instances],
                'zones': {z: list(getattr(self, z)) for z in ZONES}, 'rng': self.rng.value()}


@dataclass(frozen=True, slots=True)
class Move:
    instance_id: str
    from_zone: str
    to_zone: str
    to_index: int

    def __post_init__(self):
        identifier(self.instance_id)
        require(self.from_zone in ZONES and self.to_zone in ZONES, 'ZONE_INVALID')
        integer(self.to_index, 0, 4095)

    def value(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DeckOperation:
    after: DeckState
    moves: tuple[Move, ...]
    requested: int = 0
    drawn: int = 0
    recycled: int = 0
    stopped_by: str = 'NONE'

    @property
    def shortfall(self):
        return self.requested - self.drawn


class _Work:
    """Disposable local arrays, never aliases of an input or authoritative DTO."""
    def __init__(self, deck):
        require(isinstance(deck, DeckState), 'DECK_STATE_REQUIRED')
        self.original = deck
        self.zones = {z: list(getattr(deck, z)) for z in ZONES}
        self.rng = deck.rng
        self.moves = []

    def move(self, iid, src, dst, index):
        require(len(self.moves) < 4096, 'PATCH_CAPACITY_EXCEEDED')
        m = Move(iid, src, dst, index)
        require(iid in self.zones[src], 'DECK_MOVE_SOURCE_INVALID')
        self.zones[src].remove(iid)
        require(index <= len(self.zones[dst]), 'DECK_MOVE_INDEX_INVALID')
        self.zones[dst].insert(index, iid)
        self.moves.append(m)

    def finish(self, **report):
        after = replace(self.original, **{z: tuple(self.zones[z]) for z in ZONES}, rng=self.rng)
        return DeckOperation(after, tuple(self.moves), **report)


def shuffle_draw(deck):
    work = _Work(deck)
    target, work.rng = shuffle(deck.draw, deck.rng)
    for index, iid in enumerate(target):
        if work.zones['draw'][index] != iid:
            work.move(iid, 'draw', 'draw', index)
    return work.finish()


def draw_cards(deck, count, *, hand_limit, recycle_discard):
    integer(count, 0, 4096)
    integer(hand_limit, 0, 4096)
    require(type(recycle_discard) is bool, 'CONFIG_RECYCLE_BOOLEAN')
    require(len(deck.hand) <= hand_limit, 'HAND_LIMIT_ALREADY_EXCEEDED')
    work = _Work(deck)
    drawn = recycled = 0
    stopped_by = 'NONE'
    while drawn < count:
        if len(work.zones['hand']) >= hand_limit:
            stopped_by = 'HAND_LIMIT'
            break
        if not work.zones['draw']:
            if not recycle_discard or not work.zones['discard']:
                stopped_by = 'EMPTY_AVAILABLE_PILES'
                break
            order, work.rng = shuffle(tuple(work.zones['discard']), work.rng)
            for iid in order:
                work.move(iid, 'discard', 'draw', len(work.zones['draw']))
            recycled += 1
        iid = work.zones['draw'][0]
        work.move(iid, 'draw', 'hand', len(work.zones['hand']))
        drawn += 1
    return work.finish(requested=count, drawn=drawn, recycled=recycled, stopped_by=stopped_by)


def discard_hand(deck):
    work = _Work(deck)
    for iid in deck.hand:
        work.move(iid, 'hand', 'discard', len(work.zones['discard']))
    return work.finish()


def consume_card(deck, instance_id, destination):
    require(destination in ('discard', 'exhaust'), 'AFTER_PLAY_ZONE_UNSUPPORTED')
    require(instance_id in deck.hand, 'CARD_NOT_IN_HAND')
    work = _Work(deck)
    work.move(instance_id, 'hand', destination, len(work.zones[destination]))
    return work.finish()
