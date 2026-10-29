"""Lossless party export plus explicit existing-P13 projection."""
from character_party_runtime.common import (FrozenMessage, INTERNAL_VERSION, require,
    keys, identifier, distinct, fingerprint)
from runtime.meta.characters.rules import owned, derived
from yltt_framework.contracts import validate


def validate_party(ordered_ids,owned_ids,catalog):
    require(type(ordered_ids) is list,'E_PARTY_PAYLOAD_TYPE')
    require(len(ordered_ids)==3,'E_PARTY_SIZE')
    for cid in ordered_ids: identifier(cid,'E_CHARACTER_ID_TYPE')
    distinct(ordered_ids,'E_PARTY_DUPLICATE')
    for cid in ordered_ids:catalog.character(cid)
    for cid in ordered_ids:require(cid in owned_ids,'E_CHARACTER_NOT_OWNED')
    return ordered_ids[:]


def set_party(state,catalog,payload):
    keys(payload,'ordered_character_ids','E_PARTY_PAYLOAD_TYPE')
    state['party_slots']=validate_party(payload['ordered_character_ids'],
                                      {x['character_id'] for x in state['characters']},catalog)


def battle_export(state,catalog):
    ids=validate_party(state['party_slots'],{x['character_id'] for x in state['characters']},catalog)
    members=[]
    for slot,cid in enumerate(ids):
        c=owned(state,catalog,cid);definition=catalog.character(cid)
        members.append({'unit_id':'unit.'+fingerprint({'profile':state['profile_id'],'character':cid})[:32],
            'character_id':cid,'slot':slot,'level':c['level'],'skill_id':definition['skill_id'],
            'skill_rank':c['skill_rank'],'stats':derived(state,catalog,cid),
            'equipment':[e.copy() for e in c['equipment']],
            'p03_link':{'character_id':definition['p03_character_id'],'signature_card_id':definition['signature_card_id']},
            'card_scaling':'NONE_PENDING_P03_P05_P13_P14_CONTRACT'})
    return FrozenMessage.from_value({'schema_version':'P17-PARTY-EXPORT/0.1.0-proposal',
        'profile_id':state['profile_id'],'party_id':'party.'+fingerprint(state['profile_id'])[:32],
        'revision':state['revision'],'content_version':catalog.value['content_version'],
        'content_sha256':catalog.sha256,'members':members,'scope':'ISOLATED_READ_ONLY'})


def p13_snapshot(export):
    d=export.value
    # support, skill, equipment and P03 aliases are intentionally retained in the
    # companion lossless export. They are NOT supported P13 EntityStats fields.
    msg={'contract_version':INTERNAL_VERSION,'dto_type':'PartySnapshot',
        'party_id':d['party_id'],'revision':d['revision'],'content_version':d['content_version'],
        'members':[{**{k:m[k] for k in ('unit_id','character_id','slot')},
                    **{k:m['stats'][k] for k in ('max_hp','attack','defense')}} for m in d['members']]}
    return validate(msg,'PartySnapshot')

