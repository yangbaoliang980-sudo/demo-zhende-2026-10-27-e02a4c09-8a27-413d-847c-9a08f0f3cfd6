"""CLI for synthetic JSONL only. No network, Anki imports, or persistent writes."""
import argparse
import json
import sys
from pathlib import Path
from pos_mapper import load_rules, strict_json, classify, ContractError

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,help='JSONL records, or case objects with input')
    p.add_argument('--rules',required=True)
    p.add_argument('--rules-sha256',required=True)
    p.add_argument('--rules-version',required=True)
    p.add_argument('--profile',required=True)
    p.add_argument('--overrides')
    args=p.parse_args()
    try:
        rules=load_rules(args.rules,args.rules_sha256,args.rules_version)
        profile=strict_json(Path(args.profile).read_bytes())
        overrides=[strict_json(s) for s in Path(args.overrides).read_text().splitlines() if s.strip()] if args.overrides else None
        for line in Path(args.input).read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            obj=strict_json(line)
            record=obj.get('input',obj) if isinstance(obj,dict) else obj
            print(json.dumps(classify(record,rules,profile,overrides),ensure_ascii=False))
    except (OSError,ContractError) as exc:
        print(json.dumps({'status':'BLOCKED','reason_code':str(exc) if isinstance(exc,ContractError) else 'LOCAL_FILE_UNAVAILABLE','production_award_authorized':False}),file=sys.stderr)
        return 3
    return 0

if __name__=='__main__':sys.exit(main())
