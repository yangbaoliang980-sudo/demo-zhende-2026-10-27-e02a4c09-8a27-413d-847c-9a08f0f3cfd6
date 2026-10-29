"""P17 pure transaction planner and commit-time revalidation.

There is deliberately no authoritative mutable store or production submit here.
"""
from __future__ import annotations
from .common import (COMMAND_VERSION,CANDIDATE_VERSION,INTERNAL_VERSION,ClosedEvidence,
    ContractError,DomainError,FrozenMessage,PlanResult,array,keys,require,identifier,
    integer,sha,fingerprint,checked_add)
from .state import validate_state
from runtime.meta.wallet import rules as wallet
from runtime.meta.characters import rules as characters
from runtime.meta.party.projection import set_party,battle_export,p13_snapshot
from yltt_framework.contracts import validate

KINDS=('APPLY_GRANT','LEVEL_UP','SKILL_UP','SET_PARTY','SET_EQUIPMENT',
       'RESERVE','RELEASE','CAPTURE','SPEND','REVOKE_STUDY')


def command(snapshot,request_id,kind,payload):
    """Convenience constructor; raw commands are still fully checked by plan()."""
    s=snapshot.value
    return FrozenMessage.from_value({'schema_version':COMMAND_VERSION,'request_id':request_id,
        'profile_id':s['profile_id'],'store_instance':s['store_instance'],
        'continuity_ref':s['continuity_ref'],'expected_revision':s['revision'],
        'expected_wallet_revision':s['wallet_revision'],'content_sha256':s['content_sha256'],
        'kind':kind,'payload':payload})


