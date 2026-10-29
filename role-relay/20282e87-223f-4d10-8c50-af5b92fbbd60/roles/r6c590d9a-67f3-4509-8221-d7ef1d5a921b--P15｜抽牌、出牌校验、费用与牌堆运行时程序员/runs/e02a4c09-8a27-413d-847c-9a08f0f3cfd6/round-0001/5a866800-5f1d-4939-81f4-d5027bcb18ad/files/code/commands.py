"""Optional in-memory idempotent evidence cache around the pure planner.

No successful commit receipts or balances are stored here. Do not use this cache
to infer whether a battle transaction committed, especially after a restart.
"""
import threading
from .content import PlannerContext
from .errors import DeckRejected, integer, require
from .planner import plan
from .wire import checked


class DeckPlanner:
    def __init__(self, context, *, capacity=4096):
        require(isinstance(context, PlannerContext), 'IMMUTABLE_CONTEXT_REQUIRED')
        integer(capacity, 1, 4096)
        self._context = context
        self._capacity = capacity
        self._decisions = {}
        self._lock = threading.RLock()

    @property
    def context(self):
        return self._context

    def evaluate(self, command, snapshot):
        command = checked(command, 'BattleCommand')
        snapshot = checked(snapshot, 'BattleSnapshot')
        c = command.value
        key = c['battle_id'], c['command_id']
        with self._lock:
            prior = self._decisions.get(key)
            if prior is None and len(self._decisions) >= self._capacity:
                raise DeckRejected('DECISION_CACHE_CAPACITY')
            result = plan(command, snapshot, self._context, prior=prior)
            if prior is None:
                self._decisions[key] = result
            return result

    def decisions(self):
        with self._lock:
            return tuple(self._decisions.values())
