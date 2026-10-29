"""Source-attributed wallet candidate arithmetic. This module never commits.

All helpers work on an unpublished deep copy owned by the P17 planner. Durable
uniqueness, snapshot fencing and receipt publication belong to P21.
"""
from __future__ import annotations
from character_party_runtime.common import (
    GRANT_VERSION, QUOTE_VERSION, INTERNAL_VERSION, FrozenMessage,
    keys, require, integer, identifier, sha, array, distinct, indexed,
    resource_rows, fingerprint, checked_add)


def empty_wallet():
    return {'lots': [], 'reservations': [], 'consumptions': []}


def source_identity(profile_id, kind, identity):
    """First-clear identity intentionally excludes battle, policy and delivery IDs."""
    if kind == 'STUDY':
        keys(identity, 'source_id collection_lineage family_id')
    elif kind == 'STAGE_FIRST_CLEAR':
        keys(identity, 'campaign_id stage_id')
    elif kind == 'STAGE_REPEAT':
        keys(identity, 'campaign_id stage_id battle_id')
    else:
        require(False, 'E_SOURCE_KIND_UNAPPROVED')
    for x in identity.values(): identifier(x)
    return fingerprint({'profile_id': profile_id, 'source_kind':kind, 'identity':identity})


def grant_value(message, profile_id):
    require(type(message) is FrozenMessage, 'E_GRANT_EVIDENCE_UNBOUND')
    g=message.value
    keys(g, 'schema_version grant_ref issuer profile_id source_kind identity eligibility_ref policy_version policy_sha256 resources characters xp equipment')
    require(g['schema_version']==GRANT_VERSION, 'E_GRANT_VERSION')
    for k in ('grant_ref','profile_id','eligibility_ref','policy_version'): identifier(g[k])
    sha(g['policy_sha256'])
    require(g['profile_id']==profile_id, 'E_BENEFICIARY_MISMATCH')
    grant_key=source_identity(profile_id,g['source_kind'],g['identity'])
    require(g['issuer']==('P11' if g['source_kind']=='STUDY' else 'P18'), 'E_GRANT_ISSUER')
    g['resources']=resource_rows(g['resources'],allow_empty=True)
    for key in ('characters','xp','equipment'): array(g[key])
    for cid in g['characters']: identifier(cid, 'E_CHARACTER_ID_TYPE')
    distinct(g['characters'], 'E_CHARACTER_GRANT_DUPLICATE')
    for x in g['xp']:
        keys(x,'character_id amount'); identifier(x['character_id']); integer(x['amount'],1)
    distinct([x['character_id'] for x in g['xp']], 'E_XP_GRANT_DUPLICATE')
    for e in g['equipment']:
        keys(e,'instance_id definition_id'); identifier(e['instance_id']); identifier(e['definition_id'])
    distinct([e['instance_id'] for e in g['equipment']], 'E_EQUIPMENT_DUPLICATE')
    require(any(g[k] for k in ('resources','characters','xp','equipment')), 'E_EMPTY_GRANT')
    if g['source_kind']=='STUDY':
        require(not(g['characters'] or g['xp'] or g['equipment']), 'E_STUDY_NONWALLET_GRANT_UNBOUND')
    # References prove admission at the external port; they do not reset the
    # one-entitlement identity or change the economic content fingerprint.
    semantic={k:v for k,v in g.items() if k not in ('grant_ref','eligibility_ref')}
    return g,grant_key,fingerprint(semantic)


def source_ref(g, grant_key):
    return {'source_kind':g['source_kind'], 'source_key':grant_key,
            'policy_version':g['policy_version'],'policy_sha256':g['policy_sha256']}


def credit(wallet, g, grant_key, revision):
    source=source_ref(g,grant_key)
    for r in g['resources']:
        lot_id=fingerprint({'source_key':grant_key,'resource_id':r['resource_id']})
        require(all(x['lot_id']!=lot_id for x in wallet['lots']), 'E_SOURCE_LOT_COLLISION')
        wallet['lots'].append({'lot_id':lot_id, 'source':source.copy(),
            'resource_id':r['resource_id'], 'quantity':r['amount'],
            'available':r['amount'],'reserved':0,'spent':0,'revoked':0,
            'created_revision':revision})
    wallet['lots'].sort(key=lambda x:x['lot_id'])
    balances(wallet)  # Combined-resource overflow must fail before publication.


