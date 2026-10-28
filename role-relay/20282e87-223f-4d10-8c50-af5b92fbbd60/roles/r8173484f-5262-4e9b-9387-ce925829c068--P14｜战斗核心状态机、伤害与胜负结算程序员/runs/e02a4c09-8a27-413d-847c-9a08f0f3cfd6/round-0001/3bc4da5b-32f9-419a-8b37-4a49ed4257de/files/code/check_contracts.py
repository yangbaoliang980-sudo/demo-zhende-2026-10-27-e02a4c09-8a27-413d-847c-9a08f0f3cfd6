"""Independent JSON Schema implementation over actual runtime outputs.

This is an AUTHOR check using jsonschema, not P32 independent test acceptance.
"""
from pathlib import Path
import importlib.metadata,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from examples.demo import run_demo
from resolution_replay_tests.p02_adapter import CASES,BLOCKED_HISTORY,make_case,execute


def main():
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        result={'status':'BLOCKED','execution':'NOT_RUN','layer':'OPTIONAL_AUTHOR_SCHEMA_ALGORITHM_CROSSCHECK',
            'reason':'jsonschema==4.25.1 not installed; dependency download encountered network permission denial',
            'required_dependency':'jsonschema==4.25.1','P13_frozen_validator_author_tests':'PASS',
            'evidence_of_original_failed_attempt':'evidence/runs/contracts_001',
            'P32_independent_contract_test':'NOT_RUN'}
        (ROOT/'evidence/contract_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False));return 3
    schema=json.loads((ROOT/'upstream/P13/contracts/internal/internal_dto.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    objects=[]
    core,out=run_demo();objects.extend([core.state().value,core.result().value,out['snapshot']])
    objects.extend(out['commands']+out['replies']+out['batches'])
    for entry in out['replay']['entries']:
        objects.extend(x['candidate'] for x in entry['inputs'])
    for cid in CASES:
        if cid in BLOCKED_HISTORY:continue
        c,commands,_,_=make_case(cid);replies=execute(c,commands)
        objects.extend(x.value for x in commands+replies);objects.append(c.state().value)
        objects.append(c.state().value['snapshot'])
        if c.result() is not None:objects.append(c.result().value)
        for b in c.committed_batches():objects.append(b.value);objects.extend(b.value['events'])
        for entry in c.export_replay().entries:
            objects.extend(x['candidate'] for x in entry.value['inputs'])
    for index,value in enumerate(objects):
        errors=list(validator.iter_errors(value))
        if errors:
            print(json.dumps({'status':'FAIL','index':index,'dto_type':value.get('dto_type'),
                'errors':[e.message for e in errors]},ensure_ascii=False));return 1
    result={'status':'PASS','layer':'AUTHOR_CONTRACT_SCHEMA_VALIDATION',
        'implementation':'jsonschema','version':importlib.metadata.version('jsonschema'),
        'instances_checked':len(objects),'schema':'upstream/P13/contracts/internal/internal_dto.schema.json',
        'P32_independent_contract_test':'NOT_RUN'}
    (ROOT/'evidence/contract_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
