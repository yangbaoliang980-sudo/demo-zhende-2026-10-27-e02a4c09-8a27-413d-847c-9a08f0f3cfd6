"""Explicit P02 xorshift32 state. No global RNG, shuffle policy or clock.

Jump-ahead verifies large P15 draw_count deltas in O(log count), rather than
looping over untrusted counts. P15 still owns when/how to consume random values.
"""
from .wire import MAX_INTEGER

MASK = 0xffffffff


def next_u32(state):
    if type(state) is not int or not 1 <= state <= MASK:
        raise ValueError('INVALID_RNG_STATE')
    state ^= (state << 13) & MASK
    state ^= state >> 17
    state ^= (state << 5) & MASK
    return state & MASK


def _apply(columns, value):
    out = 0
    for i in range(32):
        if value & (1 << i):
            out ^= columns[i]
    return out


def advance(state, count):
    if type(count) is not int or not 0 <= count <= MAX_INTEGER:
        raise ValueError('INVALID_RNG_COUNT')
    if type(state) is not int or not 1 <= state <= MASK:
        raise ValueError('INVALID_RNG_STATE')
    columns = tuple(next_u32(1 << i) for i in range(32))
    while count:
        if count & 1:
            state = _apply(columns, state)
        count >>= 1
        if count:
            columns = tuple(_apply(columns, c) for c in columns)
    return state


def verify_transition(before, after):
    return (before['algorithm'] == after['algorithm'] == 'xorshift32-v1'
            and before['initial_seed'] == after['initial_seed']
            and after['draw_count'] >= before['draw_count']
            and advance(before['state'], after['draw_count'] - before['draw_count']) == after['state'])