def balances(wallet):
    result={}
    for lot in wallet['lots']:
        b=result.setdefault(lot['resource_id'],{'resource_id':lot['resource_id'],'available':0,'reserved':0})
        for k in ('available','reserved'): b[k]=checked_add(b[k],lot[k])
    return [result[k] for k in sorted(result)]


def available(wallet, resource_id):
    return sum(x['available'] for x in wallet['lots'] if x['resource_id']==resource_id)


def allocate(wallet, costs):
    costs=resource_rows(costs)
    for r in costs:
        require(available(wallet,r['resource_id'])>=r['amount'], 'E_WALLET_INSUFFICIENT')
    allocations=[]
    for r in costs:
        remaining=r['amount']
        for lot in sorted(wallet['lots'],key=lambda x:(x['created_revision'],x['lot_id'])):
            if lot['resource_id']!=r['resource_id']: continue
            take=min(remaining,lot['available'])
            if take:
                allocations.append({'lot_id':lot['lot_id'],'resource_id':r['resource_id'],'amount':take})
                remaining-=take
            if not remaining: break
        require(remaining==0,'E_SOURCE_ALLOCATION_INCOMPLETE')
    return allocations


def move(wallet, allocations, from_field, to_field):
    lots=indexed(wallet['lots'],'lot_id')
    for a in allocations:
        l=lots[a['lot_id']]
        require(l[from_field]>=a['amount'],'E_SOURCE_BALANCE_UNDERFLOW')
        l[from_field]-=a['amount']; l[to_field]=checked_add(l[to_field],a['amount'])


def spend_character(wallet, costs, purpose_key, request_id):
    """P17's own approved-by-content transition cost, never caller supplied."""
    spend_key=fingerprint({'owner':'P17','purpose_key':purpose_key})
    require(all(x['spend_key']!=spend_key for x in wallet['consumptions']), 'E_CONSUMPTION_COLLISION')
    allocations=allocate(wallet,costs)
    move(wallet,allocations,'available','spent')
    wallet['consumptions'].append({'spend_key':spend_key,'cost_sha256':fingerprint(costs),
        'request_id':request_id,'allocations':allocations})


def quote_value(message, profile_id):
    require(type(message) is FrozenMessage,'E_COST_EVIDENCE_UNBOUND')
    q=message.value
    keys(q,'schema_version quote_ref issuer profile_id purpose_key eligibility_ref policy_version policy_sha256 resources')
    require(q['schema_version']==QUOTE_VERSION,'E_COST_VERSION')
    require(q['issuer']=='P18','E_COST_ISSUER')
    for k in ('quote_ref','profile_id','purpose_key','eligibility_ref','policy_version'): identifier(q[k])
    sha(q['policy_sha256']); require(q['profile_id']==profile_id,'E_BENEFICIARY_MISMATCH')
    q['resources']=resource_rows(q['resources'])
    sk=fingerprint({'profile_id':profile_id,'owner':'P18','purpose_key':q['purpose_key']})
    semantic={k:v for k,v in q.items() if k not in ('quote_ref','eligibility_ref')}
    return q,sk,fingerprint(semantic)


def check_spend_identity(wallet, spend_key, cost_sha):
    old=next((x for x in wallet['consumptions'] if x['spend_key']==spend_key),None)
    if old:
        require(old['cost_sha256']==cost_sha,'E_CONSUMPTION_COLLISION')
        require(False,'DUPLICATE_ENTITLEMENT_NO_OP')
    for r in wallet['reservations']:
        if r['spend_key']==spend_key:
            require(r['cost_sha256']==cost_sha,'E_CONSUMPTION_COLLISION')


def reserve(wallet, quote, spend_key, cost_sha, reservation_id, revision):
    identifier(reservation_id)
    check_spend_identity(wallet,spend_key,cost_sha)
    require(all(r['reservation_id']!=reservation_id for r in wallet['reservations']),'E_RESERVATION_ID_REUSED')
    require(not any(r['spend_key']==spend_key and r['status']=='ACTIVE' for r in wallet['reservations']),
            'E_PURPOSE_ALREADY_RESERVED')
    allocations=allocate(wallet,quote['resources'])
    move(wallet,allocations,'available','reserved')
    wallet['reservations'].append({'reservation_id':reservation_id,'spend_key':spend_key,
        'cost_sha256':cost_sha,'resources':quote['resources'],'status':'ACTIVE',
        'created_revision':revision,'allocations':allocations})


