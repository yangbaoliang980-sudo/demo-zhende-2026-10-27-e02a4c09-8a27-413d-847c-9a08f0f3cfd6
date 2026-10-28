"""Capture real subprocess bytes/return code and tested-source hashes. No PASS forgery."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--cwd');p.add_argument('--timeout',type=int,default=60);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',a.label):raise ValueError('INVALID_LABEL')
    command=a.command[1:] if a.command and a.command[0]=='--' else a.command
    if not command:raise ValueError('COMMAND_REQUIRED')
    out=ROOT/'architecture/evidence/runs'/a.label;out.mkdir(parents=True,exist_ok=False)
    cwd=Path(a.cwd).resolve() if a.cwd else ROOT
    source=[]
    for f in sorted(cwd.rglob('*')):
        if not f.is_file() or f.suffix not in {'.py','.json','.js'} or any(x in f.parts for x in ['evidence','__pycache__','devdeps']):continue
        source.append({'relative_path':str(f.relative_to(cwd)),'size_bytes':f.stat().st_size,'sha256':sha(f)})
    (out/'source_hashes.json').write_text(json.dumps(source,indent=2)+'\n')
    with zipfile.ZipFile(out/'executed_sources.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for item in source:z.write(cwd/item['relative_path'],item['relative_path'])
    start=now();timed_out=False
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    try:
        r=subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=a.timeout)
        code=r.returncode;stdout=r.stdout;stderr=r.stderr
    except subprocess.TimeoutExpired as exc:
        code=None;stdout=exc.stdout or b'';stderr=exc.stderr or b'';timed_out=True
    except OSError as exc:
        code=None;stdout=b'';stderr=str(exc).encode()
    (out/'stdout.log').write_bytes(stdout);(out/'stderr.log').write_bytes(stderr)
    result={'schema_version':'P13-RUN-RECEIPT/0.1.0','label':a.label,'cwd':str(cwd),'command_argv':command,'started_at_utc':start,'ended_at_utc':now(),'exit_code':code,'timed_out':timed_out,'process_status':'EXITED_ZERO' if code==0 else 'EXITED_NONZERO' if code is not None else 'NOT_COMPLETED','python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'source_hashes_sha256':sha(out/'source_hashes.json'),'executed_sources_sha256':sha(out/'executed_sources.zip'),'stdout_sha256':sha(out/'stdout.log'),'stderr_sha256':sha(out/'stderr.log'),'stdout_bytes':len(stdout),'stderr_bytes':len(stderr),'interpretation':'See verification_status.json; exit 3 on preflight/probe means BLOCKED, not a runtime PASS.'}
    (out/'run_receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False));sys.stdout.buffer.write(stdout[-6000:]);sys.stderr.buffer.write(stderr[-10000:])
    return 0 if code==0 else 3 if code==3 else 1

if __name__=='__main__':raise SystemExit(main())
