"""Reuse P13's original, hash-bound codec/schema; never patch their wire DTOs."""
from upstream.P13.runtime.framework.yltt_framework import CONTRACT_VERSION
from upstream.P13.runtime.framework.yltt_framework.codec import (
    ContractError, FrozenMessage, MAX_INTEGER, canonical, fingerprint,
)
from upstream.P13.runtime.framework.yltt_framework.contracts import validate


def raw_message(dto_type, **fields):
    return {'contract_version': CONTRACT_VERSION, 'dto_type': dto_type, **fields}


def message(dto_type, **fields):
    return validate(raw_message(dto_type, **fields), dto_type)


def checked(value, dto_type):
    if isinstance(value, FrozenMessage):
        value = value.value
    return validate(value, dto_type)
