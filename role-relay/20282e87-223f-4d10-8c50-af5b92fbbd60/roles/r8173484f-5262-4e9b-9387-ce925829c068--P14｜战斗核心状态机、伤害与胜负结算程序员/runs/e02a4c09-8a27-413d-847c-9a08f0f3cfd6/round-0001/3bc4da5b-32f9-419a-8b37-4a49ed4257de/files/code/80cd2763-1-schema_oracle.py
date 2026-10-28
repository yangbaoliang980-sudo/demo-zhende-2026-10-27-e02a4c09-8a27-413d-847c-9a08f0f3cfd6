"""Compare the shipped local schema evaluator with jsonschema, excluding semantic rules."""
import copy
import importlib.metadata
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from runtime.framework.yltt_framework.codec import ContractError, check_profile
from runtime.framework.yltt_framework.contracts import SCHEMA, validate_shape


def leaves(value,path=()):
    if isinstance(value,dict):
        for k,v in value.items():yield from leaves(v,path+(k,))
    elif isinstance(value,list):
        for k,v in enumerate(value):yield from leaves(v,path+(k,))
    else:yield path


def main():
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    oracle=jsonschema.Draft202012Validator(SCHEMA)
    count=0;skipped=0;valid=0;invalid=0;failures=[]
    cases=[]
    for p in sorted((ROOT/'contracts/internal/examples').glob('*.json')):
        original=json.loads(p.read_text());cases.append((p.stem+':valid',original))
        for field in original:
            v=copy.deepcopy(original);del v[field];cases.append((p.stem+':missing:'+field,v))
        v=copy.deepcopy(original);v['unexpected']=True;cases.append((p.stem+':extra',v))
        for path in leaves(original):
            for replacement in [None,True,False,-1,0,1,9007199254740992,'','UNKNOWN',[],{}]:
                v=copy.deepcopy(original);parent=v
                for k in path[:-1]:parent=parent[k]
                parent[path[-1]]=replacement;cases.append((p.stem+':'+str(path)+':'+repr(replacement),v))
    for label,value in cases:
        try:check_profile(value)
        except ContractError:skipped+=1;continue
        expected=oracle.is_valid(value)
        try:validate_shape(value,SCHEMA);actual=True
        except ContractError:actual=False
        count+=1;valid+=expected;invalid+=not expected
        if actual!=expected:failures.append({'label':label,'expected':expected,'actual':actual})
    result={'status':'PASS' if not failures else 'FAIL','scope':'STRUCTURAL_SCHEMA_ORACLE_AUTHOR_CHECK_ONLY','cases_compared':count,'valid_by_schema':valid,'invalid_by_schema':invalid,'excluded_by_wire_profile':skipped,'semantic_cross_field_rules':'Covered separately by author contract tests; not expressible by this JSON Schema subset','jsonschema_version':importlib.metadata.version('jsonschema'),'failures':failures}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if failures else 0

if __name__=='__main__':raise SystemExit(main())
