"""Author semantic checks, not an independent P22/P32 contract acceptance."""
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'design/linguistic/reference'))
from pos_mapper import load_rules,strict_json,classify,ROLES,CATEGORIES

def verify():
    rules=load_rules(ROOT/'content/linguistic/pos_mapping_rules.json')
    profile=strict_json((ROOT/'content/linguistic/field_profile.synthetic.json').read_bytes())
    cases=[strict_json(l) for l in (ROOT/'content/linguistic/classification_cases.jsonl').read_text().splitlines()]
    assert len({c['case_id'] for c in cases})==len(cases),'duplicate case id'
    results=[]
    for c in cases:
        p=dict(profile);p.update(c.get('profile_patch',{}))
        r=classify(c['input'],None if c.get('missing_rules') else rules,p)
        errors=[k for k,v in c['expected'].items() if r.get(k)!=v]
        assert r['formal_resource_id'] is None and r['quantity'] is None and r['reward_effect']=='NONE_PREVIEW_ONLY'
        results.append({'case_id':c['case_id'],'status':'FAIL' if errors else 'PASS','mismatched_keys':errors,'result':r})
    dictionary=json.loads((ROOT/'content/linguistic/category_dictionary.json').read_text())
    assert dictionary['categories']==rules.data['categories'],'dictionary mismatch'
    table=list(csv.DictReader((ROOT/'content/linguistic/resource_affinity_candidates.tsv').open(),delimiter='\t'))
    assert len(table)==8 and {r['category'] for r in table}==set(CATEGORIES)
    upstream=list(csv.DictReader((ROOT/'design/linguistic/evidence/readonly_sources/p08_resource_mapping_candidates.tsv').open(),delimiter='\t'))
    assert [r['resource_role_proposal'] for r in table]==[r['resource_role_proposal'] for r in upstream],'P08 boundary mismatch'
    assert all(r['formal_resource_id']=='UNSET' and r['quantity']=='UNSET' and r['selected_economy_model']=='UNSET' and r['production_authorized']=='false' for r in table),'unauthorized resource proposal'
    unknown=list(csv.DictReader((ROOT/'content/linguistic/unknown_fallback_cases.tsv').open(),delimiter='\t'))
    expected_unknown={c['case_id']:c for c in cases if c['expected']['category']=='UNKNOWN'}
    assert len(unknown)==len(expected_unknown) and {r['case_id'] for r in unknown}==set(expected_unknown)
    for r in unknown:
        assert r['reason_code']==expected_unknown[r['case_id']]['expected']['reason_code'] and r['expected_resource_role_proposal']=='GENERAL_MATERIAL'
    registry=json.loads((ROOT/'content/linguistic/mapping_release_registry.json').read_text())
    assert registry['releases'][0]['sha256']==rules.sha256 and registry['active_production_version'] is None
    for file in (ROOT/'content/linguistic/schema').glob('*.json'):
        schema=strict_json(file.read_bytes());assert schema['$schema']=='https://json-schema.org/draft/2020-12/schema'
    return {'status':'FAIL' if any(r['status']=='FAIL' for r in results) else 'PASS','scope':'SYNTHETIC_AUTHOR_REFERENCE_CHECK',
            'cases':len(cases),'unknown_cases':len(unknown),'formal_anki_events_observed':0,'real_rewards_issued':0,
            'json_schema_engine_validation':'NOT_RUN_P22_REQUIRED','results':results}

def main():
    p=argparse.ArgumentParser();p.add_argument('--formal',action='store_true');args=p.parse_args()
    try:
        if args.formal:
            pre=json.loads((ROOT/'design/linguistic/formal_prerequisites.json').read_text())
            print(json.dumps({'status':'BLOCKED','reason':'SYNTHETIC_PACKAGE_CANNOT_AUTHORIZE_PRODUCTION','checks':pre['checks'],'real_anki_events_observed':0,'production_authorized':False},ensure_ascii=False,indent=2));return 3
        report=verify();print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['status']=='PASS' else 1
    except Exception as e:
        print(json.dumps({'status':'FAIL','error':str(e)},ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
