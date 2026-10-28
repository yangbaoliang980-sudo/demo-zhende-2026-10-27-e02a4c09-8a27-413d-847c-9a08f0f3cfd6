"""Read-side stream gate only; does not animate or mutate BattleState/HUD."""
from dataclasses import dataclass
from .codec import FrozenMessage
from .contracts import validate


@dataclass(frozen=True, slots=True)
class StreamDecision:
    disposition: str
    last_event_seq: int
    revision: int


class BattleStreamGuard:
    """Owner-facing seam for IC-08; P19/P29 implement actual view behavior.

    Every gap/conflict returns NEED_SNAPSHOT without applying partial events.
    Rebase must be supplied through the P14 read-only port, never from a UI input.
    No animation timer/callback or acknowledgement is part of battle logic.
    """
    def __init__(self):
        self._snapshot=None
        self._last_batch_sha=None

    @property
    def snapshot(self):
        if self._snapshot is None:
            return None
        return self._snapshot.value

    def rebase(self, snapshot: FrozenMessage, *, new_battle=False):
        incoming=validate(snapshot.value,'BattleSnapshot')
        old=self.snapshot;new=incoming.value
        if old is not None and not new_battle:
            if old['battle_id']!=new['battle_id']:
                raise ValueError('EXPLICIT_BATTLE_SWITCH_REQUIRED')
            if new['revision'] < old['revision'] or new['last_event_seq'] < old['last_event_seq']:
                raise ValueError('SNAPSHOT_REGRESSION')
            if new['revision']==old['revision'] and incoming.raw!=self._snapshot.raw:
                raise ValueError('SAME_REVISION_DIFFERENT_SNAPSHOT')
        self._snapshot=incoming
        self._last_batch_sha=None

    def offer(self, batch: FrozenMessage) -> StreamDecision:
        incoming=validate(batch.value,'BattleCommitBatch');b=incoming.value
        old=self.snapshot
        if old is None:
            return StreamDecision('NEED_SNAPSHOT',0,0)
        def decision(s):return StreamDecision(s,old['last_event_seq'],old['revision'])
        if old['battle_id']!=b['battle_id']:
            return decision('NEED_SNAPSHOT')
        if incoming.sha256==self._last_batch_sha:
            return decision('DUPLICATE')
        new=b['snapshot']
        if new['revision']<old['revision'] and new['last_event_seq']<=old['last_event_seq']:
            return decision('STALE')
        if (b['previous_revision']!=old['revision'] or
                b['events'][0]['seq']!=old['last_event_seq']+1):
            return decision('NEED_SNAPSHOT')
        self._snapshot=validate(new,'BattleSnapshot')
        self._last_batch_sha=incoming.sha256
        return StreamDecision('ACCEPT',new['last_event_seq'],new['revision'])

