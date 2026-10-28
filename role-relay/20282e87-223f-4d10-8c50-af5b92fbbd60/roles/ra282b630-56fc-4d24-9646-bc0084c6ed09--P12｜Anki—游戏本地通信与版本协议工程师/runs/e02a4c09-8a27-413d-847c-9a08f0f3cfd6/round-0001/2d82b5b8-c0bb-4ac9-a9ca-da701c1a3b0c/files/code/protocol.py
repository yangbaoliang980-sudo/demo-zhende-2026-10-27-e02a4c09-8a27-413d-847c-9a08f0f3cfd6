"""Bounded JSON codec and a closed evaluator for this package's exact Schema.

This is deliberately not a general JSON Schema implementation. Unknown schema
keywords and external refs fail closed; both peers load the same frozen schema.
The author suite also checks it using the independent jsonschema validator.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

PROTOCOL = 'YLTT-ANKI-TRANSPORT'
VERSION = '0.1.0-isolated'
MAX_FRAME_BYTES = 32768
MAX_DEPTH = 12
MAX_NODES = 512
SAFE_INT = 2**53 - 1
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
HEX32 = re.compile(r'[0-9a-f]{32}\Z')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9:._-]{0,127}\Z')
SCHEMA_PATH = Path(__file__).resolve().parents[4] / 'contracts/anki_transport/ipc_schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))

class ProtocolError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def byte_hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise ProtocolError('E_JSON_DUPLICATE')
        result[key] = val
    return result


def _number(text):
    if len(text) > 17:
        raise ProtocolError('E_JSON_NUMBER')
    value = int(text)
    if abs(value) > SAFE_INT:
        raise ProtocolError('E_JSON_NUMBER')
    return value


def _no_float(_):
    raise ProtocolError('E_JSON_NUMBER')


def strict_json(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FRAME_BYTES:
        raise ProtocolError('E_FRAME_LIMIT')
    # Bound depth before calling the recursive JSON decoder, respecting strings.
    depth, quoted, escape = 0, False, False
    for b in raw:
        if quoted:
            if escape:
                escape = False
            elif b == 92:
                escape = True
            elif b == 34:
                quoted = False
        elif b == 34:
            quoted = True
        elif b in (123, 91):
            depth += 1
            if depth > MAX_DEPTH:
                raise ProtocolError('E_JSON_DEPTH')
        elif b in (125, 93):
            depth -= 1
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_int=_number, parse_float=_no_float, parse_constant=_no_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ProtocolError('E_JSON_SYNTAX') from exc
    todo, nodes = [value], 0
    while todo:
        item = todo.pop(); nodes += 1
        if nodes > MAX_NODES:
            raise ProtocolError('E_JSON_COMPLEXITY')
        if isinstance(item, dict):
            todo.extend(item.values()); todo.extend(item.keys())
        elif isinstance(item, list):
            todo.extend(item)
        elif isinstance(item, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in item):
            raise ProtocolError('E_JSON_SYNTAX')
    return value


_SUPPORTED = {'$schema', '$id', '$defs', '$ref', 'title', 'description', 'type',
              'const', 'enum', 'properties', 'required', 'additionalProperties',
              'minimum', 'maximum', 'minLength', 'maxLength', 'pattern', 'oneOf',
              'allOf', 'items', 'minItems', 'maxItems'}

def _check_schema(node):
    if not isinstance(node, dict) or set(node) - _SUPPORTED:
        raise RuntimeError('UNSUPPORTED_FROZEN_SCHEMA_KEYWORD')
    if '$ref' in node and (len(node) != 1 or not node['$ref'].startswith('#/$defs/')):
        raise RuntimeError('EXTERNAL_OR_COMPOSITE_REFERENCE_FORBIDDEN')
    for k in ('$defs', 'properties'):
        for child in node.get(k, {}).values():
            _check_schema(child)
    for k in ('oneOf', 'allOf'):
        for child in node.get(k, []):
            _check_schema(child)
    if 'items' in node:
        _check_schema(node['items'])

_check_schema(SCHEMA)


def _equal(a, b):
    # Python True == 1 is not JSON equality for booleans.
    return type(a) is type(b) and a == b


def _matches(value, spec):
    if '$ref' in spec:
        return _matches(value, SCHEMA['$defs'][spec['$ref'].split('/')[-1]])
    kind = spec.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'boolean': bool, 'null': type(None)}
    if kind and type(value) is not types[kind]:
        return False
    if 'const' in spec and not _equal(value, spec['const']):
        return False
    if 'enum' in spec and not any(_equal(value, c) for c in spec['enum']):
        return False
    if 'oneOf' in spec and sum(_matches(value, s) for s in spec['oneOf']) != 1:
        return False
    if 'allOf' in spec and not all(_matches(value, s) for s in spec['allOf']):
        return False
    if isinstance(value, dict):
        if any(k not in value for k in spec.get('required', [])):
            return False
        props = spec.get('properties', {})
        if spec.get('additionalProperties') is False and set(value) - set(props):
            return False
        if any(not _matches(v, props[k]) for k, v in value.items() if k in props):
            return False
    if isinstance(value, list):
        if len(value) < spec.get('minItems', 0) or len(value) > spec.get('maxItems', MAX_NODES):
            return False
        if 'items' in spec and not all(_matches(v, spec['items']) for v in value):
            return False
    if isinstance(value, str):
        if len(value) < spec.get('minLength', 0) or len(value) > spec.get('maxLength', MAX_FRAME_BYTES):
            return False
        if 'pattern' in spec and re.search(spec['pattern'], value) is None:
            return False
    if type(value) is int and (value < spec.get('minimum', -SAFE_INT) or value > spec.get('maximum', SAFE_INT)):
        return False
    return True


def validate(value, definition):
    if not _matches(value, SCHEMA['$defs'][definition]):
        raise ProtocolError('E_SCHEMA')
    return value


def decode_request(raw):
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise ProtocolError('E_SCHEMA')
    if value.get('protocol') != PROTOCOL:
        raise ProtocolError('E_PROTOCOL')
    if value.get('protocol_version') != VERSION:
        raise ProtocolError('E_PROTOCOL_VERSION')
    if value.get('message_type') not in ('HELLO', 'SUBMIT_EVENT', 'QUERY_STATUS'):
        raise ProtocolError('E_MESSAGE_TYPE')
    if value.get('message_type') == 'SUBMIT_EVENT':
        e = value.get('payload', {})
        e = e.get('event') if isinstance(e, dict) else None
        if isinstance(e, dict) and e.get('schema_version') != 'P11-LOCAL-EVENT/0.1.0-proposal':
            raise ProtocolError('E_PAYLOAD_VERSION')
    validate(value, 'request')
    if value['message_type'] == 'HELLO' and VERSION not in value['payload']['supported_versions']:
        raise ProtocolError('E_PROTOCOL_VERSION')
    return value


def decode_response(raw):
    return validate(strict_json(raw), 'response')


def request(kind, payload, *, message_id, producer_id, scope):
    obj = {'protocol':PROTOCOL, 'protocol_version':VERSION, 'message_type':kind,
           'message_id':message_id, 'producer_id':producer_id, 'scope':scope, 'payload':payload}
    decode_request(canonical(obj))
    return obj