def reservation(wallet, reservation_id):
    identifier(reservation_id)
    r=next((x for x in wallet['reservations'] if x['reservation_id']==reservation_id),None)
    require(r is not None,'E_RESERVATION_NOT_FOUND')
    return r


def release(wallet, reservation_id):
    r=reservation(wallet,reservation_id)
    if r['status']=='RELEASED': require(False,'DUPLICATE_ENTITLEMENT_NO_OP')
    require(r['status']=='ACTIVE','E_RESERVATION_NOT_ACTIVE')
    move(wallet,r['allocations'],'reserved','available');r['status']='RELEASED'


def capture(wallet, quote, spend_key, cost_sha, reservation_id, request_id):
    r=reservation(wallet,reservation_id)
    require((r['spend_key'],r['cost_sha256'])==(spend_key,cost_sha),'E_RESERVATION_BINDING')
    check_spend_identity(wallet,spend_key,cost_sha)
    require(r['status']=='ACTIVE','E_RESERVATION_NOT_ACTIVE')
    move(wallet,r['allocations'],'reserved','spent');r['status']='CAPTURED'
    wallet['consumptions'].append({'spend_key':spend_key,'cost_sha256':cost_sha,
        'request_id':request_id,'allocations':r['allocations']})


def spend_quote(wallet, quote, spend_key, cost_sha, request_id):
    check_spend_identity(wallet,spend_key,cost_sha)
    require(not any(r['spend_key']==spend_key and r['status']=='ACTIVE' for r in wallet['reservations']),
            'E_PURPOSE_ALREADY_RESERVED')
    allocations=allocate(wallet,quote['resources']);move(wallet,allocations,'available','spent')
    wallet['consumptions'].append({'spend_key':spend_key,'cost_sha256':cost_sha,
        'request_id':request_id,'allocations':allocations})


def revoke_unspent(wallet, source_key):
    lots=[x for x in wallet['lots'] if x['source']['source_key']==source_key]
    require(bool(lots),'E_GRANT_NOT_FOUND')
    require(all(x['spent']==0 and x['reserved']==0 for x in lots),'E_RECONCILIATION_REQUIRED')
    for lot in lots:
        lot['revoked']=checked_add(lot['revoked'],lot['available']);lot['available']=0


def delta(before_state, after_state, request_sha):
    """P13 projection; complete provenance remains in the P17 candidate."""
    before=before_state['wallet'];after=after_state['wallet']
    old=indexed(before['lots'],'lot_id');new=indexed(after['lots'],'lot_id')
    allocations=[];totals={}
    for lid in sorted(set(old)|set(new)):
        b=old.get(lid,{});a=new.get(lid,{})
        av=a.get('available',0)-b.get('available',0);rs=a.get('reserved',0)-b.get('reserved',0)
        if not(av or rs):continue
        lot=a or b;rid=lot['resource_id']
        allocations.append({'resource_id':rid,'source':lot['source'].copy(),
                            'available_delta':av,'reserved_delta':rs})
        t=totals.setdefault(rid,[0,0]);t[0]+=av;t[1]+=rs
    return {'contract_version':INTERNAL_VERSION,'dto_type':'WalletDeltaCandidate',
        'wallet_id':'wallet.'+fingerprint(before_state['profile_id'])[:32],'beneficiary_id':before_state['profile_id'],
        'intent_sha256':request_sha,'expected_wallet_revision':before_state['wallet_revision'],
        'wallet_before_sha256':fingerprint(wallet_snapshot(before_state)),
        'changes':[{'resource_id':rid,'available_delta':t[0],'reserved_delta':t[1]} for rid,t in sorted(totals.items())],
        'allocations':allocations,'unresolved':False,'reason_code':'ISOLATED_CANDIDATE_ONLY'}


def wallet_snapshot(state):
    return {'contract_version':INTERNAL_VERSION,'dto_type':'WalletSnapshot',
        'wallet_id':'wallet.'+fingerprint(state['profile_id'])[:32],'beneficiary_id':state['profile_id'],
        'revision':state['wallet_revision'],'balances':balances(state['wallet'])}


