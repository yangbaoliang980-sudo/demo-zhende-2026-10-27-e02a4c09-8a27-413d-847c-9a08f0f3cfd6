"""Bounded deterministic JSON profile; ASCII keys, UTF-8 values, safe integers."""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass

MAX_INTEGER = 2**53 - 1
MAX_BYTES = 1_048_576
MAX_DEPTH = 32
MAX_NODES = 100_000


class ContractError(ValueError):
    pass


def _reject_number(value):
    raise ContractError('NON_INTEGER_JSON_NUMBER')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def check_profile(value):
    nodes = 0
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise ContractError('JSON_COMPLEXITY_LIMIT')
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            if not -MAX_INTEGER <= item <= MAX_INTEGER:
                raise ContractError('INTEGER_OUT_OF_RANGE')
        elif type(item) is str:
            if any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in item):
                raise ContractError('UNSAFE_STRING')
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        elif type(item) is dict:
            for key, child in item.items():
                if type(key) is not str or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) is None:
                    raise ContractError('NON_ASCII_SCHEMA_KEY')
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise ContractError('UNSUPPORTED_JSON_VALUE')
    visit(value, 0)


def loads(raw: bytes):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ContractError('FRAME_SIZE_OR_TYPE')
    if raw.startswith(b'\xef\xbb\xbf'):
        raise ContractError('UTF8_BOM')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ContractError('INVALID_JSON') from exc
    check_profile(value)
    return value


def canonical(value) -> bytes:
    check_profile(value)
    result = json.dumps(value, ensure_ascii=False, sort_keys=True,
                        separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(result) > MAX_BYTES:
        raise ContractError('FRAME_SIZE_OR_TYPE')
    return result


def fingerprint(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class FrozenMessage:
    """Copy boundary: callers receive a new object, never a mutable shared DTO."""
    raw: bytes

    def __post_init__(self):
        value = loads(self.raw)
        object.__setattr__(self, 'raw', canonical(value))

    @classmethod
    def from_value(cls, value):
        return cls(canonical(value))

    @property
    def value(self):
        return loads(self.raw)

    @property
    def sha256(self):
        return hashlib.sha256(self.raw).hexdigest()

