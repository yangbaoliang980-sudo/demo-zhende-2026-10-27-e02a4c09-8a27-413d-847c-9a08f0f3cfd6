"""Bounded thread handoff without business execution, persistence or reward ACK."""
from __future__ import annotations
import queue
import threading
from dataclasses import dataclass
from .codec import FrozenMessage
from .contracts import decode, validate


class Backpressure(RuntimeError):
    pass


class WrongThread(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Queued:
    ticket: int
    status: str = 'QUEUED_NOT_COMMITTED'


@dataclass(frozen=True, slots=True)
class Delivery:
    ticket: int
    status: str
    response: FrozenMessage | None
    error_type: str | None = None


class CommandMailbox:
    """UI producer(s) -> one host thread -> injected P14 port.

    Queue admission is not a business receipt. The queue is volatile; callers
    retain original requests until the domain returns its own receipt. This class
    does not deduplicate commands, calculate costs, change state or save a game.
    P14 serializes and commits. Full queues are rejected, never silently evicted.
    """
    def __init__(self, handler, *, capacity=64, allowed_kinds=('PLAY_CARD','END_TURN')):
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError('INVALID_QUEUE_CAPACITY')
        self._handler = handler
        self._allowed = frozenset(allowed_kinds)
        self._queue = queue.Queue(maxsize=capacity)
        self._lock = threading.Lock()
        self._next_ticket = 0
        self._owner_thread = threading.get_ident()
        self._closed = False
        self._draining = False

    def post(self, raw: bytes) -> Queued:
        message = decode(raw, 'BattleCommand')
        if message.value['kind'] not in self._allowed:
            raise ValueError('COMMAND_NOT_ALLOWED_ON_THIS_PORT')
        with self._lock:
            if self._closed:
                raise ValueError('MAILBOX_CLOSED')
            ticket = self._next_ticket
            try:
                self._queue.put_nowait((ticket, message))
            except queue.Full as exc:
                raise Backpressure('QUEUE_FULL_CALLER_RETAINS_REQUEST') from exc
            self._next_ticket += 1
        return Queued(ticket)

    def close(self):
        # Already queued work remains drainable; no forced discard.
        with self._lock:
            self._closed = True

    def drain(self, budget=16) -> tuple[Delivery, ...]:
        if threading.get_ident() != self._owner_thread:
            raise WrongThread('HOST_THREAD_REQUIRED')
        if type(budget) is not int or not 0 <= budget <= 4096:
            raise ValueError('INVALID_DRAIN_BUDGET')
        if self._draining:
            raise ValueError('REENTRANT_DRAIN')
        self._draining = True
        delivered=[]
        try:
            for _ in range(budget):
                try:
                    ticket,message=self._queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    result=self._handler(message)
                    if not isinstance(result, FrozenMessage):
                        raise ValueError('PORT_RESPONSE_NOT_FROZEN')
                    response=validate(result.value,'BattleReply')
                    original=message.value;rv=response.value
                    if (rv['battle_id'],rv['command_id']) != (original['battle_id'],original['command_id']):
                        raise ValueError('PORT_RESPONSE_SCOPE_MISMATCH')
                    delivered.append(Delivery(ticket,'PORT_RETURNED_UNVERIFIED',response))
                except Exception as exc:
                    # A domain may have committed before it raised. Never emit
                    # a success ACK or fabricate a rejected/uncommitted outcome.
                    delivered.append(Delivery(ticket,'PORT_EXCEPTION_OUTCOME_UNKNOWN',None,type(exc).__name__))
                finally:
                    self._queue.task_done()
        finally:
            self._draining=False
        return tuple(delivered)

