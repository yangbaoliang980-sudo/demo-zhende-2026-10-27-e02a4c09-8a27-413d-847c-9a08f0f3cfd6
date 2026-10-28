"""Execute declared synthetic event fixtures and export real observed traces."""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

from ledger_runtime import StudyLedger
from ledger_runtime.audit import verify_audit
from ledger_runtime.types import Event, canonical, digest, strict_json
from tests.support.simulated_ports import FixtureEvidence, FixturePolicy, FixtureWallet, UNIT
from tests.support.sqlite_atomic_model import SQLiteAtomicModel

ROOT = Path(__file__).resolve().parents[1]


def run_case(case, events, directory):
    db = directory/(case['case_id']+'.p11-sim.sqlite')
    store = SQLiteAtomicModel(db)
    evidence, policy, wallet = FixtureEvidence(), FixturePolicy(), FixtureWallet()
    service = StudyLedger(store,wallet,evidence,policy)
    for key,value in case.get('policy_overrides',{}).items():
        if key not in ('available','mapping_available','reclaim','restore','category'):
            raise ValueError('unknown fixture policy override')
        setattr(policy,key,value)
    outcomes, snapshots, checkpoints, rows = {}, {}, {}, []
    for index,step in enumerate(case['steps'],1):
        action = step['action']
        output = None
        if action in ('deliver','receive'):
            raw = canonical(events[step['event']])
            fn = service.handle if action == 'deliver' else service.receive
            for _ in range(step.get('repeat',1)):
                output = fn(raw)
            outcomes[step.get('save_as',step['event'])] = output
            actual = asdict(output)
        elif action == 'spend':
            family = Event.parse(canonical(events[step['event']])).family_key
            store.fixture_spend(family,UNIT,step['amount'])
            actual = {'synthetic_p17_spend':step['amount'],'source_family':family}
        elif action == 'other_source':
            store.fixture_other_source_credit(UNIT,step['amount'])
            actual = {'synthetic_other_source_credit':step['amount']}
        elif action == 'hide_attribution':
            family = Event.parse(canonical(events[step['event']])).family_key
            store.fixture_hide_attribution(family)
            actual = {'synthetic_attribution_withheld':True}
        elif action == 'policy_available':
            policy.available = step['value']; actual = {'policy_available':policy.available}
        elif action == 'restart':
            store = SQLiteAtomicModel(db)
            service = StudyLedger(store,wallet,evidence,policy)
            actual = {'reopened_persisted_store':True}
        elif action == 'resolve':
            old = outcomes[step['outcome']]
            row = store.snapshot().ledger['inbox'][old.inbox_id]
            resolution_action = step.get('resolution_action','REPROCESS')
            target = outcomes[step['target']].inbox_id if step.get('target') else None
            evidence.grant(row,step['evidence_ref'],resolution_action,target)
            output = service.resolve(old.inbox_id,step['evidence_ref'],resolution_action)
            outcomes[step.get('save_as',step['outcome'])] = output
            actual = asdict(output)
        elif action == 'query':
            output = service.query(outcomes[step['outcome']].inbox_id)
            actual = asdict(output)
        elif action == 'snapshot':
            snapshots[step['name']] = store.snapshot(); actual = {'saved_test_backup':step['name']}
        elif action == 'checkpoint':
            checkpoints[step['name']] = store.checkpoint(); actual = checkpoints[step['name']]
        elif action == 'restore_old_backup':
            store.fixture_restore_old_backup(snapshots[step['name']]); actual = {'restore_fence':True}
        elif action == 'reconcile':
            actual = service.reconcile(checkpoints.get(step.get('checkpoint')))
        elif action == 'p21_authoritative_repair':
            store.fixture_p21_restore_authoritative_copy(); actual = {'test_p21_authoritative_repair':True}
        elif action == 'reply_loss':
            store.fault = 'after_commit_before_reply'; actual = {'fault_armed':store.fault}
        elif action == 'lookup_restore':
            store.lookup_unavailable = False; actual = {'lookup_restored':True}
        else:
            raise ValueError('unknown fixture action: '+action)
        snap = store.snapshot()
        actual['wallet_balance_in_synthetic_unit'] = snap.wallet['balances'].get(UNIT,0)
        if 'balance' in step.get('expect',{}):
            assert actual['wallet_balance_in_synthetic_unit'] == step['expect']['balance'], (case['case_id'],index,actual)
        for key in ('state','ack','reason'):
            if key in step.get('expect',{}):
                assert actual.get(key) == step['expect'][key], (case['case_id'],index,key,actual)
        rows.append({'step':index,'input':step,'observed':actual,'status':'PASS'})
    snapshot = store.snapshot()
    verify_audit(snapshot.ledger)
    return {'case_id':case['case_id'],'status':'PASS','evidence_scope':'ISOLATED_SIMULATION',
            'steps':rows,'final_ledger':snapshot.ledger,'final_wallet':snapshot.wallet,
            'commit_receipts':store.export_receipts(),'wallet_calculation_calls':wallet.calls,
            'policy_calls':policy.calls,'independent_execution':'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    data = strict_json((ROOT/'event_replay_fixtures.json').read_bytes())
    if data['schema_version'] != 'P11-EVENT-REPLAY/0.1.0':
        raise ValueError('unsupported fixtures version')
    args.output.mkdir(parents=True,exist_ok=True)
    summaries = []
    compensation = []
    with tempfile.TemporaryDirectory(prefix='p11-replay-') as temp:
        directory = Path(temp); (directory/'.P11_SIMULATION_ONLY').write_text('TEST ONLY\n')
        for case in data['cases']:
            result = run_case(case,data['events'],directory)
            destination = args.output/(case['case_id']+'.json')
            destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            summaries.append({'case_id':case['case_id'],'title':case['title'],'status':result['status'],
                              'result_path':destination.name,'sha256':digest(result),
                              'steps':len(result['steps'])})
            for entry in result['final_ledger']['audit']:
                details = entry['details']
                if details.get('compensation_pending') or details.get('reward_intent',{}).get('kind') in ('UNDO','RESTORE'):
                    compensation.append({'case_id':case['case_id'],'audit':entry,
                                         'evidence_scope':'ISOLATED_SIMULATION_NOT_PLAYER_DEBT'})
    summary = {'schema_version':'P11-REPLAY-RESULTS/0.1.0','status':'PASS',
               'fixture_sha256':__import__('hashlib').sha256((ROOT/'event_replay_fixtures.json').read_bytes()).hexdigest(),
               'case_count':len(summaries),'cases':summaries,'real_anki_execution':'NOT_RUN',
               'production_awards':0,'independent_execution':'NOT_RUN'}
    (args.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (args.output/'compensation_log.jsonl').write_text(''.join(canonical(x).decode()+'\n' for x in compensation))
    print(json.dumps({'status':'PASS','cases':len(summaries),'compensation_records':len(compensation),
                      'scope':'ISOLATED_SIMULATION','real_anki':'NOT_RUN'},ensure_ascii=False))


if __name__ == '__main__':
    main()
