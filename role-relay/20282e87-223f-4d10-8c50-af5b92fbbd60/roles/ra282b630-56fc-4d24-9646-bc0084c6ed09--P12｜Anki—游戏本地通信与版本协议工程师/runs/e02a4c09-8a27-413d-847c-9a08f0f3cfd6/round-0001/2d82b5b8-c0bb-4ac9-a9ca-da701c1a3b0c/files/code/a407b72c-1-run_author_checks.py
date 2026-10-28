"""Run author checks into a NEW output directory; never overwrite archived evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(parents=True,exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    source_paths = [p for base in ('ledger_runtime','tests','verification','sources')
                    for p in sorted((root/base).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    source_paths += [root/x for x in ('event_replay_fixtures.json','source_input_receipt.json','formal_prerequisites.json')]
    hashes = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    (target/'input_hashes.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    commands = [('unit',[sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_*.py','-v']),
                ('replay',[sys.executable,'-B','-m','verification.replay','--output',str(target/'replay')]),
                ('preflight',[sys.executable,'-B','-m','ledger_runtime','preflight'])]
    records = []
    for name,command in commands:
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(command,cwd=root,capture_output=True,text=True)
        (target/(name+'.stdout.log')).write_text(result.stdout)
        (target/(name+'.stderr.log')).write_text(result.stderr)
        status = 'BLOCKED' if name=='preflight' and result.returncode==3 else 'PASS' if result.returncode==0 else 'FAIL'
        records.append({'name':name,'command':command,'started_at_utc':start,
                        'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        'exit_code':result.returncode,'status':status})
        print(json.dumps({'check':name,'status':status,'exit_code':result.returncode}),flush=True)
    value = {'schema_version':'P11-AUTHOR-RUN/0.1.0','scope':'AUTHOR_ONLY_NOT_INDEPENDENT',
             'python':sys.version,'host':platform.platform(),'runs':records,
             'production_awards':0,'formal_contract':'NOT_RUN','real_anki':'NOT_RUN',
             'p32_independent':'NOT_RUN','p35_independent':'NOT_RUN'}
    (target/'run_receipt.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return 1 if any(x['status']=='FAIL' for x in records) else 3


if __name__ == '__main__':
    sys.exit(main())
