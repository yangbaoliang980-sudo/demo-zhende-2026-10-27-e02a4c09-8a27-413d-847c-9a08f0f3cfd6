"""Generate reviewable outputs by executing P14; never read expected into core."""
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples.demo import run_demo
from battle_core.replay import replay
from battle_core.wire import canonical
from resolution_replay_tests.p02_adapter import (CASES,BLOCKED_HISTORY,make_case,execute,
    projected_state,projected_expected_state,expected_event_projection,SOURCE_SHA)


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    core,out=run_demo()
    (ROOT/'battle_snapshot.json').write_bytes(core.snapshot('fixture:demo').raw)
    (ROOT/'battle_state.json').write_bytes(core.state().raw)
    (ROOT/'battle_result.json').write_bytes(core.result().raw)
    dump(ROOT/'examples/demo_replay.json',out['replay'])
    dump(ROOT/'examples/demo_execution.json',out)
    samples=[{'sample_id':'P03-scripted-demo','fixture_only':True,'batches':out['batches'],
              'state_sha256':core.state().sha256,'result':out['result']}]
    reports=[]
    for cid,c in CASES.items():
        if cid in BLOCKED_HISTORY:
            reports.append({'fixture_id':cid,'status':'BLOCKED','runtime_execution':'NOT_RUN',
                'reason':'LEGACY_RECEIPT_FULL_COMMAND_AND_EVENT_RANGE_MISSING','source_fixture_sha256':SOURCE_SHA})
            continue
        battle,commands,deck,enemy=make_case(cid);replies=execute(battle,commands)
        assert projected_state(battle)==projected_expected_state(c),cid
        expected=expected_event_projection(c)
        actual=[e for b in battle.committed_batches() for e in b.value['events']]
        assert len(actual)==len(expected),cid
        for e,(name,data) in zip(actual,expected):
            assert e['event_type']==name and {k:e['data'][k] for k in data}==data,cid
        again=replay(battle.export_replay())
        assert again.state().raw==battle.state().raw,cid
        assert [b.raw for b in again.committed_batches()]==[b.raw for b in battle.committed_batches()],cid
        report={'fixture_id':cid,'status':'PASS','layer':'AUTHOR_P02_SEMANTIC_PROJECTION',
            'original_wire_byte_compatibility':'BLOCKED_PENDING_P02_P13_MAPPING_ACCEPTANCE',
            'source_fixture_sha256':SOURCE_SHA,'state_sha256':battle.state().sha256,
            'snapshot_sha256':battle.snapshot(c['initial_state']['battle_id']).sha256,
            'event_count':len(actual),'legacy_event_count':len(c['expected']['logic_events']),
            'replay_sha256':battle.export_replay().sha256,'p15_calls':deck.calls,
            'p16_calls':0 if enemy is None else enemy.calls,'replies':[r.value for r in replies]}
        reports.append(report)
        if cid in ('F006','F008','F014','F030','F031'):
            samples.append({'sample_id':'P02-'+cid,'fixture_only':True,
                'batches':[b.value for b in battle.committed_batches()],
                'state_sha256':battle.state().sha256,'result':None if battle.result() is None else battle.result().value})
    dump(ROOT/'battle_event_samples.json',{'format':'P14-BATTLE-EVENT-SAMPLES/0.1.0-isolated',
        'contract_version':'YLTT-INTERNAL/0.1.0-isolated','scope':'ACTUAL_ISOLATED_EXECUTION_WITH_SCRIPTED_CANDIDATES',
        'samples':samples})
    dump(ROOT/'evidence/p02_projection_results.json',{'format':'P14-P02-PROJECTION-RESULTS/0.1.0',
        'pass_count':sum(x['status']=='PASS' for x in reports),'blocked_count':sum(x['status']=='BLOCKED' for x in reports),
        'cases':reports})
    dump(ROOT/'evidence/demo_summary.json',{'scope':out['scope'],'commands_committed':out['snapshot']['revision'],
        'events_committed':out['snapshot']['last_event_seq'],'outcome':out['result']['outcome'],
        'player_turn_number':out['snapshot']['turn_number'],'p15_candidate_calls':out['p15_calls'],
        'p16_candidate_calls':out['p16_calls'],'terminal_event_seq':out['result']['terminal_event_seq'],
        'snapshot_file_sha256':hashlib.sha256((ROOT/'battle_snapshot.json').read_bytes()).hexdigest(),
        'result_file_sha256':hashlib.sha256((ROOT/'battle_result.json').read_bytes()).hexdigest(),
        'replay_input_sha256':out['replay']['sha256']})
    print(json.dumps({'p02_semantic_cases_passed':sum(x['status']=='PASS' for x in reports),
        'p02_cases_blocked':sum(x['status']=='BLOCKED' for x in reports),'demo_revision':out['snapshot']['revision'],
        'demo_events':out['snapshot']['last_event_seq'],'demo_outcome':out['result']['outcome']},ensure_ascii=False))


if __name__=='__main__':main()
