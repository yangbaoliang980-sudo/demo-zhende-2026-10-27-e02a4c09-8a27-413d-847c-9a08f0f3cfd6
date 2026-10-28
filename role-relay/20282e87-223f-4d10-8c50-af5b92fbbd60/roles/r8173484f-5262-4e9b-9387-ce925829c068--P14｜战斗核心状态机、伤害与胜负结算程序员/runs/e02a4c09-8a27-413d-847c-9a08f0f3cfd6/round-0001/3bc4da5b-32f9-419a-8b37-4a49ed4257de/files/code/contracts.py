"""Closed-schema validation + cross-field boundary invariants, no game resolution.

The local schema evaluator supports exactly the JSON Schema keywords used by this
delivery. Unsupported keywords fail closed. It is not a general JSON Schema engine.
Optional development verification uses the independent jsonschema implementation.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from . import CONTRACT_VERSION
from .codec import ContractError, FrozenMessage, canonical, check_profile

SCHEMA_PATH = Path(__file__).resolve().parents[3] / 'contracts/internal/internal_dto.schema.json'
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
KEYWORDS = {'$schema','$id','$defs','title','description','$ref','type','properties',
            'required','additionalProperties','items','minItems','maxItems','minimum',
            'maximum','minLength','maxLength','pattern','const','enum','oneOf','anyOf'}


def _matches(value, shape):
    try:
        validate_shape(value, shape)
        return True
    except ContractError:
        return False


def validate_shape(value, shape):
    unknown = set(shape) - KEYWORDS
    if unknown:
        raise ContractError('UNSUPPORTED_SCHEMA_KEYWORD:' + ','.join(sorted(unknown)))
    if '$ref' in shape:
        target = shape['$ref']
        if not target.startswith('#/$defs/') or target[8:] not in SCHEMA['$defs']:
            raise ContractError('UNKNOWN_LOCAL_SCHEMA_REF')
        validate_shape(value, SCHEMA['$defs'][target[8:]])
    if 'oneOf' in shape and sum(_matches(value, s) for s in shape['oneOf']) != 1:
        raise ContractError('SCHEMA_ONE_OF')
    if 'anyOf' in shape and not any(_matches(value, s) for s in shape['anyOf']):
        raise ContractError('SCHEMA_ANY_OF')
    if 'const' in shape and (type(value) is not type(shape['const']) or value != shape['const']):
        raise ContractError('SCHEMA_CONST')
    if 'enum' in shape and not any(type(value) is type(x) and value == x for x in shape['enum']):
        raise ContractError('SCHEMA_ENUM')
    kind = shape.get('type')
    types = {'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}
    if kind is not None and (kind not in types or type(value) is not types[kind]):
        raise ContractError('SCHEMA_TYPE')
    if kind == 'object':
        if not set(shape.get('required', [])) <= value.keys():
            raise ContractError('SCHEMA_REQUIRED')
        if shape.get('additionalProperties') is False and set(value) - set(shape.get('properties', {})):
            raise ContractError('SCHEMA_EXTRA_FIELD')
        for key, child in value.items():
            if key in shape.get('properties', {}):
                validate_shape(child, shape['properties'][key])
    elif kind == 'array':
        if not shape.get('minItems', 0) <= len(value) <= shape.get('maxItems', 10**20):
            raise ContractError('SCHEMA_ARRAY_SIZE')
        for child in value:
            validate_shape(child, shape['items'])
    elif kind == 'integer':
        if not shape.get('minimum', -10**20) <= value <= shape.get('maximum', 10**20):
            raise ContractError('SCHEMA_INTEGER_RANGE')
    elif kind == 'string':
        if not shape.get('minLength', 0) <= len(value) <= shape.get('maxLength', 10**20):
            raise ContractError('SCHEMA_STRING_SIZE')
        if 'pattern' in shape and not re.search(shape['pattern'], value):
            raise ContractError('SCHEMA_PATTERN')


def _require(condition, code):
    if not condition:
        raise ContractError(code)


def _unique(values, code):
    _require(len(values) == len(set(values)), code)


def validate(value, expected_type=None):
    check_profile(value)
    _require(type(value) is dict, 'DTO_OBJECT_REQUIRED')
    _require(value.get('contract_version') == CONTRACT_VERSION, 'UNSUPPORTED_CONTRACT_VERSION')
    name = value.get('dto_type')
    _require(type(name) is str and name in SCHEMA['$defs'] and name in [s['$ref'][8:] for s in SCHEMA['oneOf']], 'UNKNOWN_DTO')
    _require(expected_type is None or name == expected_type, 'WRONG_DTO_TYPE')
    validate_shape(value, SCHEMA['$defs'][name])
    _semantics(value)
    canonical(value)
    return FrozenMessage.from_value(value)


def decode(raw, expected_type=None):
    msg = FrozenMessage(raw)
    return validate(msg.value, expected_type)


def _semantics(d):
    t=d['dto_type']
    if t == 'BattleCommand' and d['kind'] == 'PLAY_CARD':
        _unique(d['payload']['target_ids'], 'DUPLICATE_TARGET')
    elif t == 'BattleSnapshot':
        units=d['units']; ids=[u['unit_id'] for u in units]
        _unique(ids,'DUPLICATE_UNIT')
        _unique([(u['side'],u['slot']) for u in units], 'DUPLICATE_UNIT_SLOT')
        for u in units:
            _require(u['hp'] <= u['max_hp'], 'HP_ABOVE_MAX')
            _unique([s['status_instance_id'] for s in u['statuses']], 'DUPLICATE_STATUS')
            _unique([s['insert_order'] for s in u['statuses']], 'DUPLICATE_STATUS_ORDER')
        cards=d['card_instances']; card_ids=[c['instance_id'] for c in cards]
        _unique(card_ids,'DUPLICATE_CARD_INSTANCE')
        _require(all(c['owner_unit_id'] in ids for c in cards),'UNKNOWN_CARD_OWNER')
        zone_ids=[i for zone in d['zones'].values() for i in zone]
        _unique(zone_ids,'CARD_IN_MULTIPLE_ZONES')
        _require(set(zone_ids)==set(card_ids),'ZONES_CARD_SET_MISMATCH')
        _unique([b['unit_id'] for b in d['boss_states']], 'DUPLICATE_BOSS')
        for b in d['boss_states']:
            _require(b['unit_id'] in ids,'UNKNOWN_BOSS')
            _unique(b['proposed_phase_ids'],'DUPLICATE_PHASE_PROPOSAL')
        mapping={'TERMINAL':{'WIN','LOSS','DRAW'},'ABORTED':{'ABORTED'},'FAULTED':{'FAULTED'}}
        _require(d['outcome'] in mapping.get(d['phase'],{'ONGOING'}),'PHASE_OUTCOME_MISMATCH')
    elif t == 'BattleState':
        _semantics(d['snapshot'])
        _unique([r['command_id'] for r in d['accepted_commands']], 'DUPLICATE_COMMAND_RECEIPT')
        for r in d['accepted_commands']:
            _require(r['committed_revision'] <= d['snapshot']['revision'],'RECEIPT_FROM_FUTURE')
            _require(r['first_event_seq'] <= r['last_event_seq'] <= d['snapshot']['last_event_seq'],'RECEIPT_SEQUENCE_RANGE')
    elif t == 'BattleCommitBatch':
        s=d['snapshot'];e=d['events'];_semantics(s)
        _require(s['battle_id']==d['battle_id'],'BATCH_BATTLE_MISMATCH')
        _require(s['revision']==d['previous_revision']+1,'BATCH_REVISION_RANGE')
        _require(e[0]['event_type']=='COMMAND_ACCEPTED' and e[-1]['event_type']=='COMMAND_COMMITTED','BATCH_SENTINELS')
        _require(sum(x['event_type']=='COMMAND_ACCEPTED' for x in e)==1 and sum(x['event_type']=='COMMAND_COMMITTED' for x in e)==1,'DUPLICATE_BATCH_SENTINEL')
        _require(e[-1]['data']['revision']==s['revision'],'COMMIT_REVISION_MISMATCH')
        _require(e[-1]['seq']==s['last_event_seq'],'BATCH_LAST_SEQ_MISMATCH')
        for index,x in enumerate(e):
            _require((x['battle_id'],x['command_id'],x['revision'])==(d['battle_id'],d['command_id'],s['revision']),'EVENT_SCOPE_MISMATCH')
            if index:
                _require(x['seq']==e[index-1]['seq']+1,'BATCH_SEQUENCE_GAP')
    elif t == 'BattleReply':
        if d['result']=='COMMITTED':
            _require(d['commit'] is not None,'COMMITTED_WITHOUT_BATCH')
            _semantics(d['commit'])
            _require((d['battle_id'],d['command_id'],d['observed_revision'])==(d['commit']['battle_id'],d['commit']['command_id'],d['commit']['snapshot']['revision']),'REPLY_BINDING_MISMATCH')
        else:
            _require(d['commit'] is None,'REPLAY_MUST_NOT_REPUBLISH_EVENTS')
    elif t == 'DeckPatchCandidate':
        _require(d['rng_before']['initial_seed']==d['rng_after']['initial_seed'],'RNG_SEED_CHANGE')
        _require(d['rng_after']['draw_count']>=d['rng_before']['draw_count'],'RNG_COUNT_REGRESSION')
    elif t == 'PartySnapshot':
        _require({m['slot'] for m in d['members']}=={0,1,2},'PARTY_SLOT_SET')
        _unique([m['unit_id'] for m in d['members']],'DUPLICATE_PARTY_UNIT')
        _unique([m['character_id'] for m in d['members']],'DUPLICATE_PARTY_CHARACTER')
    elif t == 'WalletSnapshot':
        _unique([x['resource_id'] for x in d['balances']],'DUPLICATE_WALLET_RESOURCE')
    elif t == 'WalletDeltaCandidate':
        _unique([x['resource_id'] for x in d['changes']],'DUPLICATE_WALLET_DELTA_RESOURCE')
        # Attribution is mandatory for any nonzero change; no policy computation.
        by_resource={}
        for a in d['allocations']:
            p=by_resource.setdefault(a['resource_id'],[0,0])
            p[0]+=a['available_delta'];p[1]+=a['reserved_delta']
        expected={x['resource_id']:[x['available_delta'],x['reserved_delta']] for x in d['changes']}
        _require(by_resource==expected,'WALLET_ATTRIBUTION_MISMATCH')
    elif t == 'CommitProofView':
        _require(d['sequence']<=d['high_watermark'],'PROOF_ABOVE_WATERMARK')
    elif t == 'StudyStatusView':
        if d['commit_proof'] is not None:
            p=d['commit_proof'];_semantics(p)
            _require((p['store_instance'],p['high_watermark'],p['continuity_ref'])==(d['observed_store_instance'],d['observed_high_watermark'],d['continuity_ref']),'STUDY_PROOF_SCOPE_MISMATCH')
        if d['state'] in {'APPLIED','REVERTED','QUARANTINED','PENDING_RECONCILIATION','REJECTED'}:
            _require(d['commit_proof'] is not None,'PERSISTED_STATE_WITHOUT_PROOF')
        if d['state']=='NOT_FOUND':
            _require(d['continuity_ref'] is not None and d['observed_store_instance'] is not None and d['observed_high_watermark'] is not None,'ABSENCE_WITHOUT_CONTINUITY')
        if d['state'] in {'NOT_FOUND','UNKNOWN'}:
            _require(d['commit_proof'] is None,'ABSENT_UNKNOWN_WITH_COMMIT_PROOF')
    elif t == 'AtomicCommitProposal' and d['wallet_candidate'] is not None:
        _semantics(d['wallet_candidate'])
    elif t == 'CommitLookupView':
        _require((d['status']=='COMMITTED') == (d['proof'] is not None),'LOOKUP_PROOF_MISMATCH')
        if d['proof']:
            p=d['proof'];_semantics(p);_require(d['transaction_id']==p['transaction_id'],'LOOKUP_TX_MISMATCH')
            _require((p['store_instance'],p['high_watermark'],p['continuity_ref'])==(d['observed_store_instance'],d['observed_high_watermark'],d['continuity_ref']),'LOOKUP_CONTINUITY_MISMATCH')
        if d['status']=='ABSENT':
            _require(d['continuity_ref'] is not None and d['observed_store_instance'] is not None and d['observed_high_watermark'] is not None,'LOOKUP_ABSENCE_WITHOUT_CONTINUITY')
    elif t == 'StageProgressView':
        _unique(d['unlocked_stage_ids'],'DUPLICATE_UNLOCK');_unique(d['first_clear_stage_ids'],'DUPLICATE_FIRST_CLEAR')
    elif t == 'SaveStatusView' and d['state']=='READY':
        _require(all(d[k] is not None for k in ['store_instance','save_format_version','high_watermark']),'READY_WITHOUT_STORE_BINDING')