class MetaPlanner:
    def __init__(self,catalog,evidence=None,*,mode='isolated'):
        require(mode=='isolated','E_PRODUCTION_BOOTSTRAP_BLOCKED')
        self.catalog=catalog
        self.evidence=evidence if evidence is not None else ClosedEvidence()

    def plan(self,request,snapshot):
        try:
            return self._plan(request,snapshot)
        except DomainError as exc:
            if exc.code=='DUPLICATE_ENTITLEMENT_NO_OP':
                return PlanResult('DUPLICATE_NO_OP',exc.code)
            status='BLOCKED' if exc.code in {
                'E_GRANT_EVIDENCE_UNBOUND','E_COST_EVIDENCE_UNBOUND','E_REVERSAL_EVIDENCE_UNBOUND',
                'E_RECONCILIATION_REQUIRED','E_PRODUCTION_BOOTSTRAP_BLOCKED',
                'E_POLICY_UNBOUND','E_STUDY_NONWALLET_GRANT_UNBOUND'} else 'REJECTED'
            return PlanResult(status,exc.code)
        except ContractError as exc:
            return PlanResult('REJECTED','E_CONTRACT:'+str(exc))

    def _plan(self,request,snapshot):
        before=validate_state(snapshot,self.catalog)
        require(type(request) is FrozenMessage,'E_COMMAND_TYPE')
        r=request.value
        keys(r,'schema_version request_id profile_id store_instance continuity_ref expected_revision expected_wallet_revision content_sha256 kind payload')
        require(r['schema_version']==COMMAND_VERSION,'E_COMMAND_VERSION')
        for k in ('request_id','profile_id','store_instance','continuity_ref','kind'):identifier(r[k])
        integer(r['expected_revision']);integer(r['expected_wallet_revision']);sha(r['content_sha256'])
        require(type(r['payload']) is dict,'E_COMMAND_PAYLOAD')
        require(r['profile_id']==before['profile_id'],'E_BENEFICIARY_MISMATCH')
        require(r['store_instance']==before['store_instance'],'E_STORE_INSTANCE')
        require(r['continuity_ref']==before['continuity_ref'],'E_CONTINUITY_FENCE')
        old=next((x for x in before['operations'] if x['request_id']==r['request_id']),None)
        if old:
            require(old['request_sha256']==request.sha256,'E_COMMAND_ID_COLLISION')
            return PlanResult('DUPLICATE_NO_OP','DUPLICATE_NO_OP',original_revision=old['committed_revision'])
        require(r['kind'] in KINDS,'E_COMMAND_KIND')
        require(r['content_sha256']==self.catalog.sha256,'E_CONTENT_CONFLICT')
        require(r['expected_revision']==before['revision'],'E_REVISION_CONFLICT')
        require(r['expected_wallet_revision']==before['wallet_revision'],'E_WALLET_REVISION_CONFLICT')
        after=snapshot.value
        binding=None;counterpart=None;kind=r['kind'];p=r['payload']
        if kind=='APPLY_GRANT':
            keys(p,'grant_ref');identifier(p['grant_ref'])
            proof=self.evidence.resolve_grant(p['grant_ref'])
            g,key,semantic=wallet.grant_value(proof,before['profile_id'])
            require(g['grant_ref']==p['grant_ref'],'E_GRANT_REFERENCE_BINDING')
            old=next((x for x in after['entitlements'] if x['key']==key),None)
            if old:
                require(old['semantic_sha256']==semantic,'E_ENTITLEMENT_COLLISION')
                require(old['status']=='ACTIVE','E_REVOKED_ENTITLEMENT_REGRANT_BLOCKED')
                require(False,'DUPLICATE_ENTITLEMENT_NO_OP')
            for cid in g['characters']:characters.acquire(after,self.catalog,cid)
            for xp in g['xp']:characters.grant_xp(after,self.catalog,xp['character_id'],xp['amount'])
            if g['equipment']:characters.grant_equipment(after,self.catalog,g['equipment'])
            wallet.credit(after['wallet'],g,key,checked_add(before['revision'],1))
            after['entitlements'].append({'key':key,'semantic_sha256':semantic,'status':'ACTIVE','grant':g})
            after['entitlements'].sort(key=lambda x:x['key'])
            binding={'reference':p['grant_ref'],'sha256':proof.sha256}
            counterpart='P11' if g['source_kind']=='STUDY' else 'P18'
        elif kind in ('LEVEL_UP','SKILL_UP'):
            characters.upgrade(after,self.catalog,p,'LEVEL' if kind=='LEVEL_UP' else 'SKILL',r['request_id'])
        elif kind=='SET_PARTY':set_party(after,self.catalog,p)
        elif kind=='SET_EQUIPMENT':characters.set_equipment(after,self.catalog,p)
        elif kind=='RELEASE':
            keys(p,'reservation_id');wallet.release(after['wallet'],p['reservation_id'])
        elif kind in ('RESERVE','CAPTURE','SPEND'):
            keys(p,'quote_ref reservation_id' if kind in ('RESERVE','CAPTURE') else 'quote_ref')
            identifier(p['quote_ref'])
            proof=self.evidence.resolve_quote(p['quote_ref'])
            q,sk,cost_sha=wallet.quote_value(proof,before['profile_id'])
            require(q['quote_ref']==p['quote_ref'],'E_COST_REFERENCE_BINDING')
            if kind=='RESERVE':
                wallet.reserve(after['wallet'],q,sk,cost_sha,p['reservation_id'],checked_add(before['revision'],1))
            elif kind=='CAPTURE':wallet.capture(after['wallet'],q,sk,cost_sha,p['reservation_id'],r['request_id'])
            else:wallet.spend_quote(after['wallet'],q,sk,cost_sha,r['request_id'])
            binding={'reference':p['quote_ref'],'sha256':proof.sha256};counterpart='P18'
        elif kind=='REVOKE_STUDY':
            keys(p,'reversal_ref');identifier(p['reversal_ref'])
            proof=self.evidence.resolve_reversal(p['reversal_ref'])
            require(type(proof) is FrozenMessage,'E_REVERSAL_EVIDENCE_UNBOUND')
            rev=proof.value
            keys(rev,'schema_version reversal_ref issuer profile_id identity policy_sha256 eligibility_ref')
            require(rev['schema_version']=='P17-REVERSAL-INPUT/0.1.0-proposal','E_REVERSAL_VERSION')
            for k in ('reversal_ref','profile_id','eligibility_ref'):identifier(rev[k])
            require(rev['reversal_ref']==p['reversal_ref'],'E_REVERSAL_REFERENCE_BINDING')
            require(rev['issuer']=='P11','E_REVERSAL_ISSUER')
            require(rev['profile_id']==before['profile_id'],'E_BENEFICIARY_MISMATCH');sha(rev['policy_sha256'])
            key=wallet.source_identity(before['profile_id'],'STUDY',rev['identity'])
            entitlement=next((e for e in after['entitlements'] if e['key']==key),None)
            require(entitlement is not None,'E_GRANT_NOT_FOUND')
            require(entitlement['grant']['policy_sha256']==rev['policy_sha256'],'E_HISTORICAL_POLICY_MISMATCH')
            require(entitlement['status']!='REVOKED','DUPLICATE_ENTITLEMENT_NO_OP')
            wallet.revoke_unspent(after['wallet'],key);entitlement['status']='REVOKED'
            binding={'reference':p['reversal_ref'],'sha256':proof.sha256};counterpart='P11'
        after['revision']=checked_add(before['revision'],1)
        if after['wallet']!=before['wallet']:
            after['wallet_revision']=checked_add(before['wallet_revision'],1)
        after['operations'].append({'request_id':r['request_id'],'request_sha256':request.sha256,
                                    'committed_revision':after['revision']})
        after_message=FrozenMessage.from_value(after);validate_state(after_message,self.catalog)
        wire_delta=wallet.delta(before,after,request.sha256)
        validate(wire_delta,'WalletDeltaCandidate')
        validate(wallet.wallet_snapshot(after),'WalletSnapshot')
        candidate=FrozenMessage.from_value({'schema_version':CANDIDATE_VERSION,'request':r,
            'request_sha256':request.sha256,'before_sha256':snapshot.sha256,
            'after_sha256':after_message.sha256,'after_state':after,'wallet_delta':wire_delta,
            'evidence_binding':binding,'required_counterpart_owner':counterpart,
            'commit_scope':'ISOLATED_CANDIDATE_NOT_COMMITTED',
            'lock_order':[{'rank':10,'key':'profile.'+fingerprint(before['profile_id'])},
                          {'rank':20,'key':'wallet.'+fingerprint(before['profile_id'])},
                          {'rank':30,'key':'request.'+fingerprint(r['request_id'])}]})
        return PlanResult('CANDIDATE','VALIDATED_NOT_COMMITTED',candidate)

    def validate_for_commit(self,candidate,current_snapshot):
        """P21 calls this under its authoritative transaction lock/CAS boundary.

        Recomputing also revalidates the trusted evidence port; it must share
        P21's coherent evidence snapshot. The final durable commit is not here.
        """
        require(type(candidate) is FrozenMessage,'E_CANDIDATE_TYPE')
        c=candidate.value
        keys(c,'schema_version request request_sha256 before_sha256 after_sha256 after_state wallet_delta evidence_binding required_counterpart_owner commit_scope lock_order')
        require(c['schema_version']==CANDIDATE_VERSION,'E_CANDIDATE_VERSION')
        request=FrozenMessage.from_value(c['request'])
        require(request.sha256==c['request_sha256'],'E_CANDIDATE_REQUEST_HASH')
        result=self.plan(request,current_snapshot)
        if result.status=='DUPLICATE_NO_OP':return result
        require(result.status=='CANDIDATE',result.reason)
        require(result.candidate.raw==candidate.raw,'E_CANDIDATE_RECOMPUTE_MISMATCH')
        return result

    def party_export(self,snapshot):
        state=validate_state(snapshot,self.catalog)
        return battle_export(state,self.catalog)

    def character_attributes(self,snapshot,character_id):
        state=validate_state(snapshot,self.catalog)
        c=characters.owned(state,self.catalog,character_id)
        return FrozenMessage.from_value({'schema_version':'P17-ATTRIBUTES/0.1.0-isolated',
            'character_id':character_id,'revision':state['revision'],
            'content_sha256':self.catalog.sha256,'level':c['level'],'skill_rank':c['skill_rank'],
            'stats':characters.derived(state,self.catalog,character_id)})

    def party_snapshot(self,snapshot):
        return p13_snapshot(self.party_export(snapshot))

    def wallet_snapshot(self,snapshot):
        state=validate_state(snapshot,self.catalog)
        return validate(wallet.wallet_snapshot(state),'WalletSnapshot')


def atomic_proposal(candidate):
    """Existing P13 projection only for self-contained character operations.

    P11/P18 joint candidates require an owner-approved composite resolver, so
    cross-domain grants and stage consumption fail closed here.
    """
    require(type(candidate) is FrozenMessage,'E_CANDIDATE_TYPE')
    c=candidate.value
    require(c['required_counterpart_owner'] is None,'E_COUNTERPART_COMMIT_CONTRACT_UNBOUND')
    r=c['request']
    return validate({'contract_version':INTERNAL_VERSION,'dto_type':'AtomicCommitProposal',
        'transaction_id':r['request_id'],'request_sha256':c['request_sha256'],
        'transaction_kind':'CHARACTER_WALLET','domain_candidate_sha256':candidate.sha256,
        'wallet_candidate':c['wallet_delta'],'expected_domain_revision':r['expected_revision'],
        'expected_store_instance':r['store_instance']},'AtomicCommitProposal')


class UnboundP21:
    def submit(self,candidate):
        raise DomainError('E_P21_NOT_BOUND_NO_STATE_COMMITTED')