def validate_wallet(wallet, revision):
    keys(wallet,'lots reservations consumptions')
    for k in wallet:array(wallet[k])
    for lot in wallet['lots']:
        keys(lot,'lot_id source resource_id quantity available reserved spent revoked created_revision')
        sha(lot['lot_id']);identifier(lot['resource_id'])
        keys(lot['source'],'source_kind source_key policy_version policy_sha256')
        require(lot['source']['source_kind'] in ('STUDY','STAGE_FIRST_CLEAR','STAGE_REPEAT'),'E_SOURCE_KIND_UNAPPROVED')
        sha(lot['source']['source_key']);identifier(lot['source']['policy_version']);sha(lot['source']['policy_sha256'])
        require(lot['lot_id']==fingerprint({'source_key':lot['source']['source_key'],'resource_id':lot['resource_id']}),
                'E_LOT_ID_BINDING')
        integer(lot['quantity'],1)
        for f in ('available','reserved','spent','revoked'):integer(lot[f])
        integer(lot['created_revision'],1,revision)
        require(lot['quantity']==sum(lot[f] for f in ('available','reserved','spent','revoked')),'E_LOT_CONSERVATION')
    distinct([x['lot_id'] for x in wallet['lots']],'E_LOT_DUPLICATE')
    lots=indexed(wallet['lots'],'lot_id')
    reserved_totals={k:0 for k in lots};spent_totals={k:0 for k in lots}
    for r in wallet['reservations']:
        keys(r,'reservation_id spend_key cost_sha256 resources status created_revision allocations')
        identifier(r['reservation_id']);sha(r['spend_key']);sha(r['cost_sha256'])
        integer(r['created_revision'],1,revision);resource_rows(r['resources'])
        require(r['status'] in ('ACTIVE','CAPTURED','RELEASED'),'E_RESERVATION_STATUS')
        _validate_allocations(r['allocations'],lots)
        amounts={}
        for a in r['allocations']:
            amounts[a['resource_id']]=amounts.get(a['resource_id'],0)+a['amount']
            if r['status']=='ACTIVE':reserved_totals[a['lot_id']]+=a['amount']
        require(amounts=={x['resource_id']:x['amount'] for x in r['resources']},'E_RESERVATION_ALLOCATION')
    distinct([r['reservation_id'] for r in wallet['reservations']],'E_RESERVATION_DUPLICATE')
    distinct([r['spend_key'] for r in wallet['reservations'] if r['status']=='ACTIVE'],'E_PURPOSE_ALREADY_RESERVED')
    for c in wallet['consumptions']:
        keys(c,'spend_key cost_sha256 request_id allocations')
        sha(c['spend_key']);sha(c['cost_sha256']);identifier(c['request_id'])
        _validate_allocations(c['allocations'],lots)
        for a in c['allocations']:spent_totals[a['lot_id']]+=a['amount']
    distinct([c['spend_key'] for c in wallet['consumptions']],'E_CONSUMPTION_DUPLICATE')
    spent=indexed(wallet['consumptions'],'spend_key')
    for r in wallet['reservations']:
        c=spent.get(r['spend_key'])
        if r['status']=='CAPTURED':
            require(c is not None and c['cost_sha256']==r['cost_sha256'] and c['allocations']==r['allocations'],
                    'E_CAPTURE_RECEIPT_BINDING')
        if r['status']=='ACTIVE':require(c is None,'E_RESERVED_AND_CONSUMED')
    for lid,lot in lots.items():
        require(lot['reserved']==reserved_totals[lid],'E_RESERVED_ATTRIBUTION')
        require(lot['spent']==spent_totals[lid],'E_SPENT_ATTRIBUTION')
    balances(wallet)


def _validate_allocations(rows,lots):
    array(rows);require(bool(rows),'E_EMPTY_ALLOCATION')
    for a in rows:
        keys(a,'lot_id resource_id amount');sha(a['lot_id']);identifier(a['resource_id']);integer(a['amount'],1)
        require(a['lot_id'] in lots and lots[a['lot_id']]['resource_id']==a['resource_id'],'E_ALLOCATION_SOURCE')
    distinct([a['lot_id'] for a in rows],'E_ALLOCATION_DUPLICATE')
