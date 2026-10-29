"""Isolated one-slot seam for the original P14 EnemyPlanner protocol.

P14 v0.1 cannot commit P06 behavior fields. This adapter therefore makes no
production or multi-turn behavior-persistence claim. It holds one frozen
announcement and never caches a successful action or increments AI state.
"""
from dataclasses import replace
from .planner import resolve_intent
from .types import AiError, checked


class P14SingleSlotAdapter:
    def __init__(self,catalog,behavior,announcement,*,rejection_type,scope):
        if scope!='ONE_SLOT_CONTRACT_TEST_ONLY':
            raise AiError('P14_BEHAVIOR_COMMIT_CONTRACT_UNBOUND')
        if not isinstance(rejection_type,type) or not issubclass(rejection_type,Exception):
            raise TypeError('P14_REJECTION_TYPE_REQUIRED')
        self._catalog=catalog; self._behavior=behavior
        self._announcement=announcement; self._rejection=rejection_type

    def propose(self,snapshot):
        try:
            msg=checked(snapshot,'BattleSnapshot'); s=msg.value
            # P14 supplies a private post-DOT snapshot within its transaction.
            # Only anchor fields are rebound; no behavior fact is inferred.
            context=replace(self._behavior,revision=s['revision'],snapshot_sha256=msg.sha256)
            result=resolve_intent(msg,context,self._catalog,self._announcement)
            if result.disposition!='ACTION_CANDIDATE' or result.intent is None:
                raise AiError('P16_ACTION_NOT_EXECUTABLE')
            return result.intent
        except AiError as exc:
            # Match the exception class used by the composed P14 module.
            raise self._rejection(exc.code) from exc
